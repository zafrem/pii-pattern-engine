#!/usr/bin/env python3
"""
Fake PII Data Generator for ML Training

Generates labeled training, validation, and test data by:
1. Reading regex patterns from the regex/ folder
2. Using reference data from the datas/ folder
3. Producing positive examples (real PII) and negative examples (non-PII)

Output: CSV files with columns [text, label, category, location, pattern_id]
"""

import csv
import hashlib
import os
import random
import re
import string
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
REGEX_DIR = PROJECT_ROOT / "regex"
DATA_DIR = PROJECT_ROOT / "datas"

random.seed(42)


# ---------------------------------------------------------------------------
# Reference data loaders
# ---------------------------------------------------------------------------

def load_csv_column(path, col=0):
    """Load a single column from a CSV, skipping the header."""
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and len(row) > col:
                rows.append(row[col].strip())
    return rows


def load_reference_data():
    """Load all reference CSV/data files into a dict."""
    data = {}
    if not DATA_DIR.exists():
        return data
    for fp in DATA_DIR.iterdir():
        if fp.suffix == ".csv":
            data[fp.stem] = load_csv_column(fp)
    return data


# ---------------------------------------------------------------------------
# Pattern loaders
# ---------------------------------------------------------------------------

def load_all_patterns():
    """Load every pattern entry from all YAML files under regex/."""
    patterns = []
    for yml_path in sorted(REGEX_DIR.rglob("*.yml")):
        try:
            with open(yml_path, encoding="utf-8") as f:
                doc = yaml.safe_load(f)
            if not doc or "patterns" not in doc:
                continue
            for p in doc["patterns"]:
                p["_file"] = str(yml_path.relative_to(PROJECT_ROOT))
                patterns.append(p)
        except Exception:
            continue
    return patterns


# ---------------------------------------------------------------------------
# Per-category fake data generators
# ---------------------------------------------------------------------------

def _rand_digits(n):
    return "".join(random.choices(string.digits, k=n))


def _rand_hex(n):
    return "".join(random.choices("0123456789abcdef", k=n))


def _rand_alnum(n):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _rand_date_yymmdd():
    y = random.randint(50, 99)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y:02d}{m:02d}{d:02d}"


def _rand_date_yyyymmdd():
    y = random.randint(1950, 2005)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return f"{y}{m:02d}{d:02d}"


# ---- US generators ----

def gen_us_ssn(n):
    samples = []
    for _ in range(n):
        a = random.randint(1, 899)
        while a in (0, 666) or a >= 900:
            a = random.randint(1, 899)
        b = random.randint(1, 99)
        c = random.randint(1, 9999)
        fmt = random.choice(["{:03d}-{:02d}-{:04d}", "{:03d}{:02d}{:04d}"])
        samples.append(fmt.format(a, b, c))
    return samples


def gen_us_itin(n):
    return [f"9{_rand_digits(2)}-{_rand_digits(2)}-{_rand_digits(4)}" for _ in range(n)]


def gen_us_phone(n):
    samples = []
    for _ in range(n):
        area = random.randint(200, 999)
        ex = random.randint(200, 999)
        sub = random.randint(0, 9999)
        fmt = random.choice([
            "({:03d}) {:03d}-{:04d}",
            "{:03d}-{:03d}-{:04d}",
            "+1 {:03d}-{:03d}-{:04d}",
            "{:03d}{:03d}{:04d}",
        ])
        samples.append(fmt.format(area, ex, sub))
    return samples


def gen_us_passport(n):
    samples = []
    for _ in range(n):
        if random.random() < 0.5:
            samples.append(_rand_digits(9))
        else:
            samples.append(random.choice(string.ascii_uppercase) + _rand_digits(8))
    return samples


def gen_us_driver_license_ca(n):
    return [random.choice(string.ascii_uppercase) + _rand_digits(7) for _ in range(n)]


def gen_us_zipcode(n, ref_data):
    zips = ref_data.get("us_zipcodes", [])
    if zips:
        return [random.choice(zips) for _ in range(n)]
    return [_rand_digits(5) for _ in range(n)]


