"""
Tests for verification functions.

This module contains comprehensive tests for all verification functions
used in the pattern engine.
"""

import sys
from pathlib import Path

# Add verification module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "verification" / "python"))

import pytest

from verification import (
    belgium_rrn_valid,
    cn_national_id_valid,
    contains_letter,
    credit_card_bin_valid,
    dms_coordinate,
    finland_hetu_valid,
    france_insee_valid,
    generic_number_not_timestamp,
    get_verification_function,
    high_entropy_token,
    iban_mod97,
    india_aadhaar_valid,
    india_pan_valid,
    ipv4_public,
    jp_my_number_valid,
    korean_bank_account_valid,
    korean_zipcode_valid,
    kr_alien_registration_valid,
    kr_business_registration_valid,
    kr_corporate_registration_valid,
    kr_rrn_valid,
    luhn,
    netherlands_bsn_valid,
    not_repeating_pattern,
    not_timestamp,
    poland_pesel_valid,
    register_verification_function,
    spain_dni_valid,
    spain_nie_valid,
    sweden_personnummer_valid,
    tw_national_id_valid,
    unregister_verification_function,
    us_ssn_valid,
    us_zipcode_valid,
)


class TestIbanMod97:
    """Tests for IBAN mod-97 verification."""

    def test_valid_iban(self):
        """Test valid IBAN numbers."""
        valid_ibans = [
            "GB82WEST12345698765432",
            "DE89370400440532013000",
            "FR1420041010050500013M02606",
            "IT60X0542811101000000123456",
            "ES9121000418450200051332",
        ]
        for iban in valid_ibans:
            assert iban_mod97(iban), f"Expected {iban} to be valid"

    def test_valid_iban_with_spaces(self):
        """Test valid IBAN with spaces."""
        assert iban_mod97("GB82 WEST 1234 5698 7654 32")

    def test_invalid_iban_checksum(self):
        """Test invalid IBAN checksum."""
        invalid_ibans = [
            "GB82WEST12345698765433",  # Wrong checksum
            "DE89370400440532013001",  # Wrong checksum
        ]
        for iban in invalid_ibans:
            assert not iban_mod97(iban), f"Expected {iban} to be invalid"

    def test_invalid_iban_characters(self):
        """Test IBAN with invalid characters."""
        assert not iban_mod97("GB82@WEST12345698765432")
        assert not iban_mod97("GB82 WEST 1234 5698 7654 3!")

    def test_empty_string(self):
        """Test empty string."""
        assert not iban_mod97("")


class TestLuhn:
    """Tests for Luhn algorithm verification."""

    def test_valid_credit_cards(self):
        """Test valid credit card numbers."""
        valid_cards = [
            "4111111111111111",  # Visa test card
            "5500000000000004",  # MasterCard test card
            "378282246310005",  # Amex test card
            "6011111111111117",  # Discover test card
        ]
        for card in valid_cards:
            assert luhn(card), f"Expected {card} to pass Luhn check"

    def test_invalid_credit_cards(self):
        """Test invalid credit card numbers."""
        invalid_cards = [
            "4111111111111112",
            "5500000000000005",
            "1234567890123456",
        ]
        for card in invalid_cards:
            assert not luhn(card), f"Expected {card} to fail Luhn check"

    def test_with_spaces_and_dashes(self):
        """Test Luhn with formatted card numbers."""
        assert luhn("4111-1111-1111-1111")
        assert luhn("4111 1111 1111 1111")

    def test_empty_string(self):
        """Test empty string."""
        assert not luhn("")

    def test_non_numeric(self):
        """Test non-numeric string."""
        assert not luhn("abcd")


