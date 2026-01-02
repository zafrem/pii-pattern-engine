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
    contains_letter,
    dms_coordinate,
    generic_number_not_timestamp,
    get_verification_function,
    high_entropy_token,
    iban_mod97,
    korean_bank_account_valid,
    korean_zipcode_valid,
    luhn,
    not_timestamp,
    register_verification_function,
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
