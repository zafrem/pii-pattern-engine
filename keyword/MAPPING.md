# Pattern to Keyword Mapping

This document maps pattern files to their corresponding keyword categories for easy reference.

## Mapping Table

| Pattern File | Keyword Category | Keyword Subcategory | Severity |
|--------------|-----------------|---------------------|----------|
| **Financial Patterns** |
| */banks.yml | financial.yml | bank | critical |
| common/credit-cards.yml | financial.yml | credit_card | critical |
| iban.yml | financial.yml | iban | critical |
| **Identification Patterns** |
| us/ssn.yml | identification.yml | ssn | critical |
| kr/rrn.yml | identification.yml | rrn | critical |
| */identification.yml | identification.yml | passport, national_id, drivers_license | critical |
| **Contact Patterns** |
| common/email.yml | contact.yml | email | medium |
| */phone.yml | contact.yml | phone | medium |
| */other.yml (addresses) | contact.yml | address, zipcode | medium |
| **Network Patterns** |
| common/ip.yml | network.yml | ip_address | low |
| common/urls.yml | network.yml | url | low |
| **Personal Patterns** |
| */other.yml (names, DOB) | personal.yml | name, date_of_birth, age, gender, nationality | medium |

## By Country/Region

### United States (us/)
- `us/ssn.yml` → identification.yml (ssn, itin)
- `us/phone.yml` → contact.yml (phone)
- `us/identification.yml` → identification.yml (drivers_license)
- `us/other.yml` → contact.yml (address, zipcode)

### Korea (kr/)
- `kr/banks.yml` → financial.yml (bank)
- `kr/rrn.yml` → identification.yml (rrn)
- `kr/phone.yml` → contact.yml (phone)
- `kr/identification.yml` → identification.yml (passport)
- `kr/other.yml` → contact.yml (address, zipcode) + personal.yml

### China (cn/)
- `cn/banks.yml` → financial.yml (bank)
- `cn/identification.yml` → identification.yml (national_id)
- `cn/phone.yml` → contact.yml (phone)
- `cn/other.yml` → contact.yml (address) + personal.yml

### Japan (jp/)
- `jp/identification.yml` → identification.yml (national_id)
- `jp/phone.yml` → contact.yml (phone)
- `jp/other.yml` → contact.yml (address) + personal.yml

### Taiwan (tw/)
- `tw/banks.yml` → financial.yml (bank)
- `tw/identification.yml` → identification.yml (national_id)
- `tw/phone.yml` → contact.yml (phone)
- `tw/other.yml` → contact.yml (address) + personal.yml

### India (in/)
- `in/identification.yml` → identification.yml (national_id - Aadhaar, PAN)
- `in/phone.yml` → contact.yml (phone)
- `in/other.yml` → contact.yml (address) + personal.yml

### Europe (eu/)
- `iban.yml` → financial.yml (iban)

### Common/International (common/)
- `common/email.yml` → contact.yml (email)
- `common/ip.yml` → network.yml (ip_address)
- `common/urls.yml` → network.yml (url)
- `common/credit-cards.yml` → financial.yml (credit_card)

## Usage Example

```python
# Map pattern files to keyword categories
PATTERN_KEYWORD_MAP = {
    "banks.yml": "financial.yml",
    "credit-cards.yml": "financial.yml",
    "iban.yml": "financial.yml",
    "ssn.yml": "identification.yml",
    "rrn.yml": "identification.yml",
    "identification.yml": "identification.yml",
    "email.yml": "contact.yml",
    "phone.yml": "contact.yml",
    "ip.yml": "network.yml",
    "urls.yml": "network.yml",
    "other.yml": "personal.yml",
}

def get_keywords_for_pattern(pattern_file):
    """Get keyword file for a pattern file."""
    for key, value in PATTERN_KEYWORD_MAP.items():
        if key in pattern_file:
            return f"regex-patterns/keywords/{value}"
    return None
```

## Category Priority

When multiple categories could apply, use this priority:

1. **identification** - Critical PII (SSN, passport, national ID)
2. **financial** - Financial data (bank accounts, credit cards)
3. **contact** - Contact information (email, phone, address)
4. **personal** - Personal attributes (name, DOB, gender)
5. **network** - Network identifiers (IP, URLs)

## Loading Patterns with Keywords

```python
from datadetector import load_registry

# Load patterns with corresponding keywords
def load_patterns_with_keywords(pattern_path):
    # Load patterns
    registry = load_registry(paths=[pattern_path])

    # Determine keyword file
    if "bank" in pattern_path or "credit" in pattern_path:
        keyword_file = "regex-patterns/keywords/financial.yml"
    elif "ssn" in pattern_path or "rrn" in pattern_path or "identification" in pattern_path:
        keyword_file = "regex-patterns/keywords/identification.yml"
    elif "email" in pattern_path or "phone" in pattern_path:
        keyword_file = "regex-patterns/keywords/contact.yml"
    # ... and so on

    return registry, keyword_file
```

## See Also

- [Keywords README](README.md) - Detailed keyword system documentation
- [Pattern Files](../pii/) - Regex pattern definitions
- [Verification Functions](../_verification/) - Pattern validation
