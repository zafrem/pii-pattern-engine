#!/usr/bin/env python3
"""
Generate Instruction-Tuning Dataset for LLM PII Detection

Reads regex patterns from the YAML files in regex/ and generates:
1. NER (Named Entity Recognition): Detect and mask PII in text with BIO tags
2. Classification: Binary PII detection
3. Category: Identify PII type, region, and risk level

Key features:
- Validates every generated PII value against the actual regex pattern
- Seeds data from test vectors (examples.match) in YAML files
- Embeds PII in multilingual natural-language sentences (EN, KR, CN, JP)
- Produces BIO-tagged output for token-level NER training

Output: JSONL files in Llama 3 chat format for SFT fine-tuning.
"""

import csv
import json
import random
import re
import string
import sys
from collections import defaultdict
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
REGEX_DIR = PROJECT_ROOT / "regex"
DATA_DIR = PROJECT_ROOT / "datas"

random.seed(42)


# ===========================================================================
# 1. Load regex patterns and reference data
# ===========================================================================

def load_all_patterns():
    """Load every pattern from YAML files under regex/.

    Returns a list of dicts with keys:
        id, location, category, description, pattern, severity,
        mask, examples_match, examples_nomatch, _file
    """
    patterns = []
    for yml_path in sorted(REGEX_DIR.rglob("*.yml")):
        try:
            with open(yml_path, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
            if not doc or "patterns" not in doc:
                continue
            for p in doc["patterns"]:
                entry = {
                    "id": p.get("id", ""),
                    "location": p.get("location", doc.get("namespace", "")),
                    "category": p.get("category", ""),
                    "description": p.get("description", ""),
                    "pattern": p.get("pattern", ""),
                    "severity": (p.get("policy", {}) or {}).get("severity", "medium"),
                    "mask": p.get("mask", ""),
                    "examples_match": (p.get("examples", {}) or {}).get("match", []),
                    "examples_nomatch": (p.get("examples", {}) or {}).get("nomatch", []),
                    "_file": str(yml_path.relative_to(PROJECT_ROOT)),
                }
                patterns.append(entry)
        except Exception:
            continue
    return patterns


def load_csv_column(path, col=0):
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row and len(row) > col:
                rows.append(row[col].strip())
    return rows


def load_reference_data():
    data = {}
    if not DATA_DIR.exists():
        return data
    for fp in DATA_DIR.iterdir():
        if fp.suffix == ".csv":
            data[fp.stem] = load_csv_column(fp)
    return data


# ===========================================================================
# 2. PII value generators (validated against regex)
# ===========================================================================

def _rand_digits(n):
    return "".join(random.choices(string.digits, k=n))


def _rand_hex(n):
    return "".join(random.choices("0123456789abcdef", k=n))


def _rand_alnum(n):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _rand_date_yymmdd():
    y = random.randint(50, 99)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y:02d}{m:02d}{d:02d}"


def _rand_date_yyyymmdd():
    y = random.randint(1950, 2005)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}{m:02d}{d:02d}"


# Per-pattern-id generators producing a list of candidate values.
# Each function returns a list[str].

def _gen_us_ssn(n):
    out = []
    for _ in range(n):
        a = random.randint(1, 899)
        while a in (0, 666) or a >= 900:
            a = random.randint(1, 899)
        b = random.randint(1, 99)
        c = random.randint(1, 9999)
        fmt = random.choice(["{:03d}-{:02d}-{:04d}", "{:03d}{:02d}{:04d}"])
        out.append(fmt.format(a, b, c))
    return out


def _gen_us_itin(n):
    return [f"9{_rand_digits(2)}-{_rand_digits(2)}-{_rand_digits(4)}" for _ in range(n)]


def _gen_us_phone(n):
    out = []
    for _ in range(n):
        area = random.randint(200, 999)
        ex = random.randint(100, 999)
        sub = random.randint(0, 9999)
        fmt = random.choice([
            "({:03d}) {:03d}-{:04d}",
            "{:03d}-{:03d}-{:04d}",
            "+1-{:03d}-{:03d}-{:04d}",
            "+1 ({:03d}) {:03d}-{:04d}",
        ])
        out.append(fmt.format(area, ex, sub))
    return out


def _gen_email(n):
    users = ["john.doe", "jane_smith", "user123", "admin", "test.user", "info",
             "alice.b", "bob_c", "support", "dev", "hello", "noreply"]
    domains = ["example.com", "mail.org", "company.co.uk", "test.io", "gmail.com",
               "yahoo.com", "outlook.com", "proton.me", "fastmail.fm"]
    out = []
    for _ in range(n):
        u = random.choice(users)
        if random.random() < 0.3:
            u += "+" + _rand_alnum(3).lower()
        out.append(f"{u}@{random.choice(domains)}")
    return out


def _gen_visa(n):
    return ["4" + _rand_digits(15) for _ in range(n)]


def _gen_mastercard(n):
    return [f"5{random.randint(1,5)}" + _rand_digits(14) for _ in range(n)]


def _gen_amex(n):
    return [f"3{random.choice('47')}" + _rand_digits(13) for _ in range(n)]


def _gen_discover(n):
    out = []
    for _ in range(n):
        if random.random() < 0.5:
            out.append("6011" + _rand_digits(12))
        else:
            out.append(f"65{_rand_digits(2)}" + _rand_digits(12))
    return out


def _gen_jcb(n):
    return [f"35{_rand_digits(3)}" + _rand_digits(11) for _ in range(n)]


def _gen_diners(n):
    return [f"3{random.choice('0689')}" + _rand_digits(12) for _ in range(n)]


def _gen_ipv4(n):
    out = []
    for _ in range(n):
        octets = [random.randint(1, 254) for _ in range(4)]
        out.append(".".join(str(o) for o in octets))
    return out


def _gen_btc(n):
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return ["1" + "".join(random.choices(chars, k=random.randint(25, 34))) for _ in range(n)]


def _gen_eth(n):
    return ["0x" + _rand_hex(40) for _ in range(n)]


def _gen_aws_access_key(n):
    return [random.choice(["AKIA", "ASIA"]) + _rand_alnum(16) for _ in range(n)]


def _gen_google_api_key(n):
    chars = string.ascii_letters + string.digits + "-_"
    return ["AIza" + "".join(random.choices(chars, k=35)) for _ in range(n)]


def _gen_swift(n):
    out = []
    for _ in range(n):
        bank = "".join(random.choices(string.ascii_uppercase, k=4))
        cc = random.choice(["US", "GB", "DE", "FR", "JP", "KR", "CN"])
        loc = _rand_alnum(2)
        if random.random() < 0.5:
            out.append(bank + cc + loc + _rand_alnum(3))
        else:
            out.append(bank + cc + loc)
    return out


def _gen_ssh_private_key(n):
    types = ["RSA", "EC", "OPENSSH", "DSA"]
    return [f"-----BEGIN {random.choice(types)} PRIVATE KEY-----" for _ in range(n)]


def _gen_iban(n):
    countries = [("DE", 18), ("FR", 23), ("GB", 18), ("IT", 23), ("ES", 20)]
    out = []
    for _ in range(n):
        cc, rest_len = random.choice(countries)
        out.append(cc + _rand_digits(2) + _rand_alnum(rest_len))
    return out


def _gen_kr_rrn(n):
    out = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        gender = random.choice("1234")
        seq = _rand_digits(6)
        if random.random() < 0.7:
            out.append(f"{dt}-{gender}{seq}")
        else:
            out.append(f"{dt}{gender}{seq}")
    return out


def _gen_kr_alien(n):
    out = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        gender = random.choice("5678")
        seq = _rand_digits(6)
        out.append(f"{dt}-{gender}{seq}")
    return out


def _gen_kr_phone(n):
    out = []
    for _ in range(n):
        prefix = random.choice(["010", "011", "016", "017", "019"])
        mid = _rand_digits(random.choice([3, 4]))
        last = _rand_digits(4)
        fmt = random.choice(["{}-{}-{}", "{}{}{}"])
        out.append(fmt.format(prefix, mid, last))
    return out


def _gen_kr_landline(n):
    out = []
    for _ in range(n):
        area = random.choice(["02", "031", "032", "033", "041", "042", "043",
                               "044", "051", "052", "053", "054", "055",
                               "061", "062", "063", "064"])
        mid = _rand_digits(random.choice([3, 4]))
        last = _rand_digits(4)
        out.append(f"{area}-{mid}-{last}")
    return out


