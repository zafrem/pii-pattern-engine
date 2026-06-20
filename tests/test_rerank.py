"""
Integration tests for the PII re-rank scoring system.

Scoring formula (re-rank/scoring.yml):
    final_score = min(keyword_avg + context_bonus + regex_score, 100)

    keyword_avg   = average score of every keyword that matched in the sentence
    context_bonus = highest flat bonus when a labeled field prefix is detected
    regex_score   = score of the matched regex pattern (0 if no match)

Test structure:
    - ReRankScorer  — loads all YAML data and computes scores
    - TestReRankEngine — structural/config tests
    - TestReRankSentences — parametrized sentence-level integration tests
    - TestReRankEdgeCases — boundary and multi-keyword averaging tests
    - TestReRankSumExamples — verifies arithmetic in every YAML sum_example block
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import pytest
import yaml

ROOT = Path(__file__).parent.parent

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — load YAML data
# ─────────────────────────────────────────────────────────────────────────────

def _load_engine() -> dict:
    return yaml.safe_load((ROOT / "re-rank" / "scoring.yml").read_text(encoding="utf-8"))


def _load_rerank_entities() -> Dict[int, dict]:
    """Load all entity scoring configs keyed by integer reference code."""
    entities: Dict[int, dict] = {}
    for f in sorted((ROOT / "re-rank").glob("*.yml")):
        if f.name == "scoring.yml":
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        for code, cfg in data.get("entities", {}).items():
            entities[int(code)] = cfg
    return entities


def _load_regex_patterns() -> Dict[str, List[re.Pattern]]:
    """
    Load every regex pattern from regex/**/*.yml.
    Returns {pattern_id: [compiled, ...]} — multiple per id when the same
    pattern_id appears in several region files (e.g. passport_01).
    """
    patterns: Dict[str, List[re.Pattern]] = defaultdict(list)
    for f in (ROOT / "regex").rglob("*.yml"):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        if not data or "patterns" not in data:
            continue
        for p in data["patterns"]:
            pid = p.get("id")
            if not pid:
                continue
            src = p.get("pattern", "")
            if "langs" in p and "python" in p["langs"]:
                src = p["langs"]["python"]
            flags = 0
            for flag in p.get("flags", []):
                if flag in ("IGNORECASE", "I"):
                    flags |= re.IGNORECASE
                elif flag in ("MULTILINE", "M"):
                    flags |= re.MULTILINE
                elif flag in ("DOTALL", "S"):
                    flags |= re.DOTALL
            try:
                patterns[pid].append(re.compile(src, flags))
            except re.error:
                pass
    return dict(patterns)


# ─────────────────────────────────────────────────────────────────────────────
# Scorer
# ─────────────────────────────────────────────────────────────────────────────

class ReRankScorer:
    """
    Lightweight implementation of the re-rank summed-score formula.

    Does NOT apply verification functions (checksum, entropy checks).
    Those are tested separately in test_verification.py and test_patterns.py.
    """

    def __init__(self):
        engine = _load_engine()
        self.thresholds: list = engine["thresholds"]
        self.entities: Dict[int, dict] = _load_rerank_entities()
        self.regex_patterns: Dict[str, List[re.Pattern]] = _load_regex_patterns()

    # ── public API ──────────────────────────────────────────────────────────

    def score(self, sentence: str, entity_code: int) -> dict:
        """
        Score a sentence against one entity and return a full breakdown dict.

        Raises KeyError if entity_code is not in the registry.
        """
        entity = self.entities[entity_code]
        s_lower = sentence.lower()

        keyword_avg, keyword_hits = self._keyword_score(entity, s_lower)
        context_bonus = self._context_bonus(entity, s_lower)
        regex_score, regex_hit = self._regex_score(entity, sentence)

        raw = keyword_avg + context_bonus + regex_score
        final = min(raw, 100.0)

        return {
            "entity_code": entity_code,
            "entity": entity.get("entity", ""),
            "keyword_hits": keyword_hits,
            "keyword_avg": round(keyword_avg, 2),
            "context_bonus": context_bonus,
            "regex_hit": regex_hit,
            "regex_score": regex_score,
            "raw_score": round(raw, 2),
            "final_score": round(final, 2),
            "label": self._label(final),
        }

    def label_for(self, sentence: str, entity_code: int) -> str:
        return self.score(sentence, entity_code)["label"]

    # ── internals ───────────────────────────────────────────────────────────

    def _keyword_score(self, entity: dict, s_lower: str):
        hits = [
            (kw, sc)
            for kw, sc in entity.get("keyword_scores", {}).items()
            if kw.lower() in s_lower
        ]
        avg = sum(sc for _, sc in hits) / len(hits) if hits else 0.0
        return avg, hits

    def _context_bonus(self, entity: dict, s_lower: str) -> int:
        return max(
            (bonus
             for ctx, bonus in entity.get("context_bonus", {}).items()
             if ctx.lower() in s_lower),
            default=0,
        )

    def _regex_score(self, entity: dict, sentence: str):
        best_score = 0
        best_pid = None
        for pid, pid_score in entity.get("regex_scores", {}).items():
            if pid == "default":
                continue  # 'default' requires source-file resolution; skipped here
            for compiled in self.regex_patterns.get(pid, []):
                if compiled.search(sentence):
                    if pid_score > best_score:
                        best_score = pid_score
                        best_pid = pid
                    break
        return best_score, best_pid

    def _label(self, score: float) -> str:
        for t in self.thresholds:
            if score >= t["min_score"]:
                return t["label"]
        return "not_pii"


# ─────────────────────────────────────────────────────────────────────────────
# Session-scoped fixture (loaded once for all tests)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def scorer() -> ReRankScorer:
    return ReRankScorer()


# ─────────────────────────────────────────────────────────────────────────────
# Parametrized sentence test cases
#
# Each tuple: (sentence, entity_code, expected_label, description)
#
# Score breakdown is shown in each docstring comment so failures are readable.
# ─────────────────────────────────────────────────────────────────────────────

SENTENCE_CASES = [

    # ── Korea ──────────────────────────────────────────────────────────────

    pytest.param(
        "이름: 김철수입니다",
        1001,
        "definite_pii",
        # keyword "이름"=50  → avg=50 | context "이름:"=+20 | regex name_01=+30
        # final = min(50+20+30, 100) = 100
        id="1001_kr_name__full_signal",
    ),
    pytest.param(
        "성명 김철수가 등록되어 있습니다",
        1001,
        "high_confidence_pii",
        # keyword "성명"=60  → avg=60 | no context | regex name_01=+30
        # final = 90
        id="1001_kr_name__no_context",
    ),
    pytest.param(
        "주민등록번호: 900101-1234568",
        1002,
        "definite_pii",
        # keyword "주민등록번호"=90 → avg=90 | context=+40 | regex rrn_01=+50
        # final = min(180, 100) = 100
        id="1002_kr_rrn__full_signal",
    ),
    pytest.param(
        "주민번호를 입력해주세요",
        1002,
        "high_confidence_pii",
        # keyword "주민번호"=90 → avg=90 | no context | no regex (no number)
        # final = 90
        id="1002_kr_rrn__keyword_only",
    ),
    pytest.param(
        "외국인등록번호: 900101-5234561",
        1003,
        "definite_pii",
        # keyword "외국인등록번호"=90 → avg=90 | context=+40 | regex alien_01=+50
        # final = min(180, 100) = 100
        id="1003_kr_alien_registration__full_signal",
    ),
    pytest.param(
        "휴대폰 전화번호: 010-1234-5678",
        1006,
        "definite_pii",
        # keywords "휴대폰"=70,"전화번호"=70 → avg=70 | context=+25 | mobile_01=+40
        # final = min(135, 100) = 100
        id="1006_kr_phone_mobile__full_signal",
    ),
    pytest.param(
        "전화번호가 필요합니다",
        1006,
        "probable_pii",
        # keyword "전화번호"=70 → avg=70 | no context | no regex (no number)
        # final = 70
        id="1006_kr_phone_mobile__keyword_only",
    ),
    pytest.param(
        "주소: 서울특별시 강남구 역삼동",
        1008,
        "definite_pii",
        # keyword "주소"=55 → avg=55 | context=+25 | regex address_01=+40
        # final = min(120, 100) = 100
        id="1008_kr_address__full_signal",
    ),
    pytest.param(
        "사업자등록번호: 123-45-67891",
        1010,
        "definite_pii",
        # keyword "사업자등록번호"=90 → avg=90 | context=+40 | business_registration_01=+45
        # final = min(175, 100) = 100
        id="1010_kr_business_registration__full_signal",
    ),

    # ── Japan ──────────────────────────────────────────────────────────────

    pytest.param(
        "氏名: 田中太郎",
        2001,
        "definite_pii",
        # keyword "氏名"=60 → avg=60 | context "氏名:"=+20 | kanji_01=+30
        # final = min(110, 100) = 100
        id="2001_jp_name_kanji__full_signal",
    ),
    pytest.param(
        "フリガナ: タナカタロウ",
        2003,
        "definite_pii",
        # keyword "フリガナ"=65 → avg=65 | context "フリガナ:"=+25 | katakana_01=+30
        # final = min(120, 100) = 100
        id="2003_jp_name_katakana__full_signal",
    ),
    pytest.param(
        "マイナンバー: 1234-5678-9018",
        2004,
        "definite_pii",
        # keyword "マイナンバー"=90 → avg=90 | context=+40 | my_number_01=+50
        # final = min(180, 100) = 100
        id="2004_jp_my_number__full_signal",
    ),
    pytest.param(
        "マイナンバーが必要です",
        2004,
        "high_confidence_pii",
        # keyword "マイナンバー"=90 → avg=90 | no context | no regex
        # final = 90
        id="2004_jp_my_number__keyword_only",
    ),

    # ── China ──────────────────────────────────────────────────────────────

    pytest.param(
        "姓名: 王小明",
        3001,
        "definite_pii",
        # keyword "姓名"=60 → avg=60 | context "姓名:"=+20 | chinese_name_01=+30
        # final = min(110, 100) = 100
        id="3001_cn_name__full_signal",
    ),
    pytest.param(
        "身份证号: 110101199001011234",
        3002,
        "definite_pii",
        # keyword "身份证号"=90 → avg=90 | context "身份证号:"=+40 | national_id_01=+50
        # final = min(180, 100) = 100
        id="3002_cn_national_id__full_signal",
    ),
    pytest.param(
        "联系电话: 13812345678",
        3004,
        "definite_pii",
        # keyword "联系电话"=70 → avg=70 | context=+25 | mobile_01=+40
        # final = min(135, 100) = 100
        id="3004_cn_phone_mobile__full_signal",
    ),

    # ── Taiwan ─────────────────────────────────────────────────────────────

    pytest.param(
        "統一編號: 12345678",
        4007,
        "definite_pii",
        # keyword "統一編號"=90 → avg=90 | context=+40 | business_id_01=+40
        # final = min(170, 100) = 100
        id="4007_tw_business_id__full_signal",
    ),

    # ── United States ──────────────────────────────────────────────────────

    pytest.param(
        "SSN: 123-45-6789",
        5002,
        "definite_pii",
        # keyword "ssn"=85 → avg=85 | context "ssn:"=+35 | ssn_01=+50
        # final = min(170, 100) = 100
        id="5002_us_ssn__full_signal",
    ),
    pytest.param(
        "Social Security Number: 987-65-4321",
        5002,
        "definite_pii",
        # keywords "social security"=85,"social security number"=90 → avg=87.5
        # context "social security number:"=+40 | ssn_01=+50
        # final = min(177.5, 100) = 100
        id="5002_us_ssn__long_label",
    ),
    pytest.param(
        "Please use ITIN 900-12-3456 for your taxes",
        5003,
        "definite_pii",
        # keyword "itin"=85 → avg=85 | no context | itin_01=+50
        # final = min(135, 100) = 100
        id="5003_us_itin__keyword_and_regex",
    ),
    pytest.param(
        "Phone: 212-555-0100",
        5007,
        "definite_pii",
        # keyword "phone"=55 → avg=55 | context "phone:"=+20 | phone_01=+40
        # final = min(115, 100) = 100
        id="5007_us_phone__full_signal",
    ),

    # ── European Union ─────────────────────────────────────────────────────

    pytest.param(
        "IBAN: GB29NWBK60161331926819",
        6053,
        "definite_pii",
        # keyword "iban"=85 → avg=85 | context "iban:"=+35 | iban_gb_01=+50
        # final = min(170, 100) = 100
        id="6053_iban_gb__full_signal",
    ),
    pytest.param(
        "Ihre PESEL-Nummer: 44051401458",
        6008,
        "definite_pii",
        # keyword "pesel"=90 → avg=90 | context "pesel:"=+40 | poland_pesel_01=+50
        # final = min(180, 100) = 100
        id="6008_eu_id_poland__full_signal",
    ),
    pytest.param(
        "BSN: 123456782",
        6006,
        "definite_pii",
        # keyword "bsn"=85 → avg=85 | context "bsn:"=+35 | netherlands_bsn_01=+50
        # final = min(170, 100) = 100
        id="6006_eu_id_netherlands__full_signal",
    ),

    # ── India ──────────────────────────────────────────────────────────────

    pytest.param(
        "Aadhaar: 2345 6789 0123",
        7001,
        "definite_pii",
        # keyword "aadhaar"=90 → avg=90 | context "aadhaar:"=+40 | aadhaar_01=+50
        # final = min(180, 100) = 100
        id="7001_in_aadhaar__full_signal",
    ),
    pytest.param(
        "PAN Card: ABCDE1234F",
        7002,
        "definite_pii",
        # keyword "pan card"=90 → avg=90 | context "pan card:"=+40 | pan_01=+50
        # final = min(180, 100) = 100
        id="7002_in_pan__full_signal",
    ),
    pytest.param(
        "IFSC Code: SBIN0001234",
        7008,
        "definite_pii",
        # keyword "ifsc code"=90 → avg=90 | context "ifsc code:"=+40 | ifsc_01=+50
        # final = min(180, 100) = 100
        id="7008_in_ifsc__full_signal",
    ),

    # ── Spain / France ─────────────────────────────────────────────────────

    pytest.param(
        "DNI: 12345678Z",
        8001,
        "definite_pii",
        # keyword "dni"=85 → avg=85 | context "dni:"=+35 | dni_01=+50
        # final = min(170, 100) = 100
        id="8001_es_dni__full_signal",
    ),
    pytest.param(
        "NIR: 1 85 12 75 116 001 98",
        8051,
        "definite_pii",
        # keyword "nir"=85 → avg=85 | context "nir:"=+35 | nir_01=+50
        # final = min(170, 100) = 100
        id="8051_fr_nir__full_signal",
    ),

    # ── Common / International ─────────────────────────────────────────────

    pytest.param(
        "이메일: john.doe@example.com 으로 연락해주세요",
        9001,
        "definite_pii",
        # keyword "이메일"=60 → avg=60 | context "이메일:"=+25 | email_01=+50
        # final = min(135, 100) = 100
        id="9001_email__korean_label",
    ),
    pytest.param(
        "Email: alice@company.org",
        9001,
        "definite_pii",
        # keyword "email"=60 → avg=60 | context "email:"=+25 | email_01=+50
        # final = min(135, 100) = 100
        id="9001_email__english_label",
    ),
    pytest.param(
        "Please contact user@example.com for details",
        9001,
        "possible_pii",
        # no keywords match | no context | regex email_01=+50
        # final = 50
        id="9001_email__regex_only",
    ),
    pytest.param(
        "The weather is beautiful today",
        9001,
        "not_pii",
        # no keywords | no context | no regex match
        # final = 0
        id="9001_email__no_signal",
    ),
    pytest.param(
        "카드번호: 4532015112830366",
        9008,
        "definite_pii",
        # keyword "카드번호"=70 → avg=70 | context "카드번호:"=+30 | visa_01=+50
        # final = min(150, 100) = 100
        id="9008_visa__korean_label",
    ),
    pytest.param(
        "Card Number: 4532015112830366",
        9008,
        "definite_pii",
        # keyword "card number"=70 → avg=70 | context "card number:"=+30 | visa_01=+50
        # final = min(150, 100) = 100
        id="9008_visa__english_label",
    ),
    pytest.param(
        "IP Address: 192.168.1.100",
        9005,
        "definite_pii",
        # keyword "ip address"=65 → avg=65 | context "ip address:"=+30 | ipv4_01=+40
        # final = min(135, 100) = 100
        id="9005_ipv4__full_signal",
    ),
    pytest.param(
        "Server IP is 10.0.0.1",
        9005,
        "high_confidence_pii",
        # keywords "ip"=50, "server"=30 → avg=40 | no context | ipv4_01=+40
        # final = 80 → high_confidence_pii
        id="9005_ipv4__partial_context",
    ),

    # ── Tech / Tokens ──────────────────────────────────────────────────────

    pytest.param(
        "AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE",
        9502,
        "definite_pii",
        # keyword "aws_access_key_id"=90,"aws"=70,"access key"=80 → avg=80
        # context "aws_access_key_id:"=+40 | aws_access_key_01=+60
        # final = min(180, 100) = 100
        id="9502_aws_access_key__full_signal",
    ),
    pytest.param(
        "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc",
        9506,
        "definite_pii",
        # keyword "bearer"=70,"authorization"=65 → avg=67.5
        # context "authorization:"=+25 | jwt_token_01=+55
        # final = min(147.5, 100) = 100
        id="9506_jwt__auth_header",
    ),

    # ── Korea — additional entities ────────────────────────────────────────

    pytest.param(
        "운전면허번호: 12-00-123456-10",
        1005,
        "definite_pii",
        # keyword "운전면허"=80,"면허번호"=80 → avg=80 | context "운전면허번호:"=+35 | driver_license_01=+45
        # final = min(160, 100) = 100
        id="1005_kr_driver_license__full_signal",
    ),
    pytest.param(
        "전화번호: 02-1234-5678",
        1007,
        "definite_pii",
        # keyword "전화"=55,"전화번호"=70 → avg=62.5 | no context | landline_01=+40
        # final = min(102.5, 100) = 100
        id="1007_kr_phone_landline__full_signal",
    ),
    pytest.param(
        "법인등록번호: 110111-1234567",
        1011,
        "definite_pii",
        # keyword "법인등록번호"=85,"법인등록"=80,"법인"=65 → avg=76.7 | context "법인등록번호:"=+40 | corporate_registration_01=+45
        # final = min(161.7, 100) = 100
        id="1011_kr_corporate_registration__full_signal",
    ),
    pytest.param(
        "차량번호: 123가4567",
        1013,
        "definite_pii",
        # keyword "차량번호"=80 → avg=80 | context "차량번호:"=+30 | default regex skipped → rx=0
        # final = min(110, 100) = 100
        id="1013_kr_vehicle_registration__keyword_context",
    ),
    pytest.param(
        "개인통관고유부호: P123456789012",
        1012,
        "definite_pii",
        # keyword "개인통관고유부호"=90,"개인통관"=80 → avg=85 | context "개인통관고유부호:"=+40 | personal_customs_code_01=+45
        # final = min(170, 100) = 100
        id="1012_kr_personal_customs_code__full_signal",
    ),

    # ── Japan — additional entities ────────────────────────────────────────

    pytest.param(
        "ふりがな: たなか たろう",
        2002,
        "definite_pii",
        # keyword "ふりがな"=60 → avg=65 | context "ふりがな:"=+25 | japanese_name_hiragana_01=+30
        # final = min(120, 100) = 100
        id="2002_jp_name_hiragana__full_signal",
    ),
    pytest.param(
        "携帯電話: 090-1234-5678",
        2007,
        "definite_pii",
        # keyword "携帯"=55,"携帯電話"=70,"電話"=50 → avg=58.3 | no context | mobile_01=+40
        # "携帯電話:" not in context_bonus → ctx=0 (no exact match with colon)
        # final = min(103, 100) = 100
        id="2007_jp_phone_mobile__full_signal",
    ),
    pytest.param(
        "固定電話: 03-1234-5678",
        2008,
        "definite_pii",
        # keyword "電話"=50,"固定電話"=70 → avg=60 | context "固定電話:"=+20 | landline_01=+40
        # final = min(120, 100) = 100
        id="2008_jp_phone_landline__full_signal",
    ),
    pytest.param(
        "住所: 東京都渋谷区神南1-2-3",
        2009,
        "definite_pii",
        # keyword "住所"=55 → avg=55 | context "住所:"=+25 | address_simple_01=+40
        # final = min(120, 100) = 100
        id="2009_jp_address__full_signal",
    ),
    pytest.param(
        "口座番号: 110-123-1234567",
        2010,
        "definite_pii",
        # keyword "口座番号"=80,"口座"=70 → avg=75 | context "口座番号:"=+30 | no regex (pattern missing) → rx=0
        # final = min(105, 100) = 100
        id="2010_jp_bank_account__keyword_context",
    ),
    pytest.param(
        "パスポート番号: TK1234567",
        2005,
        "definite_pii",
        # keyword "パスポート"=80,"パスポート番号"=85 → avg=82.5 (rounded 85) | context "パスポート番号:"=+35 | passport_01=+45
        # final = min(165, 100) = 100
        id="2005_jp_passport__full_signal",
    ),

    # ── China — additional entities ────────────────────────────────────────

    pytest.param(
        "护照号码: G12345678",
        3003,
        "definite_pii",
        # keyword "护照"=80,"护照号码"=90,"护照号"=85 → avg=85 | context "护照号码:"=+35 | passport_01=+45
        # final = min(165, 100) = 100
        id="3003_cn_passport__full_signal",
    ),
    pytest.param(
        "固定电话: 010-1234-5678",
        3005,
        "definite_pii",
        # keyword "电话"=55,"固定电话"=65 → avg=60 | context "固定电话:"=+20 | landline_01=+40
        # final = min(120, 100) = 100
        id="3005_cn_phone_landline__full_signal",
    ),

    # ── United States — additional entities ───────────────────────────────

    pytest.param(
        "Passport Number: A12345678",
        5004,
        "definite_pii",
        # keyword "passport"=75,"passport number"=85 → avg=80 | context "passport number:"=+35 | passport_01=+45
        # final = min(160, 100) = 100
        id="5004_us_passport__full_signal",
    ),
    pytest.param(
        "Name: John Smith",
        5001,
        "high_confidence_pii",
        # keyword "name"=40 → avg=40 | context "name:"=+15 | name_en_01=+30
        # final = 85 → high_confidence_pii
        id="5001_us_name__partial_signal",
    ),

    # ── EU — IBAN variants ─────────────────────────────────────────────────

    pytest.param(
        "IBAN: DE89370400440532013000",
        6051,
        "definite_pii",
        # keyword "iban"=85 → avg=85 | context "iban:"=+35 | iban_de_01=+50
        # final = min(170, 100) = 100
        id="6051_iban_de__full_signal",
    ),
    pytest.param(
        "IBAN: FR7614508059471840011210606",
        6052,
        "definite_pii",
        # keyword "iban"=85 → avg=85 | context "iban:"=+35 | iban_fr_01=+50
        # final = min(170, 100) = 100
        id="6052_iban_fr__full_signal",
    ),

    # ── India — additional entities ────────────────────────────────────────

    pytest.param(
        "Voter ID: ABC1234567",
        7004,
        "definite_pii",
        # keyword "voter id"=85 → avg=85 | context "voter id:"=+35 | voter_id_01=+45
        # final = min(165, 100) = 100
        id="7004_in_voter_id__full_signal",
    ),
    pytest.param(
        "GSTIN: 22AAAAA0000A1Z5",
        7009,
        "definite_pii",
        # keyword "gst"=80,"gstin"=85 → avg=82.5 | context "gstin:"=+40 | gst_01=+45
        # final = min(167.5, 100) = 100
        id="7009_in_gst__full_signal",
    ),
    pytest.param(
        "Mobile: +91 98765 43210",
        7006,
        "high_confidence_pii",
        # keyword "mobile"=60 → avg=60 | context "mobile:"=+20 | mobile_01 no match for +91 format → rx=0
        # final = 80 → high_confidence_pii
        id="7006_in_phone_mobile__keyword_context",
    ),

    # ── Spain / France — additional entities ──────────────────────────────

    pytest.param(
        "NIE: X1234567L",
        8002,
        "definite_pii",
        # keyword "nie"=85 → avg=85 | context "nie:"=+35 | nie_01=+50
        # final = min(170, 100) = 100
        id="8002_es_nie__full_signal",
    ),
    pytest.param(
        "CIF: A12345678",
        8004,
        "definite_pii",
        # keyword "cif"=85 → avg=85 | context "cif:"=+35 | cif_01=+50
        # final = min(170, 100) = 100
        id="8004_es_cif__full_signal",
    ),
    pytest.param(
        "Téléphone: 0612345678",
        8054,
        "definite_pii",
        # keyword "téléphone"=55,"tél"=50 → avg=52.5 | context "téléphone:"=+20 | phone_01=+40
        # final = min(112.5, 100) = 100
        id="8054_fr_phone__full_signal",
    ),
    pytest.param(
        "Passeport: 12AB34567",
        8053,
        "definite_pii",
        # keyword "passeport"=85 → avg=85 | context "passeport:"=+35 | passport_01=+45
        # final = min(165, 100) = 100
        id="8053_fr_passport__full_signal",
    ),

    # ── Common — additional entities ──────────────────────────────────────

    pytest.param(
        "Date of Birth: 1990-01-15",
        9003,
        "definite_pii",
        # keyword "date of birth"=80 → avg=80 | context "date of birth:"=+35 | date_iso_01=+40
        # final = min(155, 100) = 100
        id="9003_date_iso__full_signal",
    ),
    pytest.param(
        "DOB: 25/12/1990",
        9004,
        "definite_pii",
        # keyword "dob"=75 → avg=75 | context "dob:"=+30 | date_slash_01 no match (DD/MM/YYYY) → rx=0
        # final = min(105, 100) = 100
        id="9004_date_slash__keyword_context",
    ),
    pytest.param(
        "URL: https://example.com/profile",
        9007,
        "definite_pii",
        # keyword "url"=55,"https"=50,"http"=50 → avg=51.7 | context "url:"=+20 | url_01=+30
        # final = min(101.7, 100) = 100
        id="9007_url__full_signal",
    ),
    pytest.param(
        "Card Number: 5425233430109903",
        9009,
        "definite_pii",
        # keyword "card number"=70 → avg=70 | context "card number:"=+30 | credit_card_mastercard_01=+50
        # final = min(150, 100) = 100
        id="9009_mastercard__full_signal",
    ),
    pytest.param(
        "American Express: 371449635398431",
        9010,
        "definite_pii",
        # keyword "american express"=80 → avg=80 | no context | credit_card_amex_01=+50
        # final = min(130, 100) = 100
        id="9010_amex__full_signal",
    ),
    pytest.param(
        "IPv6: 2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        9006,
        "definite_pii",
        # keyword "ip"=50,"ipv6"=70 → avg=60 | no context | ipv6_01=+40
        # final = 100 (60+0+40)
        id="9006_ipv6__full_signal",
    ),

    # ── Tech — additional entities with full signal ───────────────────────

    pytest.param(
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        9503,
        "definite_pii",
        # keyword "aws"=70,"aws_secret_access_key"=90 → avg=80 | no context | aws_secret_key_01=+60
        # final = min(140, 100) = 100
        id="9503_aws_secret_key__env_var",
    ),
    pytest.param(
        "GITHUB_TOKEN=ghp_ABCDefghijklmnopqrstuvwxyz1234567890abcdef",
        9504,
        "definite_pii",
        # keyword "github"=70,"ghp"=85 → avg=77.5 | no context | github_token_01=+60
        # final = min(137.5, 100) = 100
        id="9504_github_token__env_var",
    ),
    pytest.param(
        "STRIPE_SECRET_KEY=sk_demo_ExAMPLEKEY1234567890abcdefgh12345",
        9505,
        "definite_pii",
        # keyword "stripe"=75 → avg=75 | no context | stripe_key_01=+60 (demo variant)
        # final = min(135, 100) = 100
        id="9505_stripe_key__env_var",
    ),
    pytest.param(
        "GOOGLE_API_KEY=AIzaSyDchDv11g0G4ygrk7g6E1MgY_3B2fGz7Hk",
        9508,
        "definite_pii",
        # keyword "aiza"=85 → avg=85 | no context | google_api_key_01=+60
        # final = min(145, 100) = 100
        id="9508_google_api_key__env_var",
    ),
    pytest.param(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEvgIBADANBgk=\n-----END RSA PRIVATE KEY-----",
        9510,
        "definite_pii",
        # keyword "private key"=85,"rsa"=70 → avg=77.5 | no context | private_key_01=+65
        # final = min(142.5, 100) = 100
        id="9510_private_key__pem_block",
    ),

    # ── Tech — bare token (regex only, no keyword/context signal) ─────────

    pytest.param(
        "rk_demo_AbcdefghijklmnopQRSTUVWXYZ12345678",
        9505,
        "probable_pii",
        # no keywords match | no context | stripe_key_01=+60 (demo variant)
        # final = 60 → probable_pii  (was possible_pii at score 50 before bump)
        id="9505_stripe_key__bare_token",
    ),
    pytest.param(
        "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        9503,
        "probable_pii",
        # no keywords match | no context | aws_secret_key_01=+60
        # final = 60 → probable_pii  (was possible_pii at score 50 before bump)
        id="9503_aws_secret_key__bare_token",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Test classes
# ─────────────────────────────────────────────────────────────────────────────

class TestReRankEngine:
    """Structural tests — engine config and YAML file validity."""

    def test_scoring_yml_loads(self):
        data = _load_engine()
        assert data["version"] == "2.0"
        assert "algorithm" in data
        assert "thresholds" in data
        assert "entity_index" in data

    def test_thresholds_are_descending(self):
        data = _load_engine()
        scores = [t["min_score"] for t in data["thresholds"]]
        assert scores == sorted(scores, reverse=True), "Thresholds must be in descending order"

    def test_thresholds_cover_zero(self):
        data = _load_engine()
        assert data["thresholds"][-1]["min_score"] == 0, "Last threshold must cover score 0"

    def test_all_regional_files_load(self):
        files = list((ROOT / "re-rank").glob("*.yml"))
        assert len(files) > 1, "Expected more than just scoring.yml"
        for f in files:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            assert data is not None, f"{f.name} failed to parse"

    def test_entity_index_references_existing_files(self):
        engine = _load_engine()
        for region, path in engine["entity_index"].items():
            full = ROOT / path
            assert full.exists(), f"entity_index entry '{region}' → '{path}' not found"

    def test_total_entity_count(self):
        entities = _load_rerank_entities()
        assert len(entities) == 153, f"Expected 153 entities, got {len(entities)}"

    def test_all_entity_codes_are_in_registry(self):
        registry = yaml.safe_load(
            (ROOT / "reference" / "registry.yml").read_text(encoding="utf-8")
        )
        registry_codes = {v for v in registry.values() if isinstance(v, int)}
        rerank_codes = set(_load_rerank_entities().keys())
        missing = rerank_codes - registry_codes
        assert not missing, f"re-rank codes not in registry: {sorted(missing)}"

    def test_no_duplicate_entity_codes(self):
        seen = []
        for f in (ROOT / "re-rank").glob("*.yml"):
            if f.name == "scoring.yml":
                continue
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            for code in data.get("entities", {}):
                seen.append((int(code), f.name))
        codes = [c for c, _ in seen]
        duplicates = [c for c in codes if codes.count(c) > 1]
        assert not duplicates, f"Duplicate entity codes found: {sorted(set(duplicates))}"

    def test_each_entity_has_required_keys(self):
        for code, cfg in _load_rerank_entities().items():
            assert "entity" in cfg,         f"Code {code}: missing 'entity'"
            assert "keyword_scores" in cfg,  f"Code {code}: missing 'keyword_scores'"
            assert "regex_scores" in cfg,    f"Code {code}: missing 'regex_scores'"
            assert "sum_example" in cfg,     f"Code {code}: missing 'sum_example'"


class TestReRankSumExamples:
    """Verify every sum_example block in every re-rank YAML file."""

    @pytest.mark.parametrize("entity_code,entity_cfg", _load_rerank_entities().items())
    def test_sum_example_arithmetic(self, entity_code, entity_cfg):
        ex = entity_cfg.get("sum_example", {})
        if not ex:
            pytest.skip("No sum_example")
        ka = ex.get("keyword_avg", 0)
        cb = ex.get("context_bonus", 0)
        rs = ex.get("regex_score", 0)
        declared = ex.get("final_score")
        expected = min(ka + cb + rs, 100)
        assert declared == expected, (
            f"Code {entity_code} ({entity_cfg.get('entity')}): "
            f"sum_example says final_score={declared} "
            f"but {ka} + {cb} + {rs} = {ka+cb+rs} → capped to {expected}"
        )

    @pytest.mark.parametrize("entity_code,entity_cfg", _load_rerank_entities().items())
    def test_sum_example_label_matches_thresholds(self, entity_code, entity_cfg):
        ex = entity_cfg.get("sum_example", {})
        if not ex:
            pytest.skip("No sum_example")
        declared_label = ex.get("label")
        if not declared_label:
            pytest.skip("No label in sum_example")
        engine = _load_engine()
        scorer_tmp = ReRankScorer()
        computed_label = scorer_tmp._label(ex["final_score"])
        assert declared_label == computed_label, (
            f"Code {entity_code}: sum_example label='{declared_label}' "
            f"but final_score={ex['final_score']} → computed='{computed_label}'"
        )


class TestReRankSentences:
    """
    Integration tests: score a natural-language sentence against one entity
    and verify the expected confidence label.
    """

    @pytest.mark.parametrize("sentence,entity_code,expected_label", SENTENCE_CASES)
    def test_sentence_label_named(self, scorer, sentence, entity_code, expected_label):
        """Same checks as test_sentence_label but with pytest IDs for readability."""
        result = scorer.score(sentence, entity_code)
        assert result["label"] == expected_label, (
            f"\nSentence : {sentence!r}"
            f"\nEntity   : {entity_code} ({result['entity']})"
            f"\nBreakdown: kw_avg={result['keyword_avg']} + ctx={result['context_bonus']}"
            f" + regex={result['regex_score']} = raw {result['raw_score']} → {result['final_score']}"
            f"\nExpected : {expected_label}  |  Got: {result['label']}"
        )


class TestReRankEdgeCases:
    """Edge cases: multi-keyword averaging, score capping, code lookup errors."""

    def test_multi_keyword_average(self, scorer):
        """
        "계좌번호 및 은행 정보" against kr_bank_account (1009).
        keywords: "계좌번호"=80, "계좌"=70 (substring), "은행"=55 → avg = 68.33
        no context | no regex  → final = 68.33 → probable_pii
        """
        result = scorer.score("계좌번호 및 은행 정보가 필요합니다", 1009)
        assert result["label"] == "probable_pii"
        assert result["keyword_avg"] == pytest.approx(68.33, abs=0.1)

    def test_keyword_only_high_confidence(self, scorer):
        """
        Strong keyword alone ("주민번호") should reach high_confidence_pii
        even without a regex match.
        """
        result = scorer.score("주민번호를 알고 싶습니다", 1002)
        assert result["label"] == "high_confidence_pii"
        assert result["regex_score"] == 0
        assert result["keyword_avg"] >= 80

    def test_regex_only_possible_pii(self, scorer):
        """
        An email address with no surrounding keyword context should be possible_pii.
        """
        result = scorer.score("send to noreply@service.io now", 9001)
        assert result["label"] == "possible_pii"
        assert result["keyword_avg"] == 0
        assert result["regex_score"] == 50

    def test_score_cap_at_100(self, scorer):
        """
        Even with massive combined signals, final_score must never exceed 100.
        """
        # "주민등록번호: 900101-1234568" → raw = 90+40+50 = 180
        result = scorer.score("주민등록번호: 900101-1234568", 1002)
        assert result["final_score"] <= 100
        assert result["raw_score"] > 100

    def test_no_signal_not_pii(self, scorer):
        """A generic sentence with no PII content should score 0."""
        result = scorer.score("Today is a great day for a walk in the park", 9001)
        assert result["final_score"] == 0
        assert result["label"] == "not_pii"

    def test_unknown_entity_code_raises(self, scorer):
        """Querying a non-existent entity code must raise KeyError."""
        with pytest.raises(KeyError):
            scorer.score("some text", 9999)

    def test_context_bonus_case_insensitive(self, scorer):
        """Context labels are matched case-insensitively."""
        # "ssn:" from context_bonus should match "SSN:" in sentence
        result_upper = scorer.score("SSN: 123-45-6789", 5002)
        result_lower = scorer.score("ssn: 123-45-6789", 5002)
        assert result_upper["context_bonus"] == result_lower["context_bonus"]
        assert result_upper["label"] == result_lower["label"]

    def test_highest_context_bonus_wins(self, scorer):
        """When multiple context labels match, the highest bonus applies."""
        # entity 5002 (us_ssn): "SSN:" → 35, "Social Security Number:" → 40
        only_ssn = scorer.score("SSN: 000-00-0001", 5002)
        both     = scorer.score("Social Security Number: SSN: 000-00-0001", 5002)
        assert both["context_bonus"] >= only_ssn["context_bonus"]

    def test_multiple_regex_ids_best_wins(self, scorer):
        """
        When an entity has several pattern IDs, the highest matching score applies.
        kr_phone_mobile has mobile_01 and mobile_02, both score 40.
        Either match is sufficient.
        """
        result = scorer.score("전화번호: 010-1234-5678", 1006)
        assert result["regex_score"] == 40
