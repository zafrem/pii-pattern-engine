# Re-Rank Scoring System

The re-rank engine converts raw pattern matches into a calibrated **0–100 confidence score** by combining three independent signals: keyword frequency, field-label context, and regex structure.

## Scoring Formula

```
final_score = min(keyword_avg + context_bonus + regex_score, 100)
```

| Signal | Description | Range |
|--------|-------------|-------|
| `keyword_avg` | Average score across every keyword found in the text | 0–100 |
| `context_bonus` | Flat bonus when a labeled field prefix (e.g. `"주민등록번호:"`) is present | 0–45 |
| `regex_score` | Score of the best-matching regex pattern for this entity | 0–65 |

All three signals are additive and capped at 100. A score above 100 before capping confirms multiple independent signals align, providing maximum certainty.

## Confidence Thresholds

Defined in `scoring.yml`:

| Min Score | Label | Confidence | Default Action |
|-----------|-------|-----------|----------------|
| 100 | `definite_pii` | 1.00 | redact |
| 80 | `high_confidence_pii` | 0.80 | redact |
| 60 | `probable_pii` | 0.60 | flag |
| 40 | `possible_pii` | 0.40 | review |
| 20 | `low_confidence_pii` | 0.20 | log |
| 0 | `not_pii` | 0.00 | pass |

## Entity Files

Each regional file contains entity definitions keyed by their reference code:

| File | Region | Codes | Entities |
|------|--------|-------|----------|
| `kr.yml` | Korea | 1001–1013 | 13 |
| `jp.yml` | Japan | 2001–2016 | 16 |
| `cn.yml` | China | 3001–3012 | 12 |
| `tw.yml` | Taiwan | 4001–4016 | 16 |
| `us.yml` | United States | 5001–5009 | 9 |
| `eu.yml` | European Union | 6001–6054 | 43 |
| `in.yml` | India | 7001–7009 | 9 |
| `es_fr.yml` | Spain & France | 8001–8056 | 12 |
| `common.yml` | Common / International | 9001–9013 | 13 |
| `tech.yml` | Tech / Tokens | 9501–9510 | 10 |

## Entity Definition Structure

```yaml
<reference_code>:
  entity: <snake_case_name>
  keyword_scores:
    <keyword>: <score>          # 0–100 per keyword
    ...
  context_bonus:
    "<Label:>": <bonus>         # flat bonus when this prefix is found in text
    ...
  regex_scores:
    <pattern_id>: <score>       # score if this regex pattern matches
    ...
  sum_example:                  # documents a representative scoring scenario
    keyword_hits: [<scores>]
    keyword_avg: <avg>
    context_bonus: <bonus>
    regex_score: <score>
    final_score: <capped_total>
    label: <threshold_label>
```

## Signal Calibration

### Keyword Scores

Scores reflect how strongly a keyword implies this specific PII type:

| Range | Meaning | Examples |
|-------|---------|---------|
| 85–90 | Near-certain indicator | `주민등록번호`, `aadhaar`, `aws_secret_access_key` |
| 70–84 | Strong indicator | `passport number`, `iban`, `ghp` |
| 55–69 | Moderate indicator | `mobile`, `address`, `email` |
| 30–54 | Weak / broad indicator | `name`, `number`, `id` |

All keywords found in the text are averaged. Substring matching is used (case-insensitive), so `계좌번호` matches text containing `계좌번호:` or `은행계좌번호`.

### Context Bonus

Awarded when a labeled field prefix is detected immediately before the value:

| Bonus | Meaning | Examples |
|-------|---------|---------|
| 40–45 | Unmistakable label | `"AWS_SECRET_ACCESS_KEY:"`, `"주민등록번호:"` |
| 30–39 | Strong label | `"SSN:"`, `"IBAN:"`, `"DNI:"` |
| 20–29 | Moderate label | `"Email:"`, `"Phone:"`, `"이름:"` |
| 15 | Weak label | `"Name:"`, `"Contact:"` |

Only the highest matching bonus applies. Matching is case-insensitive.

### Regex Scores

Calibrated by how structurally distinctive the pattern is:

