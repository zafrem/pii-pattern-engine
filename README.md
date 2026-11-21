# PII Pattern Engine

A comprehensive collection of regex patterns, verification functions, and a re-rank scoring system for detecting personally identifiable information (PII) and sensitive data across multiple languages and regions.

## Overview

PII Pattern Engine provides:
- **Regex Patterns**: 211 patterns for PII detection across US, Korea, Japan, China, Taiwan, India, EU, Spain, France, and common international formats
- **Re-Rank Scoring System**: Confidence scoring engine (`re-rank/rerank.py`) that combines keyword signals, field-label context, and verified regex evidence into a single 0–100 score
- **Reference Registry**: Stable numeric codes (1001–9526) for all 189 PII entity types — safe for use in logs, configs, and APIs
- **Verification Functions**: 62 checksum/validation functions, implemented identically in Python, Go, Java, and JavaScript (behavioral parity is verified against the shared pattern examples)
- **Keyword Mappings**: Context-aware keywords in multiple languages for improved accuracy
- **Comprehensive Tests**: 3,800+ automated tests ensuring accuracy and reliability


---

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/zafrem)

---

## Project Structure

```
pii-pattern-engine/
├── regex/                        # Regex pattern definitions (YAML)
│   ├── pii/                     # Personally Identifiable Information
│   │   ├── us/                 # United States (SSN, passport, phone, etc.)
│   │   ├── kr/                 # South Korea (RRN, bank accounts, phone, etc.)
│   │   ├── jp/                 # Japan (My Number, bank accounts, phone, etc.)
│   │   ├── cn/                 # China (ID cards, bank accounts, phone, etc.)
│   │   ├── tw/                 # Taiwan (ID cards, bank accounts, phone, etc.)
│   │   ├── in/                 # India (Aadhaar, PAN, GST, phone, etc.)
│   │   ├── eu/                 # European Union (VAT, national IDs, passports, etc.)
│   │   ├── es/                 # Spain (DNI, NIE, CIF, phone)
│   │   ├── fr/                 # France (NIR, CNI, passport, phone)
│   │   ├── common/             # International (email, IP, credit cards, URLs, etc.)
│   │   └── iban.yml            # IBAN patterns (DE, FR, GB, IT + generic)
│   ├── hash/                    # High-entropy tokens and secrets
│   │   └── tokens.yml          # API keys, JWT, AWS keys, GitHub tokens, etc.
│   ├── sox/                     # SOX financial control patterns
│   └── tech/                    # Technical identifiers (patents, UUIDs, etc.)
│
├── re-rank/                      # Confidence scoring engine (v2.0)
│   ├── rerank.py                # Production ReRankScorer runtime module
│   ├── scoring.yml              # Engine config: formula, thresholds, entity index
│   ├── kr.yml                   # Korea entities (codes 1001–1014)
│   ├── jp.yml                   # Japan entities (codes 2001–2018)
│   ├── cn.yml                   # China entities (codes 3001–3013)
│   ├── tw.yml                   # Taiwan entities (codes 4001–4018)
│   ├── us.yml                   # United States entities (codes 5001–5012)
│   ├── eu.yml                   # European Union entities (codes 6001–6054)
│   ├── in.yml                   # India entities (codes 7001–7010)
│   ├── es_fr.yml                # Spain & France entities (codes 8001–8056)
│   ├── common.yml               # Common/international entities (codes 9001–9023)
│   └── tech.yml                 # Tech tokens & secrets (codes 9501–9526)
│
├── reference/                    # Stable numeric code registry
│   ├── registry.yml             # Master flat code map (all 189 entities)
│   ├── kr.yml                   # Korea entity reference
│   ├── jp.yml                   # Japan entity reference
│   ├── cn.yml                   # China entity reference
│   ├── tw.yml                   # Taiwan entity reference
│   ├── us.yml                   # United States entity reference
│   ├── eu.yml                   # European Union entity reference
│   ├── in.yml                   # India entity reference
│   ├── es_fr.yml                # Spain & France entity reference
│   ├── common.yml               # Common/international entity reference
│   └── tech.yml                 # Tech tokens entity reference
│
├── verification/                 # Validation functions (multi-language)
│   ├── python/
│   │   ├── verification.py      # 62 verification functions
│   │   └── __init__.py
│   ├── golang/
│   │   ├── verification.go
│   │   └── go.mod
│   ├── java/
│   │   └── src/main/java/com/piipatternengine/verification/
│   │       └── Verification.java
│   ├── javascript/
│   │   └── verification.js
│   ├── __init__.py
│   ├── README.md
│   └── USAGE.md
│
├── keyword/                      # Context-aware keywords (multi-language)
│   ├── financial.yml
│   ├── identification.yml
│   ├── contact.yml
│   ├── network.yml
│   ├── personal.yml
│   └── README.md
│
├── prefilter/                    # Scan-optimization layer (pre-filter)
│   ├── prefilter.py             # Aho-Corasick keywords + min_digit_run gating
│   └── README.md
│
├── examples/                     # Runnable, end-to-end examples
│   ├── detect.py                # Detection engine using the Aho-Corasick pre-filter
│   └── README.md
│
├── tests/                        # Test suite
│   ├── test_rerank.py           # Re-rank scoring tests
│   ├── test_verification.py     # Verification function tests
│   ├── test_patterns.py         # Pattern validation tests
│   ├── test_prefilter.py        # Pre-filter + hit_keywords/min_digit_run tests
│   ├── test_examples.py         # End-to-end example + pre-filter equivalence tests
│   └── README.md
│
├── INTEGRATION.md                # How to build a detector on this library
├── pytest.ini
└── README.md
```

