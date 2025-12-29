#!/bin/bash
# Test runner script for Pattern Engine

set -e

echo "==================================="
echo "Pattern Engine Test Runner"
echo "==================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing dependencies..."
    pip install -r tests/requirements.txt
fi

echo "Running verification function tests..."
pytest tests/test_verification.py -v

echo ""
echo "Running pattern definition tests..."
pytest tests/test_patterns.py -v

echo ""
echo "==================================="
echo "All tests completed!"
echo "==================================="