| Score | Pattern Type | Examples |
|-------|-------------|---------|
| 65 | Unmistakable block structure | `private_key_01` (-----BEGIN…KEY-----) |
| 60 | Highly distinctive prefix + length | `aws_access_key_01` (AKIA+16), `github_token_01` (gh[pousr]_+36), `stripe_key_01`, `slack_token_01`, `google_api_key_01` |
| 55 | Fairly distinctive structure | `jwt_token_01` (eyJ…3-part) |
| 50 | Checksum-validated | `credit_card_visa_01` (Luhn), `iban_de_01` (mod-97), `rrn_01` (RRN checksum) |
| 45 | Fixed-length structured format | `pan_01` (AAAAA9999A), `passport_01` |
| 40 | Phone / address patterns | `mobile_01`, `landline_01`, `ipv4_01`, `date_iso_01` |
| 30 | Broad character-class patterns | `name_01` ([가-힣]{2,5}), `generic_token_01` |

A regex score of 60+ alone reaches `probable_pii` — appropriate for tech tokens whose structural prefix (e.g. `ghp_`, `AKIA`, `xoxb-`) is provider-specific.

## Scoring Examples

### Full Signal — Korean RRN

Text: `"주민등록번호: 900101-1234568"`

```
keyword "주민등록번호"=90, "주민번호"=90 → avg = 90
context "주민등록번호:" → +40
regex rrn_01 matches → +50
─────────────────────────────
raw  = 90 + 40 + 50 = 180 → capped to 100
label: definite_pii
```

### Keyword + Context Only — DOB with slash date

Text: `"DOB: 25/12/1990"`

```
keyword "dob"=75 → avg = 75
context "DOB:" → +30
regex date_slash_01 no match (pattern expects YYYY/MM/DD) → +0
─────────────────────────────
raw  = 75 + 30 + 0 = 105 → capped to 100
label: definite_pii
```

### Bare Tech Token — Stripe key (no keyword context)

Text: `"rk_demo_AbcdefghijklmnopQRSTUVWXYZ12345678"`

```
no keywords match → avg = 0
no context label  → +0
regex stripe_key_01 matches → +60
─────────────────────────────
raw  = 0 + 0 + 60 = 60
label: probable_pii
```

### Partial Signal — IP address with weak keyword

Text: `"Server IP is 10.0.0.1"`

```
keyword "ip"=50, "server"=30 → avg = 40
no context label              → +0
regex ipv4_01 matches         → +40
─────────────────────────────
raw  = 40 + 0 + 40 = 80
label: high_confidence_pii
```

### Regex Only — Email address, no keyword

Text: `"Please contact user@example.com for details"`

```
no keywords match → avg = 0
no context label  → +0
regex email_01 matches → +50
─────────────────────────────
raw  = 0 + 0 + 50 = 50
label: possible_pii
```

## Entity Quick Reference

### Korea (1001–1013)

| Code | Entity | Key Keywords | Regex Pattern |
|------|--------|-------------|---------------|
| 1001 | `kr_name` | 이름, 성명, 성함 | `name_01` |
| 1002 | `kr_rrn` | 주민등록번호, 주민번호 | `rrn_01` (checksum) |
| 1003 | `kr_alien_registration` | 외국인등록번호 | `alien_registration_01` |
| 1004 | `kr_passport` | 여권번호, 여권 | `passport_01` |
| 1005 | `kr_driver_license` | 운전면허번호 | `driver_license_01` |
| 1006 | `kr_phone_mobile` | 핸드폰, 휴대폰, 전화번호 | `mobile_01` |
| 1007 | `kr_phone_landline` | 전화번호, 유선전화 | `landline_01` |
| 1008 | `kr_address` | 주소, 도로명주소 | `address_01` |
| 1009 | `kr_bank_account` | 계좌번호, 은행 | `bank_account_01` |
| 1010 | `kr_business_number` | 사업자등록번호 | `business_number_01` |
| 1011 | `kr_corporate_registration` | 법인등록번호 | `corporate_registration_01` |
| 1012 | `kr_personal_customs_code` | 개인통관고유부호 | `personal_customs_code_01` |
| 1013 | `kr_vehicle_registration` | 차량번호 | `default` |

### Japan (2001–2016)

| Code | Entity | Key Keywords |
|------|--------|-------------|
| 2001 | `jp_name_kanji` | 氏名, お名前, 名前 |
| 2002 | `jp_name_hiragana` | ふりがな, フリガナ |
| 2003 | `jp_name_katakana` | カタカナ, フリガナ |
| 2004 | `jp_my_number` | マイナンバー, 個人番号 |
| 2005 | `jp_passport` | パスポート番号 |
| 2006 | `jp_driver_license` | 運転免許証 |
| 2007 | `jp_phone_mobile` | 携帯電話, 携帯 |
| 2008 | `jp_phone_landline` | 固定電話 |
| 2009 | `jp_address` | 住所 |
| 2010–2016 | `jp_bank_*` | 口座番号, major banks |