def _gen_kr_name(n, ref_data):
    surnames = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
                "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
    given = ref_data.get("kr_given_names", ["민수", "영희", "철수", "지현", "수진"])
    return [random.choice(surnames) + random.choice(given) for _ in range(n)]


def _gen_cn_national_id(n):
    out = []
    for _ in range(n):
        area = _rand_digits(6)
        birth = _rand_date_yyyymmdd()
        seq = _rand_digits(3)
        check = random.choice(string.digits + "X")
        out.append(area + birth + seq + check)
    return out


def _gen_cn_phone(n):
    out = []
    for _ in range(n):
        second = random.choice("3456789")
        rest = _rand_digits(9)
        if random.random() < 0.5:
            out.append(f"1{second}{rest[0]}-{rest[1:5]}-{rest[5:]}")
        else:
            out.append(f"1{second}{rest}")
    return out


def _gen_cn_name(n, ref_data):
    surnames = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
                "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
    given = ref_data.get("cn_given_names", ["小明", "小红", "伟", "芳", "丽"])
    return [random.choice(surnames) + random.choice(given) for _ in range(n)]


def _gen_cn_passport(n):
    return [random.choice("EG") + _rand_digits(8) for _ in range(n)]


def _gen_jp_my_number(n):
    out = []
    for _ in range(n):
        if random.random() < 0.5:
            out.append(_rand_digits(4) + "-" + _rand_digits(4) + "-" + _rand_digits(4))
        else:
            out.append(_rand_digits(12))
    return out


def _gen_jp_phone(n):
    out = []
    for _ in range(n):
        prefix = random.choice(["090", "080", "070"])
        mid = _rand_digits(4)
        last = _rand_digits(4)
        out.append(f"{prefix}-{mid}-{last}")
    return out


def _gen_jp_passport(n):
    return ["".join(random.choices(string.ascii_uppercase, k=2)) + _rand_digits(7)
            for _ in range(n)]


def _gen_jp_driver_license(n):
    out = []
    for _ in range(n):
        if random.random() < 0.5:
            out.append(_rand_digits(4) + "-" + _rand_digits(2) + "-" + _rand_digits(6))
        else:
            out.append(_rand_digits(12))
    return out


def _gen_tw_national_id(n):
    letters = [c for c in string.ascii_uppercase if c not in "IOW"]
    out = []
    for _ in range(n):
        letter = random.choice(letters)
        gender = random.choice("12")
        rest = _rand_digits(8)
        out.append(f"{letter}{gender}{rest}")
    return out


def _gen_tw_phone(n):
    out = []
    for _ in range(n):
        rest = _rand_digits(6)
        mid = _rand_digits(2)
        if random.random() < 0.5:
            out.append(f"09{mid}-{rest[:3]}-{rest[3:]}")
        else:
            out.append(f"09{mid}{rest}")
    return out


def _gen_in_aadhaar(n):
    out = []
    for _ in range(n):
        first = random.randint(2, 9)
        rest = _rand_digits(11)
        raw = str(first) + rest
        if random.random() < 0.5:
            out.append(f"{raw[:4]}-{raw[4:8]}-{raw[8:]}")
        else:
            out.append(raw)
    return out


def _gen_in_pan(n):
    return ["".join(random.choices(string.ascii_uppercase, k=5)) +
            _rand_digits(4) + random.choice(string.ascii_uppercase)
            for _ in range(n)]


def _gen_in_phone(n):
    return [str(random.choice([6, 7, 8, 9])) + _rand_digits(9) for _ in range(n)]


def _gen_in_passport(n):
    return [random.choice(string.ascii_uppercase) + _rand_digits(7) for _ in range(n)]


def _gen_in_voter_id(n):
    return ["".join(random.choices(string.ascii_uppercase, k=3)) + _rand_digits(7)
            for _ in range(n)]


def _gen_in_driving_license(n):
    states = ["DL", "MH", "KA", "TN", "AP", "UP", "GJ", "RJ", "WB", "MP"]
    out = []
    for _ in range(n):
        st = random.choice(states)
        rto = _rand_digits(2)
        year = str(random.randint(2010, 2024))
        serial = _rand_digits(7)
        out.append(st + rto + year + serial)
    return out


def _gen_eu_de_id(n):
    out = []
    for _ in range(n):
        s = _rand_alnum(9)
        while s.isdigit():
            s = _rand_alnum(9)
        out.append(s)
    return out


def _gen_eu_fr_insee(n):
    return [random.choice("12") + _rand_digits(14) for _ in range(n)]


def _gen_eu_it_cf(n):
    out = []
    for _ in range(n):
        letters1 = "".join(random.choices(string.ascii_uppercase, k=6))
        d1 = _rand_digits(2)
        l1 = random.choice(string.ascii_uppercase)
        d2 = _rand_digits(2)
        l2 = random.choice(string.ascii_uppercase)
        d3 = _rand_digits(3)
        l3 = random.choice(string.ascii_uppercase)
        out.append(letters1 + d1 + l1 + d2 + l2 + d3 + l3)
    return out


def _gen_eu_es_dni(n):
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    out = []
    for _ in range(n):
        num = random.randint(0, 99999999)
        letter = letters[num % 23]
        out.append(f"{num:08d}{letter}")
    return out


def _gen_eu_es_nie(n):
    out = []
    for _ in range(n):
        prefix = random.choice("XYZ")
        num = _rand_digits(7)
        letter = random.choice(string.ascii_uppercase)
        out.append(f"{prefix}{num}{letter}")
    return out


def _gen_eu_uk_nino(n):
    exclude = set("DFIQUV")
    letters = [c for c in string.ascii_uppercase if c not in exclude]
    out = []
    for _ in range(n):
        prefix = random.choice(letters) + random.choice(letters)
        suffix = random.choice("ABCD")
        out.append(prefix + _rand_digits(6) + suffix)
    return out


def _gen_eu_be_rrn(n):
    out = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        seq = _rand_digits(3)
        cc = _rand_digits(2)
        if random.random() < 0.5:
            out.append(f"{dt[:2]}.{dt[2:4]}.{dt[4:]}-{seq}-{cc}")
        else:
            out.append(dt + seq + cc)
    return out


def _gen_eu_pl_pesel(n):
    return [_rand_digits(11) for _ in range(n)]


def _gen_eu_se_personnummer(n):
    out = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        seq = _rand_digits(4)
        if random.random() < 0.5:
            out.append(f"{dt}-{seq}")
        else:
            out.append(dt + seq)
    return out


def _gen_eu_dk_cpr(n):
    out = []
    for _ in range(n):
        d = random.randint(1, 28)
        m = random.randint(1, 12)
        y = random.randint(50, 99)
        dt = f"{d:02d}{m:02d}{y:02d}"
        seq = _rand_digits(4)
        if random.random() < 0.5:
            out.append(f"{dt}-{seq}")
        else:
            out.append(dt + seq)
    return out


def _gen_eu_fi_hetu(n):
    out = []
    for _ in range(n):
        d = random.randint(1, 28)
        m = random.randint(1, 12)
        y = random.randint(50, 99)
        dt = f"{d:02d}{m:02d}{y:02d}"
        sep = random.choice(["+", "-", "A"])
        seq = _rand_digits(3)
        check_chars = "0123456789ABCDEFHJKLMNPRSTUVWXY"
        check = random.choice(check_chars)
        out.append(f"{dt}{sep}{seq}{check}")
    return out


def _gen_eu_pt_nif(n):
    return [str(random.randint(1, 3)) + _rand_digits(8) for _ in range(n)]


def _gen_eu_at_svnr(n):
    out = []
    for _ in range(n):
        serial = _rand_digits(4)
        d = random.randint(1, 28)
        m = random.randint(1, 12)
        y = random.randint(50, 99)
        dt = f"{d:02d}{m:02d}{y:02d}"
        if random.random() < 0.5:
            out.append(f"{serial} {dt}")
        else:
            out.append(serial + dt)
    return out


# ---- Korean bank account generators ----

def _gen_kr_bank_kookmin(n):
    prefixes = ["110", "120", "150", "190", "830"]
    out = []
    for _ in range(n):
        p = random.choice(prefixes)
        mid = _rand_digits(3)
        rest = _rand_digits(random.choice([6, 7]))
        if random.random() < 0.7:
            out.append(f"{p}-{mid}-{rest}")
        else:
            out.append(p + mid + rest)
    return out


