# Keywords Directory

This directory contains keyword mappings organized by category to help with context-aware pattern detection.

## Purpose

Keywords provide contextual clues that commonly appear near sensitive data patterns. They can be used to:

1. **Reduce false positives** - Confirm that a pattern match is likely real PII
2. **Improve accuracy** - Provide additional context for pattern matching
3. **Enable context filtering** - Filter patterns based on surrounding text
4. **Multi-language support** - Include keywords in multiple languages

## Structure

```
keywords/
├── README.md              # This file
├── financial.yml          # Bank accounts, credit cards, IBAN
├── identification.yml     # SSN, passport, national IDs
├── contact.yml           # Email, phone, addresses
├── network.yml           # IP addresses, URLs
└── personal.yml          # Names, DOB, gender, etc.
```

## File Format

Each keyword file follows this structure:

```yaml
category: <category_name>
description: <category_description>

categories:
  <subcategory>:
    description: <subcategory_description>
    patterns:
      - keyword1
      - keyword2
      - 한국어_키워드
      - 日本語キーワード
      - 中文关键词
    contexts:
      - "Label: "
      - "Context phrase"

metadata:
  related_categories: [...]
  severity: <critical|high|medium|low>
  common_contexts: [...]
```

## Keyword Categories

### Financial (`financial.yml`)
- **bank** - Bank account numbers and routing information
- **credit_card** - Credit/debit card numbers
- **iban** - International Bank Account Numbers

**Related Patterns:**
- `regex-patterns/pii/*/banks.yml`
- `regex-patterns/pii/common/credit-cards.yml`
- `regex-patterns/pii/iban.yml`

### Identification (`identification.yml`)
- **ssn** - US Social Security Numbers
- **rrn** - Korean Resident Registration Numbers
- **passport** - Passport numbers
- **national_id** - National ID cards (China, India, etc.)
- **drivers_license** - Driver's license numbers

**Related Patterns:**
- `regex-patterns/pii/us/ssn.yml`
- `regex-patterns/pii/kr/rrn.yml`
- `regex-patterns/pii/*/identification.yml`

### Contact (`contact.yml`)
- **email** - Email addresses
- **phone** - Phone numbers
- **address** - Physical addresses
- **zipcode** - Postal/ZIP codes

**Related Patterns:**
- `regex-patterns/pii/common/email.yml`
- `regex-patterns/pii/*/phone.yml`
- `regex-patterns/pii/*/other.yml` (addresses)

### Network (`network.yml`)
- **ip_address** - IPv4/IPv6 addresses
- **url** - URLs and web addresses
- **mac_address** - MAC addresses

**Related Patterns:**
- `regex-patterns/pii/common/ip.yml`
- `regex-patterns/pii/common/urls.yml`

### Personal (`personal.yml`)
- **name** - Personal names
- **date_of_birth** - Birth dates
- **age** - Age information
- **gender** - Gender/sex
- **nationality** - Citizenship/nationality

**Related Patterns:**
- Various patterns in `regex-patterns/pii/*/other.yml`

## Usage

### 1. Context-Aware Detection

Use keywords to filter or prioritize pattern matches based on surrounding text:

```python
from datadetector import Engine, load_registry

# Load patterns and keywords
registry = load_registry(paths=["regex-patterns/pii/us/ssn.yml"])
engine = Engine(registry)

# Text with context
text = "Employee SSN: 123-45-6789"

# The keyword "SSN" provides context for the number
result = engine.find(text)
```

### 2. Multi-Language Support

Keywords include terms in multiple languages:

- **English** - Primary keywords
- **Korean (한국어)** - 계좌번호, 주민등록번호, etc.
- **Japanese (日本語)** - 口座番号, マイナンバー, etc.
- **Chinese (中文)** - 银行账号, 身份证, etc.

### 3. False Positive Reduction

Check if a pattern match is near relevant keywords:

```python
def is_likely_ssn(text, match_position):
    """Check if SSN match has nearby context keywords."""
    # Get 50 chars before and after match
    context = text[max(0, match_position-50):match_position+50]

    # Check for SSN-related keywords
    ssn_keywords = ["ssn", "social security", "ss#", "tax id"]
    return any(kw in context.lower() for kw in ssn_keywords)
```

### 4. Pattern Selection

Use keywords to determine which patterns to load:

```python
# User mentions "bank account" - load bank-related patterns
if "bank" in user_query.lower():
    registry = load_registry(paths=["regex-patterns/pii/*/banks.yml"])
```

## Adding New Keywords

When adding new keywords:

1. Determine the appropriate category file
2. Add keywords in multiple languages if applicable
3. Include common context phrases (labels, form fields)
4. Update this README if creating a new category

Example:

```yaml
categories:
  new_subcategory:
    description: Description of new subcategory
    patterns:
      - english_keyword
      - 한국어_키워드
      - 日本語キーワード
      - 中文关键词
    contexts:
      - "Form label: "
      - "Context phrase"
```

## Integration with Pattern Files

Keywords complement the regex patterns in `regex-patterns/pii/` and `regex-patterns/hash/`:

| Keyword Category | Pattern Files |
|-----------------|---------------|
| financial.yml | */banks.yml, credit-cards.yml, iban.yml |
| identification.yml | */identification.yml, */ssn.yml, */rrn.yml |
| contact.yml | */email.yml, */phone.yml, */other.yml |
| network.yml | */ip.yml, */urls.yml |
| personal.yml | */other.yml |

## Best Practices

1. **Use with patterns** - Keywords are not meant to replace regex patterns, but to enhance them
2. **Consider context window** - Look at 50-100 characters around the match
3. **Case-insensitive matching** - Keywords should be matched case-insensitively
4. **Language detection** - Use language-specific keywords based on detected language
5. **Combine signals** - Use keywords + pattern match + verification functions for best accuracy

## See Also

- [Pattern Files](../pii/) - Regex patterns for PII detection
- [Verification Functions](../_verification/) - Additional validation logic
- [Hash Patterns](../hash/) - Token and secret detection patterns
