# Pattern Engine

A comprehensive collection of regular expression patterns and verification functions for detecting personally identifiable information (PII) and sensitive data across multiple languages and regions.

## Overview

Pattern Engine provides:
- **Regex Patterns**: 160+ patterns for PII detection across US, Korea, Japan, China, Taiwan, India, EU, and common international formats
- **Verification Functions**: 32 Python verification functions for checksum validation and data quality checks
- **Keyword Mappings**: Context-aware keywords in multiple languages for improved accuracy
- **Comprehensive Tests**: 1,965+ automated tests ensuring pattern accuracy and reliability

## Project Structure

```
pattern-engine/
├── regex/                    # Regex pattern definitions (YAML)
│   ├── pii/                 # Personally Identifiable Information patterns
│   │   ├── us/             # United States (SSN, driver's license, passport, phone, etc.)
│   │   ├── kr/             # South Korea (RRN, bank accounts, phone, etc.)
│   │   ├── jp/             # Japan (My Number, bank accounts, phone, etc.)
│   │   ├── cn/             # China (ID cards, bank accounts, phone, etc.)
│   │   ├── tw/             # Taiwan (ID cards, bank accounts, phone, etc.)
│   │   ├── in/             # India (Aadhaar, PAN, phone, etc.)
│   │   ├── eu/             # European Union (VAT, national IDs, passports, etc.)
│   │   ├── common/         # International formats (email, IP, credit cards, etc.)
│   │   └── iban.yml        # IBAN patterns with mod-97 validation
│   └── hash/                # High-entropy tokens and secrets
│       └── tokens.yml       # API keys, JWT, AWS keys, GitHub tokens, etc.
│
├── verification/            # Verification functions for pattern validation
│   ├── python/             # Python implementation
│   │   ├── verification.py # 32 verification functions
│   │   └── __init__.py
│   └── README.md
│
├── keyword/                 # Context-aware keywords (multi-language)
│   ├── financial.yml       # Bank, credit card, IBAN keywords
│   ├── identification.yml  # SSN, passport, national ID keywords
│   ├── contact.yml         # Email, phone, address keywords
│   ├── network.yml         # IP, URL, MAC address keywords
│   ├── personal.yml        # Name, DOB, gender keywords
│   └── README.md
│
├── tests/                   # Comprehensive test suite
│   ├── test_verification.py # Verification function tests (129 tests)
│   ├── test_patterns.py     # Pattern validation tests (1,836+ tests)
│   ├── requirements.txt     # Test dependencies
│   ├── run_tests.sh        # Test runner script
│   └── README.md
│
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pattern-engine.git
cd pattern-engine

# Install test dependencies
pip install -r tests/requirements.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_verification.py
pytest tests/test_patterns.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=verification --cov-report=html
```

### Using Patterns

```python
import re
import yaml
from verification.python.verification import luhn, iban_mod97

# Load a pattern file
with open('regex/pii/common/credit-cards.yml') as f:
    patterns = yaml.safe_load(f)

# Use a pattern
visa_pattern = patterns['patterns'][0]['pattern']
text = "My card is 4111111111111111"

match = re.search(visa_pattern, text)
if match and luhn(match.group(0)):
    print("Valid Visa card detected!")
```

### Using Verification Functions

```python
from verification.python.verification import (
    iban_mod97,
    luhn,
    high_entropy_token,
    us_ssn_valid,
    kr_rrn_valid,
    cn_national_id_valid,
    jp_my_number_valid
)

# Verify IBAN
if iban_mod97("GB82WEST12345698765432"):
    print("Valid IBAN")

# Verify credit card using Luhn algorithm
if luhn("4111111111111111"):
    print("Valid card number")

# Detect high-entropy tokens (API keys, secrets)
if high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T"):
    print("High-entropy token detected")

# Validate US SSN
if us_ssn_valid("123-45-6789"):
    print("Valid SSN format")

# Validate Korean RRN
if kr_rrn_valid("850101-1234567"):
    print("Valid Korean RRN")

# Validate Chinese national ID
if cn_national_id_valid("11010519491231002X"):
    print("Valid Chinese national ID")

# Validate Japanese My Number
if jp_my_number_valid("123456789012"):
    print("Valid Japanese My Number")
```

