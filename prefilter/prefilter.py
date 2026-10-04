"""Pre-filter for PII pattern matching: decide which regexes are worth running.

Running all 200+ regexes against every input is wasteful — for a given text most
patterns cannot possibly match. Each pattern may declare *necessary conditions*
that any match is guaranteed to satisfy; the pre-filter checks those cheaply and
skips patterns whose conditions the text fails. Two kinds are supported:

* ``hit_keywords`` — literal anchor strings (>=1 must be present). Scanned with a
  single Aho-Corasick automaton over the whole text. Good for patterns with a
  mandatory literal (``AKIA``, ``@``, a province name, ...).

* ``min_digit_run`` — the longest run of consecutive digits that every match must
  contain. Good for the pure-numeric patterns (SSN, phones, cards, IDs) that have
  no literal anchor. The text's longest digit run is computed once.

A pattern is a candidate iff **all** the conditions it declares pass. A pattern
that declares neither is always a candidate (it cannot be pre-filtered).

Soundness: every declared condition is *necessary* for a match, so skipping a
pattern whose condition fails can never drop a real match. Keyword matching is
case-insensitive, which only ever adds candidates. ``min_digit_run`` values are a
conservative lower bound (see ``min_digit_run()``), so they under-filter if
anything — never over-filter.

Pure standard library (only PyYAML, to read the patterns). ``min_digit_run`` is
stored in the YAML so other-language engines need only compare integers; the
analyzer below lets the test-suite recompute and guard against drift.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterator, List, NamedTuple, Optional, Set, Tuple

import yaml


# --------------------------------------------------------------------------- #
# Aho-Corasick multi-string matcher
# --------------------------------------------------------------------------- #
class AhoCorasick:
    """Minimal Aho-Corasick multi-string matcher (linear-time scan)."""

    __slots__ = ("_children", "_fail", "_outputs", "_built")

    def __init__(self) -> None:
        self._children: List[Dict[str, int]] = [{}]
        self._fail: List[int] = [0]
        self._outputs: List[List[str]] = [[]]
        self._built = False

    def add(self, word: str) -> None:
        if not word:
            raise ValueError("keyword must be non-empty")
        node = 0
        for ch in word:
            nxt = self._children[node].get(ch)
            if nxt is None:
                nxt = len(self._children)
                self._children.append({})
                self._fail.append(0)
                self._outputs.append([])
                self._children[node][ch] = nxt
            node = nxt
        self._outputs[node].append(word)

    def build(self) -> None:
        q: deque[int] = deque()
        for nxt in self._children[0].values():
            self._fail[nxt] = 0
            q.append(nxt)
        while q:
            cur = q.popleft()
            for ch, nxt in self._children[cur].items():
                q.append(nxt)
                f = self._fail[cur]
                while f and ch not in self._children[f]:
                    f = self._fail[f]
                self._fail[nxt] = self._children[f].get(ch, 0)
                self._outputs[nxt].extend(self._outputs[self._fail[nxt]])
        self._built = True

    def iter_matches(self, text: str) -> Iterator[Tuple[int, str]]:
        if not self._built:
            raise RuntimeError("call build() before iter_matches()")
        node = 0
        children, fail, outputs = self._children, self._fail, self._outputs
        for i, ch in enumerate(text):
            while node and ch not in children[node]:
                node = fail[node]
            node = children[node].get(ch, 0)
            for w in outputs[node]:
                yield i, w


# --------------------------------------------------------------------------- #
# min_digit_run analyzer: conservative lower bound on the longest run of
# consecutive digits that EVERY match of a regex must contain.
# --------------------------------------------------------------------------- #
import re as _re

_DIGIT_CLASS = _re.compile(r"(?:[0-9]-[0-9]|[0-9])+$")  # e.g. 0-9, 6-9, 1-9, 13579


class _Run(NamedTuple):
    m: int  # guaranteed max run anywhere
    p: int  # guaranteed leading (prefix) run
    s: int  # guaranteed trailing (suffix) run
    d: bool  # whole thing is contiguous mandatory digits (can bridge neighbours)


def _empty() -> _Run:
    return _Run(0, 0, 0, True)  # zero-width, transparent


def _break() -> _Run:
    return _Run(0, 0, 0, False)  # mandatory non-digit atom


def _dig(n: int) -> _Run:
    return _Run(n, n, n, True)  # mandatory digit block of length n


def _cat(a: _Run, b: _Run) -> _Run:
    return _Run(
        max(a.m, b.m, a.s + b.p),
        a.p + (b.p if a.d else 0),
        b.s + (a.s if b.d else 0),
        a.d and b.d,
    )


def _alt(a: _Run, b: _Run) -> _Run:
    return _Run(min(a.m, b.m), min(a.p, b.p), min(a.s, b.s), a.d and b.d)


class _DigitRunParser:
    def __init__(self, p: str) -> None:
        self.p, self.i, self.n = p, 0, len(p)

    def _pk(self) -> str:
        return self.p[self.i] if self.i < self.n else ""

    def parse(self) -> _Run:
        node = self._concat()
        while self._pk() == "|":
            self.i += 1
            node = _alt(node, self._concat())
        return node

    def _concat(self) -> _Run:
        node = _empty()
        while self.i < self.n and self._pk() not in "|)":
            node = _cat(node, self._quant())
        return node

    def _skip_group(self) -> None:
        depth = 0
        while self.i < self.n:
            c = self.p[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                self.i += 1
                if depth == 0:
                    return
                continue
            self.i += 1

    def _quant(self) -> _Run:
        atom = self._atom()
        c = self._pk()
        if c == "?" or c == "*":
            self.i += 1
            if self._pk() == "?":
                self.i += 1
            return _break()  # optional -> conservative break
        if c == "+":
            self.i += 1
            if self._pk() == "?":
                self.i += 1
            return atom
        if c == "{":
            j = self.p.find("}", self.i)
            spec = self.p[self.i + 1 : j]
            self.i = j + 1
            if self._pk() == "?":
                self.i += 1
            lo_str = spec.split(",")[0]
            lo = int(lo_str) if lo_str.isdigit() else 0
            if lo == 0:
                return _break()
            acc = atom
            for _ in range(lo - 1):
                acc = _cat(acc, atom)
            return acc
        return atom

    def _atom(self) -> _Run:
        c = self._pk()
        if c == "(":
            if self.p[self.i : self.i + 3] in ("(?=", "(?!") or self.p[
                self.i : self.i + 4
            ] in ("(?<=", "(?<!"):
                self._skip_group()
                return _break()
            self.i += 1
            if self.p[self.i : self.i + 2] == "?:":
                self.i += 2
            node = self.parse()
            if self._pk() == ")":
                self.i += 1
            return node
        if c == "[":
            j = self.i + 1
            if self.p[j : j + 1] == "^":
                j += 1
            if self.p[j : j + 1] == "]":
                j += 1
            while j < self.n and self.p[j] != "]":
                if self.p[j] == "\\":
                    j += 1
                j += 1
            content = self.p[self.i + 1 : j]
            self.i = j + 1
            return _dig(1) if _DIGIT_CLASS.match(content) else _break()
        if c == "\\":
            esc = self.p[self.i + 1 : self.i + 2]
            self.i += 2
            return _empty() if esc == "b" else _break()
        if c in "^$":
            self.i += 1
            return _empty()
        self.i += 1
        return _dig(1) if c.isdigit() else _break()


def min_digit_run(pattern: str) -> int:
    """Lower bound on the longest consecutive-digit run every match must contain.

    Conservative: may return a value lower than the true guaranteed run, never
    higher — so using it to skip patterns is always sound.
    """
    try:
        return _DigitRunParser(pattern).parse().m
    except Exception:
        return 0


def longest_digit_run(text: str) -> int:
    """Length of the longest run of consecutive ASCII digits in ``text``."""
    best = cur = 0
    for ch in text:
        if "0" <= ch <= "9":
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


# --------------------------------------------------------------------------- #
# The pre-filter
# --------------------------------------------------------------------------- #
class _Pattern(NamedTuple):
    key: str
    keywords: Optional[frozenset]  # None => no keyword gate
    min_digit_run: int  # 0 => no digit gate


class PatternPrefilter:
    """Answers "which patterns are worth evaluating against this text?"."""

    def __init__(self, regex_dir: Optional[str] = None) -> None:
        if regex_dir is not None:
            self.regex_dir = Path(regex_dir)
        else:
            self.regex_dir = Path(__file__).resolve().parent.parent / "regex"
        self.patterns: List[_Pattern] = []
        self.keyword_to_patterns: Dict[str, Set[str]] = defaultdict(set)
        self._ac = AhoCorasick()
        self._load()

    def _pattern_key(self, path: Path, pattern: dict) -> str:
        return f"{path.relative_to(self.regex_dir).as_posix()}::{pattern.get('id', '?')}"

    def _load(self) -> None:
        files = sorted(self.regex_dir.glob("**/*.yml")) + sorted(
            self.regex_dir.glob("**/*.yaml")
        )
        for path in files:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for pattern in data.get("patterns", []) or []:
                key = self._pattern_key(path, pattern)
                kws = pattern.get("hit_keywords")
                kwset = frozenset(k.lower() for k in kws) if kws else None
                mdr = int(pattern.get("min_digit_run", 0) or 0)
                self.patterns.append(_Pattern(key, kwset, mdr))
                if kwset:
                    for kw in kwset:
                        self.keyword_to_patterns[kw].add(key)
        for kw in self.keyword_to_patterns:
            self._ac.add(kw)
        self._ac.build()

    @property
    def always_run(self) -> Set[str]:
        """Patterns with no gate at all — cannot be pre-filtered."""
        return {p.key for p in self.patterns if p.keywords is None and p.min_digit_run == 0}

    @property
    def gated_patterns(self) -> Set[str]:
        """Patterns with at least one gate (skippable for some inputs)."""
        return {p.key for p in self.patterns if p.keywords is not None or p.min_digit_run}

    def candidate_patterns(self, text: str) -> Set[str]:
        """Return the pattern keys worth evaluating against ``text``.

        A pattern is included iff every gate it declares passes (keyword present
        and/or the text's longest digit run is long enough). Patterns with no
        gate are always included.
        """
        present_kw: Set[str] = set()
        lowered = text.lower()
        for _, kw in self._ac.iter_matches(lowered):
            present_kw.add(kw)
        run = longest_digit_run(text)

        candidates: Set[str] = set()
        for p in self.patterns:
            if p.keywords is not None and not (p.keywords & present_kw):
                continue
            if p.min_digit_run and run < p.min_digit_run:
                continue
            candidates.add(p.key)
        return candidates

    def stats(self) -> Dict[str, int]:
        return {
            "patterns": len(self.patterns),
            "keyword_gated": sum(1 for p in self.patterns if p.keywords is not None),
            "digit_gated": sum(1 for p in self.patterns if p.min_digit_run),
            "always_run": len(self.always_run),
            "keywords": len(self.keyword_to_patterns),
        }


if __name__ == "__main__":
    pf = PatternPrefilter()
    print("prefilter stats:", pf.stats())
    for sample in (
        "Contact alice@example.com or push key AKIAIOSFODNN7EXAMPLE",
        "Just some prose with no identifiers at all, page 7.",
        "card 4111111111111111 on file",
    ):
        cands = pf.candidate_patterns(sample)
        print(f"\nText: {sample!r}")
        print(
            f"  candidates: {len(cands)} / {len(pf.patterns)}  "
            f"(skipped {len(pf.patterns) - len(cands)})"
        )
