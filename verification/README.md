# Verification Functions

This directory contains reusable verification functions for pattern validation across different implementations.

## Structure

```
verification/
├── README.md           # This file
├── python/             # Python implementation
│   ├── __init__.py     # Module exports
│   └── verification.py # Verification functions
├── javascript/         # JavaScript implementation
│   └── verification.js # Verification functions
├── golang/             # Go implementation
│   └── verification.go # Verification functions
└── java/               # Java implementation
    └── src/main/java/com/piipatternengine/verification/Verification.java
```

## Verification Functions

All four implementations (Python, JavaScript, Go, Java) expose the same set of functions. The table below lists every available function and which languages implement it.

| Function | Python | JS | Go | Java | Description |
|---|:---:|:---:|:---:|:---:|----|
| `iban_mod97` | ✓ | ✓ | ✓ | ✓ | IBAN Mod-97 checksum |
| `luhn` | ✓ | ✓ | ✓ | ✓ | Luhn algorithm (credit cards, etc.) |
| `high_entropy_token` | ✓ | ✓ | ✓ | ✓ | API key / secret token detection |
| `not_timestamp` | ✓ | ✓ | ✓ | ✓ | Reject Unix timestamp-like numbers |
| `generic_number_not_timestamp` | ✓ | ✓ | ✓ | ✓ | Generic timestamp rejection |
| `contains_letter` | ✓ | ✓ | ✓ | ✓ | String contains at least one letter |
| `dms_coordinate` | ✓ | ✓ | ✓ | ✓ | DMS coordinate format validation |
| `korean_bank_account_valid` | ✓ | ✓ | ✓ | ✓ | Korean bank account validation |
| `us_ssn_valid` | ✓ | ✓ | ✓ | ✓ | US Social Security Number |
| `cn_national_id_valid` | ✓ | ✓ | ✓ | ✓ | Chinese National ID (18-digit) |
| `tw_national_id_valid` | ✓ | ✓ | ✓ | ✓ | Taiwan National ID |
| `india_aadhaar_valid` | ✓ | ✓ | ✓ | ✓ | India Aadhaar (Verhoeff) |
| `india_pan_valid` | ✓ | ✓ | ✓ | ✓ | India PAN format |
| `kr_rrn_valid` | ✓ | ✓ | ✓ | ✓ | Korean Resident Registration Number |
| `kr_alien_registration_valid` | ✓ | ✓ | ✓ | ✓ | Korean Alien Registration Number |
| `kr_business_registration_valid` | ✓ | ✓ | ✓ | ✓ | Korean Business Registration Number |
| `kr_corporate_registration_valid` | ✓ | ✓ | ✓ | ✓ | Korean Corporate Registration Number |
| `jp_my_number_valid` | ✓ | ✓ | ✓ | ✓ | Japanese My Number |
| `jp_corporate_number_valid` | ✓ | ✓ | ✓ | ✓ | Japanese Corporate Number |
| `tw_ubn_valid` | ✓ | ✓ | ✓ | ✓ | Taiwan Unified Business Number |
| `us_npi_valid` | ✓ | ✓ | ✓ | ✓ | US National Provider Identifier |
| `uk_nino_valid` | ✓ | ✓ | ✓ | ✓ | UK National Insurance Number |
| `spain_dni_valid` | ✓ | ✓ | ✓ | ✓ | Spanish DNI |
| `spain_nie_valid` | ✓ | ✓ | ✓ | ✓ | Spanish NIE |
| `netherlands_bsn_valid` | ✓ | ✓ | ✓ | ✓ | Dutch BSN |
| `poland_pesel_valid` | ✓ | ✓ | ✓ | ✓ | Polish PESEL |
| `sweden_personnummer_valid` | ✓ | ✓ | ✓ | ✓ | Swedish Personnummer |
| `france_insee_valid` | ✓ | ✓ | ✓ | ✓ | French INSEE/NIR |
| `belgium_rrn_valid` | ✓ | ✓ | ✓ | ✓ | Belgian RRN |
| `finland_hetu_valid` | ✓ | ✓ | ✓ | ✓ | Finnish HETU |
| `swift_bic_valid` | ✓ | ✓ | ✓ | ✓ | SWIFT/BIC code |
| `aws_access_key_valid` | ✓ | ✓ | ✓ | ✓ | AWS Access Key |
| `google_api_key_valid` | ✓ | ✓ | ✓ | ✓ | Google API Key |
| `crypto_btc_valid` | ✓ | ✓ | ✓ | ✓ | Bitcoin address |
| `crypto_eth_valid` | ✓ | ✓ | ✓ | ✓ | Ethereum address |
| `ipv4_public` | ✓ | ✓ | ✓ | ✓ | IPv4 public (non-private) address |
| `not_repeating_pattern` | ✓ | ✓ | ✓ | ✓ | Reject all-same / sequential patterns |
| `credit_card_bin_valid` | ✓ | ✓ | ✓ | ✓ | Credit card BIN + Luhn check |
| `cjk_name_standalone` | ✓ | ✓ | ✓ | ✓ | CJK-only character string |
| `chinese_name_valid` | ✓ | ✓ | ✓ | ✓ | Chinese name (surname + given name) |
| `korean_name_valid` | ✓ | ✓ | ✓ | ✓ | Korean name (surname + given name) |
| `japanese_name_kanji_valid` | ✓ | ✓ | ✓ | ✓ | Japanese kanji name |
| `english_name_valid` | ✓ | ✓ | ✓ | ✓ | English name (First Last) |
| `korean_address_valid` | ✓ | ✓ | ✓ | ✓ | Korean address (province-level check) |
| `japanese_address_valid` | ✓ | ✓ | ✓ | ✓ | Japanese address (prefecture check) |
| `chinese_address_valid` | ✓ | ✓ | ✓ | ✓ | Chinese address (province check) |
| `us_address_valid` | ✓ | ✓ | ✓ | ✓ | US address (city + state) |
| `uscc_valid` | ✓ | ✓ | ✓ | ✓ | Chinese Unified Social Credit Code (MOD-31) |
| `korean_zipcode_valid` | ✓ | ✓ | ✓ | ✓ | Korean 5-digit postal code |
| `us_zipcode_valid` | ✓ | ✓ | ✓ | ✓ | US 5-digit / ZIP+4 postal code |
| `jp_zipcode_valid` | ✓ | ✓ | ✓ | ✓ | Japanese 7-digit postal code |
| `cn_zipcode_valid` | ✓ | ✓ | ✓ | ✓ | Chinese 6-digit postal code |
| `tw_zipcode_valid` | ✓ | ✓ | ✓ | ✓ | Taiwan 3/5/6-digit postal code |
| `in_pincode_valid` | ✓ | ✓ | ✓ | ✓ | Indian 6-digit PIN code |
| `kr_driver_license_valid` | ✓ | ✓ | ✓ | ✓ | Korean driver's license number |
| `kr_pccc_valid` | ✓ | ✓ | ✓ | ✓ | Korean Personal Customs Clearance Code |
| `kr_vehicle_registration_valid` | ✓ | ✓ | ✓ | ✓ | Korean vehicle license plate |
| `mac_address_valid` | ✓ | ✓ | ✓ | ✓ | IEEE 802 MAC address (non-broadcast/zero) |
| `imei_valid` | ✓ | ✓ | ✓ | ✓ | 15-digit IMEI with Luhn check |
| `latitude_valid` | ✓ | ✓ | ✓ | ✓ | Decimal latitude (-90 to 90) |
| `longitude_valid` | ✓ | ✓ | ✓ | ✓ | Decimal longitude (-180 to 180) |