## Quick Start

### Installation

```bash
git clone https://github.com/zafrem/pii-pattern-engine.git
cd pii-pattern-engine

# Install as an editable library (pulls in the runtime dependency, PyYAML)
pip install -e .

# Optional extras
pip install -e ".[test]"     # test runner (pytest, google-re2)
pip install -e ".[vector]"   # optional ML/vector Korean name verification
```

The verification code loads its data (`datas/`, `keyword/`, …) relative to the
project root. An editable install (`pip install -e .`) works out of the box. For
a non-editable install where the data ships outside the package, point the
engine at the data with the `PII_PATTERN_ENGINE_ROOT` environment variable.

### Running Tests

```bash
# Run all tests
pytest

# Run re-rank scoring tests only
pytest tests/test_rerank.py -v

# Run pattern validation tests
pytest tests/test_patterns.py

# Run with coverage
pytest --cov=verification --cov-report=html
```

### Detecting PII (end-to-end example)

A runnable reference engine ties the patterns, the Aho-Corasick pre-filter, and
the verification functions together:

```bash
python examples/detect.py
```

```python
import sys; sys.path.insert(0, "examples")
from detect import Detector

det = Detector()
text = "SSN 123-45-6789, email alice@example.com"
for f in det.detect_clean(text):
    print(f.category, f.text)        # -> ssn 123-45-6789  /  email alice@example.com

# The pre-filter narrows ~200 patterns to a handful before any regex runs,
# and returns identical results to scanning with every pattern:
det.detect(text, use_prefilter=True) == det.detect(text, use_prefilter=False)  # True
```

See [examples/README.md](examples/README.md) and [INTEGRATION.md](INTEGRATION.md).

### Using the Re-Rank Scorer

```python
import sys; sys.path.insert(0, "re-rank")
from rerank import ReRankScorer

scorer = ReRankScorer()

# Score a sentence against entity 9001 (common_email)
res = scorer.score("Email: alice@company.org", 9001)
print(res["final_score"], res["label"], res["action"])
# -> 100 definite_pii redact

# Or run end-to-end detection + confidence re-ranking via Detector:
sys.path.insert(0, "examples")
from detect import Detector

det = Detector()
for r in det.detect_reranked("주민등록번호: 900101-1234568", min_score=60):
    print(r.entity_code, r.entity, r.final_score, r.label, r.finding.text)
```

See [re-rank/README.md](re-rank/README.md) for the full scoring guide and integration examples.

### Using Regex Patterns