## Pattern Categories

### Geographic Coverage

| Region | Patterns | Description |
|--------|----------|-------------|
| **US** | 8 | SSN, ITIN, passport, driver's license, phone, zipcode |
| **Korea** | 28 | RRN, alien registration, bank accounts, phone, zipcode |
| **Japan** | 17 | My Number, bank accounts, phone, zipcode |
| **China** | 12 | ID cards, bank accounts, phone |
| **Taiwan** | 20 | ID cards, bank accounts, phone |
| **India** | 10 | Aadhaar, PAN, phone |
| **EU** | 38 | VAT, national IDs, passports (FR, DE, IT, ES, NL, BE, etc.) |
| **Common** | 22 | Email, IP, credit cards, URLs, IBAN, tokens/secrets |

### Data Types

- **Financial**: Bank accounts, credit cards, IBAN, routing numbers
- **Identification**: National IDs, SSN, passports, driver's licenses
- **Contact**: Email, phone numbers, addresses, zipcodes
- **Network**: IPv4, IPv6, URLs, MAC addresses
- **Tokens/Secrets**: API keys, JWT, AWS keys, GitHub tokens, private keys

## Verification Functions

The project includes 32 verification functions for advanced validation:

### Core Validators

| Function | Purpose | Example |
|----------|---------|---------|
| `iban_mod97` | IBAN checksum validation | GB82WEST12345698765432 |
| `luhn` | Credit card validation | 4111111111111111 |
| `credit_card_bin_valid` | Credit card BIN validation | Valid issuer prefix check |
| `dms_coordinate` | GPS coordinate validation | 37°46′29.7″N |
| `high_entropy_token` | API key/secret detection | High randomness check |
| `not_timestamp` | Reject timestamp-like numbers | Filter false positives |
| `generic_number_not_timestamp` | Generic timestamp filtering | Flexible validation |
| `not_repeating_pattern` | Reject repeating digits | Filter 111-1111-1111 |
| `contains_letter` | Check for alphabetic characters | A1234567 |
| `ipv4_public` | Validate public IPv4 address | Non-private IP check |
| `cjk_name_standalone` | Validate CJK name format | Standalone name detection |

### US Validators

| Function | Purpose |
|----------|---------|
| `us_ssn_valid` | US SSN validation (area/group/serial checks) |
| `us_zipcode_valid` | US ZIP code validation |

### Korea Validators

| Function | Purpose |
|----------|---------|
| `korean_zipcode_valid` | Korean postal code validation |
| `korean_bank_account_valid` | Korean bank account validation with prefix checking |
| `kr_rrn_valid` | Korean Resident Registration Number validation |
| `kr_alien_registration_valid` | Korean alien registration number validation |
| `kr_corporate_registration_valid` | Korean corporate registration number validation |
| `kr_business_registration_valid` | Korean business registration number validation |

### Japan Validators

| Function | Purpose |
|----------|---------|
| `jp_my_number_valid` | Japanese My Number validation with check digit |

### China/Taiwan Validators

| Function | Purpose |
|----------|---------|
| `cn_national_id_valid` | Chinese national ID validation with checksum |
| `tw_national_id_valid` | Taiwanese national ID validation |

### India Validators

| Function | Purpose |
|----------|---------|
| `india_aadhaar_valid` | Indian Aadhaar number validation |
| `india_pan_valid` | Indian PAN validation |

### European Validators

| Function | Purpose |
|----------|---------|
| `spain_dni_valid` | Spanish DNI validation |
| `spain_nie_valid` | Spanish NIE validation |
| `netherlands_bsn_valid` | Dutch BSN validation |
| `poland_pesel_valid` | Polish PESEL validation |
| `sweden_personnummer_valid` | Swedish personal number validation |
| `france_insee_valid` | French INSEE number validation |
| `belgium_rrn_valid` | Belgian national register number validation |
| `finland_hetu_valid` | Finnish HETU validation |

## Pattern File Format

Each pattern file follows this YAML structure:

```yaml
namespace: <namespace>
description: <description>

patterns:
  - id: <unique_id>
    location: <country_code>
    category: <category>
    description: <human_readable_description>
    pattern: '<regex_pattern>'
    mask: "<mask_format>"
    verification: <verification_function>  # Optional
    flags:                                  # Optional
      - IGNORECASE
    examples:
      match:
        - "example1"
        - "example2"
      nomatch:
        - "invalid1"
        - "invalid2"
    policy:
      store_raw: false
      action_on_match: redact
      severity: critical
    metadata:
      note: "Additional information"
    priority: 100  # Optional
```

### Required Fields

- `id`: Unique identifier for the pattern
- `location`: Country/region code (us, kr, jp, cn, tw, in, eu, co)
- `category`: Pattern category (ssn, bank, credit_card, phone, email, etc.)
- `description`: Human-readable description
- `pattern`: Regular expression pattern
- `mask`: Masking format for redaction
- `examples`: Match and nomatch examples
- `policy`: Data handling policy

### Optional Fields

- `verification`: Name of verification function to apply
- `flags`: Regex flags (IGNORECASE, MULTILINE, DOTALL, VERBOSE)
- `priority`: Pattern matching priority (lower = higher priority)
- `metadata`: Additional information

## Test Suite

### Coverage

- **1,965+ tests collected** ✓
- **100% verification function coverage**

### Test Categories

1. **Verification Tests** (`test_verification.py` - 129 tests):
   - IBAN mod-97 validation
   - Luhn algorithm
   - Coordinate validation
   - Token entropy detection
   - Timestamp detection
   - Zipcode validation (US, Korea)
   - National ID validation (US, KR, CN, TW, JP, IN, EU)
   - Function registry

2. **Pattern Tests** (`test_patterns.py`):
   - YAML structure validation
   - Regex compilation
   - Match/nomatch examples
   - Verification function integration
   - Metadata validation
   - Pattern coverage
   - Flag support (IGNORECASE, etc.)

### Running Specific Tests

```bash
# Run verification tests
pytest tests/test_verification.py

# Run pattern structure tests
pytest tests/test_patterns.py::TestPatternStructure

# Run pattern matching tests
pytest tests/test_patterns.py::TestPatternMatching

# Run with specific pattern
pytest tests/test_patterns.py -k "credit_card"
```

## Keywords

The `keyword/` directory contains context-aware keywords in multiple languages:

- **English**: Primary keywords
- **Korean (한국어)**: 계좌번호, 주민등록번호, etc.
- **Japanese (日本語)**: 口座番号, マイナンバー, etc.
- **Chinese (中文)**: 银行账号, 身份证, etc.

Use keywords to:
- Reduce false positives
- Provide context for matches
- Enable multi-language detection
- Improve pattern selection

See [keyword/README.md](keyword/README.md) for details.

## Development

### Adding New Patterns

1. Choose the appropriate directory in `regex/pii/`
2. Add pattern to existing YAML file or create new file
3. Include all required fields
4. Add match and nomatch examples
5. Run tests: `pytest tests/test_patterns.py`

### Adding Verification Functions

1. Add function to `verification/python/verification.py`
2. Register in `VERIFICATION_FUNCTIONS` dict
3. Add comprehensive tests to `tests/test_verification.py`
4. Update documentation
5. Run tests: `pytest tests/test_verification.py`

### Code Style

- Follow PEP 8 for Python code
- Use YAML 1.2 for pattern files
- Include docstrings for all functions
- Add type hints where applicable

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add patterns/functions with tests
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Resources

- **Documentation**:
  - [Verification Functions](verification/README.md)
  - [Keywords](keyword/README.md)
  - [Tests](tests/README.md)

- **Pattern Files**:
  - [US Patterns](regex/pii/us/)
  - [Korea Patterns](regex/pii/kr/)
  - [Japan Patterns](regex/pii/jp/)
  - [Common Patterns](regex/pii/common/)
  - [Token/Secret Patterns](regex/hash/)

## Statistics

- **Total Patterns**: 160+
- **Countries Covered**: 7+ (US, KR, JP, CN, TW, IN, EU)
- **Verification Functions**: 32
- **Test Cases**: 1,965+
- **Languages**: Python (more coming)
- **Pattern Categories**: 15+

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit a pull request
- Contact the maintainers

---

**Note**: This project is for legitimate use cases such as data protection, compliance, and security. Use responsibly and in accordance with applicable laws and regulations.