def gen_us_ein(n):
    return [f"{_rand_digits(2)}-{_rand_digits(7)}" for _ in range(n)]


def gen_us_medicare(n):
    allowed = "ACDEFGHJKMNPQRTUVWXY"
    samples = []
    for _ in range(n):
        s = ""
        for i in range(11):
            if i in (0, 4, 7, 10):
                s += random.choice(allowed)
            else:
                s += random.choice(string.digits)
        samples.append(s)
    return samples


def gen_us_npi(n):
    return [str(random.randint(1, 9)) + _rand_digits(9) for _ in range(n)]


# ---- Email ----

def gen_email(n):
    users = ["john.doe", "jane_smith", "user123", "admin", "test.user", "info",
             "alice.b", "bob_c", "support", "dev", "hello", "noreply"]
    domains = ["example.com", "mail.org", "company.co.uk", "test.io", "gmail.com",
               "yahoo.com", "outlook.com", "proton.me", "fastmail.fm"]
    samples = []
    for _ in range(n):
        u = random.choice(users)
        if random.random() < 0.3:
            u += "+" + _rand_alnum(3).lower()
        samples.append(f"{u}@{random.choice(domains)}")
    return samples


# ---- Credit cards ----

def gen_visa(n):
    return ["4" + _rand_digits(15) for _ in range(n)]


def gen_mastercard(n):
    return [f"5{random.randint(1,5)}" + _rand_digits(14) for _ in range(n)]


def gen_amex(n):
    return [f"3{random.choice('47')}" + _rand_digits(13) for _ in range(n)]


def gen_discover(n):
    samples = []
    for _ in range(n):
        if random.random() < 0.5:
            samples.append("6011" + _rand_digits(12))
        else:
            samples.append(f"65{_rand_digits(2)}" + _rand_digits(12))
    return samples


def gen_jcb(n):
    return [f"35{_rand_digits(3)}" + _rand_digits(11) for _ in range(n)]


def gen_diners(n):
    return [f"3{random.choice('0689')}" + _rand_digits(12) for _ in range(n)]


# ---- IP ----

def gen_ipv4(n):
    samples = []
    for _ in range(n):
        octets = [random.randint(1, 254) for _ in range(4)]
        samples.append(".".join(str(o) for o in octets))
    return samples


# ---- Crypto ----

def gen_btc(n):
    return ["1" + "".join(random.choices("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
            k=random.randint(25, 34))) for _ in range(n)]


def gen_eth(n):
    return ["0x" + _rand_hex(40) for _ in range(n)]


# ---- AWS ----

def gen_aws_access_key(n):
    return [random.choice(["AKIA", "ASIA"]) + _rand_alnum(16) for _ in range(n)]


# ---- IBAN ----

def gen_iban(n):
    countries = [("DE", 18), ("FR", 23), ("GB", 18), ("IT", 23), ("ES", 20)]
    samples = []
    for _ in range(n):
        cc, rest_len = random.choice(countries)
        samples.append(cc + _rand_digits(2) + _rand_alnum(rest_len))
    return samples


# ---- Korea ----

def gen_kr_rrn(n):
    samples = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        gender = random.choice("1234")
        seq = _rand_digits(6)
        if random.random() < 0.7:
            samples.append(f"{dt}-{gender}{seq}")
        else:
            samples.append(f"{dt}{gender}{seq}")
    return samples


def gen_kr_alien(n):
    samples = []
    for _ in range(n):
        dt = _rand_date_yymmdd()
        gender = random.choice("5678")
        seq = _rand_digits(6)
        samples.append(f"{dt}-{gender}{seq}")
    return samples


def gen_kr_phone(n):
    samples = []
    for _ in range(n):
        prefix = random.choice(["010", "011", "016", "017", "019"])
        mid = _rand_digits(random.choice([3, 4]))
        last = _rand_digits(4)
        fmt = random.choice(["{}-{}-{}", "{}{}{}"])
        samples.append(fmt.format(prefix, mid, last))
    return samples


