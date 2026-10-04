"""Tests for the Aho-Corasick detection example (examples/detect.py).

The headline test is *equivalence*: detecting with the Aho-Corasick pre-filter
must return exactly the same findings as the brute-force scan that runs every
regex. That is the empirical proof that the pre-filter is a sound optimization —
it only ever changes speed, never results.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "examples"))

from detect import Detector  # noqa: E402


@pytest.fixture(scope="module")
def det():
    return Detector()


# Texts spanning digits, keywords, CJK, mixed, and clean prose.
EQUIVALENCE_TEXTS = [
    "",
    "nothing to see here, just words",
    "Employee SSN 123-45-6789, card on file 4111111111111111.",
    "Contact Alice at alice@example.com or push AKIAIOSFODNN7EXAMPLE.",
    "Korean mobile +82 10-1234-5678; billing pay@acme.co.",
    "주소: 서울특별시 강남구, 전화 010-1234-5678",
    "CVE-2021-44228 affects the server; token sk_live_abcdefghijklmnopqrstuvwx.",
    "mix 0x52908400098527886E0F7030069857D2E4169EE7 and 192.0.2.1 and 7000000000",
    "page 3, section 2, revision 14 — no identifiers at all",
]


class TestPrefilterEquivalence:
    @pytest.mark.parametrize("text", EQUIVALENCE_TEXTS)
    def test_prefilter_matches_bruteforce(self, det, text):
        with_pf = det.detect(text, use_prefilter=True)
        without_pf = det.detect(text, use_prefilter=False)
        assert with_pf == without_pf, (
            "Aho-Corasick pre-filter changed the findings for "
            f"{text!r} — it must only affect speed, not results"
        )


class TestKnownDetections:
    def test_detects_ssn(self, det):
        found = det.detect_clean("my ssn is 123-45-6789 ok")
        assert any(f.pattern.endswith("::ssn_01") and f.text == "123-45-6789" for f in found)

    def test_detects_email(self, det):
        found = det.detect_clean("write to alice@example.com please")
        assert any(f.category == "email" and f.text == "alice@example.com" for f in found)

    def test_detects_aws_key(self, det):
        found = det.detect_clean("key AKIAIOSFODNN7EXAMPLE here")
        assert any(f.text == "AKIAIOSFODNN7EXAMPLE" for f in found)

    def test_clean_prose_has_no_digit_pii(self, det):
        found = det.detect_clean("a perfectly ordinary sentence about nothing")
        # no numeric PII in digit-free prose
        assert all(f.category not in ("ssn", "credit_card", "phone", "bank") for f in found)

    def test_detect_clean_spans_are_non_overlapping(self, det):
        found = det.detect_clean(
            "Employee SSN 123-45-6789, card on file 4111111111111111."
        )
        spans = sorted((f.start, f.end) for f in found)
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            assert e1 <= s2, f"overlapping findings: {(s1, e1)} and {(s2, e2)}"


class TestPrefilterPrunes:
    def test_digit_free_text_prunes_numeric_patterns(self, det):
        text = "purely alphabetic prose without any numerals whatsoever"
        candidates = det.prefilter.candidate_patterns(text)
        assert len(candidates) < len(det.patterns)  # something was skipped

    def test_card_text_keeps_card_patterns(self, det):
        candidates = det.prefilter.candidate_patterns("4111111111111111")
        assert any("credit" in k for k in candidates)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