class TestDmsCoordinate:
    """Tests for DMS coordinate verification."""

    def test_valid_latitude(self):
        """Test valid latitude coordinates."""
        valid_coords = [
            "37°46′29.7″N",
            "40°42′46″N",
            "0°0′0″N",
            "90°0′0″S",
        ]
        for coord in valid_coords:
            assert dms_coordinate(coord), f"Expected {coord} to be valid"

    def test_valid_longitude(self):
        """Test valid longitude coordinates."""
        valid_coords = [
            "122°25′9.8″W",
            "74°0′21.5″W",
            "0°0′0″E",
            "180°0′0″W",
        ]
        for coord in valid_coords:
            assert dms_coordinate(coord), f"Expected {coord} to be valid"

    def test_invalid_latitude_degrees(self):
        """Test latitude with invalid degrees (>90)."""
        assert not dms_coordinate("91°0′0″N")
        assert not dms_coordinate("100°0′0″S")

    def test_invalid_longitude_degrees(self):
        """Test longitude with invalid degrees (>180)."""
        assert not dms_coordinate("181°0′0″E")
        assert not dms_coordinate("200°0′0″W")

    def test_invalid_minutes(self):
        """Test coordinates with invalid minutes (>59)."""
        assert not dms_coordinate("40°60′0″N")
        assert not dms_coordinate("40°70′0″N")

    def test_invalid_seconds(self):
        """Test coordinates with invalid seconds (>=60)."""
        assert not dms_coordinate("40°30′60″N")
        assert not dms_coordinate("40°30′65.5″N")

    def test_invalid_format(self):
        """Test invalid coordinate formats."""
        assert not dms_coordinate("40 degrees 30 minutes N")
        assert not dms_coordinate("40.123N")


class TestHighEntropyToken:
    """Tests for high entropy token verification."""

    def test_valid_high_entropy_tokens(self):
        """Test valid high entropy tokens."""
        valid_tokens = [
            "ghp_1234567890abcdefghijklmnopqrstuvwxyz",  # GitHub token-like
            "sk_test_4eC39HqLyjWDarjtT1zdp7dc",  # Stripe test key-like
            "xoxb-1234567890123-1234567890123-abcdefghijklmnopqrstuvwx",  # Slack-like
            "AIzaSyD-1234567890abcdefghijklmnopqrstuv",  # Google API key-like
            (
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
                "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
            ),  # JWT
        ]
        for token in valid_tokens:
            assert high_entropy_token(token), f"Expected {token} to be high entropy"

    def test_low_entropy_tokens(self):
        """Test low entropy tokens (repetitive)."""
        low_entropy = [
            "aaaaaaaaaaaaaaaaaaaa",
            "1111111111111111111111",
            "abcabcabcabcabcabcabcabc",
        ]
        for token in low_entropy:
            assert not high_entropy_token(token), f"Expected {token} to be low entropy"

    def test_too_short(self):
        """Test tokens that are too short."""
        assert not high_entropy_token("abc123")
        assert not high_entropy_token("shorttoken")

    def test_with_spaces(self):
        """Test tokens with spaces (should fail)."""
        assert not high_entropy_token("ghp_1234567890 abcdefghijklmnopqrstuvwxyz")

    def test_invalid_characters(self):
        """Test tokens with invalid characters."""
        assert not high_entropy_token("ghp_1234567890@#$%^&*()")