def gen_kr_name(n, ref_data):
    surnames = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임",
                "한", "오", "서", "신", "권", "황", "안", "송", "류", "홍"]
    given = ref_data.get("kr_given_names", ["민수", "영희", "철수", "지현", "수진"])
    return [random.choice(surnames) + random.choice(given) for _ in range(n)]


def gen_kr_zipcode(n, ref_data):
    zips = ref_data.get("kr_zipcodes", [])
    if zips:
        return [random.choice(zips) for _ in range(n)]
    return [_rand_digits(5) for _ in range(n)]


def gen_kr_bank(n):
    prefixes = ["110", "120", "150", "1002", "3333", "081", "301"]
    samples = []
    for _ in range(n):
        p = random.choice(prefixes)
        rest = _rand_digits(random.randint(8, 11))
        if random.random() < 0.5:
            samples.append(f"{p}-{rest[:3]}-{rest[3:]}")
        else:
            samples.append(p + rest)
    return samples


# ---- China ----

def gen_cn_national_id(n):
    samples = []
    for _ in range(n):
        area = _rand_digits(6)
        birth = _rand_date_yyyymmdd()
        seq = _rand_digits(3)
        check = random.choice(string.digits + "X")
        samples.append(area + birth + seq + check)
    return samples


def gen_cn_phone(n):
    samples = []
    for _ in range(n):
        second = random.choice("3456789")
        rest = _rand_digits(9)
        if random.random() < 0.5:
            samples.append(f"1{second}{rest[0]}-{rest[1:5]}-{rest[5:]}")
        else:
            samples.append(f"1{second}{rest}")
    return samples


def gen_cn_name(n, ref_data):
    surnames = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
                "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
    given = ref_data.get("cn_given_names", ["小明", "小红", "伟", "芳", "丽"])
    return [random.choice(surnames) + random.choice(given) for _ in range(n)]


def gen_cn_zipcode(n, ref_data):
    zips = ref_data.get("cn_zipcodes", [])
    if zips:
        return [random.choice(zips) for _ in range(n)]
    return [_rand_digits(6) for _ in range(n)]


def gen_cn_bank(n):
    prefixes = ["622", "436", "103", "456", "621"]
    return [random.choice(prefixes) + _rand_digits(random.randint(13, 17)) for _ in range(n)]


# ---- Japan ----

def gen_jp_my_number(n):
    return [_rand_digits(4) + "-" + _rand_digits(4) + "-" + _rand_digits(4)
            if random.random() < 0.5 else _rand_digits(12) for _ in range(n)]


def gen_jp_phone(n):
    samples = []
    for _ in range(n):
        prefix = random.choice(["090", "080", "070"])
        mid = _rand_digits(4)
        last = _rand_digits(4)
        samples.append(f"{prefix}-{mid}-{last}")
    return samples


def gen_jp_zipcode(n, ref_data):
    zips = ref_data.get("jp_zipcodes", [])
    if zips:
        return [random.choice(zips) for _ in range(n)]
    return [_rand_digits(3) + "-" + _rand_digits(4) for _ in range(n)]


def gen_jp_bank(n):
    codes = ["0001", "0009", "0005", "0010", "0034"]
    samples = []
    for _ in range(n):
        code = random.choice(codes)
        branch = _rand_digits(3)
        acct = _rand_digits(7)
        samples.append(f"{code}-{branch}-{acct}")
    return samples


# ---- English Names ----

def gen_en_name(n, ref_data):
    surnames = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
                "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
                "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    given = ref_data.get("en_given_names", ["John", "Jane", "James", "Mary", "Robert"])
    samples = []
    for _ in range(n):
        first = random.choice(given)
        last = random.choice(surnames)
        if random.random() < 0.2:  # 20% middle name
            middle = random.choice(given)
            samples.append(f"{first} {middle} {last}")
        else:
            samples.append(f"{first} {last}")
    return samples


# ---- Taiwan ----

def gen_tw_national_id(n):
    letters = [c for c in string.ascii_uppercase if c not in "IOW"]
    samples = []
    for _ in range(n):
        letter = random.choice(letters)
        gender = random.choice("12")
        rest = _rand_digits(8)
        samples.append(f"{letter}{gender}{rest}")
    return samples