def _gen_kr_bank_shinhan(n):
    out = []
    for _ in range(n):
        mid = _rand_digits(3)
        rest = _rand_digits(random.choice([6, 7]))
        if random.random() < 0.7:
            out.append(f"110-{mid}-{rest}")
        else:
            out.append("110" + mid + rest)
    return out


def _gen_kr_bank_woori(n):
    out = []
    for _ in range(n):
        mid = _rand_digits(3)
        rest = _rand_digits(random.choice([6, 7]))
        if random.random() < 0.7:
            out.append(f"1002-{mid}-{rest}")
        else:
            out.append("1002" + mid + rest)
    return out


def _gen_kr_bank_hana(n):
    out = []
    for _ in range(n):
        a = _rand_digits(3)
        b = _rand_digits(6)
        c = _rand_digits(random.choice([4, 5]))
        if random.random() < 0.7:
            out.append(f"{a}-{b}-{c}")
        else:
            out.append(a + b + c)
    return out


def _gen_kr_bank_nonghyup(n):
    out = []
    for _ in range(n):
        a = _rand_digits(4)
        b = _rand_digits(4)
        c = _rand_digits(2)
        if random.random() < 0.7:
            out.append(f"301-{a}-{b}-{c}")
        else:
            out.append("301" + a + b + c)
    return out


def _gen_kr_bank_ibk(n):
    out = []
    for _ in range(n):
        a = _rand_digits(3)
        b = _rand_digits(6)
        c = _rand_digits(2)
        d = _rand_digits(3)
        if random.random() < 0.7:
            out.append(f"{a}-{b}-{c}-{d}")
        else:
            out.append(a + b + c + d)
    return out


def _gen_kr_bank_sc(n):
    return [f"{_rand_digits(3)}-{_rand_digits(2)}-{_rand_digits(6)}" for _ in range(n)]


def _gen_kr_bank_citi(n):
    out = []
    for _ in range(n):
        a = _rand_digits(3)
        b = _rand_digits(5)
        c = _rand_digits(2)
        d = _rand_digits(3)
        if random.random() < 0.7:
            out.append(f"{a}-{b}-{c}-{d}")
        else:
            out.append(a + b + c + d)
    return out


def _gen_kr_bank_busan(n):
    out = []
    for _ in range(n):
        a = _rand_digits(3)
        b = _rand_digits(4)
        c = _rand_digits(4)
        d = _rand_digits(2)
        if random.random() < 0.7:
            out.append(f"{a}-{b}-{c}-{d}")
        else:
            out.append(a + b + c + d)
    return out


def _gen_kr_bank_daegu(n):
    return [f"{_rand_digits(3)}-{_rand_digits(2)}-{_rand_digits(6)}-{_rand_digits(1)}"
            for _ in range(n)]


def _gen_kr_bank_gwangju(n):
    return [f"{_rand_digits(3)}-{_rand_digits(3)}-{_rand_digits(6)}" for _ in range(n)]


def _gen_kr_bank_jeonbuk(n):
    return [f"{_rand_digits(3)}-{_rand_digits(2)}-{_rand_digits(6)}" for _ in range(n)]


def _gen_kr_bank_jeju(n):
    out = []
    for _ in range(n):
        a = _rand_digits(2)
        b = _rand_digits(6)
        c = _rand_digits(2)
        if random.random() < 0.5:
            out.append(f"{a}-{b}-{c}")
        else:
            out.append(a + b + c)
    return out


def _gen_kr_bank_kakao(n):
    out = []
    for _ in range(n):
        a = _rand_digits(2)
        b = _rand_digits(7)
        if random.random() < 0.7:
            out.append(f"3333-{a}-{b}")
        else:
            out.append("3333" + a + b)
    return out


def _gen_kr_bank_digital(n):
    out = []
    for _ in range(n):
        a = _rand_digits(3)
        b = _rand_digits(6)
        if random.random() < 0.7:
            out.append(f"100-{a}-{b}")
        else:
            out.append("100" + a + b)
    return out


# ---- Korean other generators ----

def _gen_kr_passport(n):
    return [random.choice("MS") + _rand_digits(8) for _ in range(n)]


def _gen_kr_driver_license(n):
    return [f"{_rand_digits(2)}-{_rand_digits(6)}-{_rand_digits(2)}" for _ in range(n)]


def _gen_kr_business_reg(n):
    return [f"{_rand_digits(3)}-{_rand_digits(2)}-{_rand_digits(5)}" for _ in range(n)]


def _gen_kr_corporate_reg(n):
    out = []
    for _ in range(n):
        a = _rand_digits(6)
        b = _rand_digits(7)
        if random.random() < 0.7:
            out.append(f"{a}-{b}")
        else:
            out.append(a + b)
    return out


# ---- Date generators ----

def _gen_date_iso(n):
    out = []
    for _ in range(n):
        y = random.randint(1950, 2025)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        out.append(f"{y}-{m:02d}-{d:02d}")
    return out


def _gen_date_slash(n):
    out = []
    for _ in range(n):
        y = random.randint(1950, 2025)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        fmt = random.choice([f"{y}/{m:02d}/{d:02d}", f"{m:02d}/{d:02d}/{y}"])
        out.append(fmt)
    return out


# ---- URL generator ----

def _gen_url(n):
    domains = ["example.com", "test.org", "site.io", "app.dev", "shop.co"]
    paths = ["", "/home", "/about", "/api/v1/data", "/user/123", "/docs"]
    return [f"https://{random.choice(domains)}{random.choice(paths)}" for _ in range(n)]


# ---- JP name generator ----

def _gen_jp_name(n, ref_data):
    surnames = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村",
                "小林", "加藤", "吉田", "山田", "松本", "井上", "木村"]
    given = ref_data.get("jp_given_names", ["太郎", "花子", "一郎", "美咲", "健太"])
    return [random.choice(surnames) + random.choice(given) for _ in range(n)]


# ---- Token/hash generators ----

def _gen_stripe_key(n):
    prefixes = ["sk_live_", "sk_test_", "pk_live_", "pk_test_",
                "rk_live_", "rk_test_"]
    chars = string.ascii_letters + string.digits
    return [random.choice(prefixes) + "".join(random.choices(chars, k=24))
            for _ in range(n)]


def _gen_jwt(n):
    b64 = string.ascii_letters + string.digits + "+/="
    out = []
    for _ in range(n):
        h = "".join(random.choices(b64, k=random.randint(20, 40)))
        p = "".join(random.choices(b64, k=random.randint(40, 100)))
        s = "".join(random.choices(b64, k=random.randint(30, 50)))
        out.append(f"eyJ{h}.eyJ{p}.{s}")
    return out


def _gen_slack_token(n):
    prefixes = ["xoxb-", "xoxp-", "xoxs-"]
    return [random.choice(prefixes) + "-".join([_rand_digits(random.randint(9, 12))
            for _ in range(3)]) + "-" + _rand_alnum(24)
            for _ in range(n)]


def _gen_generic_api_key(n):
    chars = string.ascii_letters + string.digits
    return ["".join(random.choices(chars, k=random.randint(32, 48))) for _ in range(n)]


# ---- CN/TW/JP bank generators ----

def _gen_cn_bank(n):
    prefixes = ["622", "436", "103", "456", "621"]
    return [random.choice(prefixes) + _rand_digits(random.randint(13, 17)) for _ in range(n)]


def _gen_jp_bank(n):
    codes = ["0001", "0009", "0005", "0010", "0034"]
    return [f"{random.choice(codes)}-{_rand_digits(3)}-{_rand_digits(7)}" for _ in range(n)]


def _gen_tw_bank(n):
    return [_rand_digits(random.choice([12, 13, 14])) for _ in range(n)]


def _gen_jp_corporate_number(n):
    return [_rand_digits(13) for _ in range(n)]


# ---- EU passport / VAT generators ----

def _gen_eu_passport(n):
    formats = [
        lambda: random.choice("CFGHJK") + _rand_alnum(8),          # DE
        lambda: _rand_digits(2) + "".join(random.choices(string.ascii_uppercase, k=2)) + _rand_digits(5),  # FR
        lambda: "".join(random.choices(string.ascii_uppercase, k=2)) + _rand_digits(7),  # IT
        lambda: "".join(random.choices(string.ascii_uppercase, k=3)) + _rand_digits(6),  # ES
        lambda: _rand_digits(9),  # UK
    ]
    return [random.choice(formats)() for _ in range(n)]