```python
import re
import yaml
from verification.python.verification import luhn

with open('regex/pii/common/credit-cards.yml') as f:
    patterns = yaml.safe_load(f)

visa_pattern = patterns['patterns'][0]['pattern']
text = "My card is 4111111111111111"
match = re.search(visa_pattern, text)
if match and luhn(match.group(0)):
    print("Valid Visa card detected")
```

### Using Verification Functions

```python
from verification.python.verification import (
    iban_mod97, luhn, high_entropy_token,
    us_ssn_valid, kr_rrn_valid, cn_national_id_valid,
    jp_my_number_valid, india_aadhaar_valid
)

iban_mod97("GB82WEST12345698765432")   # True — valid IBAN
luhn("4111111111111111")               # True — valid Luhn
kr_rrn_valid("850101-1234567")        # True — valid Korean RRN
cn_national_id_valid("11010519491231002X")  # True
```

## Re-Rank Scoring System

The re-rank engine produces a confidence score (0–100) using three additive signals:

```
final_score = min(keyword_avg + context_bonus + regex_score, 100)
```

| Signal | Description |
|--------|-------------|
| `keyword_avg` | Average score of all keywords found in the text (0–100 each) |
| `context_bonus` | Flat bonus when a labeled field prefix (e.g. `"SSN:"`) is detected |
| `regex_score` | Score of the best-matching regex pattern (calibrated 30–65) |

### Confidence Thresholds

| Score | Label | Action |
|-------|-------|--------|
| 100 | `definite_pii` | redact |
| 80–99 | `high_confidence_pii` | redact |
| 60–79 | `probable_pii` | flag |
| 40–59 | `possible_pii` | review |
| 20–39 | `low_confidence_pii` | log |
| 0–19 | `not_pii` | pass |

### Entity Coverage

| Region | File | Entity Codes | Count |
|--------|------|-------------|-------|
| Korea | `kr.yml` | 1001–1014 | 14 |
| Japan | `jp.yml` | 2001–2018 | 18 |
| China | `cn.yml` | 3001–3013 | 13 |
| Taiwan | `tw.yml` | 4001–4018 | 18 |
| United States | `us.yml` | 5001–5012 | 12 |
| European Union | `eu.yml` | 6001–6054 | 43 |
| India | `in.yml` | 7001–7010 | 10 |
| Spain & France | `es_fr.yml` | 8001–8056 | 12 |
| Common / International | `common.yml` | 9001–9023 | 23 |
| Tech / Tokens | `tech.yml` | 9501–9526 | 26 |
| **Total** | | | **189** |

See [re-rank/README.md](re-rank/README.md) for the full scoring reference.

## Regex Pattern Coverage

### By Region

| Region | Patterns | Key Types |
|--------|----------|-----------|
| **Korea** | 30 | RRN, alien reg., bank accounts, phone, vehicle, address, zipcode |
| **EU** | 39 | National IDs, passports, VAT numbers (14 countries) |
| **Common** | 32 | Email, IP, credit cards, URLs, dates, names, MAC, IMEI, BIC, coordinates |
| **Taiwan** | 20 | National IDs, bank accounts, phone, business, zipcode |
| **Japan** | 17 | My Number, bank accounts, phone, address, corporate number, zipcode |
| **Hash/Tokens** | 10 | AWS keys, GitHub tokens, Stripe, Slack, JWT, private keys |
| **China** | 12 | National IDs, bank accounts, phone, USCC, zipcode |
| **India** | 9 | Aadhaar, PAN, GST, voter ID, phone, pincode |
| **US** | 10 | SSN, ITIN, EIN, NPI, passport, driver's license, phone, zipcode |
| **Spain** | 7 | DNI, NIE, CIF, phone |
| **France** | 6 | NIR, CNI, passport, phone |
| **IBAN** | 5 | DE, FR, GB, IT + generic |
| **SOX** | 7 | Financial control patterns |
| **Tech** | 7 | Patents, UUIDs, identifiers |
| **Total** | **211** | |

### Data Types

- **Financial**: Bank accounts, credit cards, IBAN, routing numbers
- **Identification**: National IDs, SSN, passports, driver's licenses
- **Contact**: Email, phone numbers, addresses
- **Network**: IPv4, IPv6, URLs, MAC addresses
- **Tokens/Secrets**: API keys, JWT, AWS keys, GitHub tokens, private keys

