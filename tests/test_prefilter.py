"""Tests for the pre-filter (Aho-Corasick keywords + min_digit_run) and its data.

The central property is *soundness*: the pre-filter must never discard a pattern
for an input the pattern would actually match. These tests enforce that for every
declared match example and for both gate kinds (hit_keywords, min_digit_run).
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "prefilter"))

from prefilter import (  # noqa: E402
    AhoCorasick,
    PatternPrefilter,
    longest_digit_run,
    min_digit_run,
)

REGEX_DIR = REPO / "regex"


def _all_patterns():
    rows = []
    for f in sorted(REGEX_DIR.glob("**/*.yml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for p in data.get("patterns", []) or []:
            rows.append((f, p))
    return rows


ALL = _all_patterns()
KW_PATTERNS = [(f, p) for f, p in ALL if p.get("hit_keywords")]
DR_PATTERNS = [(f, p) for f, p in ALL if p.get("min_digit_run")]
GATED = [(f, p) for f, p in ALL if p.get("hit_keywords") or p.get("min_digit_run")]


class TestHitKeywordData:
    def test_some_patterns_declare_keywords(self):
        assert len(KW_PATTERNS) > 0

    @pytest.mark.parametrize("f,p", KW_PATTERNS)
    def test_keywords_are_nonempty_strings(self, f, p):
        kws = p["hit_keywords"]
        assert isinstance(kws, list) and kws
        for kw in kws:
            assert isinstance(kw, str) and kw

    @pytest.mark.parametrize("f,p", KW_PATTERNS)
    def test_soundness_every_match_example_contains_a_keyword(self, f, p):
        kws = [k.lower() for k in p["hit_keywords"]]
        for ex in (p.get("examples", {}) or {}).get("match", []) or []:
            s = str(ex).lower()
            assert any(k in s for k in kws), (
                f"{f}::{p['id']} match example {ex!r} contains none of its "
                f"hit_keywords {p['hit_keywords']}"
            )


class TestMinDigitRunData:
    def test_some_patterns_declare_min_digit_run(self):
        assert len(DR_PATTERNS) > 0

    @pytest.mark.parametrize("f,p", DR_PATTERNS)
    def test_value_is_positive_int(self, f, p):
        assert isinstance(p["min_digit_run"], int) and p["min_digit_run"] >= 1

    @pytest.mark.parametrize("f,p", DR_PATTERNS)
    def test_not_above_analyzer_bound(self, f, p):
        """Stored value must not exceed the analyzer's guaranteed lower bound;
        otherwise it could over-filter. (They are generated to be equal.)"""
        computed = min_digit_run(p["pattern"])
        assert p["min_digit_run"] <= computed, (
            f"{f}::{p['id']} stored min_digit_run={p['min_digit_run']} exceeds "
            f"analyzer bound {computed} — would over-filter"
        )

    @pytest.mark.parametrize("f,p", DR_PATTERNS)
    def test_soundness_every_match_example_has_the_run(self, f, p):
        k = p["min_digit_run"]
        for ex in (p.get("examples", {}) or {}).get("match", []) or []:
            assert longest_digit_run(str(ex)) >= k, (
                f"{f}::{p['id']} match example {ex!r} has digit-run "
                f"{longest_digit_run(str(ex))} < min_digit_run {k}"
            )


class TestAhoCorasick:
    def test_finds_all_occurrences(self):
        ac = AhoCorasick()
        for w in ("he", "she", "his", "hers"):
            ac.add(w)
        ac.build()
        assert sorted({w for _, w in ac.iter_matches("ushers")}) == ["he", "hers", "she"]

    def test_no_false_positives(self):
        ac = AhoCorasick()
        ac.add("AKIA")
        ac.build()
        assert list(ac.iter_matches("no key here")) == []

    def test_requires_build(self):
        ac = AhoCorasick()
        ac.add("x")
        with pytest.raises(RuntimeError):
            list(ac.iter_matches("x"))


class TestDigitRunAnalyzer:
    @pytest.mark.parametrize(
        "pat,expected",
        [
            ("(?:[0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{9})", 4),
            ("[0-9]{4}", 4),
            ("[6-9][0-9]{9}", 10),
            ("[1-9][0-9]{5}", 6),
            (r"\bCVE-[0-9]{4}-[0-9]{4,7}\b", 4),
            ("[A-Z][a-z]+", 0),
            ("0x[a-fA-F0-9]{40}", 1),  # literal '0' is guaranteed; hex class is not digit-only
        ],
    )
    def test_known_bounds(self, pat, expected):
        assert min_digit_run(pat) == expected

    def test_longest_digit_run(self):
        assert longest_digit_run("ab123cd45678") == 5
        assert longest_digit_run("no digits") == 0


class TestPatternPrefilter:
    @pytest.fixture(scope="class")
    def pf(self):
        return PatternPrefilter(regex_dir=str(REGEX_DIR))

    def test_stats_consistent(self, pf):
        s = pf.stats()
        assert s["keyword_gated"] > 0 and s["digit_gated"] > 0 and s["patterns"] > 0

    def test_always_run_always_candidates(self, pf):
        # text with no digits and no keywords: only always-run patterns survive
        assert pf.candidate_patterns("plain words only") >= pf.always_run

    def test_no_digit_text_skips_digit_gated(self, pf):
        cands = pf.candidate_patterns("plain words only, no numbers here")
        digit_gated = {
            p.key for p in pf.patterns if p.min_digit_run and p.keywords is None
        }
        assert not (cands & digit_gated), "digit-gated patterns should be skipped"

    def test_long_digit_run_includes_card_patterns(self, pf):
        cands = pf.candidate_patterns("4111111111111111")
        assert any("credit" in k for k in cands)

    def test_email_triggers_email_pattern(self, pf):
        cands = pf.candidate_patterns("reach me at alice@example.com")
        assert any(k.endswith("::email_01") for k in cands)

    def test_end_to_end_soundness(self, pf):
        """Every gated pattern must be a candidate for each of its own match
        examples — the pre-filter must never drop a pattern for a real match."""
        for f, p in GATED:
            key = f"{f.relative_to(REGEX_DIR).as_posix()}::{p['id']}"
            for ex in (p.get("examples", {}) or {}).get("match", []) or []:
                cands = pf.candidate_patterns(str(ex))
                assert key in cands, (
                    f"pre-filter dropped {key} for its own match example {ex!r}"
                )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
