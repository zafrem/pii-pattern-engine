# Integration Guide — building a detector on this library

This repository is a **data + reference-function library**, not a runnable
detector. It ships:

- regex patterns (`regex/**/*.yml`) with pre-filter metadata,
- verification functions in 4 languages (`verification/{python,golang,java,javascript}/`),
- a reference pre-filter (`prefilter/prefilter.py`),
- an optional confidence-scoring config (`re-rank/`) and stable code registry (`reference/`).

To actually scan text for PII you implement a small **engine** that drives these
pieces. This document describes exactly what you must build, the contracts you
must honor, and what is provided for you.

---

## 1. The detection pipeline

```
          ┌─────────────┐   ┌───────────────┐   ┌────────────┐   ┌───────────────┐
 text ──► │ 0. load     │─► │ 1. pre-filter │─► │ 2. regex   │─► │ 3. verify     │─► matches
          │   patterns  │   │  (candidates) │   │  (match)   │   │  (checksum)   │
          └─────────────┘   └───────────────┘   └────────────┘   └───────────────┘
                                                                        │
                                                   ┌────────────────────┴───────────┐
                                                   ▼                                 ▼
                                          4. mask & apply policy        5. (optional) re-rank score
                                                                        6. (optional) map to code
```

### Stage 0 — Load patterns
Parse every `regex/**/*.yml`. Each file has `namespace`, `description`, and a
`patterns:` list. See the schema in §3.

### Stage 1 — Pre-filter (decide which regexes to run)
Most patterns cannot possibly match a given text. A pattern declares *necessary
conditions*; skip it when the text fails one. Two gate kinds:

- **`hit_keywords`** — literal anchors; ≥1 must be present (OR, case-insensitive).
  Scan the text once with an Aho-Corasick automaton built from all keywords.
- **`min_digit_run`** — the longest consecutive-digit run every match must
  contain. Compute the text's longest digit run once; skip patterns whose value
  exceeds it.

A pattern is a **candidate** iff *every* gate it declares passes. **A pattern
that declares no gate must always run** — this is the rule that, if missed,
silently drops PII (see §4). Reference implementation: `prefilter/prefilter.py`.

### Stage 2 — Regex match
For each candidate pattern, run its `pattern` regex over the text. Use an
**RE2-compatible engine** (all patterns are kept in the RE2 subset — no
backreferences/lookaround — so matching is linear-time and ReDoS-safe). Honor
`flags` (e.g. `IGNORECASE`) and, for the one pattern that has a `langs:` block
with differing variants, use your language's variant (see §5).

### Stage 3 — Verify
If a pattern has a `verification:` field, call that function (from
`verification/<your-lang>/`) on the **matched substring**. Keep the match only if
it returns `true`. Functions have the signature `(string) -> bool` and are
behavior-identical across the four languages. 91 of the patterns use one.

### Stage 4 — Mask & apply policy
Each pattern carries `mask` (redaction string) and `policy`
(`store_raw`, `action_on_match`, `severity`). Apply per your requirements.

### Stage 5 — (optional) Re-rank confidence score
If you want a 0–100 confidence instead of a boolean, load `re-rank/scoring.yml`
plus the regional `re-rank/*.yml` and combine keyword/context/regex signals. See
`re-rank/README.md`.

### Stage 6 — (optional) Stable entity codes
Map a detected entity to its stable integer code via `reference/registry.yml`
for logs/APIs.

---

## 2. What is provided vs. what you implement

| Piece | Provided | You implement |
|-------|----------|---------------|
| Pattern data (regex + metadata) | ✅ `regex/**/*.yml` | loader (parse YAML) |
| Pre-filter logic | ✅ Python (`prefilter/prefilter.py`) | port/reuse for your language |
| `hit_keywords` / `min_digit_run` data | ✅ in the YAML | read the fields |
| Verification functions | ✅ Python, Go, Java, JS | wire name → function; call on match |
| Regex execution | — | run with an RE2-compatible engine |
| Masking / policy enforcement | policy *data* only | the masking/redaction action |
| Re-rank scoring | ✅ config (`re-rank/`) | the scoring loop (formula in README) |
| Entity-code mapping | ✅ `reference/` | the lookup |

**Only Python gets a ready-made pre-filter.** For Go/Java/JS you port the
pre-filter (it is small — see §5) or precompute candidate sets. The verification
functions, by contrast, are already written in all four languages.

---

## 3. Pattern schema (fields you consume)

```yaml
- id: ssn_01                 # unique within the file
  location: us               # region code
  category: ssn              # grouping
  description: ...           # human text
  pattern: '(?:[0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{3}[0-9]{2}[0-9]{4})'  # the regex
  flags: [IGNORECASE]        # optional; apply to the regex
  verification: us_ssn_valid # optional; function name in verification/<lang>/
  hit_keywords: ['@']        # optional; pre-filter literal anchors (Stage 1)
  min_digit_run: 4           # optional; pre-filter digit gate (Stage 1)
  mask: '***-**-****'        # redaction string (Stage 4)
  match_type: exactly_matches  # see note below
  langs: {python: ..., go: ...}  # optional; per-language regex override (rare)
  policy:
    store_raw: false
    action_on_match: redact  # redact | report | alert | block | log
    severity: critical       # low | medium | high | critical
  examples:                  # match / nomatch — used by the test suite
    match: [...]
    nomatch: [...]
  metadata: {...}            # optional notes
  priority: 180              # optional; lower = higher priority (for overlap resolution)
```