## Reference Registry

All 189 PII entity types have stable integer codes, safe for use in logs, pipelines, and APIs:

```yaml
# reference/registry.yml (excerpt)
kr_name:                      1001
kr_rrn:                       1002
us_ssn:                       5002
common_email:                 9001
tech_aws_access_key:          9502
tech_github_token:            9504
tech_private_key:             9510
```

Regional detail files (`reference/kr.yml`, `reference/eu.yml`, etc.) provide per-entity metadata: severity, PII type, linked regex patterns, and keyword categories.

## Verification Functions

62 functions for advanced validation beyond regex (available in Python, Go, Java, and JavaScript):

### Core

| Function | Purpose |
|----------|---------|
| `iban_mod97` | IBAN mod-97 checksum |
| `luhn` | Credit card Luhn algorithm |
| `high_entropy_token` | API key / secret entropy check |
| `not_timestamp` | Reject timestamp-like numbers |
| `ipv4_public` | Validate public IPv4 |
| `cjk_name_standalone` | CJK standalone name format |

### Regional

| Region | Functions |
|--------|-----------|
| **US** | `us_ssn_valid` |
| **Korea** | `kr_rrn_valid`, `kr_alien_registration_valid`, `kr_corporate_registration_valid`, `kr_business_registration_valid`, `korean_bank_account_valid` |
| **Japan** | `jp_my_number_valid` |
| **China / Taiwan** | `cn_national_id_valid`, `tw_national_id_valid` |
| **India** | `india_aadhaar_valid`, `india_pan_valid` |
| **Europe** | `spain_dni_valid`, `spain_nie_valid`, `netherlands_bsn_valid`, `poland_pesel_valid`, `sweden_personnummer_valid`, `france_insee_valid`, `belgium_rrn_valid`, `finland_hetu_valid` |

## Pattern File Format

```yaml
namespace: <namespace>
description: <description>

patterns:
  - id: <unique_id>
    location: <country_code>        # us, kr, jp, cn, tw, in, eu, comm
    category: <category>
    description: <description>
    pattern: '<regex_pattern>'      # single source of truth; RE2-compatible
    mask: "<redaction_format>"
    verification: <function_name>   # optional
    hit_keywords: ['AKIA', '@']     # optional; literal anchors for the
                                    # Aho-Corasick pre-filter (see prefilter/)
    min_digit_run: 4                # optional; longest consecutive-digit run every
                                    # match must contain — numeric pre-filter gate
    flags:                          # optional
      - IGNORECASE
    examples:
      match:
        - "example_match"
      nomatch:
        - "non_match"
    policy:
      store_raw: false
      action_on_match: redact
      severity: critical
    metadata:
      note: "Optional notes"
    match_type: exactly_matches     # exactly_matches | contains
    priority: 1                     # optional; lower = higher priority
```

Every pattern is written for **cross-engine portability**, so the same `pattern`
string runs identically on Python `re`, Go (RE2), Java, and JavaScript:

- **No engine-specific constructs** — no backreferences, lookaround, inline
  flags, named groups, `\p{...}`, or POSIX classes. This keeps patterns inside
  the RE2 subset (enforced by `tests/test_patterns.py::TestPatternRE2`), which
  also guarantees linear-time matching (ReDoS safety) on every engine.
- **Explicit ASCII character classes** instead of `\d` and `\s`. `\d`/`\s` are
  Unicode-aware in Python (and partly in JS) but ASCII-only in Go/Java, so a
  bare `\d` would match fullwidth `０-９` or Arabic-Indic digits in Python only.
  Patterns use `[0-9]` and `[\t\n\f\r ]` so digit/whitespace matching is
  byte-for-byte identical across languages. (`\b` is used only next to ASCII
  characters, where all engines agree.)

Because the regex is identical across languages, each pattern carries a single
`pattern` field rather than per-language copies.

### What each field is for

