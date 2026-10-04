# Pattern Pre-filter

Running all 200+ regexes against every input is wasteful — for a given text most
patterns cannot possibly match. This pre-filter checks each pattern's cheap
**necessary conditions** and returns only the patterns worth evaluating. Two gate
kinds are supported, and a pattern may declare either, both, or neither:

| Gate | For | Checked by |
|------|-----|-----------|
| `hit_keywords` | patterns with a mandatory literal (`AKIA`, `@`, a province name) | one [Aho-Corasick](https://en.wikipedia.org/wiki/Aho%E2%80%93Corasick_algorithm) scan over the text |
| `min_digit_run` | pure-numeric patterns (SSN, phones, cards, IDs) | the text's longest consecutive-digit run, computed once |

A pattern is a candidate iff **every** gate it declares passes. A pattern with no
gate is always a candidate (it cannot be pre-filtered).

## `hit_keywords`

A pattern may declare `hit_keywords` in its YAML — literal strings chosen so that
**every** string the regex matches is guaranteed to contain at least one of them:

```yaml
- id: aws_access_key_01
  pattern: 'AKIA[0-9A-Z]{16}'
  hit_keywords: ['AKIA']            # every match starts with AKIA

- id: email_01
  pattern: '...@...'
  hit_keywords: ['@']               # every email contains @

- id: address_01                    # China
  pattern: '(?:北京市|天津市|…|台湾省)…'
  hit_keywords: ['北京市', '天津市', …]  # every match starts with one province
```

**Semantics:** OR — a match requires **at least one** listed keyword to be
present. Matching is **case-insensitive**.

**Soundness rule (the only rule that matters):** a pattern may carry
`hit_keywords` *only* if every possible match contains one of them. Then skipping
a keyword-gated pattern whose keywords are all absent can never drop a real
match. Patterns with no reliable literal anchor (pure digit IDs, phone numbers,
high-entropy tokens, …) simply omit `hit_keywords` and are always evaluated.

Keep keywords **selective**: a 2-letter token like `US` occurs inside ordinary
words (`push`, `repo`) and triggers constantly, so such patterns are left
unfiltered rather than given a weak keyword.

## `min_digit_run`

For patterns with no literal anchor (a bare SSN is just digits), the gate is the
**longest run of consecutive digits** that every match must contain:

```yaml
- id: ssn_01
  pattern: '(?:[0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{3}[0-9]{2}[0-9]{4})'
  min_digit_run: 4          # the dashed form's last group guarantees a 4-digit run

- id: credit_card_visa_01
  pattern: '4[0-9]{12}(?:[0-9]{3})?'
  min_digit_run: 13         # a 13-digit run is guaranteed
```

The pre-filter computes the text's longest digit run once and skips any pattern
whose `min_digit_run` exceeds it. So prose with no long number skips every card
and ID pattern, while `"4111111111111111"` keeps them.

The value is a **conservative lower bound**: the analyzer (`min_digit_run()` in
`prefilter.py`) only ever under-estimates the guaranteed run, so it can
under-filter but never over-filter. The values are stored in the YAML so other
languages compare a plain integer rather than porting the analyzer;
`tests/test_prefilter.py` recomputes them to guard against drift and asserts
every match example actually contains the run.

## Soundness, in one line

Every gate is a *necessary* condition for a match, so skipping a pattern whose
gate fails can never drop a real match. `tests/test_prefilter.py` enforces this
for both gate kinds and checks the pre-filter returns each gated pattern for its
own match examples.

## Usage

```python
from prefilter import PatternPrefilter

pf = PatternPrefilter()                       # loads regex/**/*.yml once
candidates = pf.candidate_patterns(text)      # set of "<file>::<id>" keys

# Evaluate only these regexes instead of all of them:
for key in candidates:
    run_regex(key, text)
```

`candidate_patterns(text)` returns every keyword-gated pattern whose keyword
appears in `text`, **plus** every always-run pattern (those without
`hit_keywords`). `pf.stats()` reports how many patterns are gated vs always-run.

## Implementation notes

`prefilter.py` is pure standard library (only PyYAML, to read the patterns). The
`AhoCorasick` class is a compact trie + failure links with linear-time scanning.
For high-throughput production use, feed the same `hit_keywords` data into a
native automaton (e.g. `pyahocorasick` in Python, `cloudflare/ahocorasick` in
Go) — the YAML data is the language-agnostic source of truth; only the scanner
changes.