def gen_tw_phone(n):
    samples = []
    for _ in range(n):
        rest = _rand_digits(6)
        mid = _rand_digits(3)
        samples.append(f"09{_rand_digits(2)}-{mid}-{rest[:3]}")
    return samples


def gen_tw_zipcode(n, ref_data):
    zips = ref_data.get("tw_zipcodes", [])
    if zips:
        return [random.choice(zips) for _ in range(n)]
    return [_rand_digits(random.choice([3, 5])) for _ in range(n)]


# ---- India ----

def gen_in_aadhaar(n):
    samples = []
    for _ in range(n):
        first = random.randint(2, 9)
        rest = _rand_digits(11)
        raw = str(first) + rest
        if random.random() < 0.5:
            samples.append(f"{raw[:4]} {raw[4:8]} {raw[8:]}")
        else:
            samples.append(raw)
    return samples


def gen_in_pan(n):
    return ["".join(random.choices(string.ascii_uppercase, k=5)) +
            _rand_digits(4) + random.choice(string.ascii_uppercase)
            for _ in range(n)]


def gen_in_phone(n):
    return [str(random.choice([6, 7, 8, 9])) + _rand_digits(9) for _ in range(n)]


def gen_in_pincode(n, ref_data):
    pins = ref_data.get("in_pincodes", [])
    if pins:
        return [random.choice(pins) for _ in range(n)]
    return [str(random.randint(1, 9)) + _rand_digits(5) for _ in range(n)]


# ---- EU ----

def gen_eu_de_id(n):
    samples = []
    for _ in range(n):
        s = _rand_alnum(9)
        while s.isdigit():
            s = _rand_alnum(9)
        samples.append(s)
    return samples


def gen_eu_fr_insee(n):
    return [random.choice("12") + _rand_digits(14) for _ in range(n)]


def gen_eu_es_dni(n):
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    samples = []
    for _ in range(n):
        num = random.randint(0, 99999999)
        letter = letters[num % 23]
        samples.append(f"{num:08d}{letter}")
    return samples


def gen_eu_nl_bsn(n):
    return [_rand_digits(9) for _ in range(n)]


def gen_eu_uk_nino(n):
    exclude = set("DFIQUV")
    letters = [c for c in string.ascii_uppercase if c not in exclude]
    samples = []
    for _ in range(n):
        prefix = random.choice(letters) + random.choice(letters)
        suffix = random.choice("ABCD")
        samples.append(prefix + _rand_digits(6) + suffix)
    return samples


def gen_eu_passport(n):
    formats = [
        lambda: random.choice("CFGHJK") + _rand_alnum(8),          # DE
        lambda: _rand_digits(2) + "".join(random.choices(string.ascii_uppercase, k=2)) + _rand_digits(5),  # FR
        lambda: "".join(random.choices(string.ascii_uppercase, k=2)) + _rand_digits(7),  # IT
        lambda: "".join(random.choices(string.ascii_uppercase, k=3)) + _rand_digits(6),  # ES
        lambda: _rand_digits(9),  # UK
    ]
    return [random.choice(formats)() for _ in range(n)]


def gen_eu_vat(n):
    fmts = [
        lambda: "DE" + _rand_digits(9),
        lambda: "FR" + _rand_alnum(2) + _rand_digits(9),
        lambda: "IT" + _rand_digits(11),
        lambda: "PL" + _rand_digits(10),
        lambda: "ATU" + _rand_digits(8),
    ]
    return [random.choice(fmts)() for _ in range(n)]


# ---- Common ----

def gen_url(n):
    domains = ["example.com", "test.org", "site.io", "app.dev", "shop.co"]
    paths = ["", "/home", "/about", "/api/v1/data", "/user/123", "/docs"]
    return [f"https://{random.choice(domains)}{random.choice(paths)}" for _ in range(n)]


def gen_date(n):
    samples = []
    for _ in range(n):
        y = random.randint(1950, 2025)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        fmt = random.choice([
            f"{y}-{m:02d}-{d:02d}",
            f"{y}/{m:02d}/{d:02d}",
            f"{m:02d}/{d:02d}/{y}",
        ])
        samples.append(fmt)
    return samples