class TestNotTimestamp:
    """Tests for not-timestamp verification."""

    def test_unix_timestamp_10_digits(self):
        """Test 10-digit Unix timestamps (should return False)."""
        timestamps = [
            "1609459200",  # 2021-01-01
            "1735689600",  # 2025-01-01
            "1234567890",  # 2009-02-13
        ]
        for ts in timestamps:
            assert not not_timestamp(ts), f"Expected {ts} to be detected as timestamp"

    def test_unix_timestamp_ms_13_digits(self):
        """Test 13-digit Unix timestamps in milliseconds (should return False)."""
        timestamps = [
            "1609459200000",  # 2021-01-01
            "1735689600000",  # 2025-01-01
        ]
        for ts in timestamps:
            assert not not_timestamp(ts), f"Expected {ts} to be detected as timestamp"

    def test_compact_datetime_14_digits(self):
        """Test 14-digit compact datetime (should return False)."""
        timestamps = [
            "20210101120000",  # 2021-01-01 12:00:00
            "20251231235959",  # 2025-12-31 23:59:59
        ]
        for ts in timestamps:
            assert not not_timestamp(ts), f"Expected {ts} to be detected as timestamp"

    def test_valid_account_numbers(self):
        """Test valid account numbers (should return True)."""
        accounts = [
            "123456789",  # 9 digits
            "12345678",  # 8 digits
            "123456789012",  # 12 digits (not timestamp range)
        ]
        for account in accounts:
            assert not_timestamp(account), f"Expected {account} to NOT be timestamp"

    def test_non_numeric(self):
        """Test non-numeric strings."""
        assert not_timestamp("abc123")
        assert not_timestamp("not-a-number")


class TestKoreanZipcodeValid:
    """Tests for Korean zipcode verification."""

    def test_valid_zipcodes(self):
        """Test valid Korean postal codes."""
        valid_codes = [
            "06234",
            "13579",
            "24680",
            "03158",
        ]
        for code in valid_codes:
            assert korean_zipcode_valid(code), f"Expected {code} to be valid"

    def test_sequential_patterns(self):
        """Test sequential patterns (should be rejected)."""
        invalid_codes = [
            "12345",  # Sequential up
            "54321",  # Sequential down
        ]
        for code in invalid_codes:
            assert not korean_zipcode_valid(code), f"Expected {code} to be invalid"

    def test_all_same_digit(self):
        """Test all same digit (should be rejected)."""
        invalid_codes = [
            "00000",
            "11111",
            "99999",
        ]
        for code in invalid_codes:
            assert not korean_zipcode_valid(code), f"Expected {code} to be invalid"

    def test_too_round_numbers(self):
        """Test numbers that are multiples of 10000."""
        invalid_codes = [
            "10000",
            "50000",
            "90000",
        ]
        for code in invalid_codes:
            assert not korean_zipcode_valid(code), f"Expected {code} to be invalid"

    def test_wrong_length(self):
        """Test wrong length postal codes."""
        assert not korean_zipcode_valid("1234")
        assert not korean_zipcode_valid("123456")


class TestUsZipcodeValid:
    """Tests for US zipcode verification."""

    def test_valid_5_digit_zip(self):
        """Test valid 5-digit ZIP codes."""
        valid_codes = [
            "10001",
            "90210",
            "60601",
        ]
        for code in valid_codes:
            assert us_zipcode_valid(code), f"Expected {code} to be valid"

    def test_valid_9_digit_zip(self):
        """Test valid 9-digit ZIP+4 codes."""
        valid_codes = [
            "10001-1234",
            "902101234",
            "60601-5678",
        ]
        for code in valid_codes:
            assert us_zipcode_valid(code), f"Expected {code} to be valid"

    def test_sequential_patterns(self):
        """Test sequential patterns (should be rejected)."""
        invalid_codes = [
            "12345",
            "54321",
        ]
        for code in invalid_codes:
            assert not us_zipcode_valid(code), f"Expected {code} to be invalid"

    def test_all_same_digit(self):
        """Test all same digit (should be rejected)."""
        invalid_codes = [
            "00000",
            "11111",
            "99999",
        ]
        for code in invalid_codes:
            assert not us_zipcode_valid(code), f"Expected {code} to be invalid"

    def test_wrong_length(self):
        """Test wrong length ZIP codes."""
        assert not us_zipcode_valid("1234")
        assert not us_zipcode_valid("123456")


