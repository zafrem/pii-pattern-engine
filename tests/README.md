# Pattern Engine Tests

This directory contains comprehensive tests for the Pattern Engine project.

## Test Files

### `test_verification.py`
Tests for all verification functions in `verification/python/verification.py`:
- IBAN mod-97 validation
- Luhn algorithm (credit cards)
- DMS coordinate validation
- High entropy token detection
- Timestamp detection
- Zipcode validation (US, Korea)
- Bank account validation
- SSN validation
- Verification function registry

### `test_patterns.py`
Tests for all regex patterns defined in YAML files:
- Pattern structure validation
- Regex compilation tests
- Match/nomatch example verification
- Verification function integration tests
- Metadata and policy validation
- Pattern coverage tests

## Running Tests

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_verification.py
pytest tests/test_patterns.py
```

### Run Specific Test Class
```bash
pytest tests/test_verification.py::TestLuhn
pytest tests/test_patterns.py::TestPatternMatching
```

### Run Specific Test
```bash
pytest tests/test_verification.py::TestLuhn::test_valid_credit_cards
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage
```bash
pip install pytest-cov
pytest --cov=verification --cov-report=html
```

## Test Structure

### Verification Tests
- Each verification function has its own test class
- Tests cover valid inputs, invalid inputs, edge cases
- Tests verify function registry operations

### Pattern Tests
- Automatically discovers all YAML pattern files
- Parametrized tests run for every pattern
- Validates YAML structure and required fields
- Tests regex compilation and matching
- Verifies integration with verification functions
- Checks metadata consistency

## Writing New Tests

### Adding Verification Function Tests
1. Create a new test class in `test_verification.py`
2. Follow the naming convention: `TestFunctionName`
3. Add test methods covering valid/invalid cases
4. Include edge cases and error conditions

Example:
```python
class TestMyNewFunction:
    def test_valid_input(self):
        assert my_new_function("valid")

    def test_invalid_input(self):
        assert not my_new_function("invalid")
```

### Adding Pattern Files
No code changes needed! Tests automatically discover and validate new YAML pattern files.

Just ensure your pattern file has:
- Required fields: id, location, category, description, pattern
- Examples section with match and nomatch arrays
- Valid regex pattern
- Proper verification function reference (if applicable)

## Continuous Integration

These tests are designed to be run in CI/CD pipelines. They will:
- Validate all pattern definitions
- Ensure verification functions work correctly
- Catch regex errors and invalid configurations
- Verify pattern examples match expected behavior

## Test Coverage

Current test coverage includes:
- 11 verification functions with comprehensive tests
- All regex patterns in YAML files
- Pattern structure and metadata validation
- Integration between patterns and verification functions