def gen_swift(n):
    samples = []
    for _ in range(n):
        bank = "".join(random.choices(string.ascii_uppercase, k=4))
        country = random.choice(["US", "GB", "DE", "FR", "JP", "KR", "CN"])
        loc = _rand_alnum(2)
        if random.random() < 0.5:
            branch = _rand_alnum(3)
            samples.append(bank + country + loc + branch)
        else:
            samples.append(bank + country + loc)
    return samples


def gen_ssh_private_key(n):
    types = ["RSA", "EC", "OPENSSH", "DSA"]
    return [f"-----BEGIN {random.choice(types)} PRIVATE KEY-----" for _ in range(n)]


def gen_google_api_key(n):
    return ["AIza" + "".join(random.choices(string.ascii_letters + string.digits + "-_", k=35))
            for _ in range(n)]


# ---------------------------------------------------------------------------
# Negative (non-PII) sample generators
# ---------------------------------------------------------------------------

BENIGN_WORDS = [
    "hello", "world", "the", "quick", "brown", "fox", "jumps", "over", "lazy",
    "dog", "python", "machine", "learning", "data", "science", "algorithm",
    "function", "variable", "module", "class", "object", "array", "string",
    "number", "boolean", "error", "warning", "debug", "info", "server",
    "client", "request", "response", "status", "code", "message", "pattern",
    "engine", "regex", "match", "search", "replace", "split", "join",
    "project", "build", "deploy", "release", "version", "update", "config",
]

BENIGN_SENTENCES = [
    "The meeting is scheduled for next Tuesday.",
    "Please review the pull request before merging.",
    "The server returned a 200 OK response.",
    "We need to update the documentation.",
    "The test suite passed all 42 checks.",
    "Refactored the data processing pipeline.",
    "Added error handling for edge cases.",
    "The deployment was successful.",
    "Fixed a bug in the sorting algorithm.",
    "Updated dependencies to latest versions.",
    "The API rate limit is 1000 requests per hour.",
    "Memory usage is within acceptable limits.",
    "The database migration completed without errors.",
    "Code coverage increased to 85 percent.",
    "The feature flag is currently disabled.",
]


def gen_negative_random_text(n):
    samples = []
    for _ in range(n):
        length = random.randint(3, 10)
        samples.append(" ".join(random.choices(BENIGN_WORDS, k=length)))
    return samples


def gen_negative_sentences(n):
    return [random.choice(BENIGN_SENTENCES) for _ in range(n)]


def gen_negative_numbers(n):
    """Random numbers that look numeric but aren't PII."""
    samples = []
    for _ in range(n):
        kind = random.choice(["short", "decimal", "large", "version", "hex_short"])
        if kind == "short":
            samples.append(str(random.randint(0, 9999)))
        elif kind == "decimal":
            samples.append(f"{random.uniform(0, 1000):.2f}")
        elif kind == "large":
            samples.append(str(random.randint(100000000000000, 999999999999999)))
        elif kind == "version":
            samples.append(f"{random.randint(0,9)}.{random.randint(0,99)}.{random.randint(0,999)}")
        else:
            samples.append("0x" + _rand_hex(random.randint(4, 8)))
    return samples


def gen_negative_near_miss(n):
    """Strings that resemble PII formats but are clearly invalid."""
    samples = []
    for _ in range(n):
        kind = random.choice([
            "bad_ssn", "bad_email", "bad_phone", "bad_cc", "bad_ip", "short_digits"
        ])
        if kind == "bad_ssn":
            samples.append(f"000-00-{_rand_digits(4)}")
        elif kind == "bad_email":
            samples.append(random.choice(["user@", "@domain.com", "no-at-sign.com", "user@.com"]))
        elif kind == "bad_phone":
            samples.append(f"({_rand_digits(2)}) {_rand_digits(3)}-{_rand_digits(2)}")
        elif kind == "bad_cc":
            samples.append(_rand_digits(random.choice([10, 11, 20])))
        elif kind == "bad_ip":
            samples.append(f"999.999.999.999")
        else:
            samples.append(_rand_digits(random.randint(1, 4)))
    return samples