class TestKoreanBankAccountValid:
    """Tests for Korean bank account verification."""

    def test_valid_with_known_prefix(self):
        """Test valid bank accounts with known prefixes."""
        valid_accounts = [
            "110-123-456789",  # Kookmin Bank
            "1002-123-456789",  # Woori Bank
            "301-1234-5678",  # Nonghyup
            "3333-12-3456789",  # Kakao Bank
        ]
        for account in valid_accounts:
            assert korean_bank_account_valid(account), f"Expected {account} to be valid"

    def test_unix_timestamp_rejected(self):
        """Test that Unix timestamps are rejected."""
        timestamps = [
            "1609459200",  # 10-digit Unix timestamp
            "1735689600000",  # 13-digit Unix timestamp ms
        ]
        for ts in timestamps:
            assert not korean_bank_account_valid(ts), f"Expected {ts} to be rejected"

    def test_compact_datetime_rejected(self):
        """Test that compact datetime is rejected."""
        assert not korean_bank_account_valid("20210101120000")

    def test_account_without_known_prefix(self):
        """Test accounts without known prefixes (more strict validation)."""
        # Valid account that's not a timestamp
        assert korean_bank_account_valid("987-654-321012")


class TestGenericNumberNotTimestamp:
    """Tests for generic number timestamp verification."""

    def test_with_separators_accepted(self):
        """Test that numbers with separators are generally accepted."""
        assert generic_number_not_timestamp("123-456-789")
        assert generic_number_not_timestamp("123 456 789")
        assert generic_number_not_timestamp("123/456/789")

    def test_unix_timestamp_rejected(self):
        """Test that Unix timestamps without separators are rejected."""
        assert not generic_number_not_timestamp("1609459200")
        assert not generic_number_not_timestamp("1735689600000")

    def test_compact_datetime_rejected(self):
        """Test that compact datetime is rejected."""
        assert not generic_number_not_timestamp("20210101120000")

    def test_compact_datetime_with_separators_rejected(self):
        """Test that compact datetime with separators is also rejected."""
        assert not generic_number_not_timestamp("2021-01-01-120000")


class TestContainsLetter:
    """Tests for contains_letter verification."""

    def test_strings_with_letters(self):
        """Test strings containing letters."""
        assert contains_letter("abc123")
        assert contains_letter("hello")
        assert contains_letter("123a456")
        assert contains_letter("A")

    def test_strings_without_letters(self):
        """Test strings without letters."""
        assert not contains_letter("123456")
        assert not contains_letter("!@#$%")
        assert not contains_letter("123-456-789")

    def test_empty_string(self):
        """Test empty string."""
        assert not contains_letter("")


class TestUsSsnValid:
    """Tests for US SSN verification."""

    def test_valid_ssn(self):
        """Test valid SSN numbers."""
        valid_ssns = [
            "123-45-6789",
            "123456789",
            "765-43-2109",
        ]
        for ssn in valid_ssns:
            assert us_ssn_valid(ssn), f"Expected {ssn} to be valid"

    def test_invalid_area_000(self):
        """Test SSN with area 000 (invalid)."""
        assert not us_ssn_valid("000-45-6789")

    def test_invalid_area_666(self):
        """Test SSN with area 666 (invalid)."""
        assert not us_ssn_valid("666-45-6789")

    def test_invalid_area_900_plus(self):
        """Test SSN with area 900+ (invalid)."""
        assert not us_ssn_valid("900-45-6789")
        assert not us_ssn_valid("999-45-6789")

    def test_invalid_group_00(self):
        """Test SSN with group 00 (invalid)."""
        assert not us_ssn_valid("123-00-6789")

    def test_invalid_serial_0000(self):
        """Test SSN with serial 0000 (invalid)."""
        assert not us_ssn_valid("123-45-0000")

    def test_wrong_length(self):
        """Test SSN with wrong length."""
        assert not us_ssn_valid("123-45-678")
        assert not us_ssn_valid("123-45-67890")