### United States (5001–5009)

| Code | Entity | Key Keywords |
|------|--------|-------------|
| 5001 | `us_name` | name, full name |
| 5002 | `us_ssn` | ssn, social security number |
| 5003 | `us_ein` | ein, employer identification |
| 5004 | `us_passport` | passport number |
| 5005 | `us_driver_license_ca` | driver license |
| 5006 | `us_medicare` | medicare |
| 5007 | `us_phone` | phone, telephone |
| 5008 | `us_address` | address, street |
| 5009 | `us_ein` | ein |

### Common / International (9001–9013)

| Code | Entity | Key Keywords | Regex Score |
|------|--------|-------------|-------------|
| 9001 | `common_email` | email, e-mail, 이메일, 电子邮件 | 50 |
| 9002 | `common_name_en` | name, full name, first name | 30 |
| 9003 | `common_date_iso` | date of birth, dob, 생년월일 | 40 |
| 9004 | `common_date_slash` | date of birth, dob | 40 |
| 9005 | `common_ipv4` | ip address, client ip | 40 |
| 9006 | `common_ipv6` | ip address, ipv6 | 40 |
| 9007 | `common_url` | url, website, https | 30 |
| 9008–9013 | `common_credit_card_*` | card number, visa, mastercard, … | 50 |

### Tech / Tokens (9501–9510)

| Code | Entity | Prefix / Format | Regex Score |
|------|--------|----------------|-------------|
| 9501 | `tech_generic_token` | high-entropy char class | 30 |
| 9502 | `tech_aws_access_key` | `AKIA` + 16 chars | **60** |
| 9503 | `tech_aws_secret_key` | 40-char base64 | **60** |
| 9504 | `tech_github_token` | `gh[pousr]_` + 36+ chars | **60** |
| 9505 | `tech_stripe_key` | `(rk\|sk\|pk)_(live\|test)_` + 24+ chars | **60** |
| 9506 | `tech_jwt_token` | `eyJ…` 3-part structure | **55** |
| 9507 | `tech_slack_token` | `xox[bpsa]-` prefix | **60** |
| 9508 | `tech_google_api_key` | `AIza` + 35 chars | **60** |
| 9509 | `tech_generic_api_key` | `key=value` pattern | 30 |
| 9510 | `tech_private_key` | `-----BEGIN…PRIVATE KEY-----` | **65** |

Tech tokens with scores ≥ 60 reach `probable_pii` (60+) from regex evidence alone, even without any keyword or context signal. This is appropriate because their structural prefix is provider-specific.

## Reference Codes

The `reference/` directory contains stable numeric codes for all entities. Use these codes — not string names — in logs, configs, and API responses to avoid coupling to entity name changes.

```yaml
# reference/registry.yml (excerpt)
kr_rrn:                       1002
us_ssn:                       5002
common_email:                 9001
tech_aws_access_key:          9502
tech_private_key:             9510
```

Regional detail files (e.g. `reference/kr.yml`) include per-entity metadata:

```yaml
1002:
  code: 1002
  entity: kr_rrn
  description: Korean Resident Registration Number
  category: national_id
  pii_type: government_id
  severity: critical
  regex:
    source: regex/pii/kr/rrn.yml
    pattern_id: rrn_01
  keyword:
    source: keyword/identification.yml
    category: national_id
  rerank:
    source: re-rank/kr.yml
    category: national_id
```

## Testing

The `tests/test_rerank.py` suite contains 400 tests:

| Class | Tests | What it checks |
|-------|-------|---------------|
| `TestReRankEngine` | 9 | YAML structure, threshold ordering, entity count, registry alignment |
| `TestReRankSumExamples` | 306 | Arithmetic of every `sum_example` block across all 153 entities |
| `TestReRankSentences` | 69 | Natural-language sentences scored against expected labels |
| `TestReRankEdgeCases` | 8 | Capping at 100, substring keywords, context case-insensitivity, unknown codes |

```bash
# Run all re-rank tests
pytest tests/test_rerank.py -v

# Run sentence tests only
pytest tests/test_rerank.py::TestReRankSentences -v

# Filter by entity code or region
pytest tests/test_rerank.py -k "1002"
pytest tests/test_rerank.py -k "tech"
```
