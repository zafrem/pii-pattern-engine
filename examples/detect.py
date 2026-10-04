"""End-to-end PII detection example built on the Aho-Corasick pre-filter.

This is a *minimal reference engine* that ties the library together:

    load patterns  ->  pre-filter (Aho-Corasick keywords + digit-run gate)
                   ->  run only the candidate regexes
                   ->  verify matches (checksums)
                   ->  resolve overlaps  ->  report findings

Its purpose is to show the Aho-Corasick pre-filter in action: for a given text it
narrows ~200 patterns to a handful of candidates before any regex runs, and —
crucially — produces the *same* matches as running every regex (see the
equivalence check in `_benchmark`).

Run it:  python examples/detect.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "prefilter"))
sys.path.insert(0, str(REPO / "verification" / "python"))

from prefilter import AhoCorasick, PatternPrefilter  # noqa: E402
from verification import get_verification_function  # noqa: E402

REGEX_DIR = REPO / "regex"


class Finding(NamedTuple):
    pattern: str   # "<file>::<id>"
    category: str
    text: str      # matched substring
    start: int
    end: int
    priority: int
    confident: bool  # has a verification function or a literal keyword anchor


class _Compiled(NamedTuple):
    regex: "re.Pattern"
    verification: Optional[str]
    category: str
    priority: int
    confident: bool


class Detector:
    """A tiny PII detector built on the library's patterns + pre-filter."""

    def __init__(self) -> None:
        self.prefilter = PatternPrefilter(regex_dir=str(REGEX_DIR))
        self.patterns: Dict[str, _Compiled] = {}
        self._load()

    def _key(self, path: Path, p: dict) -> str:
        return f"{path.relative_to(REGEX_DIR).as_posix()}::{p.get('id','?')}"

    def _load(self) -> None:
        for f in sorted(REGEX_DIR.glob("**/*.yml")):
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            for p in data.get("patterns", []) or []:
                src = p["pattern"]
                if p.get("langs") and "python" in p["langs"]:  # language override (rare)
                    src = p["langs"]["python"]
                flags = re.IGNORECASE if "IGNORECASE" in (p.get("flags") or []) else 0
                try:
                    rx = re.compile(src, flags)
                except re.error:
                    continue
                confident = bool(p.get("verification")) or bool(p.get("hit_keywords"))
                self.patterns[self._key(f, p)] = _Compiled(
                    rx, p.get("verification"), p.get("category", ""),
                    int(p.get("priority", 999)), confident,
                )

    def detect(self, text: str, use_prefilter: bool = True) -> List[Finding]:
        """All raw findings. With the pre-filter only candidate patterns run; the
        result must equal the brute-force (``use_prefilter=False``) result."""
        keys: Set[str] = (
            self.prefilter.candidate_patterns(text) if use_prefilter else set(self.patterns)
        )
        out: List[Finding] = []
        for key in keys:
            comp = self.patterns.get(key)
            if comp is None:
                continue
            vf = get_verification_function(comp.verification) if comp.verification else None
            for m in comp.regex.finditer(text):
                s = m.group(0)
                if vf is not None and not vf(s):
                    continue
                out.append(
                    Finding(key, comp.category, s, m.start(), m.end(), comp.priority, comp.confident)
                )
        out.sort(key=lambda x: (x.start, x.end, x.pattern))
        return out

    def detect_clean(self, text: str) -> List[Finding]:
        """High-signal findings: keep only verification/keyword-anchored patterns,
        then drop overlapping spans (longest wins, then higher priority)."""
        confident = [f for f in self.detect(text) if f.confident]
        kept: List[Finding] = []
        for f in sorted(confident, key=lambda x: (-(x.end - x.start), x.priority)):
            if any(not (f.end <= k.start or f.start >= k.end) for k in kept):
                continue  # overlaps a longer/higher-priority match already kept
            kept.append(f)
        return sorted(kept, key=lambda x: x.start)


# --------------------------------------------------------------------------- #
# Demos
# --------------------------------------------------------------------------- #
_SAMPLES = [
    "Contact Alice at alice@example.com or push key AKIAIOSFODNN7EXAMPLE.",
    "Employee SSN 123-45-6789, card on file 4111111111111111.",
    "Just a friendly note about the meeting on the 3rd floor — nothing sensitive.",
    "Korean mobile +82 10-1234-5678; reach billing at pay@acme.co.",
]


def _spotlight() -> None:
    print("=" * 64)
    print("Aho-Corasick spotlight — one linear pass finds every keyword")
    print("=" * 64)
    ac = AhoCorasick()
    for kw in ("akia", "@", "sk_", "北京市", "cve-"):
        ac.add(kw)
    ac.build()
    text = "see CVE-2021-1234, mail a@b.com, key AKIAABCD, addr 北京市海淀区"
    print(f"keywords : akia, @, sk_, 北京市, cve-")
    print(f"text     : {text}")
    for end, kw in ac.iter_matches(text.lower()):
        print(f"   found {kw!r:8} ending at index {end}")
    print()


def _demo() -> None:
    det = Detector()
    total = len(det.patterns)
    print(f"Loaded {total} patterns. Pre-filter: {det.prefilter.stats()}\n")

    for text in _SAMPLES:
        cands = det.prefilter.candidate_patterns(text)
        print(f"TEXT: {text}")
        print(
            f"  pre-filter: {len(cands)}/{total} candidates "
            f"(skipped {total - len(cands)} without running a regex)"
        )
        findings = det.detect_clean(text)
        if findings:
            for f in findings:
                pid = f.pattern.split("::")[-1]
                print(f"    [{f.category:11}] {f.text!r:34} ({pid})")
        else:
            print("    (no high-signal PII detected)")
        print()

    print(
        "Note: format-only patterns (e.g. SWIFT/BIC = any 8 letters, or a 2-word\n"
        "      name) still produce matches here. A production pipeline suppresses\n"
        "      those with the context-scoring layer in re-rank/ — out of scope for\n"
        "      this pre-filter example.\n"
    )
    _benchmark(det)


def _benchmark(det: Detector, iterations: int = 400) -> None:
    # a realistic corpus: mostly prose (where the pre-filter skips the most)
    prose = (
        "This quarterly review covers staffing, morale, and the office move. "
        "Nothing in this paragraph is sensitive; it is ordinary narrative text "
        "that a scanner must still read in full. "
    ) * 6
    corpus = prose + " SSN 123-45-6789. " + prose

    same = det.detect(corpus, use_prefilter=True) == det.detect(corpus, use_prefilter=False)

    t0 = time.perf_counter()
    for _ in range(iterations):
        det.detect(corpus, use_prefilter=False)
    brute = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(iterations):
        det.detect(corpus, use_prefilter=True)
    pref = time.perf_counter() - t0

    print("-" * 64)
    print(f"Correctness: prefiltered == brute-force findings?  {same}")
    print(f"Brute force  ({iterations}x over {len(corpus)} chars): {brute*1000:7.1f} ms")
    print(f"Pre-filtered ({iterations}x over {len(corpus)} chars): {pref*1000:7.1f} ms")
    if pref > 0:
        print(f"Speed-up on mostly-prose text: {brute/pref:.1f}x")


if __name__ == "__main__":
    _spotlight()
    _demo()
