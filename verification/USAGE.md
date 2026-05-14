# Verification Functions Usage Guide

## Overview

The verification functions have been centralized in `pii-pattern-engine/verification/python/` to enable code reuse across different pattern detection implementations and languages.

## Directory Structure

```
pii-pattern-engine/
├── verification/
│   ├── README.md              # Full documentation
│   ├── USAGE.md               # This file - Quick usage guide
│   └── python/
│       ├── __init__.py        # Module exports
│       └── verification.py    # Core verification functions
├── regex/
│   └── hash/
│       └── tokens.yml         # Token pattern definitions
└── regex/
    └── pii/
        └── *.yml              # PII pattern definitions
```

## Quick Start (Python)

### Option 1: Import from centralized location (recommended for new code)

```python
# Direct import from verification module
from pii_pattern_engine.verification.python import (
    high_entropy_token,
    luhn,
    iban_mod97,
    korean_bank_account_valid,
)

# Use in your code
if high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P"):
    print("High entropy token detected")
```

### Option 2: Import from datadetector (backward compatible)

```python
# Existing code continues to work
from datadetector.verification import (
    high_entropy_token,
    luhn,
    get_verification_function,
)

# The datadetector module now re-exports from centralized location
validator = get_verification_function("luhn")
is_valid = validator("4532015112830366")
```

## Available Verification Functions

### Generic / Utility

| Function | Purpose | Example |
|----------|---------|---------|
| `iban_mod97` | IBAN Mod-97 checksum | `iban_mod97("GB82WEST12345698765432")` |
| `luhn` | Luhn checksum (credit cards) | `luhn("4532015112830366")` |
| `high_entropy_token` | API keys / secrets (entropy ≥ 4.5) | `high_entropy_token("ghp_...")` |
| `not_timestamp` | Reject Unix timestamps | `not_timestamp("1234567890")` |
| `generic_number_not_timestamp` | Generic timestamp rejection | `generic_number_not_timestamp(...)` |
| `contains_letter` | Has alphabetic chars | `contains_letter("ABC123")` |
| `not_repeating_pattern` | Reject sequential/all-same patterns | `not_repeating_pattern("1111")` |
| `dms_coordinate` | GPS DMS coordinates | `dms_coordinate("37°46′29.7″N")` |
| `ipv4_public` | Public (non-private) IPv4 | `ipv4_public("8.8.8.8")` |
| `credit_card_bin_valid` | Credit card BIN + Luhn | `credit_card_bin_valid("4532015112830366")` |

### Name Validators

| Function | Purpose | Example |
|----------|---------|---------|
| `english_name_valid` | English first + last name | `english_name_valid("John Smith")` |
| `chinese_name_valid` | Chinese name (surname lookup) | `chinese_name_valid("王伟")` |
| `korean_name_valid` | Korean name (surname lookup) | `korean_name_valid("김민준")` |
| `japanese_name_kanji_valid` | Japanese kanji name | `japanese_name_kanji_valid("田中花子")` |
| `cjk_name_standalone` | CJK-only character string | `cjk_name_standalone("王伟")` |

### Address Validators

| Function | Purpose | Example |
|----------|---------|---------|
| `korean_address_valid` | Korean province-level check | `korean_address_valid("서울특별시 강남구...")` |
| `japanese_address_valid` | Japanese prefecture check | `japanese_address_valid("東京都渋谷区...")` |
| `chinese_address_valid` | Chinese province check | `chinese_address_valid("北京市朝阳区...")` |
| `us_address_valid` | US city + state (Python only) | `us_address_valid("New York, NY")` |

### National ID / Government ID

| Function | Purpose |
|----------|---------|
| `us_ssn_valid` | US Social Security Number |
| `cn_national_id_valid` | Chinese National ID (18-digit checksum) |
| `tw_national_id_valid` | Taiwan National ID |
| `india_aadhaar_valid` | India Aadhaar (Verhoeff algorithm) |
| `india_pan_valid` | India PAN format |
| `kr_rrn_valid` | Korean Resident Registration Number |
| `kr_alien_registration_valid` | Korean Alien Registration Number |
| `kr_business_registration_valid` | Korean Business Registration Number |
| `kr_corporate_registration_valid` | Korean Corporate Registration Number |
| `jp_my_number_valid` | Japanese My Number |
| `jp_corporate_number_valid` | Japanese Corporate Number |
| `tw_ubn_valid` | Taiwan Unified Business Number |
| `us_npi_valid` | US National Provider Identifier |
| `uk_nino_valid` | UK National Insurance Number |
| `spain_dni_valid` | Spanish DNI |
| `spain_nie_valid` | Spanish NIE |
| `netherlands_bsn_valid` | Dutch BSN |
| `poland_pesel_valid` | Polish PESEL |
| `sweden_personnummer_valid` | Swedish Personnummer |
| `france_insee_valid` | French INSEE/NIR |
| `belgium_rrn_valid` | Belgian RRN |
| `finland_hetu_valid` | Finnish HETU |

### Financial / Crypto / Tokens

| Function | Purpose |
|----------|---------|
| `swift_bic_valid` | SWIFT/BIC code |
| `aws_access_key_valid` | AWS Access Key format |
| `google_api_key_valid` | Google API Key format |
| `crypto_btc_valid` | Bitcoin address (Base58) |
| `crypto_eth_valid` | Ethereum address (0x hex) |

## Using in Pattern YAML Files

In your pattern definition files (e.g., `pii-pattern-engine/regex/hash/tokens.yml`):

```yaml
patterns:
  - id: github_token_01
    location: comm
    pattern: 'ghp_[A-Za-z0-9]{36,}'
    verification: high_entropy_token  # References the function name
    category: token
    severity: critical
```

## Implementing in Other Languages

To implement verification functions in other languages:

1. Create a directory: `pii-pattern-engine/verification/<language>/`
2. Implement the same functions with equivalent logic
3. Maintain consistent function signatures
4. Update the main README with usage examples

Example for Go:
```go
// pii-pattern-engine/verification/golang/verification.go
package verification

func HighEntropyToken(value string) bool {
    // Shannon entropy on raw value, threshold 4.5
    return entropy >= 4.5
}
```

## Testing

Test files are located in `tests/test_verification*.py`:

```bash
# Run verification tests
pytest tests/test_verification.py -v

# Run integration tests
pytest tests/test_verification_integration.py -v

# Run token pattern tests (uses verification)
pytest tests/test_token_patterns.py -v
```

## Benefits of Centralization

1. **Single source of truth** - One implementation used everywhere
2. **Consistency** - Same validation logic across all patterns
3. **Reusability** - Easy to use in different projects/languages
4. **Maintainability** - Update once, apply everywhere
5. **Testability** - Centralized tests cover all usage

## Migration Notes

- Existing code using `from datadetector.verification import ...` continues to work
- The `src/datadetector/verification.py` module now re-exports from centralized location
- No changes required to existing pattern YAML files
- Tests pass without modification

## See Also

- [Full Documentation](README.md) - Complete verification functions reference
- [Pattern Files](../regex/hash/tokens.yml) - Example usage in patterns
- [Tests](../../tests/test_verification.py) - Comprehensive test suite