def _gen_eu_vat(n):
    fmts = [
        lambda: "DE" + _rand_digits(9),
        lambda: "FR" + _rand_alnum(2) + _rand_digits(9),
        lambda: "IT" + _rand_digits(11),
        lambda: "PL" + _rand_digits(10),
        lambda: "ATU" + _rand_digits(8),
    ]
    return [random.choice(fmts)() for _ in range(n)]


# ---- US extra generators ----

def _gen_us_ein(n):
    return [f"{_rand_digits(2)}-{_rand_digits(7)}" for _ in range(n)]


def _gen_us_medicare(n):
    allowed = "ACDEFGHJKMNPQRTUVWXY"
    out = []
    for _ in range(n):
        s = ""
        for i in range(11):
            if i in (0, 4, 7, 10):
                s += random.choice(allowed)
            else:
                s += random.choice(string.digits)
            out.append(s)
    return out


def _gen_us_npi(n):
    return [str(random.randint(1, 9)) + _rand_digits(9) for _ in range(n)]


def _gen_us_passport(n):
    out = []
    for _ in range(n):
        if random.random() < 0.5:
            out.append(_rand_digits(9))
        else:
            out.append(random.choice(string.ascii_uppercase) + _rand_digits(8))
    return out


def _gen_us_driver_license_ca(n):
    return [random.choice(string.ascii_uppercase) + _rand_digits(7) for _ in range(n)]


# ---- IBAN country-specific ----

def _gen_iban_de(n):
    return ["DE" + _rand_digits(2) + _rand_alnum(18) for _ in range(n)]


def _gen_iban_fr(n):
    return ["FR" + _rand_digits(2) + _rand_alnum(23) for _ in range(n)]


def _gen_iban_gb(n):
    return ["GB" + _rand_digits(2) + _rand_alnum(18) for _ in range(n)]


def _gen_iban_it(n):
    return ["IT" + _rand_digits(2) + _rand_alnum(23) for _ in range(n)]


# ---- CN landline ----

def _gen_cn_landline(n):
    area_codes = ["010", "021", "0755", "0571", "0755", "020", "029", "022"]
    out = []
    for _ in range(n):
        area = random.choice(area_codes)
        num = _rand_digits(8)
        if random.random() < 0.5:
            out.append(f"{area}-{num}")
        else:
            out.append(area + num)
    return out


# ---- TW landline ----

def _gen_tw_landline(n):
    out = []
    for _ in range(n):
        area = f"0{random.randint(2, 8)}"
        num = _rand_digits(random.choice([7, 8]))
        if random.random() < 0.5:
            out.append(f"{area}-{num}")
        else:
            out.append(area + num)
    return out


# ---- JP landline ----

def _gen_jp_landline(n):
    prefixes = ["03", "06", "011", "045", "052", "075", "082", "092"]
    out = []
    for _ in range(n):
        p = random.choice(prefixes)
        mid = _rand_digits(4)
        last = _rand_digits(4)
        if random.random() < 0.7:
            out.append(f"{p}-{mid}-{last}")
        else:
            out.append(p + mid + last)
    return out


# ---- SOX financial controls ----

def _gen_sox_account_number(n):
    return [_rand_digits(random.randint(8, 12)) for _ in range(n)]


# Master mapping: pattern_id -> generator function
# Functions accepting ref_data have a second parameter.
GENERATORS = {
    # US
    "ssn_01": _gen_us_ssn,
    "itin_01": _gen_us_itin,
    "phone_01": _gen_us_phone,
    "ein_01": _gen_us_ein,
    "npi_id": _gen_us_npi,
    "medicare_01": _gen_us_medicare,
    # Common
    "email_01": _gen_email,
    "credit_card_visa_01": _gen_visa,
    "credit_card_mastercard_01": _gen_mastercard,
    "credit_card_amex_01": _gen_amex,
    "credit_card_discover_01": _gen_discover,
    "credit_card_jcb_01": _gen_jcb,
    "credit_card_diners_01": _gen_diners,
    "ipv4_01": _gen_ipv4,
    "crypto_btc_p2pkh": _gen_btc,
    "crypto_eth_01": _gen_eth,
    "aws_access_key": _gen_aws_access_key,
    "google_api_key": _gen_google_api_key,
    "swift_bic": _gen_swift,
    "ssh_private_key": _gen_ssh_private_key,
    "url_01": _gen_url,
    "date_iso_01": _gen_date_iso,
    "date_slash_01": _gen_date_slash,
    # IBAN
    "iban_01": _gen_iban,
    "iban_de_01": _gen_iban_de,
    "iban_fr_01": _gen_iban_fr,
    "iban_gb_01": _gen_iban_gb,
    "iban_it_01": _gen_iban_it,
    # Korea
    "rrn_01": _gen_kr_rrn,
    "alien_registration_01": _gen_kr_alien,
    "mobile_01": _gen_kr_phone,  # overridden per-location below
    "mobile_02": _gen_kr_phone,
    "landline_01": _gen_kr_landline,
    "landline_02": _gen_kr_landline,
    "landline_03": _gen_kr_landline,
    "bank_account_01": _gen_kr_bank_kookmin,
    "bank_account_02": _gen_kr_bank_shinhan,
    "bank_account_03": _gen_kr_bank_woori,
    "bank_account_04": _gen_kr_bank_hana,
    "bank_account_05": _gen_kr_bank_nonghyup,
    "bank_account_06": _gen_kr_bank_ibk,
    "bank_account_07": _gen_kr_bank_sc,
    "bank_account_08": _gen_kr_bank_citi,
    "bank_account_09": _gen_kr_bank_busan,
    "bank_account_10": _gen_kr_bank_daegu,
    "bank_account_11": _gen_kr_bank_gwangju,
    "bank_account_12": _gen_kr_bank_jeonbuk,
    "bank_account_13": _gen_kr_bank_jeju,
    "bank_account_14": _gen_kr_bank_kakao,
    "bank_account_15": _gen_kr_bank_digital,
    "business_registration_01": _gen_kr_business_reg,
    "corporate_registration_01": _gen_kr_corporate_reg,
    "driver_license_01": _gen_kr_driver_license,
    # China
    "national_id_01": _gen_cn_national_id,  # overridden per-location
    "passport_01": _gen_cn_passport,  # overridden per-location
    # Japan
    "my_number_01": _gen_jp_my_number,
    "jp_corporate_number": _gen_jp_corporate_number,
    # India
    "aadhaar_01": _gen_in_aadhaar,
    "pan_01": _gen_in_pan,
    "voter_id_01": _gen_in_voter_id,
    "driving_license_01": _gen_in_driving_license,
    # EU
    "germany_personalausweis_01": _gen_eu_de_id,
    "france_insee_01": _gen_eu_fr_insee,
    "italy_codice_fiscale_01": _gen_eu_it_cf,
    "spain_dni_01": _gen_eu_es_dni,
    "spain_nie_01": _gen_eu_es_nie,
    "uk_nino_01": _gen_eu_uk_nino,
    "belgium_rrn_01": _gen_eu_be_rrn,
    "poland_pesel_01": _gen_eu_pl_pesel,
    "sweden_personnummer_01": _gen_eu_se_personnummer,
    "denmark_cpr_01": _gen_eu_dk_cpr,
    "finland_hetu_01": _gen_eu_fi_hetu,
    "portugal_nif_01": _gen_eu_pt_nif,
    "austria_sozialversicherungsnummer_01": _gen_eu_at_svnr,
    # Tokens
    "stripe_key_01": _gen_stripe_key,
    "jwt_token_01": _gen_jwt,
    "slack_token_01": _gen_slack_token,
    "generic_api_key_01": _gen_generic_api_key,
}

# Location-specific overrides for pattern IDs that share an id across locations
GENERATORS_BY_LOC = {
    ("cn", "mobile_01"): _gen_cn_phone,
    ("jp", "mobile_01"): _gen_jp_phone,
    ("tw", "mobile_01"): _gen_tw_phone,
    ("in", "mobile_01"): _gen_in_phone,
    ("tw", "national_id_01"): _gen_tw_national_id,
    ("in", "passport_01"): _gen_in_passport,
    ("jp", "passport_01"): _gen_jp_passport,
    ("kr", "passport_01"): _gen_kr_passport,
    ("kr", "driver_license_01"): _gen_kr_driver_license,
    ("jp", "driver_license_01"): _gen_jp_driver_license,
    ("cn", "landline_01"): _gen_cn_landline,
    ("tw", "landline_01"): _gen_tw_landline,
    ("jp", "landline_01"): _gen_jp_landline,
    ("eu", "uk_nino_01"): _gen_eu_uk_nino,
}

