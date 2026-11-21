"""Production Re-Rank Scoring Engine for PII Pattern Engine.

Combines three additive signals into a calibrated 0–100 confidence score:
    final_score = min(keyword_avg + context_bonus + regex_score, 100)

* ``keyword_avg``   — average score of every entity keyword found in the text
                      (or within a proximity window around a regex match span).
* ``context_bonus`` — highest flat bonus when a labeled field prefix (e.g.
                      ``"SSN:"``, ``"주민등록번호:"``) is present.
* ``regex_score``   — score of the best-matching regex pattern for this entity.

Source-scoped pattern resolution:
    Several regional pattern files share bare pattern IDs (e.g. ``passport_01``
    exists in ``cn``, ``es``, ``fr``, ``in``, ``jp``, ``kr``, ``tw``, ``us``).
    This module links each entity code to its exact ``(source_file, pattern_id)``
    pairs declared in ``reference/*.yml``, so evaluating ``us_passport`` (5004)
    only runs ``regex/pii/us/identification.yml::passport_01`` rather than every
    region's ``passport_01``.
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Optional, Set, Tuple

import yaml

def _get_repo_root() -> Path:
    env_root = os.getenv("PII_PATTERN_ENGINE_ROOT")
    if env_root:
        return Path(env_root)
    return Path(__file__).resolve().parent.parent


ROOT = _get_repo_root()

# Ensure verification is importable
_VERIFICATION_DIR = str(ROOT / "verification" / "python")
if _VERIFICATION_DIR not in sys.path:
    sys.path.insert(0, _VERIFICATION_DIR)

try:
    from verification import get_verification_function
except ImportError:  # pragma: no cover
    def get_verification_function(name: str) -> Optional[Callable[[str], bool]]:
        return None


class ScoredFinding(NamedTuple):
    """A regex finding enriched with its re-rank confidence score and entity code."""

    entity_code: int
    entity: str
    pattern: str       # "<relative_file>::<pattern_id>"
    category: str
    text: str          # matched substring
    start: int
    end: int
    priority: int
    keyword_hits: List[Tuple[str, float]]
    keyword_avg: float
    context_bonus: int
    regex_hit: Optional[str]
    regex_score: int
    raw_score: float
    final_score: float
    confidence: float
    label: str
    action: str


class _CompiledPattern(NamedTuple):
    key: str           # "<relative_to_regex_dir>::<pattern_id>"
    source: str        # "regex/<relative_to_regex_dir>"
    pattern_id: str
    regex: "re.Pattern"
    verification: Optional[str]
    category: str
    priority: int


def _load_engine(root: Path = ROOT) -> dict:
    return yaml.safe_load((root / "re-rank" / "scoring.yml").read_text(encoding="utf-8"))


def _load_rerank_entities(root: Path = ROOT) -> Dict[int, dict]:
    """Load all entity scoring configs from re-rank/*.yml keyed by integer code."""
    entities: Dict[int, dict] = {}
    for f in sorted((root / "re-rank").glob("*.yml")):
        if f.name == "scoring.yml":
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for code, cfg in (data.get("entities") or {}).items():
            entities[int(code)] = cfg
    return entities


def _load_reference_entities(root: Path = ROOT) -> Dict[int, dict]:
    """Load all entity reference metadata from reference/*.yml keyed by integer code."""
    ref_entities: Dict[int, dict] = {}
    for f in sorted((root / "reference").glob("*.yml")):
        if f.name == "registry.yml":
            continue
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        for ent_name, cfg in (data.get("entities") or {}).items():
            if not isinstance(cfg, dict) or "code" not in cfg:
                continue
            code = int(cfg["code"])
            entry = dict(cfg)
            entry.setdefault("entity", ent_name)
            ref_entities[code] = entry
    return ref_entities


def _compile_all_patterns(root: Path = ROOT) -> Tuple[
    Dict[str, _CompiledPattern],
    Dict[Tuple[str, str], _CompiledPattern],
    Dict[str, List[_CompiledPattern]],
]:
    """Compile all regex patterns from regex/**/*.yml.

    Returns:
        by_key:       {"pii/us/ssn.yml::ssn_01": _CompiledPattern}
        by_src_id:    {("regex/pii/us/ssn.yml", "ssn_01"): _CompiledPattern}
        by_bare_id:   {"ssn_01": [_CompiledPattern, ...]}
    """
    regex_dir = root / "regex"
    by_key: Dict[str, _CompiledPattern] = {}
    by_src_id: Dict[Tuple[str, str], _CompiledPattern] = {}
    by_bare_id: Dict[str, List[_CompiledPattern]] = defaultdict(list)

    for f in sorted(regex_dir.rglob("*.yml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if "patterns" not in data:
            continue
        rel_to_regex = f.relative_to(regex_dir).as_posix()
        rel_to_root = f"regex/{rel_to_regex}"
        for p in data.get("patterns") or []:
            pid = p.get("id")
            if not pid:
                continue
            src = p.get("pattern", "")
            if "langs" in p and "python" in p["langs"]:
                src = p["langs"]["python"]
            flags = 0
            for flag in p.get("flags") or []:
                if flag in ("IGNORECASE", "I"):
                    flags |= re.IGNORECASE
                elif flag in ("MULTILINE", "M"):
                    flags |= re.MULTILINE
                elif flag in ("DOTALL", "S"):
                    flags |= re.DOTALL
            try:
                compiled_rx = re.compile(src, flags)
            except re.error:
                continue
            key = f"{rel_to_regex}::{pid}"
            cp = _CompiledPattern(
                key=key,
                source=rel_to_root,
                pattern_id=pid,
                regex=compiled_rx,
                verification=p.get("verification"),
                category=p.get("category", ""),
                priority=int(p.get("priority", 999)),
            )
            by_key[key] = cp
            by_src_id[(rel_to_root, pid)] = cp
            by_bare_id[pid].append(cp)

    return by_key, by_src_id, dict(by_bare_id)


class ReRankScorer:
    """Confidence scoring engine combining keyword, field-label context, and regex signals.

    Supports both:
    1. Sentence-level scoring by entity code: ``scorer.score(sentence, entity_code)``
    2. Span-aware re-ranking of detector findings: ``scorer.rerank_findings(text, findings)``
    """

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else ROOT
        engine = _load_engine(self.root)
        self.thresholds: List[dict] = engine["thresholds"]
        self.entities: Dict[int, dict] = _load_rerank_entities(self.root)
        self.reference_entities: Dict[int, dict] = _load_reference_entities(self.root)

        (
            self.patterns_by_key,
            self.patterns_by_src_id,
            self._compiled_by_bare_id,
        ) = _compile_all_patterns(self.root)

        # Backwards-compatible map {pattern_id: [re.Pattern, ...]}
        self.regex_patterns: Dict[str, List[re.Pattern]] = {
            pid: [cp.regex for cp in cps]
            for pid, cps in self._compiled_by_bare_id.items()
        }

        # Map each entity_code -> {pattern_id: [_CompiledPattern, ...]} scoped to its
        # declared source file(s) in reference/*.yml, plus reverse index pattern_key -> [entity_code]
        self.entity_patterns: Dict[int, Dict[str, List[_CompiledPattern]]] = {}
        self.pattern_key_to_entities: Dict[str, List[int]] = defaultdict(list)
        self._build_entity_pattern_links()

    def _build_entity_pattern_links(self) -> None:
        for code, entity_cfg in self.entities.items():
            ref_cfg = self.reference_entities.get(code, {})
            ref_regex_list = ref_cfg.get("regex") or []

            # Collect source files declared in reference/*.yml for this entity
            ref_by_pid: Dict[str, List[_CompiledPattern]] = defaultdict(list)
            ref_sources: List[str] = []
            for rx_entry in ref_regex_list:
                if not isinstance(rx_entry, dict):
                    continue
                src = rx_entry.get("source")
                pid = rx_entry.get("pattern_id")
                if src:
                    ref_sources.append(src)
                if src and pid and (src, pid) in self.patterns_by_src_id:
                    cp = self.patterns_by_src_id[(src, pid)]
                    ref_by_pid[pid].append(cp)
                    if code not in self.pattern_key_to_entities[cp.key]:
                        self.pattern_key_to_entities[cp.key].append(code)

            scoped: Dict[str, List[_CompiledPattern]] = {}
            for pid in (entity_cfg.get("regex_scores") or {}):
                if pid in ref_by_pid:
                    scoped[pid] = ref_by_pid[pid]
                elif pid == "default":
                    # Resolve 'default' using any pattern in the entity's reference source file(s)
                    resolved: List[_CompiledPattern] = []
                    for src in ref_sources:
                        for (s, _), cp in self.patterns_by_src_id.items():
                            if s == src:
                                resolved.append(cp)
                                if code not in self.pattern_key_to_entities[cp.key]:
                                    self.pattern_key_to_entities[cp.key].append(code)
                    if resolved:
                        scoped[pid] = resolved
                else:
                    # Fallback if not explicitly paired in reference/*.yml
                    cps = self._compiled_by_bare_id.get(pid, [])
                    scoped[pid] = cps
                    for cp in cps:
                        if code not in self.pattern_key_to_entities[cp.key]:
                            self.pattern_key_to_entities[cp.key].append(code)

            self.entity_patterns[code] = scoped

    # ── public API ──────────────────────────────────────────────────────────

    def score(
        self,
        sentence: str,
        entity_code: int,
        *,
        verify: bool = False,
        match_span: Optional[Tuple[int, int]] = None,
        window: Optional[int] = None,
    ) -> dict:
        """Score a sentence against one entity and return a full breakdown dict.

        Args:
            sentence:    Input text to score.
            entity_code: Integer reference code from ``reference/registry.yml``.
            verify:      When True, only award ``regex_score`` if the matched
                         substring also passes the pattern's verification function.
            match_span:  Optional ``(start, end)`` character offsets of a match.
            window:      Optional character radius around ``match_span`` within
                         which keywords and context labels are searched.

        Raises:
            KeyError: If ``entity_code`` is not in the registry.
        """
        entity = self.entities[entity_code]

        if match_span is not None and window is not None:
            start, end = match_span
            ctx_start = max(0, start - window)
            ctx_end = min(len(sentence), end + window)
            context_text = sentence[ctx_start:ctx_end]
        else:
            context_text = sentence

        s_lower = context_text.lower()

        keyword_avg, keyword_hits = self._keyword_score(entity, s_lower)
        context_bonus = self._context_bonus(entity, s_lower)
        regex_score, regex_hit = self._regex_score(
            entity_code, entity, sentence, verify=verify
        )

        raw = keyword_avg + context_bonus + regex_score
        final = min(raw, 100.0)
        threshold_info = self._threshold_for(final)

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
            "confidence": threshold_info["confidence"],
            "label": threshold_info["label"],
            "action": threshold_info["action"],
        }

    def label_for(self, sentence: str, entity_code: int) -> str:
        return self.score(sentence, entity_code)["label"]

    def entities_for_pattern(self, pattern_key: str) -> List[int]:
        """Return the entity code(s) linked to ``<relative_file>::<pattern_id>``."""
        norm = pattern_key
        if norm.startswith("regex/"):
            norm = norm[len("regex/"):]
        return list(self.pattern_key_to_entities.get(norm, []))

    def score_finding(
        self,
        text: str,
        pattern_key: str,
        matched_text: str,
        start: int,
        end: int,
        *,
        priority: int = 999,
        category: str = "",
        window: Optional[int] = 100,
    ) -> List[ScoredFinding]:
        """Compute re-ranked ``ScoredFinding`` objects for a verified regex match."""
        norm_key = pattern_key[len("regex/"):] if pattern_key.startswith("regex/") else pattern_key
        codes = self.entities_for_pattern(norm_key)
        pid = norm_key.split("::")[-1]
        cp = self.patterns_by_key.get(norm_key)
        if not category and cp is not None:
            category = cp.category
        if priority == 999 and cp is not None:
            priority = cp.priority

        if window is not None:
            ctx_start = max(0, start - window)
            ctx_end = min(len(text), end + window)
            context_slice = text[ctx_start:ctx_end]
        else:
            context_slice = text
        s_lower = context_slice.lower()

        results: List[ScoredFinding] = []
        for code in codes:
            entity = self.entities[code]
            kw_avg, kw_hits = self._keyword_score(entity, s_lower)
            ctx_bonus = self._context_bonus(entity, s_lower)
            rx_scores = entity.get("regex_scores") or {}
            rx_score = int(rx_scores.get(pid, rx_scores.get("default", 0)))
            raw = kw_avg + ctx_bonus + rx_score
            final = min(raw, 100.0)
            t_info = self._threshold_for(final)
            results.append(
                ScoredFinding(
                    entity_code=code,
                    entity=entity.get("entity", ""),
                    pattern=norm_key,
                    category=category,
                    text=matched_text,
                    start=start,
                    end=end,
                    priority=priority,
                    keyword_hits=kw_hits,
                    keyword_avg=round(kw_avg, 2),
                    context_bonus=ctx_bonus,
                    regex_hit=pid if rx_score > 0 else None,
                    regex_score=rx_score,
                    raw_score=round(raw, 2),
                    final_score=round(final, 2),
                    confidence=t_info["confidence"],
                    label=t_info["label"],
                    action=t_info["action"],
                )
            )
        return results

    def rerank_findings(
        self,
        text: str,
        findings: Iterable[Any],
        *,
        window: Optional[int] = 100,
        min_score: float = 0.0,
        resolve_overlaps: bool = True,
    ) -> List[ScoredFinding]:
        """Re-rank an iterable of detector findings (such as ``examples/detect.py::Finding``).

        Each finding is mapped to its entity code(s), scored using its surrounding
        context window, filtered by ``min_score``, and optionally deduplicated on
        overlapping spans (highest ``final_score`` wins, then longest span, then
        lowest ``priority`` number).
        """
        scored: List[ScoredFinding] = []
        for f in findings:
            scored.extend(
                self.score_finding(
                    text,
                    pattern_key=f.pattern,
                    matched_text=f.text,
                    start=f.start,
                    end=f.end,
                    priority=getattr(f, "priority", 999),
                    category=getattr(f, "category", ""),
                    window=window,
                )
            )

        if min_score > 0:
            scored = [sf for sf in scored if sf.final_score >= min_score]

        if not resolve_overlaps:
            return sorted(scored, key=lambda x: (x.start, x.end, -x.final_score, x.entity_code))

        # Overlap resolution: highest final_score -> longest span -> highest priority (lowest int) -> lowest entity_code
        ordered = sorted(
            scored,
            key=lambda x: (-x.final_score, -(x.end - x.start), x.priority, x.entity_code),
        )
        kept: List[ScoredFinding] = []
        for sf in ordered:
            if any(not (sf.end <= k.start or sf.start >= k.end) for k in kept):
                continue
            kept.append(sf)
        return sorted(kept, key=lambda x: (x.start, x.end))

    # ── internals ───────────────────────────────────────────────────────────

    def _keyword_score(self, entity: dict, s_lower: str) -> Tuple[float, List[Tuple[str, float]]]:
        hits = [
            (str(kw), sc)
            for kw, sc in (entity.get("keyword_scores") or {}).items()
            if str(kw).lower() in s_lower
        ]
        avg = sum(sc for _, sc in hits) / len(hits) if hits else 0.0
        return avg, hits

    def _context_bonus(self, entity: dict, s_lower: str) -> int:
        return max(
            (
                int(bonus)
                for ctx, bonus in (entity.get("context_bonus") or {}).items()
                if str(ctx).lower() in s_lower
            ),
            default=0,
        )

    def _regex_score(
        self,
        entity_code: int,
        entity: dict,
        sentence: str,
        *,
        verify: bool = False,
    ) -> Tuple[int, Optional[str]]:
        best_score = 0
        best_pid: Optional[str] = None
        scoped_map = self.entity_patterns.get(entity_code, {})

        for pid, pid_score in (entity.get("regex_scores") or {}).items():
            compiled_list = scoped_map.get(pid)
            if compiled_list is None:
                # Fallback to bare-ID lookup if entity_patterns was not populated for pid
                for rx in self.regex_patterns.get(pid, []):
                    if rx.search(sentence):
                        if pid_score > best_score:
                            best_score = pid_score
                            best_pid = pid
                        break
                continue

            for cp in compiled_list:
                matched = False
                vf = (
                    get_verification_function(cp.verification)
                    if (verify and cp.verification)
                    else None
                )
                for m in cp.regex.finditer(sentence):
                    if vf is not None and not vf(m.group(0)):
                        continue
                    matched = True
                    break
                if matched:
                    if pid_score > best_score:
                        best_score = pid_score
                        best_pid = cp.pattern_id if pid == "default" else pid
                    break
        return best_score, best_pid

    def _threshold_for(self, score: float) -> dict:
        for t in self.thresholds:
            if score >= t["min_score"]:
                return t
        return {
            "min_score": 0,
            "confidence": 0.0,
            "label": "not_pii",
            "action": "pass",
        }

    def _label(self, score: float) -> str:
        return self._threshold_for(score)["label"]