# ---------------------------------------------------------------------------
# Master generator
# ---------------------------------------------------------------------------

GENERATORS = {
    # US
    ("us", "ssn", "ssn_01"): gen_us_ssn,
    ("us", "ssn", "itin_01"): gen_us_itin,
    ("us", "phone", "phone_01"): gen_us_phone,
    ("us", "identification", "passport_01"): gen_us_passport,
    ("us", "identification", "driver_license_ca_01"): gen_us_driver_license_ca,
    ("us", "identification", "medicare_01"): gen_us_medicare,
    ("us", "medical", "npi_id"): gen_us_npi,
    ("us", "other", "ein_01"): gen_us_ein,
    # Common
    ("comm", "email", "email_01"): gen_email,
    ("comm", "credit_card", "credit_card_visa_01"): gen_visa,
    ("comm", "credit_card", "credit_card_mastercard_01"): gen_mastercard,
    ("comm", "credit_card", "credit_card_amex_01"): gen_amex,
    ("comm", "credit_card", "credit_card_discover_01"): gen_discover,
    ("comm", "credit_card", "credit_card_jcb_01"): gen_jcb,
    ("comm", "credit_card", "credit_card_diners_01"): gen_diners,
    ("comm", "ip", "ipv4_01"): gen_ipv4,
    ("comm", "crypto", "crypto_btc_p2pkh"): gen_btc,
    ("comm", "crypto", "crypto_eth_01"): gen_eth,
    ("comm", "cloud_credentials", "aws_access_key"): gen_aws_access_key,
    ("comm", "cloud_credentials", "google_api_key"): gen_google_api_key,
    ("comm", "financial", "swift_bic"): gen_swift,
    ("comm", "private_keys", "ssh_private_key"): gen_ssh_private_key,
    ("comm", "url", "url_01"): gen_url,
    ("comm", "date", "date_iso_01"): gen_date,
    # Korea
    ("kr", "rrn", "rrn_01"): gen_kr_rrn,
    ("kr", "rrn", "alien_registration_01"): gen_kr_alien,
    ("kr", "phone", "mobile_01"): gen_kr_phone,
    ("kr", "bank", "kr_bank"): gen_kr_bank,
    # China
    ("cn", "identification", "national_id_01"): gen_cn_national_id,
    ("cn", "phone", "mobile_01"): gen_cn_phone,
    ("cn", "bank", "cn_bank"): gen_cn_bank,
    # Japan
    ("jp", "identification", "my_number_01"): gen_jp_my_number,
    ("jp", "phone", "mobile_01"): gen_jp_phone,
    ("jp", "bank", "jp_bank"): gen_jp_bank,
    # Taiwan
    ("tw", "identification", "national_id_01"): gen_tw_national_id,
    ("tw", "phone", "mobile_01"): gen_tw_phone,
    # India
    ("in", "identification", "aadhaar_01"): gen_in_aadhaar,
    ("in", "identification", "pan_01"): gen_in_pan,
    ("in", "phone", "mobile_01"): gen_in_phone,
    # EU
    ("eu", "identification", "germany_personalausweis_01"): gen_eu_de_id,
    ("eu", "identification", "france_insee_01"): gen_eu_fr_insee,
    ("eu", "identification", "spain_dni_01"): gen_eu_es_dni,
    ("eu", "identification", "netherlands_bsn_01"): gen_eu_nl_bsn,
    ("eu", "identification", "uk_nino_01"): gen_eu_uk_nino,
    ("eu", "passport", "eu_passport"): gen_eu_passport,
    ("eu", "vat", "eu_vat"): gen_eu_vat,
    # IBAN
    ("comm", "iban", "iban_01"): gen_iban,
}

# Generators that need reference data (pass ref_data as second arg)
GENERATORS_WITH_REF = {
    ("us", "other", "zipcode_01"): gen_us_zipcode,
    ("kr", "other", "zipcode_kr"): gen_kr_zipcode,
    ("kr", "name", "korean_name"): gen_kr_name,
    ("cn", "other", "zipcode_cn"): gen_cn_zipcode,
    ("cn", "name", "chinese_name"): gen_cn_name,
    ("jp", "other", "zipcode_jp"): gen_jp_zipcode,
    ("tw", "other", "zipcode_tw"): gen_tw_zipcode,
    ("in", "other", "pincode_in"): gen_in_pincode,
    ("comm", "other", "name_en"): gen_en_name,
}