# Generators that need ref_data as second argument
GENERATORS_WITH_REF = {
    "korean_name_01": _gen_kr_name,
    "korean_name": _gen_kr_name,
    "chinese_name": _gen_cn_name,
    "jp_name": _gen_jp_name,
}


def generate_values_for_pattern(pat, n, ref_data):
    """Generate n PII values for a given pattern dict.

    First tries the pattern-specific generator, then falls back to
    seeding from examples.match in the YAML.  All returned values are
    validated against the regex pattern.
    """
    pid = pat["id"]
    loc = pat["location"]
    regex_str = pat["pattern"]

    # Compile regex (full match)
    try:
        rx = re.compile(f"^{regex_str}$",
                        re.IGNORECASE if "IGNORECASE" in str(pat.get("flags", [])) else 0)
    except re.error:
        rx = None

    # --- Collect candidate values ---
    candidates = []

    # a) From generator
    gen_fn = GENERATORS_BY_LOC.get((loc, pid)) or GENERATORS.get(pid)
    if gen_fn:
        if pid in GENERATORS_WITH_REF:
            candidates.extend(gen_fn(n * 2, ref_data))
        else:
            try:
                candidates.extend(gen_fn(n * 2))
            except TypeError:
                candidates.extend(gen_fn(n * 2, ref_data))

    ref_gen_fn = GENERATORS_WITH_REF.get(pid)
    if ref_gen_fn and not gen_fn:
        candidates.extend(ref_gen_fn(n * 2, ref_data))

    # b) From YAML test vectors (examples.match)
    for ex in pat.get("examples_match", []):
        candidates.append(str(ex))

    # --- Validate against regex ---
    if rx:
        valid = [c for c in candidates if rx.match(c)]
    else:
        valid = candidates

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for v in valid:
        if v not in seen:
            seen.add(v)
            unique.append(v)

    # If we don't have enough, just repeat from what we have
    if not unique:
        return []
    while len(unique) < n:
        unique.append(random.choice(unique))

    random.shuffle(unique)
    return unique[:n]


# ===========================================================================
# 3. Sentence templates (multilingual)
# ===========================================================================

# --- English ---
EN_TEMPLATES = [
    "My {category} is {pii}.",
    "Please contact me at {pii}.",
    "The {category} on file is {pii}.",
    "Patient record shows {category}: {pii}.",
    "Account holder: {pii}",
    "Billing information: {pii}",
    "Send the documents to {pii} please.",
    "The customer provided their {category} as {pii}.",
    "For verification, my {category} is {pii}.",
    "Registered under {pii}.",
    "Here is my information: {pii}",
    "Please update the {category} to {pii}.",
    "The {category} listed is {pii}, please confirm.",
    "I'd like to verify my {category}: {pii}",
    "Attached is the record for {pii}.",
    "Hello, my name is John and my {category} is {pii}.",
    "Could you look up account {pii} for me?",
    "The payment was sent from {pii}.",
    "Please add {pii} to the allow-list.",
    "Employee ID: {pii}, department: Engineering.",
    "The shipping address associated with {pii} needs to be updated.",
    "Cc: {pii} on the next email thread.",
    "Secure document access for {pii}.",
    "I am writing to confirm that my {category} is {pii}.",
    "Dear Support, the {category} associated with my profile is {pii}.",
    "Applicant's {category}: {pii}.",
    "System log entry: user identified by {category} {pii} accessed the resource.",
    "Incoming wire transfer from {pii}.",
    "ALERT: {category} {pii} has been flagged for review.",
    "Insurance claim filed under {category}: {pii}.",
    "The tenant's {category} on the lease is {pii}.",
    "Customer support ticket #42: {category} is {pii}.",
    "New enrollment request with {category} {pii}.",
    "KYC verification: {category} = {pii}.",
    "Please whitelist the following {category}: {pii}.",
    "As per our records, the {category} is {pii}.",
    "Transaction receipt: sender {pii}.",
    "Payroll record: {category} — {pii}.",
    "Shipping label generated for {pii}.",
    "The {category} ending in {pii} was compromised.",
    "Two-factor authentication was sent to {pii}.",
    "Your {category} has been updated to {pii}.",
    "Backup contact: {pii}.",
    "Primary identifier: {pii}. Secondary: N/A.",
    "The audit log shows activity from {pii} at 14:32 UTC.",
    "Refund processed to {category}: {pii}.",
    "Medical record linked to {category} {pii}.",
    "Tax filing reference: {pii}.",
    "Vendor payment routed through {pii}.",
    "Compliance check: {category} = {pii}, status OK.",
    "Outbound notification sent to {pii}.",
    "User profile — {category}: {pii}.",
]

# --- Korean ---
KR_TEMPLATES = [
    "제 {category}은(는) {pii}입니다.",
    "{pii}(으)로 연락 주세요.",
    "고객 {category}: {pii}",
    "환자 기록에 {category}(이)가 {pii}(으)로 등록되어 있습니다.",
    "계좌번호 {pii}(으)로 입금해 주세요.",
    "{category}(을)를 {pii}(으)로 변경해 주세요.",
    "본인 확인을 위해 {category}(을)를 알려드립니다: {pii}",
    "{pii}(으)로 등록된 정보를 확인해 주세요.",
    "배송지 정보: {pii}",
    "직원 정보: {category} {pii}",
    "주문번호 확인을 위해 {pii}(을)를 입력해 주세요.",
    "긴급 연락처: {pii}",
    "안녕하세요, 본인의 {category}은(는) {pii}입니다.",
    "세금 신고 시 사용되는 {category}: {pii}",
    "택배 수령인 정보: {pii}",
    "보험 가입 시 제출한 {category}: {pii}",
    "결제 내역 확인: {category} {pii}",
    "회원 가입 정보 — {category}: {pii}",
    "거래 명세서에 기재된 {category}은(는) {pii}입니다.",
    "근로계약서에 명시된 {category}: {pii}",
    "고객님의 {category}이(가) {pii}(으)로 확인됩니다.",
    "SMS 인증번호가 {pii}(으)로 발송되었습니다.",
    "입금 확인: 수신 {category} {pii}",
    "환불 처리 완료: {category} {pii}",
    "대출 신청서: {category} {pii}",
    "수취인: {pii}",
    "부동산 계약서 — {category}: {pii}",
    "의료 기록 열람: {category} {pii}",
    "납세자 번호: {pii}",
    "고객센터 문의: {category}이(가) {pii}인 건에 대해 확인 부탁드립니다.",
]

# --- Chinese ---
CN_TEMPLATES = [
    "我的{category}是{pii}。",
    "请通过{pii}联系我。",
    "客户{category}：{pii}",
    "患者记录显示{category}为{pii}。",
    "请将{category}更新为{pii}。",
    "账户信息：{pii}",
    "请核实以下{category}：{pii}",
    "收件人信息：{pii}",
    "员工信息：{category} {pii}",
    "紧急联系方式：{pii}",
    "银行转账至{category}：{pii}。",
    "保险登记的{category}为{pii}。",
    "报税使用的{category}：{pii}",
    "会员注册信息 — {category}：{pii}",
    "快递收件人：{pii}",
    "交易明细：{category} {pii}",
    "贷款申请表：{category} {pii}",
    "短信验证码已发送至{pii}。",
    "系统日志：用户{category} {pii}已登录。",
    "退款至{category}：{pii}。",
    "客服查询：{category}为{pii}的账户。",
    "合同中列明的{category}：{pii}。",
]