class TestKoreanRrnValid:
    """Tests for Korean RRN (주민등록번호) verification."""

    def test_valid_rrn(self):
        """Test valid Korean RRN numbers."""
        valid_rrns = [
            "900101-1234568",
            "850315-2345678",
            "0502153456789",
        ]
        for rrn in valid_rrns:
            assert kr_rrn_valid(rrn), f"Expected {rrn} to be valid"

    def test_invalid_month(self):
        """Test RRN with invalid month (>12)."""
        assert not kr_rrn_valid("901301-1234567")  # Month 13
        assert not kr_rrn_valid("900001-1234567")  # Month 00

    def test_invalid_day(self):
        """Test RRN with invalid day (>31)."""
        assert not kr_rrn_valid("900132-1234567")  # Day 32
        assert not kr_rrn_valid("900100-1234567")  # Day 00

    def test_invalid_gender_digit(self):
        """Test RRN with invalid gender/century digit."""
        assert not kr_rrn_valid("900101-5234567")  # 5 is for foreigners
        assert not kr_rrn_valid("900101-0234567")  # 0 is invalid

    def test_invalid_checksum(self):
        """Test RRN with invalid checksum."""
        assert not kr_rrn_valid("900101-1234567")  # Wrong checksum

    def test_all_same_digits(self):
        """Test RRN with all same digits."""
        assert not kr_rrn_valid("1111111111111")


class TestKoreanAlienRegistrationValid:
    """Tests for Korean Alien Registration (외국인등록번호) verification."""

    def test_valid_alien_registration(self):
        """Test valid alien registration numbers."""
        valid_numbers = [
            "900101-5234567",
            "850315-6789012",
            "920228-7123456",
        ]
        for num in valid_numbers:
            assert kr_alien_registration_valid(num), f"Expected {num} to be valid"

    def test_invalid_gender_digit(self):
        """Test with citizen gender digits (should fail)."""
        assert not kr_alien_registration_valid("900101-1234567")  # 1 is for citizens
        assert not kr_alien_registration_valid("900101-4234567")  # 4 is for citizens

    def test_invalid_month(self):
        """Test with invalid month."""
        assert not kr_alien_registration_valid("901301-5234567")  # Month 13

    def test_invalid_day(self):
        """Test with invalid day."""
        assert not kr_alien_registration_valid("900132-5234567")  # Day 32


class TestKoreanCorporateRegistrationValid:
    """Tests for Korean Corporate Registration Number (법인등록번호) verification."""

    def test_valid_corporate_registration(self):
        """Test valid corporate registration numbers."""
        valid_numbers = [
            "110111-1234568",
            "134511-2345671",
            "1801115678906",
        ]
        for num in valid_numbers:
            assert kr_corporate_registration_valid(num), f"Expected {num} to be valid"

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not kr_corporate_registration_valid("123456-1234567")

    def test_all_same_digits(self):
        """Test with all same digits."""
        assert not kr_corporate_registration_valid("1111111111111")


class TestJapaneseMyNumberValid:
    """Tests for Japanese My Number (マイナンバー) verification."""

    def test_valid_my_number(self):
        """Test valid My Number."""
        valid_numbers = [
            "1234-5678-9018",
            "987654321093",
            "5555-5555-5557",
        ]
        for num in valid_numbers:
            assert jp_my_number_valid(num), f"Expected {num} to be valid"

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not jp_my_number_valid("123456789012")
        assert not jp_my_number_valid("1234-5678-9012")

    def test_all_same_digits(self):
        """Test with all same digits."""
        assert not jp_my_number_valid("111111111111")

    def test_sequential_pattern(self):
        """Test sequential patterns."""
        assert not jp_my_number_valid("123456789012")


class TestChineseNationalIdValid:
    """Tests for Chinese National ID verification."""

    def test_valid_national_id(self):
        """Test valid Chinese National ID."""
        valid_ids = [
            "110101199003074557",
            "32010219901010123X",
            "440301198501014568",
        ]
        for id_num in valid_ids:
            assert cn_national_id_valid(id_num), f"Expected {id_num} to be valid"

    def test_invalid_province(self):
        """Test with invalid province code."""
        assert not cn_national_id_valid("990101199003074559")  # 99 is invalid

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not cn_national_id_valid("110101199003074559")

    def test_invalid_date(self):
        """Test with invalid birth date."""
        assert not cn_national_id_valid("110101199013074557")  # Month 13


