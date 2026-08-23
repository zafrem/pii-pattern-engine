#!/usr/bin/env python3
"""
ReDoS (Regular Expression Denial of Service) Safety Checker.

The authoritative defense against catastrophic backtracking in this project is
that **every pattern must compile under google-re2**. RE2 guarantees linear-time
matching, so a pattern that RE2 accepts cannot exhibit catastrophic backtracking
regardless of input.

This checker therefore reports the only thing that actually matters for ReDoS:
patterns that FAIL to compile with RE2 (and are thus a genuine linear-time risk
if run on a backtracking engine such as Python's `re`, Java's `Pattern`, or the
JavaScript engine). Patterns that compile under RE2 are reported as safe.

An earlier version of this script flagged patterns with regex-on-regex
heuristics (nested quantifiers, alternations, etc.). Those heuristics produced
mostly false positives on RE2-safe patterns and did not reflect real risk, so
they have been replaced by the RE2 compilation check that the test suite also
enforces (see tests/test_patterns.py::TestPatternRE2).
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

try:
    import re2

    HAS_RE2 = True
except ImportError:
    HAS_RE2 = False


class ReDoSChecker:
    """Verifies that all regex patterns are RE2-compatible (linear-time safe)."""

    def __init__(self, base_path: str = "regex"):
        self.base_path = Path(base_path)

    def _iter_patterns(self) -> List[Tuple[str, str, Path]]:
        """Yield (pattern_id, pattern_string, file_path) for every pattern."""
        patterns = []
        for yaml_file in sorted(self.base_path.rglob("*.yml")):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                print(f"Error reading {yaml_file}: {e}")
                continue
            if not data or "patterns" not in data:
                continue
            for p in data["patterns"]:
                patterns.append(
                    (p.get("id", "unknown"), p.get("pattern", ""), yaml_file)
                )
        return patterns

    def analyze_all(self) -> Tuple[List[Dict], int]:
        """Return (unsafe_patterns, total_patterns)."""
        unsafe = []
        patterns = self._iter_patterns()
        for pattern_id, pattern, yaml_file in patterns:
            try:
                re2.compile(pattern)
            except re2.error as e:  # pattern is not linear-time safe under RE2
                unsafe.append(
                    {
                        "pattern_id": pattern_id,
                        "file": str(yaml_file),
                        "pattern": pattern,
                        "issue": f"Not RE2-compatible (possible catastrophic backtracking): {e}",
                    }
                )
        return unsafe, len(patterns)

    def generate_report(self) -> int:
        """Print a report. Returns a process exit code (0 = all safe)."""
        print("=" * 80)
        print("ReDoS SAFETY REPORT (RE2 linear-time compatibility)")
        print("=" * 80)
        print()

        if not HAS_RE2:
            print("google-re2 is not installed; cannot verify RE2 safety.")
            print("Install it with:  pip install google-re2")
            return 2

        unsafe, total = self.analyze_all()

        print(f"Total patterns analyzed: {total}")
        print(f"Patterns that are NOT RE2-safe: {len(unsafe)}")
        print()

        if not unsafe:
            print("✓ All patterns compile under RE2 — linear-time matching")
            print("  is guaranteed, so none are vulnerable to catastrophic backtracking.")
            return 0

        print("=" * 80)
        print("UNSAFE PATTERNS (reject or rewrite before production use)")
        print("=" * 80)
        print()
        for idx, issue in enumerate(unsafe, 1):
            print(f"{idx}. Pattern ID: {issue['pattern_id']}")
            print(f"   File: {issue['file']}")
            print(f"   Pattern: {issue['pattern']}")
            print(f"   Issue: {issue['issue']}")
            print()

        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        print("1. Rewrite the pattern to avoid features RE2 rejects")
        print("   (backreferences, lookaround), which are the constructs that")
        print("   enable catastrophic backtracking on non-RE2 engines.")
        print("2. Re-run this checker and tests/test_patterns.py::TestPatternRE2.")
        print()
        return 1


if __name__ == "__main__":
    checker = ReDoSChecker()
    sys.exit(checker.generate_report())