def generate_all_positive(samples_per_pattern=30, ref_data=None):
    """Generate positive (PII) samples for all pattern types."""
    if ref_data is None:
        ref_data = {}

    rows = []
    for (loc, cat, pid), gen_fn in GENERATORS.items():
        for text in gen_fn(samples_per_pattern):
            rows.append({
                "text": text,
                "label": 1,
                "category": cat,
                "location": loc,
                "pattern_id": pid,
            })

    for (loc, cat, pid), gen_fn in GENERATORS_WITH_REF.items():
        for text in gen_fn(samples_per_pattern, ref_data):
            rows.append({
                "text": text,
                "label": 1,
                "category": cat,
                "location": loc,
                "pattern_id": pid,
            })

    return rows


def generate_all_negative(total):
    """Generate negative (non-PII) samples."""
    rows = []
    per_type = total // 4

    for text in gen_negative_random_text(per_type):
        rows.append({"text": text, "label": 0, "category": "none", "location": "none", "pattern_id": "none"})
    for text in gen_negative_sentences(per_type):
        rows.append({"text": text, "label": 0, "category": "none", "location": "none", "pattern_id": "none"})
    for text in gen_negative_numbers(per_type):
        rows.append({"text": text, "label": 0, "category": "none", "location": "none", "pattern_id": "none"})
    for text in gen_negative_near_miss(total - 3 * per_type):
        rows.append({"text": text, "label": 0, "category": "none", "location": "none", "pattern_id": "none"})

    return rows


# ---------------------------------------------------------------------------
# Split & write
# ---------------------------------------------------------------------------

def split_data(rows, train_ratio=0.7, val_ratio=0.15):
    """Shuffle and split into train / val / test."""
    random.shuffle(rows)
    n = len(rows)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    return rows[:train_end], rows[train_end:val_end], rows[val_end:]


def write_csv(rows, path):
    fields = ["text", "label", "category", "location", "pattern_id"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate PII training data for ML classifiers")
    parser.add_argument("--output_dir", type=str, default=None,
                        help="Directory to save generated CSV data (default: ml/data/)")
    parser.add_argument("--samples_per_pattern", type=int, default=35,
                        help="Number of samples to generate per pattern")
    cli_args = parser.parse_args()

    print("Loading reference data...")
    ref_data = load_reference_data()

    samples_per_pattern = cli_args.samples_per_pattern

    print("Generating positive (PII) samples...")
    positive = generate_all_positive(samples_per_pattern, ref_data)
    print(f"  Positive samples: {len(positive)}")

    # Generate negatives to reach >= 3000 total (roughly 40% negative)
    neg_count = max(1200, int(len(positive) * 0.65))
    print("Generating negative (non-PII) samples...")
    negative = generate_all_negative(neg_count)
    print(f"  Negative samples: {len(negative)}")

    all_rows = positive + negative
    print(f"  Total samples:    {len(all_rows)}")

    print("Splitting into train / val / test...")
    train, val, test = split_data(all_rows)

    out_dir = Path(cli_args.output_dir) if cli_args.output_dir else Path(__file__).parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(train, out_dir / "train.csv")
    write_csv(val, out_dir / "val.csv")
    write_csv(test, out_dir / "test.csv")

    print(f"\nDataset written to {out_dir}/")
    print(f"  train.csv: {len(train)} rows")
    print(f"  val.csv:   {len(val)} rows")
    print(f"  test.csv:  {len(test)} rows")
    print(f"  TOTAL:     {len(train) + len(val) + len(test)} rows")

    # Category distribution
    from collections import Counter
    cat_counts = Counter(r["category"] for r in all_rows)
    print("\nCategory distribution:")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:<25s} {cnt:>5d}")


if __name__ == "__main__":
    main()
