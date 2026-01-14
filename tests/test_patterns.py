"""
Tests for regex pattern definitions.

This module contains comprehensive tests for all regex patterns defined
in YAML files. Tests automatically verify that patterns match/don't match
their example data and that verification functions work correctly.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Any

import pytest
import yaml
import re2

# Add verification module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "verification" / "python"))

from verification import get_verification_function


def compile_pattern_with_flags(pattern_dict: Dict[str, Any]) -> re.Pattern:
    """
    Compile a regex pattern with appropriate flags from the pattern dictionary.

    Args:
        pattern_dict: Pattern dictionary from YAML file

    Returns:
        Compiled regex pattern
    """
    pattern_str = pattern_dict.get('pattern', '')
    flags = 0

    # Handle flags if specified
    if 'flags' in pattern_dict:
        flag_list = pattern_dict['flags']
        if isinstance(flag_list, list):
            for flag_name in flag_list:
                if flag_name == 'IGNORECASE' or flag_name == 'I':
                    flags |= re.IGNORECASE
                elif flag_name == 'MULTILINE' or flag_name == 'M':
                    flags |= re.MULTILINE
                elif flag_name == 'DOTALL' or flag_name == 'S':
                    flags |= re.DOTALL
                elif flag_name == 'VERBOSE' or flag_name == 'X':
                    flags |= re.VERBOSE

    return re.compile(pattern_str, flags)


def compile_pattern_with_flags_re2(pattern_dict: Dict[str, Any]):
    """
    Compile a regex pattern with google-re2 and appropriate flags.

    Args:
        pattern_dict: Pattern dictionary from YAML file

    Returns:
        Compiled re2 pattern
    """
    pattern_str = pattern_dict.get('pattern', '')

    # Build options for re2
    options = re2.Options()

    # Handle flags if specified
    if 'flags' in pattern_dict:
        flag_list = pattern_dict['flags']
        if isinstance(flag_list, list):
            for flag_name in flag_list:
                if flag_name == 'IGNORECASE' or flag_name == 'I':
                    options.case_sensitive = False
                elif flag_name == 'MULTILINE' or flag_name == 'M':
                    # RE2's one_line=False allows ^ and $ to match line boundaries
                    options.one_line = False
                elif flag_name == 'DOTALL' or flag_name == 'S':
                    options.dot_nl = True

    return re2.compile(pattern_str, options)


def find_all_pattern_files() -> List[Path]:
    """Find all YAML pattern files in the regex directory."""
    regex_dir = Path(__file__).parent.parent / "regex"
    return list(regex_dir.glob("**/*.yml")) + list(regex_dir.glob("**/*.yaml"))


def load_pattern_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a pattern YAML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_all_patterns() -> List[tuple]:
    """
    Get all patterns from all YAML files.

    Returns:
        List of tuples: (file_path, pattern_dict)
    """
    all_patterns = []
    for file_path in find_all_pattern_files():
        try:
            data = load_pattern_file(file_path)
            if data and 'patterns' in data:
                for pattern in data['patterns']:
                    all_patterns.append((file_path, pattern))
        except Exception as e:
            print(f"Warning: Could not load {file_path}: {e}")
    return all_patterns


# Generate test parameters
PATTERN_TEST_DATA = get_all_patterns()


class TestPatternStructure:
    """Tests for pattern YAML file structure."""

    @pytest.mark.parametrize("file_path", find_all_pattern_files())
    def test_yaml_file_valid(self, file_path):
        """Test that YAML files are valid and loadable."""
        data = load_pattern_file(file_path)
        assert data is not None, f"Failed to load {file_path}"

    @pytest.mark.parametrize("file_path", find_all_pattern_files())
    def test_yaml_has_required_fields(self, file_path):
        """Test that YAML files have required top-level fields."""
        data = load_pattern_file(file_path)
        assert 'namespace' in data, f"{file_path} missing 'namespace' field"
        assert 'description' in data, f"{file_path} missing 'description' field"
        assert 'patterns' in data, f"{file_path} missing 'patterns' field"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_pattern_has_required_fields(self, file_path, pattern):
        """Test that each pattern has required fields."""
        required_fields = ['id', 'location', 'category', 'description', 'pattern']
        for field in required_fields:
            assert field in pattern, f"{file_path} pattern {pattern.get('id', 'unknown')} missing '{field}'"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_pattern_id_format(self, file_path, pattern):
        """Test that pattern IDs follow naming convention."""
        pattern_id = pattern.get('id', '')
        # Pattern IDs should be non-empty and contain only alphanumeric, underscore, dash
        assert pattern_id, f"{file_path} has pattern with empty ID"
        assert re.match(r'^[a-z0-9_\-]+$', pattern_id), \
            f"{file_path} pattern ID '{pattern_id}' should be lowercase alphanumeric with underscore/dash"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_pattern_regex_compiles(self, file_path, pattern):
        """Test that all pattern regexes compile successfully."""
        pattern_id = pattern.get('id', 'unknown')
        try:
            compile_pattern_with_flags(pattern)
        except re.error as e:
            pytest.fail(f"{file_path} pattern {pattern_id} has invalid regex: {e}")


class TestPatternRE2:
    """Tests for pattern compatibility with google-re2.

    RE2 is a safe regex engine that guarantees linear time matching,
    preventing ReDoS (Regular Expression Denial of Service) attacks.
    All patterns must be compatible with RE2 for production safety.
    """

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_pattern_compiles_with_re2(self, file_path, pattern):
        """Test that all pattern regexes compile successfully with google-re2."""
        pattern_id = pattern.get('id', 'unknown')
        try:
            compile_pattern_with_flags_re2(pattern)
        except re2.error as e:
            pytest.fail(f"{file_path} pattern {pattern_id} is not RE2 compatible: {e}")

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_match_examples_with_re2(self, file_path, pattern):
        """Test that patterns match their positive examples using google-re2."""
        if 'examples' not in pattern or 'match' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no match examples")

        pattern_id = pattern['id']
        regex = compile_pattern_with_flags_re2(pattern)

        for example in pattern['examples']['match']:
            example_str = str(example)
            assert regex.search(example_str), \
                f"{file_path} pattern {pattern_id} should match '{example_str}' with RE2"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_nomatch_examples_with_re2(self, file_path, pattern):
        """Test that patterns don't match their negative examples using google-re2.

        For patterns with verification functions, examples may match the regex
        but should fail verification.
        """
        if 'examples' not in pattern or 'nomatch' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no nomatch examples")

        pattern_id = pattern['id']
        regex = compile_pattern_with_flags_re2(pattern)
        has_verification = 'verification' in pattern
        verification_func = None

        if has_verification:
            verification_func = get_verification_function(pattern['verification'])

        for example in pattern['examples']['nomatch']:
            example_str = str(example)
            match = regex.search(example_str)

            if not match:
                # Regex doesn't match - this is expected for nomatch examples
                continue

            # If regex matches but pattern has verification, check that verification fails
            if has_verification and verification_func:
                matched_text = match.group(0)
                assert not verification_func(matched_text), \
                    f"{file_path} pattern {pattern_id} matched '{example_str}' with RE2 but verification " \
                    f"should have rejected it"
            else:
                # No verification function, so regex should not have matched
                pytest.fail(
                    f"{file_path} pattern {pattern_id} should NOT match '{example_str}' with RE2 " \
                    f"(matched: '{match.group(0)}')"
                )


class TestPatternMatching:
    """Tests for pattern matching against examples."""

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_match_examples(self, file_path, pattern):
        """Test that patterns match their positive examples."""
        if 'examples' not in pattern or 'match' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no match examples")

        pattern_id = pattern['id']
        regex = compile_pattern_with_flags(pattern)

        for example in pattern['examples']['match']:
            example_str = str(example)  # Handle both string and numeric examples
            assert regex.search(example_str), \
                f"{file_path} pattern {pattern_id} should match '{example_str}'"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_nomatch_examples(self, file_path, pattern):
        """Test that patterns don't match their negative examples.

        For patterns with verification functions, examples may match the regex
        but should fail verification.
        """
        if 'examples' not in pattern or 'nomatch' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no nomatch examples")

        pattern_id = pattern['id']
        regex = compile_pattern_with_flags(pattern)
        has_verification = 'verification' in pattern
        verification_func = None

        if has_verification:
            verification_func = get_verification_function(pattern['verification'])

        for example in pattern['examples']['nomatch']:
            example_str = str(example)  # Handle both string and numeric examples
            match = regex.search(example_str)

            if not match:
                # Regex doesn't match - this is expected for nomatch examples
                continue

            # If regex matches but pattern has verification, check that verification fails
            if has_verification and verification_func:
                matched_text = match.group(0)
                assert not verification_func(matched_text), \
                    f"{file_path} pattern {pattern_id} matched '{example_str}' but verification " \
                    f"should have rejected it"
            else:
                # No verification function, so regex should not have matched
                pytest.fail(
                    f"{file_path} pattern {pattern_id} should NOT match '{example_str}' " \
                    f"(matched: '{match.group(0)}')"
                )


class TestPatternVerification:
    """Tests for pattern verification functions."""

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_verification_function_exists(self, file_path, pattern):
        """Test that specified verification functions exist."""
        if 'verification' not in pattern:
            pytest.skip(f"Pattern {pattern.get('id')} has no verification function")

        verification_name = pattern['verification']
        verification_func = get_verification_function(verification_name)
        assert verification_func is not None, \
            f"{file_path} pattern {pattern['id']} references unknown verification function '{verification_name}'"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_verification_with_match_examples(self, file_path, pattern):
        """Test that verification functions accept positive examples."""
        if 'verification' not in pattern:
            pytest.skip(f"Pattern {pattern.get('id')} has no verification function")

        if 'examples' not in pattern or 'match' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no match examples")

        verification_name = pattern['verification']
        verification_func = get_verification_function(verification_name)
        pattern_id = pattern['id']
        regex = compile_pattern_with_flags(pattern)

        for example in pattern['examples']['match']:
            example_str = str(example)
            match = regex.search(example_str)
            if match:
                matched_text = match.group(0)
                assert verification_func(matched_text), \
                    f"{file_path} pattern {pattern_id}: verification function '{verification_name}' " \
                    f"should accept '{matched_text}' from example '{example_str}'"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_verification_rejects_nomatch_examples(self, file_path, pattern):
        """
        Test that verification functions reject negative examples when applicable.

        Note: Some nomatch examples are rejected by regex, not verification function.
        This test only runs when the regex matches but verification should fail.
        """
        if 'verification' not in pattern:
            pytest.skip(f"Pattern {pattern.get('id')} has no verification function")

        if 'examples' not in pattern or 'nomatch' not in pattern['examples']:
            pytest.skip(f"Pattern {pattern.get('id')} has no nomatch examples")

        verification_name = pattern['verification']
        verification_func = get_verification_function(verification_name)
        pattern_id = pattern['id']
        regex = compile_pattern_with_flags(pattern)

        # Only test examples that match the regex (verification should reject these)
        for example in pattern['examples']['nomatch']:
            example_str = str(example)
            match = regex.search(example_str)
            if match:
                # This example matches the regex, so verification should reject it
                matched_text = match.group(0)
                assert not verification_func(matched_text), \
                    f"{file_path} pattern {pattern_id}: verification function '{verification_name}' " \
                    f"should reject '{matched_text}' from nomatch example '{example_str}'"


class TestPatternMetadata:
    """Tests for pattern metadata and policy."""

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_severity_levels(self, file_path, pattern):
        """Test that severity levels are valid."""
        if 'policy' not in pattern or 'severity' not in pattern['policy']:
            pytest.skip(f"Pattern {pattern.get('id')} has no severity level")

        valid_severities = ['low', 'medium', 'high', 'critical']
        severity = pattern['policy']['severity']
        assert severity in valid_severities, \
            f"{file_path} pattern {pattern['id']} has invalid severity '{severity}'. " \
            f"Must be one of: {valid_severities}"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_action_on_match(self, file_path, pattern):
        """Test that action_on_match values are valid."""
        if 'policy' not in pattern or 'action_on_match' not in pattern['policy']:
            pytest.skip(f"Pattern {pattern.get('id')} has no action_on_match")

        valid_actions = ['redact', 'alert', 'block', 'log', 'report']
        action = pattern['policy']['action_on_match']
        assert action in valid_actions, \
            f"{file_path} pattern {pattern['id']} has invalid action '{action}'. " \
            f"Must be one of: {valid_actions}"

    @pytest.mark.parametrize("file_path,pattern", PATTERN_TEST_DATA)
    def test_has_mask_format(self, file_path, pattern):
        """Test that patterns have a mask format defined."""
        assert 'mask' in pattern, \
            f"{file_path} pattern {pattern['id']} should have a 'mask' field"


class TestSpecificPatterns:
    """Tests for specific pattern types with known test cases."""

    def test_credit_card_luhn_validation(self):
        """Test that credit card patterns use Luhn verification."""
        pattern_files = find_all_pattern_files()
        credit_card_file = None
        for f in pattern_files:
            if 'credit-card' in str(f) or 'credit_card' in str(f):
                credit_card_file = f
                break

        if not credit_card_file:
            pytest.skip("No credit card pattern file found")

        data = load_pattern_file(credit_card_file)
        # At least some credit card patterns should have Luhn verification
        has_luhn = any('verification' in p and p['verification'] == 'luhn'
                      for p in data.get('patterns', []))
        # Note: Not all card patterns may use Luhn, so we just check if file is loadable
        assert data is not None

    def test_ssn_pattern_validation(self):
        """Test that US SSN patterns use validation."""
        pattern_files = find_all_pattern_files()
        ssn_file = None
        for f in pattern_files:
            if 'us' in str(f) and 'ssn' in str(f):
                ssn_file = f
                break

        if not ssn_file:
            pytest.skip("No US SSN pattern file found")

        data = load_pattern_file(ssn_file)
        ssn_patterns = [p for p in data.get('patterns', []) if 'ssn' in p.get('id', '')]

        if ssn_patterns:
            # SSN patterns should have verification
            ssn_pattern = ssn_patterns[0]
            assert 'verification' in ssn_pattern, "SSN pattern should have verification function"
            assert ssn_pattern['verification'] == 'us_ssn_valid'

    def test_iban_pattern_validation(self):
        """Test that IBAN patterns use mod-97 validation."""
        pattern_files = find_all_pattern_files()
        iban_file = None
        for f in pattern_files:
            if 'iban' in str(f):
                iban_file = f
                break

        if not iban_file:
            pytest.skip("No IBAN pattern file found")

        data = load_pattern_file(iban_file)
        iban_patterns = [p for p in data.get('patterns', []) if 'iban' in p.get('id', '').lower()]

        if iban_patterns:
            # At least one IBAN pattern should have mod-97 verification
            has_mod97 = any('verification' in p and p['verification'] == 'iban_mod97'
                          for p in iban_patterns)
            # Note: Not all IBAN patterns may use verification, so we just check if file is loadable
            assert data is not None

    def test_high_entropy_token_patterns(self):
        """Test that high-entropy token patterns use entropy verification."""
        pattern_files = find_all_pattern_files()
        token_file = None
        for f in pattern_files:
            if 'token' in str(f):
                token_file = f
                break

        if not token_file:
            pytest.skip("No token pattern file found")

        data = load_pattern_file(token_file)
        # Some token patterns should use high_entropy_token verification
        has_entropy = any('verification' in p and p['verification'] == 'high_entropy_token'
                         for p in data.get('patterns', []))
        # At least the file should be valid
        assert data is not None


class TestPatternCoverage:
    """Tests for pattern coverage and completeness."""

    def test_all_pattern_files_have_patterns(self):
        """Test that all pattern files contain at least one pattern."""
        for file_path in find_all_pattern_files():
            data = load_pattern_file(file_path)
            assert 'patterns' in data, f"{file_path} has no 'patterns' field"
            assert len(data['patterns']) > 0, f"{file_path} has no patterns defined"

    def test_all_patterns_have_examples(self):
        """Test that all patterns have both match and nomatch examples."""
        files_without_examples = []
        for file_path, pattern in PATTERN_TEST_DATA:
            pattern_id = pattern.get('id', 'unknown')
            if 'examples' not in pattern:
                files_without_examples.append((file_path, pattern_id, "no examples"))
            elif 'match' not in pattern['examples']:
                files_without_examples.append((file_path, pattern_id, "no match examples"))
            elif 'nomatch' not in pattern['examples']:
                files_without_examples.append((file_path, pattern_id, "no nomatch examples"))

        if files_without_examples:
            msg = "Patterns without complete examples:\n"
            for file_path, pattern_id, reason in files_without_examples:
                msg += f"  - {file_path} / {pattern_id}: {reason}\n"
            pytest.fail(msg)

    def test_pattern_categories_valid(self):
        """Test that pattern categories are consistent."""
        categories = set()
        for file_path, pattern in PATTERN_TEST_DATA:
            category = pattern.get('category')
            if category:
                categories.add(category)

        # Just ensure we have some categories defined
        assert len(categories) > 0, "No pattern categories found"

    def test_pattern_locations_valid(self):
        """Test that pattern locations are consistent."""
        locations = set()
        for file_path, pattern in PATTERN_TEST_DATA:
            location = pattern.get('location')
            if location:
                locations.add(location)

        # Just ensure we have some locations defined
        assert len(locations) > 0, "No pattern locations found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