class TestTaiwanNationalIdValid:
    """Tests for Taiwan National ID verification."""

    def test_valid_national_id(self):
        """Test valid Taiwan National ID."""
        valid_ids = [
            "A123456789",
            "B123456780",
            "F131104093",
        ]
        for id_num in valid_ids:
            assert tw_national_id_valid(id_num), f"Expected {id_num} to be valid"

    def test_invalid_letter(self):
        """Test with invalid first letter (I, O, W not used)."""
        assert not tw_national_id_valid("I123456789")
        assert not tw_national_id_valid("O123456789")
        assert not tw_national_id_valid("W123456789")

    def test_invalid_gender_digit(self):
        """Test with invalid gender digit."""
        assert not tw_national_id_valid("A023456789")  # Gender must be 1 or 2

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not tw_national_id_valid("A123456788")


class TestIndiaAadhaarValid:
    """Tests for India Aadhaar verification (Verhoeff algorithm)."""

    def test_valid_aadhaar(self):
        """Test valid Aadhaar numbers."""
        valid_numbers = [
            "2345-6789-0124",
            "499118665246",
            "8765-4321-0988",
        ]
        for num in valid_numbers:
            assert india_aadhaar_valid(num), f"Expected {num} to be valid"

    def test_first_digit_invalid(self):
        """Test that first digit cannot be 0 or 1."""
        assert not india_aadhaar_valid("0234-5678-9012")
        assert not india_aadhaar_valid("1234-5678-9012")

    def test_all_same_digits(self):
        """Test with all same digits."""
        assert not india_aadhaar_valid("222222222222")

    def test_invalid_checksum(self):
        """Test with invalid Verhoeff checksum."""
        assert not india_aadhaar_valid("2345-6789-0123")


class TestIndiaPanValid:
    """Tests for India PAN verification."""

    def test_valid_pan(self):
        """Test valid PAN numbers."""
        valid_pans = [
            "BNZPM2501F",
            "AFRPC1234M",
            "XYZKP9876M",
        ]
        for pan in valid_pans:
            assert india_pan_valid(pan), f"Expected {pan} to be valid"

    def test_invalid_entity_type(self):
        """Test with invalid 4th character (entity type)."""
        assert not india_pan_valid("ABCDE1234F")  # D is invalid entity type
        assert not india_pan_valid("ABXYZ1234F")  # Y is invalid entity type

    def test_test_patterns_rejected(self):
        """Test that obvious test patterns are rejected."""
        assert not india_pan_valid("AAAAA1234F")
        assert not india_pan_valid("ABCDE1234F")


class TestSpainDniValid:
    """Tests for Spanish DNI verification."""

    def test_valid_dni(self):
        """Test valid DNI numbers."""
        valid_dnis = [
            "12345678Z",
            "87654321X",
            "44444444A",
        ]
        for dni in valid_dnis:
            assert spain_dni_valid(dni), f"Expected {dni} to be valid"

    def test_invalid_checksum(self):
        """Test with invalid checksum letter."""
        assert not spain_dni_valid("12345678A")  # Wrong letter
        assert not spain_dni_valid("12345678B")


class TestSpainNieValid:
    """Tests for Spanish NIE verification."""

    def test_valid_nie(self):
        """Test valid NIE numbers."""
        valid_nies = [
            "X1234567L",
            "Y1234567X",
            "Z1234567R",
        ]
        for nie in valid_nies:
            assert spain_nie_valid(nie), f"Expected {nie} to be valid"

    def test_invalid_first_letter(self):
        """Test with invalid first letter."""
        assert not spain_nie_valid("A1234567L")

    def test_invalid_checksum(self):
        """Test with invalid checksum letter."""
        assert not spain_nie_valid("X1234567A")