| Field | Used for | Consumed by |
|-------|----------|-------------|
| `id` | Stable identifier within the file | logs, dedup, overlap resolution |
| `location` / `category` | Grouping & routing (region, data type) | filtering which patterns to run |
| `pattern` | The detector itself — one RE2-safe regex | the regex engine (Stage 2) |
| `flags` | Regex flags, e.g. `IGNORECASE` | the regex engine |
| `verification` | Name of a checksum/validity function to confirm a raw match (Luhn, mod-97, SSA rules…) | `verification/<lang>/` (Stage 3) |
| **`hit_keywords`** | **Literal anchors for a multi-pattern pre-scan — build an Aho-Corasick automaton and skip the pattern when none are present. Pure scan optimization.** | `prefilter/` (Stage 1) |
| **`min_digit_run`** | **Scan optimization for numeric patterns with no literal anchor — skip the pattern unless the text has a digit run this long.** | `prefilter/` (Stage 1) |
| `mask` | Redaction/replacement string once matched | masking step (Stage 4) |
| `match_type` | How a match relates to the token (whole-token vs substring); drives example validation | test suite / scanning strategy |
| `policy` | `action_on_match` (redact/report/…), `severity`, `store_raw` — what to *do* with a hit | your enforcement/DLP layer |
| `priority` | Tie-breaking when spans overlap (lower = higher priority) | match-resolution step |
| `metadata` | Human notes (provider, type) | documentation only |
| `examples` | `match`/`nomatch` fixtures | the test suite |

`hit_keywords` and `min_digit_run` are **optional optimization hints only** — they
never change *what* is detected, only *how fast*. A detector that ignores them is
still correct (just slower); a detector that uses them must follow the soundness
rules in [prefilter/README.md](prefilter/README.md). See
[INTEGRATION.md](INTEGRATION.md) for the full pipeline and the contracts a
consuming engine must honor.

## Test Suite

| File | Tests | Coverage |
|------|-------|----------|
| `test_rerank.py` | 400 | Engine config, sum_example arithmetic (153 entities), 69 sentence cases, edge cases |
| `test_verification.py` | ~133 | All 55 verification functions |
| `test_patterns.py` | ~3,000+ | YAML structure, regex compilation, match/nomatch examples |
| `test_prefilter.py` | ~560 | Aho-Corasick automaton, `hit_keywords`/`min_digit_run` soundness, gate behavior |
| `test_examples.py` | ~16 | End-to-end example; pre-filter vs brute-force equivalence |
| **Total** | **3,800+** | |

```bash
# Run all
pytest

# Re-rank only
pytest tests/test_rerank.py -v

# Filter by entity
pytest tests/test_rerank.py -k "kr_rrn or us_ssn"

# Pattern tests for a specific region
pytest tests/test_patterns.py -k "credit_card"
```

## Development

### Adding a New Pattern

1. Add the pattern to the appropriate `regex/pii/<region>/` YAML file
2. Include all required fields and match/nomatch examples
3. Run `pytest tests/test_patterns.py`

### Adding a New Re-Rank Entity

1. Add the entity block to the relevant `re-rank/<region>.yml` with `keyword_scores`, `context_bonus`, `regex_scores`, and a `sum_example`
2. Add the numeric code to `reference/registry.yml` and the regional `reference/<region>.yml`
3. Add sentence test cases to `tests/test_rerank.py`
4. Run `pytest tests/test_rerank.py`

### Adding a Verification Function

1. Add the function to `verification/python/verification.py`
2. Register it in `VERIFICATION_FUNCTIONS`
3. Add tests to `tests/test_verification.py`
4. Run `pytest tests/test_verification.py`

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Resources

- [Integration Guide](INTEGRATION.md) — how to build a detector on this library (the pipeline, what you must implement, and the contracts)
- [Examples](examples/README.md) — runnable end-to-end detection using the Aho-Corasick pre-filter
- [Pre-filter (Aho-Corasick + digit-run)](prefilter/README.md) — scan-optimization layer
- [Re-Rank Scoring Guide](re-rank/README.md)
- [Verification Functions](verification/README.md)
- [Keywords](keyword/README.md)
- [Tests](tests/README.md)

---

**Note**: For legitimate use cases — data protection, compliance, and security tooling. Use responsibly and in accordance with applicable laws.

