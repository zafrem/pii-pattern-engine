# PII Pattern Engine

A comprehensive collection of regex patterns, verification functions, and a re-rank scoring system for detecting personally identifiable information (PII) and sensitive data across multiple languages and regions.

## Overview

PII Pattern Engine provides:
- **Regex Patterns**: 204 patterns for PII detection across US, Korea, Japan, China, Taiwan, India, EU, Spain, France, and common international formats
- **Re-Rank Scoring System**: Confidence scoring engine that combines keyword signals, field-label context, and regex evidence into a single 0–100 score
- **Reference Registry**: Stable numeric codes (1001–9510) for all 153 PII entity types — safe for use in logs, configs, and APIs
- **Verification Functions**: 59 Python functions for checksum validation and data quality checks
- **Keyword Mappings**: Context-aware keywords in multiple languages for improved accuracy
- **Comprehensive Tests**: 3,500+ automated tests ensuring accuracy and reliability

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
│   ├── scoring.yml              # Engine config: formula, thresholds, entity index
│   ├── kr.yml                   # Korea entities (codes 1001–1013)
│   ├── jp.yml                   # Japan entities (codes 2001–2016)
│   ├── cn.yml                   # China entities (codes 3001–3012)
│   ├── tw.yml                   # Taiwan entities (codes 4001–4016)
│   ├── us.yml                   # United States entities (codes 5001–5009)
│   ├── eu.yml                   # European Union entities (codes 6001–6054)
│   ├── in.yml                   # India entities (codes 7001–7009)
│   ├── es_fr.yml                # Spain & France entities (codes 8001–8056)
│   ├── common.yml               # Common/international entities (codes 9001–9013)
│   └── tech.yml                 # Tech tokens & secrets (codes 9501–9510)
│
├── reference/                    # Stable numeric code registry
│   ├── registry.yml             # Master flat code map (all 153 entities)
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
│   │   ├── verification.py      # 59 verification functions
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
├── tests/                        # Test suite
│   ├── test_rerank.py           # Re-rank scoring tests (400 tests)
│   ├── test_verification.py     # Verification function tests
│   ├── test_patterns.py         # Pattern validation tests
│   └── README.md
│
├── pytest.ini
└── README.md
```

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/pii-pattern-engine.git
cd pii-pattern-engine
pip install -r tests/requirements.txt
```

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

### Using the Re-Rank Scorer

```python
import re
import yaml
from pathlib import Path
from collections import defaultdict

# Load engine config and all entity definitions
engine   = yaml.safe_load(Path('re-rank/scoring.yml').read_text(encoding='utf-8'))
entities = {}
for f in Path('re-rank').glob('*.yml'):
    if f.name == 'scoring.yml':
        continue
    data = yaml.safe_load(f.read_text(encoding='utf-8'))
    for code, cfg in data.get('entities', {}).items():
        entities[int(code)] = cfg

# Score a sentence against entity 9001 (common_email)
sentence   = "Email: alice@company.org"
entity     = entities[9001]
s_lower    = sentence.lower()

kw_hits    = [(kw, sc) for kw, sc in entity['keyword_scores'].items() if kw.lower() in s_lower]
kw_avg     = sum(sc for _, sc in kw_hits) / len(kw_hits) if kw_hits else 0
ctx_bonus  = max((b for c, b in entity['context_bonus'].items() if c.lower() in s_lower), default=0)
# regex_score added after pattern matching ...

# final_score = min(kw_avg + ctx_bonus + regex_score, 100)
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
| Korea | `kr.yml` | 1001–1013 | 13 |
| Japan | `jp.yml` | 2001–2016 | 16 |
| China | `cn.yml` | 3001–3012 | 12 |
| Taiwan | `tw.yml` | 4001–4016 | 16 |
| United States | `us.yml` | 5001–5009 | 9 |
| European Union | `eu.yml` | 6001–6054 | 43 |
| India | `in.yml` | 7001–7009 | 9 |
| Spain & France | `es_fr.yml` | 8001–8056 | 12 |
| Common / International | `common.yml` | 9001–9013 | 13 |
| Tech / Tokens | `tech.yml` | 9501–9510 | 10 |
| **Total** | | | **153** |

See [re-rank/README.md](re-rank/README.md) for the full scoring reference.

## Regex Pattern Coverage

### By Region

| Region | Patterns | Key Types |
|--------|----------|-----------|
| **Korea** | 30 | RRN, alien reg., bank accounts, phone, vehicle, address |
| **EU** | 39 | National IDs, passports, VAT numbers (14 countries) |
| **Common** | 25 | Email, IP, credit cards, URLs, dates, names, IBAN |
| **Taiwan** | 20 | National IDs, bank accounts, phone, business |
| **Japan** | 17 | My Number, bank accounts, phone, address |
| **Hash/Tokens** | 10 | AWS keys, GitHub tokens, Stripe, Slack, JWT, private keys |
| **China** | 12 | National IDs, bank accounts, phone |
| **India** | 9 | Aadhaar, PAN, GST, voter ID, phone |
| **US** | 10 | SSN, ITIN, passport, driver's license, phone |
| **Spain** | 7 | DNI, NIE, CIF, phone |
| **France** | 6 | NIR, CNI, passport, phone |
| **IBAN** | 5 | DE, FR, GB, IT + generic |
| **SOX** | 7 | Financial control patterns |
| **Tech** | 7 | Patents, UUIDs, identifiers |
| **Total** | **204** | |

### Data Types

- **Financial**: Bank accounts, credit cards, IBAN, routing numbers
- **Identification**: National IDs, SSN, passports, driver's licenses
- **Contact**: Email, phone numbers, addresses
- **Network**: IPv4, IPv6, URLs, MAC addresses
- **Tokens/Secrets**: API keys, JWT, AWS keys, GitHub tokens, private keys

## Reference Registry

All 153 PII entity types have stable integer codes, safe for use in logs, pipelines, and APIs:

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

59 functions for advanced validation beyond regex:

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
    pattern: '<regex_pattern>'
    mask: "<redaction_format>"
    verification: <function_name>   # optional
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
    priority: 1                     # optional; lower = higher priority
```

## Test Suite

| File | Tests | Coverage |
|------|-------|----------|
| `test_rerank.py` | 400 | Engine config, sum_example arithmetic (153 entities), 69 sentence cases, edge cases |
| `test_verification.py` | ~133 | All 59 verification functions |
| `test_patterns.py` | ~3,000+ | YAML structure, regex compilation, match/nomatch examples |
| **Total** | **3,500+** | |

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

- [Re-Rank Scoring Guide](re-rank/README.md)
- [Verification Functions](verification/README.md)
- [Keywords](keyword/README.md)
- [Tests](tests/README.md)

---

**Note**: For legitimate use cases — data protection, compliance, and security tooling. Use responsibly and in accordance with applicable laws.