class TestNetherlandsBsnValid:
    """Tests for Dutch BSN (11-proof) verification."""

    def test_valid_bsn(self):
        """Test valid BSN numbers."""
        valid_bsns = [
            "111111110",
            "234567892",
        ]
        for bsn in valid_bsns:
            assert netherlands_bsn_valid(bsn), f"Expected {bsn} to be valid"

    def test_invalid_11_proof(self):
        """Test BSN that fails 11-proof."""
        assert not netherlands_bsn_valid("123456789")
        assert not netherlands_bsn_valid("111111111")

    def test_8_digit_bsn(self):
        """Test that 8-digit BSN is handled."""
        # 8 digits get prepended with 0
        assert netherlands_bsn_valid("10000008")  # Becomes 010000008


class TestPolandPeselValid:
    """Tests for Polish PESEL verification."""

    def test_valid_pesel(self):
        """Test valid PESEL numbers."""
        valid_pesels = [
            "44051401359",
            "02261308547",
        ]
        for pesel in valid_pesels:
            assert poland_pesel_valid(pesel), f"Expected {pesel} to be valid"

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not poland_pesel_valid("44051401350")

    def test_all_same_digits(self):
        """Test with all same digits."""
        assert not poland_pesel_valid("11111111111")

    def test_2000s_birth(self):
        """Test PESEL for person born in 2000s (month + 20)."""
        # Month 26 means June 2000s
        assert poland_pesel_valid("02261308547")  # Born in Feb 2002


class TestSwedenPersonnummerValid:
    """Tests for Swedish Personnummer (Luhn) verification."""

    def test_valid_personnummer(self):
        """Test valid Personnummer."""
        valid_pnums = [
            "900101-1239",
            "850315-2343",
            "199001011239",
        ]
        for pnum in valid_pnums:
            assert sweden_personnummer_valid(pnum), f"Expected {pnum} to be valid"

    def test_invalid_luhn(self):
        """Test with invalid Luhn checksum."""
        assert not sweden_personnummer_valid("900101-1230")

    def test_invalid_date(self):
        """Test with invalid date."""
        assert not sweden_personnummer_valid("901301-1234")  # Month 13


class TestFranceInseeValid:
    """Tests for French INSEE (mod-97) verification."""

    def test_valid_insee(self):
        """Test valid INSEE numbers."""
        valid_insees = [
            "188057813579816",
            "295017535679891",
        ]
        for insee in valid_insees:
            assert france_insee_valid(insee), f"Expected {insee} to be valid"

    def test_invalid_sex_digit(self):
        """Test with invalid sex digit (must be 1 or 2)."""
        assert not france_insee_valid("388057813579897")

    def test_invalid_checksum(self):
        """Test with invalid mod-97 checksum."""
        assert not france_insee_valid("188057813579897")


class TestBelgiumRrnValid:
    """Tests for Belgian RRN (mod-97) verification."""

    def test_valid_rrn(self):
        """Test valid Belgian RRN."""
        valid_rrns = [
            "85.07.30-123-35",
            "850730-123-35",
            "85073012335",
        ]
        for rrn in valid_rrns:
            assert belgium_rrn_valid(rrn), f"Expected {rrn} to be valid"

    def test_invalid_checksum(self):
        """Test with invalid checksum."""
        assert not belgium_rrn_valid("85.07.30-123-45")

    def test_invalid_date(self):
        """Test with invalid date."""
        assert not belgium_rrn_valid("85.13.30-123-35")  # Month 13


class TestFinlandHetuValid:
    """Tests for Finnish HETU verification."""

    def test_valid_hetu(self):
        """Test valid HETU."""
        valid_hetus = [
            "010190-123M",
            "311285-456A",
        ]
        for hetu in valid_hetus:
            assert finland_hetu_valid(hetu), f"Expected {hetu} to be valid"

    def test_invalid_check_char(self):
        """Test with invalid check character."""
        assert not finland_hetu_valid("010190-123A")

    def test_invalid_century_sign(self):
        """Test with invalid century sign."""
        assert not finland_hetu_valid("010190*123A")

    def test_invalid_date(self):
        """Test with invalid date."""
        assert not finland_hetu_valid("321285-456A")  # Day 32