# --- Japanese ---
JP_TEMPLATES = [
    "私の{category}は{pii}です。",
    "{pii}までご連絡ください。",
    "顧客の{category}：{pii}",
    "患者記録の{category}は{pii}です。",
    "{category}を{pii}に更新してください。",
    "アカウント情報：{pii}",
    "以下の{category}をご確認ください：{pii}",
    "配送先情報：{pii}",
    "従業員情報：{category} {pii}",
    "緊急連絡先：{pii}",
    "銀行振込先：{category} {pii}",
    "保険登録の{category}は{pii}です。",
    "確定申告用の{category}：{pii}",
    "会員登録情報 — {category}：{pii}",
    "宅配便の受取人：{pii}",
    "取引明細：{category} {pii}",
    "ローン申請書：{category} {pii}",
    "SMSが{pii}に送信されました。",
    "システムログ：ユーザー{category} {pii}がアクセスしました。",
    "返金先の{category}：{pii}",
    "お問い合わせ：{category}が{pii}のアカウントについて。",
    "契約書に記載の{category}：{pii}。",
]

# Template selection by location
TEMPLATES_BY_LOC = {
    "us": EN_TEMPLATES,
    "comm": EN_TEMPLATES,
    "co": EN_TEMPLATES,
    "kr": KR_TEMPLATES,
    "cn": CN_TEMPLATES,
    "jp": JP_TEMPLATES,
    "tw": CN_TEMPLATES,
    "in": EN_TEMPLATES,
    "eu": EN_TEMPLATES,
}

# Multi-PII sentence templates (English only for simplicity)
MULTI_PII_EN = [
    "Name: {name}, Phone: {phone}, Email: {email}",
    "Contact {name} at {phone} or {email}.",
    "Customer {name} — Phone: {phone}",
    "Record: name={name}, ID={id}, phone={phone}",
    "Dear {name}, your account ({email}) has been updated. Call {phone} for help.",
    "Applicant: {name}. Verification phone: {phone}. Notification email: {email}.",
]

MULTI_PII_KR = [
    "이름: {name}, 전화번호: {phone}, 이메일: {email}",
    "{name}님에게 {phone} 또는 {email}(으)로 연락하세요.",
    "고객명: {name} — 연락처: {phone}",
    "기록: 이름={name}, 연락처={phone}",
]


# ===========================================================================
# 4. PII tag / category mappings
# ===========================================================================

CATEGORY_LABELS = {
    "ssn": "Social Security Number",
    "phone": "Phone Number",
    "email": "Email Address",
    "credit_card": "Credit Card Number",
    "credential": "Cloud API Key",
    "ip": "IP Address",
    "financial": "Financial Identifier",
    "iban": "IBAN",
    "rrn": "Resident Registration Number",
    "bank": "Bank Account Number",
    "name": "Personal Name",
    "passport": "Passport Number",
    "other": "Government ID",
}

LOCATION_LABELS = {
    "us": "United States",
    "kr": "South Korea",
    "cn": "China",
    "jp": "Japan",
    "tw": "Taiwan",
    "in": "India",
    "eu": "European Union",
    "comm": "International",
    "co": "International",
}

CATEGORY_TO_TAG = {
    "ssn": "SSN",
    "phone": "PHONE",
    "email": "EMAIL",
    "credit_card": "CREDIT_CARD",
    "credential": "API_KEY",
    "ip": "IP_ADDRESS",
    "financial": "FINANCIAL_ID",
    "iban": "IBAN",
    "rrn": "ID_NUMBER",
    "bank": "BANK_ACCOUNT",
    "name": "NAME",
    "passport": "ID_NUMBER",
    "other": "ID_NUMBER",
}

RISK_LEVELS = {
    "ssn": "critical",
    "rrn": "critical",
    "credit_card": "critical",
    "credential": "critical",
    "passport": "high",
    "bank": "high",
    "iban": "high",
    "financial": "high",
    "phone": "medium",
    "email": "medium",
    "name": "medium",
    "ip": "medium",
    "other": "high",
}


# ===========================================================================
# 5. Negative (non-PII) sample generators
# ===========================================================================

BENIGN_WORDS = [
    "hello", "world", "the", "quick", "brown", "fox", "jumps", "over", "lazy",
    "dog", "python", "machine", "learning", "data", "science", "algorithm",
    "function", "variable", "module", "class", "object", "array", "string",
    "number", "boolean", "error", "warning", "debug", "info", "server",
    "client", "request", "response", "status", "code", "message", "pattern",
    "engine", "regex", "match", "search", "replace", "split", "join",
    "project", "build", "deploy", "release", "version", "update", "config",
]

BENIGN_SENTENCES_EN = [
    "The meeting is scheduled for next Tuesday.",
    "Please review the pull request before merging.",
    "The server returned a 200 OK response.",
    "We need to update the documentation.",
    "The test suite passed all 42 checks.",
    "Refactored the data processing pipeline.",
    "Added error handling for edge cases.",
    "The deployment was successful.",
    "Fixed a bug in the sorting algorithm.",
    "Updated dependencies to latest versions.",
    "The API rate limit is 1000 requests per hour.",
    "Memory usage is within acceptable limits.",
    "The database migration completed without errors.",
    "Code coverage increased to 85 percent.",
    "The feature flag is currently disabled.",
    "Today's weather forecast calls for sunshine and mild temperatures.",
    "The quarterly report shows a 12 percent increase in revenue.",
    "Let's schedule a follow-up meeting for next week.",
    "The product launch is on track for the target date.",
]

BENIGN_SENTENCES_KR = [
    "회의는 다음 주 화요일로 예정되어 있습니다.",
    "병합하기 전에 풀 리퀘스트를 검토해 주세요.",
    "서버가 200 OK 응답을 반환했습니다.",
    "문서를 업데이트해야 합니다.",
    "테스트 스위트가 42개의 검사를 모두 통과했습니다.",
    "데이터 처리 파이프라인을 리팩토링했습니다.",
    "배포가 성공적으로 완료되었습니다.",
    "정렬 알고리즘의 버그를 수정했습니다.",
    "오늘 날씨가 맑겠습니다.",
    "분기 보고서에서 매출 12% 증가를 보여줍니다.",
]

BENIGN_SENTENCES_CN = [
    "会议定于下周二举行。",
    "请在合并之前审查拉取请求。",
    "服务器返回了200 OK响应。",
    "我们需要更新文档。",
    "测试套件通过了所有42项检查。",
    "部署成功完成。",
    "修复了排序算法中的错误。",
    "今天天气晴朗。",
    "季度报告显示收入增长了12%。",
]

BENIGN_SENTENCES_JP = [
    "会議は来週火曜日に予定されています。",
    "マージする前にプルリクエストを確認してください。",
    "サーバーが200 OKレスポンスを返しました。",
    "ドキュメントを更新する必要があります。",
    "テストスイートが42件のチェックをすべてパスしました。",
    "デプロイが正常に完了しました。",
    "ソートアルゴリズムのバグを修正しました。",
    "今日は晴れの予報です。",
    "四半期レポートで売上が12%増加しました。",
]


def gen_negative_random_text(n):
    out = []
    for _ in range(n):
        length = random.randint(3, 10)
        out.append(" ".join(random.choices(BENIGN_WORDS, k=length)))
    return out


def gen_negative_sentences(n):
    all_benign = (BENIGN_SENTENCES_EN + BENIGN_SENTENCES_KR +
                  BENIGN_SENTENCES_CN + BENIGN_SENTENCES_JP)
    return [random.choice(all_benign) for _ in range(n)]


def gen_negative_numbers(n):
    out = []
    for _ in range(n):
        kind = random.choice(["short", "decimal", "large", "version", "hex_short"])
        if kind == "short":
            out.append(str(random.randint(0, 9999)))
        elif kind == "decimal":
            out.append(f"{random.uniform(0, 1000):.2f}")
        elif kind == "large":
            out.append(str(random.randint(100000000000000, 999999999999999)))
        elif kind == "version":
            out.append(f"{random.randint(0,9)}.{random.randint(0,99)}.{random.randint(0,999)}")
        else:
            out.append("0x" + _rand_hex(random.randint(4, 8)))
    return out


def gen_negative_near_miss(n):
    out = []
    for _ in range(n):
        kind = random.choice(["bad_ssn", "bad_email", "bad_phone", "bad_cc", "bad_ip"])
        if kind == "bad_ssn":
            out.append(f"000-00-{_rand_digits(4)}")
        elif kind == "bad_email":
            out.append(random.choice(["user@", "@domain.com", "no-at-sign.com", "user@.com"]))
        elif kind == "bad_phone":
            out.append(f"({_rand_digits(2)}) {_rand_digits(3)}-{_rand_digits(2)}")
        elif kind == "bad_cc":
            out.append(_rand_digits(random.choice([10, 11, 20])))
        else:
            out.append("999.999.999.999")
    return out