**`match_type`** is `exactly_matches` for every current pattern. It governs how
the bundled `examples` are validated (whole-token = `fullmatch`). A
document-scanning engine normally uses **search / find-all** (`re.finditer` or
equivalent) to locate matches anywhere, relying on each pattern's own anchors
(`\b`, structure) to avoid over-matching — then optionally confirms the span is a
standalone token.

---

## 4. Contracts you must honor (the sharp edges)

1. **No gate ⇒ always run.** A pattern with neither `hit_keywords` nor
   `min_digit_run` cannot be pre-filtered and must be evaluated on every input.
   If you build an Aho-Corasick automaton and run *only* patterns whose keyword
   fired, you will skip every un-gated pattern (bare SSNs, phones, cards) →
   massive false negatives.
2. **Pre-filter gates are necessary, not sufficient.** A keyword hit (or a long
   digit run) means a pattern *might* match — you still run the regex to confirm
   and locate it.
3. **`hit_keywords`: OR + case-insensitive.** ≥1 keyword present ⇒ pass; match
   keywords case-insensitively.
4. **`min_digit_run`: gate = text's longest digit run ≥ value.** The stored value
   is a conservative lower bound; never raise it at runtime.
5. **All declared gates must pass (AND).** A pattern with both a keyword and a
   digit gate is a candidate only if both pass. (Both are necessary conditions.)
6. **Use an RE2-compatible engine.** The patterns are guaranteed RE2-safe; this
   is what gives linear-time (ReDoS-free) matching. On backtracking engines
   (Python `re`, Java, JS) the same patterns are safe because they avoid
   backreferences/lookaround — do not "optimize" them into unsafe forms.
7. **Verification runs on the matched text and gates the result.** `false` ⇒
   discard the match.

---

## 5. Per-language notes

### Python (most batteries included)
```python
import sys; sys.path += ["prefilter", "verification/python"]
from prefilter import PatternPrefilter
from verification import get_verification_function
import re, yaml

pf = PatternPrefilter()                 # Stage 1
# ... load patterns, then per text:
candidates = pf.candidate_patterns(text)
# for each candidate: run re.finditer(pattern, text), then
#   fn = get_verification_function(p["verification"]); keep if fn(match) is True
```
Use `google-re2` instead of `re` if you want the linear-time guarantee enforced.

### Go
- Matching: standard `regexp` (RE2) — compile `pattern` directly.
- Verification: `verification/golang/verification.go`,
  `GetVerificationFunction(name) (fn, ok)`.
- Pre-filter: port it (small): build an Aho-Corasick over all `hit_keywords`
  (e.g. `cloudflare/ahocorasick`), compute longest digit run with a one-pass
  loop, then apply the Stage-1 candidate rule reading `hit_keywords` /
  `min_digit_run` from the YAML.

### Java
- Matching: `java.util.regex.Pattern` (add `Pattern.CASE_INSENSITIVE` for the
  `IGNORECASE` flag).
- Verification: `Verification.java`, `getVerificationFunction(name)` →
  `Optional<Predicate<String>>`.
- Pre-filter: port as for Go (Aho-Corasick lib + digit-run scan).

### JavaScript / TypeScript
- Matching: native `RegExp`, or the `re2` npm package for linear-time safety.
- Verification: `verification/javascript/verification.js`,
  `getVerificationFunction(name)`.
- Pre-filter: port as above (`aho-corasick` npm or a small trie).

### The one language-divergent pattern
`regex/pii/kr/phone.yml :: mobile_hangul_spoken_01` uses look-behind/look-ahead
that RE2 cannot express, so it carries a `langs:` block: the `go` variant drops
the guards (relying on the length bound), while `python`/`java`/`javascript` keep
them. **Rule: if a pattern has `langs.<yourlang>`, use it; otherwise use
`pattern`.** All other `langs:` blocks are identical across languages and can be
ignored in favor of `pattern`.

---

## 6. Dependencies

- A YAML parser (PyYAML, gopkg.in/yaml, SnakeYAML, js-yaml, …).
- An Aho-Corasick implementation (a library, or port `prefilter.py`'s ~40-line
  one). `min_digit_run` needs no library — it is a stored integer plus a
  one-pass "longest digit run" scan.
- Recommended: an RE2 engine (`google-re2`, Go `regexp`, `re2` npm) for
  guaranteed linear-time matching.

---

## 7. Minimal end-to-end (pseudocode)

```
patterns = load_all("regex/**/*.yml")
ac       = aho_corasick(all hit_keywords, lowercased)

def scan(text):
    present  = set(ac.find(text.lower()))
    run      = longest_digit_run(text)
    for p in patterns:
        if p.hit_keywords and not (p.hit_keywords & present):   continue   # keyword gate
        if p.min_digit_run and run < p.min_digit_run:           continue   # digit gate
        for m in find_all(p.regex(flags), text):                           # Stage 2
            if p.verification and not verify(p.verification, m.text): continue  # Stage 3
            emit(mask(m, p.mask), p.policy)                                 # Stage 4
```

This reduces the "always evaluated" set from ~193 patterns to ~30; the rest run
only when their keyword or digit-run gate is satisfied.