class TestIpv4Public:
    """Tests for IPv4 public address verification."""

    def test_public_ips(self):
        """Test public IP addresses."""
        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "142.250.185.206",
        ]
        for ip in public_ips:
            assert ipv4_public(ip), f"Expected {ip} to be public"

    def test_private_ips(self):
        """Test private IP addresses (should return False)."""
        private_ips = [
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
        ]
        for ip in private_ips:
            assert not ipv4_public(ip), f"Expected {ip} to be private"

    def test_loopback(self):
        """Test loopback addresses."""
        assert not ipv4_public("127.0.0.1")

    def test_reserved(self):
        """Test reserved addresses."""
        assert not ipv4_public("0.0.0.0")
        assert not ipv4_public("255.255.255.255")


class TestCreditCardBinValid:
    """Tests for credit card BIN validation."""

    def test_valid_visa(self):
        """Test valid Visa card."""
        assert credit_card_bin_valid("4111111111111111")

    def test_valid_mastercard(self):
        """Test valid Mastercard."""
        assert credit_card_bin_valid("5500000000000004")

    def test_valid_amex(self):
        """Test valid American Express."""
        assert credit_card_bin_valid("378282246310005")

    def test_invalid_bin(self):
        """Test invalid BIN prefix."""
        assert not credit_card_bin_valid("9111111111111111")  # 9 is not valid BIN

    def test_invalid_luhn(self):
        """Test invalid Luhn checksum."""
        assert not credit_card_bin_valid("4111111111111112")


class TestNotRepeatingPattern:
    """Tests for not-repeating-pattern verification."""

    def test_valid_non_repeating(self):
        """Test valid non-repeating values."""
        valid_values = [
            "135792468024",
            "RandomString",
            "Test-Value-123",
        ]
        for value in valid_values:
            assert not_repeating_pattern(value), f"Expected {value} to be valid"

    def test_all_same_character(self):
        """Test all same character (should fail)."""
        assert not not_repeating_pattern("11111111")
        assert not not_repeating_pattern("AAAAAAAA")

    def test_sequential_digits(self):
        """Test sequential digits (should fail)."""
        assert not not_repeating_pattern("12345678")
        assert not not_repeating_pattern("87654321")

    def test_two_char_repeat(self):
        """Test two-character repeating pattern."""
        assert not not_repeating_pattern("12121212")
        assert not not_repeating_pattern("ABABABAB")


class TestVerificationRegistry:
    """Tests for verification function registry."""

    def test_get_verification_function(self):
        """Test getting verification functions by name."""
        assert get_verification_function("luhn") == luhn
        assert get_verification_function("iban_mod97") == iban_mod97
        assert get_verification_function("nonexistent") is None

    def test_register_verification_function(self):
        """Test registering custom verification function."""

        def custom_verify(value: str) -> bool:
            return value == "custom"

        register_verification_function("custom_test", custom_verify)
        assert get_verification_function("custom_test") == custom_verify
        assert get_verification_function("custom_test")("custom")
        assert not get_verification_function("custom_test")("other")

        # Cleanup
        unregister_verification_function("custom_test")

    def test_unregister_verification_function(self):
        """Test unregistering verification function."""

        def temp_verify(value: str) -> bool:
            return True

        register_verification_function("temp_test", temp_verify)
        assert get_verification_function("temp_test") is not None

        assert unregister_verification_function("temp_test")
        assert get_verification_function("temp_test") is None

    def test_unregister_nonexistent_function(self):
        """Test unregistering non-existent function."""
        assert not unregister_verification_function("nonexistent")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