def generate_all_negative(total):
    per_type = total // 4
    rows = []
    for text in gen_negative_random_text(per_type):
        rows.append(text)
    for text in gen_negative_sentences(per_type):
        rows.append(text)
    for text in gen_negative_numbers(per_type):
        rows.append(text)
    for text in gen_negative_near_miss(total - 3 * per_type):
        rows.append(text)
    return rows


# ===========================================================================
# 6. BIO tagging
# ===========================================================================

def bio_tag_sentence(text, pii_value, tag_type):
    """Generate BIO-tagged output for a sentence containing one PII span.

    Returns a string like:
        token1/O token2/O pii_tok1/B-SSN pii_tok2/I-SSN token3/O
    """
    if not pii_value or pii_value not in text:
        # All tokens are O
        tokens = text.split()
        return " ".join(f"{t}/O" for t in tokens)

    idx = text.find(pii_value)
    before = text[:idx]
    after = text[idx + len(pii_value):]

    result_parts = []

    # Tokens before PII
    for t in before.split():
        if t:
            result_parts.append(f"{t}/O")

    # PII tokens
    pii_tokens = pii_value.split()
    if not pii_tokens:
        pii_tokens = [pii_value]
    for i, t in enumerate(pii_tokens):
        if i == 0:
            result_parts.append(f"{t}/B-{tag_type}")
        else:
            result_parts.append(f"{t}/I-{tag_type}")

    # Tokens after PII
    for t in after.split():
        if t:
            result_parts.append(f"{t}/O")

    return " ".join(result_parts)


def bio_tag_multi(text, pii_spans):
    """BIO-tag a sentence with multiple PII spans.

    pii_spans: list of (pii_value, tag_type) sorted by position in text.
    """
    # Build a character-level tag map
    char_tags = ["O"] * len(text)
    for pii_val, tag_type in pii_spans:
        idx = text.find(pii_val)
        if idx < 0:
            continue
        for i in range(idx, idx + len(pii_val)):
            if i == idx:
                char_tags[i] = f"B-{tag_type}"
            else:
                char_tags[i] = f"I-{tag_type}"

    # Tokenize by whitespace and assign tag per token
    tokens = text.split()
    result = []
    pos = 0
    for token in tokens:
        # Find token start in original text
        tok_start = text.find(token, pos)
        if tok_start < 0:
            tok_start = pos
        tok_end = tok_start + len(token)
        # Use the tag of the first character of the token
        tag = char_tags[tok_start] if tok_start < len(char_tags) else "O"
        # If it's I- but the previous token wasn't part of the same entity, use B-
        if tag.startswith("I-"):
            entity = tag[2:]
            if not result or not result[-1].endswith(f"-{entity}"):
                tag = f"B-{entity}"
        result.append(f"{token}/{tag}")
        pos = tok_end
    return " ".join(result)


# ===========================================================================
# 7. Task builders (system prompts + examples)
# ===========================================================================

NER_SYSTEM = (
    "You are a PII detection expert. Identify all personally identifiable "
    "information in the given text and replace each instance with the "
    "appropriate tag: [NAME], [PHONE], [EMAIL], [SSN], [CREDIT_CARD], "
    "[ID_NUMBER], [IP_ADDRESS], [BANK_ACCOUNT], [IBAN], [FINANCIAL_ID], "
    "[API_KEY], [PRIVATE_KEY], or [OTHER_PII]. "
    "If no PII is found, return the text unchanged."
)

BIO_SYSTEM = (
    "You are a PII NER tagging expert. For each token in the input text, "
    "output the token followed by its BIO tag separated by a slash. Use "
    "B-<TYPE> for the first token of a PII entity, I-<TYPE> for continuation "
    "tokens, and O for non-PII tokens. Supported types: NAME, PHONE, EMAIL, "
    "SSN, CREDIT_CARD, ID_NUMBER, IP_ADDRESS, BANK_ACCOUNT, IBAN, "
    "FINANCIAL_ID, API_KEY."
)

CLASSIFY_SYSTEM = (
    "You are a security analyst. Determine whether the given text contains "
    "personally identifiable information (PII). Respond with exactly "
    "'PII_DETECTED' or 'NO_PII'."
)

CATEGORY_SYSTEM = (
    "You are a PII classification expert. Analyze the given text and identify "
    "what type(s) of PII it contains. Respond with a JSON object containing: "
    '"has_pii" (boolean), "pii_types" (list of detected types), '
    '"risk_level" (low/medium/high/critical), and "explanation" (brief reason).'
)


def to_llama3_chat(system, instruction, input_text, output_text):
    """Build Llama 3 chat-format message list."""
    messages = [{"role": "system", "content": system}]
    user_content = instruction
    if input_text:
        user_content += f"\n\n{input_text}"
    messages.append({"role": "user", "content": user_content})
    messages.append({"role": "assistant", "content": output_text})
    return {"messages": messages}


# ===========================================================================
# 8. Main generation pipeline
# ===========================================================================