### Notes on Key Functions

#### `high_entropy_token`
Shannon entropy is calculated on the **raw value** (no normalization). Threshold is **4.0 bits/char** (>= 4.0). Accepts characters from `A-Za-z0-9_-+/.=`, minimum 20 characters.

#### Address Validators
Python uses database-backed lookups (`*_addresses.csv`) with a province/prefecture fallback. Go, Java, and JavaScript use the hardcoded fallback list directly (province/prefecture/state string containment check).

#### Name Validators
`chinese_name_valid`, `korean_name_valid`, and `japanese_name_kanji_valid` load given-name dictionaries from CSV files when available. `english_name_valid` checks against a hardcoded surname list plus optional `en_surnames.csv` / `en_given_names.csv`.

### Usage in Python

```python
# Import from the verification module
from pii_pattern_engine.verification.python import high_entropy_token, luhn

# Use in pattern validation
if high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T"):
    print("Valid high-entropy token")

if luhn("4532015112830366"):
    print("Valid credit card number")
```

### Adding Custom Verification Functions

```python
from pii_pattern_engine.verification.python import register_verification_function

def custom_verify(value: str) -> bool:
    # Your custom validation logic
    return len(value) > 10

register_verification_function("custom", custom_verify)
```

## Using in Other Languages

The following language implementations are currently supported:

### JavaScript

```javascript
const { high_entropy_token, luhn } = require("./javascript/verification");

if (high_entropy_token("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T")) {
    console.log("Valid high-entropy token");
}
```

### Go

```go
import "verification/golang/verification"

if verification.HighEntropyToken("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T") {
    fmt.Println("Valid high-entropy token")
}
```

### Java

```java
import com.piipatternengine.verification.Verification;

if (Verification.highEntropyToken("ghp_1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6P7q8R9s0T")) {
    System.out.println("Valid high-entropy token");
}
```

## Function Signature

All verification functions should follow this signature:

- **Input**: A string value to validate
- **Output**: Boolean (true if valid, false otherwise)
- **Side effects**: None (pure functions)

## Testing

Each verification function should have corresponding tests that verify:
- Valid inputs return true
- Invalid inputs return false
- Edge cases are handled correctly
- Performance is acceptable for large-scale validation

## Contributing

When adding new verification functions:

1. Add the function to the appropriate language directory
2. Document the function with clear docstrings/comments
3. Add the function to the registry (VERIFICATION_FUNCTIONS dict in Python)
4. Update this README with the new function
5. Add comprehensive tests