def generate_dataset(samples_per_pattern=25):
    """Generate the full instruction-tuning dataset."""
    patterns = load_all_patterns()
    ref_data = load_reference_data()

    print(f"Loaded {len(patterns)} regex patterns from YAML files")
    print(f"Loaded reference data keys: {list(ref_data.keys())}")

    all_examples = []
    stats = defaultdict(int)

    # --- Generate PII values per pattern, embed in sentences, create tasks ---
    for pat in patterns:
        values = generate_values_for_pattern(pat, samples_per_pattern, ref_data)
        if not values:
            print(f"  WARNING: No values generated for {pat['id']} ({pat['_file']})")
            continue

        loc = pat["location"]
        cat = pat["category"]
        pid = pat["id"]
        severity = pat["severity"]
        tag = CATEGORY_TO_TAG.get(cat, "OTHER_PII")
        cat_display = CATEGORY_LABELS.get(cat, cat).lower()
        templates = TEMPLATES_BY_LOC.get(loc, EN_TEMPLATES)

        for pii_val in values:
            template = random.choice(templates)
            sentence = template.format(category=cat_display, pii=pii_val)

            # --- Task A: NER masking ---
            masked = sentence.replace(pii_val, f"[{tag}]")
            all_examples.append(to_llama3_chat(
                NER_SYSTEM,
                "Detect and mask all PII in the following text.",
                sentence,
                masked,
            ))
            stats["ner_positive"] += 1

            # --- Task B: BIO tagging ---
            bio_output = bio_tag_sentence(sentence, pii_val, tag)
            all_examples.append(to_llama3_chat(
                BIO_SYSTEM,
                "Tag each token with its BIO label.",
                sentence,
                bio_output,
            ))
            stats["bio_positive"] += 1

            # --- Task C: Binary classification ---
            all_examples.append(to_llama3_chat(
                CLASSIFY_SYSTEM,
                "Does the following text contain PII?",
                sentence,
                "PII_DETECTED",
            ))
            stats["classify_positive"] += 1

            # --- Task D: Category classification ---
            cat_label = CATEGORY_LABELS.get(cat, cat)
            loc_label = LOCATION_LABELS.get(loc, loc)
            risk = RISK_LEVELS.get(cat, "medium")
            cat_output = json.dumps({
                "has_pii": True,
                "pii_types": [cat_label],
                "region": loc_label,
                "risk_level": risk,
                "explanation": f"Text contains {cat_label} ({loc_label} format).",
            }, ensure_ascii=False)
            all_examples.append(to_llama3_chat(
                CATEGORY_SYSTEM,
                "Classify the PII in the following text.",
                sentence,
                cat_output,
            ))
            stats["category_positive"] += 1

    # --- Negative examples ---
    neg_count = max(3000, stats["classify_positive"] // 2)
    print(f"Generating {neg_count} negative samples...")
    negatives = generate_all_negative(neg_count)

    for neg_text in negatives:
        # NER: no PII to mask → return unchanged
        all_examples.append(to_llama3_chat(
            NER_SYSTEM,
            "Detect and mask all PII in the following text.",
            neg_text,
            neg_text,
        ))
        stats["ner_negative"] += 1

        # BIO: all O tags
        bio_out = " ".join(f"{t}/O" for t in neg_text.split())
        all_examples.append(to_llama3_chat(
            BIO_SYSTEM,
            "Tag each token with its BIO label.",
            neg_text,
            bio_out,
        ))
        stats["bio_negative"] += 1

        # Classify: NO_PII
        all_examples.append(to_llama3_chat(
            CLASSIFY_SYSTEM,
            "Does the following text contain PII?",
            neg_text,
            "NO_PII",
        ))
        stats["classify_negative"] += 1

        # Category: no PII
        cat_output = json.dumps({
            "has_pii": False,
            "pii_types": [],
            "region": "N/A",
            "risk_level": "none",
            "explanation": "No personally identifiable information detected.",
        })
        if random.random() < 0.6:
            all_examples.append(to_llama3_chat(
                CATEGORY_SYSTEM,
                "Classify the PII in the following text.",
                neg_text,
                cat_output,
            ))
            stats["category_negative"] += 1

    # --- Multi-PII examples ---
    print("Generating multi-PII sentence examples...")
    multi_count = 0
    en_names = ["John Smith", "Jane Doe", "Alice Johnson", "Bob Williams",
                "Maria Garcia", "David Brown", "Sarah Davis", "Michael Wilson",
                "Emily Taylor", "James Anderson", "Jennifer Thomas", "Robert Jackson"]
    names_kr = _gen_kr_name(300, ref_data)
    names_cn = _gen_cn_name(200, ref_data)
    names_jp = _gen_jp_name(200, ref_data)
    phones_kr = _gen_kr_phone(300)
    phones_us = _gen_us_phone(300)
    phones_cn = _gen_cn_phone(200)
    phones_jp = _gen_jp_phone(200)
    emails = _gen_email(300)
    ssns = _gen_us_ssn(200)
    kr_rrns = _gen_kr_rrn(200)
    ipv4s = _gen_ipv4(100)

    # English multi-PII
    for _ in range(250):
        name = random.choice(en_names)
        phone = random.choice(phones_us)
        email = random.choice(emails)
        template = random.choice(MULTI_PII_EN)
        sentence = template.format(
            name=name, phone=phone, email=email,
            id=random.choice(ssns),
        )
        masked = sentence.replace(name, "[NAME]").replace(phone, "[PHONE]").replace(email, "[EMAIL]")
        all_examples.append(to_llama3_chat(
            NER_SYSTEM,
            "Detect and mask all PII in the following text.",
            sentence, masked,
        ))
        spans = [(name, "NAME"), (phone, "PHONE"), (email, "EMAIL")]
        bio_out = bio_tag_multi(sentence, spans)
        all_examples.append(to_llama3_chat(
            BIO_SYSTEM,
            "Tag each token with its BIO label.",
            sentence, bio_out,
        ))
        all_examples.append(to_llama3_chat(
            CLASSIFY_SYSTEM,
            "Does the following text contain PII?",
            sentence, "PII_DETECTED",
        ))
        multi_count += 1

    # Korean multi-PII
    for _ in range(250):
        name = random.choice(names_kr)
        phone = random.choice(phones_kr)
        email = random.choice(emails)
        template = random.choice(MULTI_PII_KR)
        sentence = template.format(name=name, phone=phone, email=email)
        masked = sentence.replace(name, "[NAME]").replace(phone, "[PHONE]").replace(email, "[EMAIL]")
        all_examples.append(to_llama3_chat(
            NER_SYSTEM,
            "Detect and mask all PII in the following text.",
            sentence, masked,
        ))
        spans = [(name, "NAME"), (phone, "PHONE"), (email, "EMAIL")]
        bio_out = bio_tag_multi(sentence, spans)
        all_examples.append(to_llama3_chat(
            BIO_SYSTEM,
            "Tag each token with its BIO label.",
            sentence, bio_out,
        ))
        all_examples.append(to_llama3_chat(
            CLASSIFY_SYSTEM,
            "Does the following text contain PII?",
            sentence, "PII_DETECTED",
        ))
        multi_count += 1

    # Chinese multi-PII
    CN_MULTI = [
        "姓名：{name}，电话：{phone}，邮箱：{email}",
        "联系{name}，电话{phone}，邮箱{email}。",
        "客户{name} — 联系方式：{phone}",
        "记录：{name}，联系电话{phone}",
    ]
    for _ in range(150):
        name = random.choice(names_cn)
        phone = random.choice(phones_cn)
        email = random.choice(emails)
        template = random.choice(CN_MULTI)
        sentence = template.format(name=name, phone=phone, email=email)
        masked = sentence.replace(name, "[NAME]").replace(phone, "[PHONE]").replace(email, "[EMAIL]")
        all_examples.append(to_llama3_chat(
            NER_SYSTEM,
            "Detect and mask all PII in the following text.",
            sentence, masked,
        ))
        spans = [(name, "NAME"), (phone, "PHONE"), (email, "EMAIL")]
        bio_out = bio_tag_multi(sentence, spans)
        all_examples.append(to_llama3_chat(
            BIO_SYSTEM,
            "Tag each token with its BIO label.",
            sentence, bio_out,
        ))
        all_examples.append(to_llama3_chat(
            CLASSIFY_SYSTEM,
            "Does the following text contain PII?",
            sentence, "PII_DETECTED",
        ))
        multi_count += 1

    # Japanese multi-PII
    JP_MULTI = [
        "氏名：{name}、電話：{phone}、メール：{email}",
        "{name}様へ。{phone}または{email}までご連絡ください。",
        "顧客{name} — 連絡先：{phone}",
        "記録：{name}、電話番号{phone}",
    ]
    for _ in range(150):
        name = random.choice(names_jp)
        phone = random.choice(phones_jp)
        email = random.choice(emails)
        template = random.choice(JP_MULTI)
        sentence = template.format(name=name, phone=phone, email=email)
        masked = sentence.replace(name, "[NAME]").replace(phone, "[PHONE]").replace(email, "[EMAIL]")
        all_examples.append(to_llama3_chat(
            NER_SYSTEM,
            "Detect and mask all PII in the following text.",
            sentence, masked,
        ))
        spans = [(name, "NAME"), (phone, "PHONE"), (email, "EMAIL")]
        bio_out = bio_tag_multi(sentence, spans)
        all_examples.append(to_llama3_chat(
            BIO_SYSTEM,
            "Tag each token with its BIO label.",
            sentence, bio_out,
        ))
        all_examples.append(to_llama3_chat(
            CLASSIFY_SYSTEM,
            "Does the following text contain PII?",
            sentence, "PII_DETECTED",
        ))
        multi_count += 1

    stats["multi_pii"] = multi_count

    random.shuffle(all_examples)
    return all_examples, stats


def split_and_save(examples, output_dir, train_ratio=0.85, val_ratio=0.10):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    n = len(examples)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    splits = {
        "train": examples[:train_end],
        "val": examples[train_end:val_end],
        "test": examples[val_end:],
    }

    for name, data in splits.items():
        path = output_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  {name}.jsonl: {len(data)} examples")

    return splits


# ===========================================================================
# 9. Main
# ===========================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate PII instruction-tuning dataset")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Directory to save generated data (default: local_llm/data/)")
    parser.add_argument("--samples_per_pattern", type=int, default=50,
                        help="Number of samples to generate per pattern")
    cli_args = parser.parse_args()

    print("=" * 60)
    print("Generating Instruction-Tuning Dataset for PII Detection")
    print("  Source: regex/*.yml patterns + synthetic generators")
    print("  Tasks:  NER masking, BIO tagging, Classification, Category")
    print("=" * 60)

    examples, stats = generate_dataset(samples_per_pattern=cli_args.samples_per_pattern)
    print(f"\nTotal examples: {len(examples)}")
    print(f"\nTask breakdown:")
    for k, v in sorted(stats.items()):
        print(f"  {k:<25s} {v:>6d}")

    output_dir = Path(cli_args.output_dir) if cli_args.output_dir else Path(__file__).parent / "data"
    print(f"\nSaving to {output_dir}/")
    splits = split_and_save(examples, output_dir)

    print(f"\nDataset Statistics:")
    print(f"  Total:  {len(examples)}")
    print(f"  Train:  {len(splits['train'])}")
    print(f"  Val:    {len(splits['val'])}")
    print(f"  Test:   {len(splits['test'])}")

    # Show a sample
    print(f"\n--- Sample entry ---")
    sample = random.choice(examples)
    print(json.dumps(sample, indent=2, ensure_ascii=False)[:1000])


if __name__ == "__main__":
    main()
