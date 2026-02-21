
import sys
from pathlib import Path

# Add verification module to path
sys.path.insert(0, str(Path(__file__).parent / "verification" / "python"))

from verification import korean_name_valid

def test_korean_name_valid():
    test_cases = [
        ("김철수", True),      # Normal name (dictionary match)
        ("이영희", True),      # Normal name (dictionary match)
        ("박민수", True),      # Normal name (dictionary match)
        ("전화번호", False),    # Blacklist match
        ("전화번호는", False),  # Blacklist + particle match
        ("이메일", False),      # Blacklist match
        ("이메일은", False),    # Blacklist + particle match
        ("이름은", False),      # Blacklist match
        ("성명은", False),      # Blacklist match
        ("박성은", True),      # Valid name ("성은" is in dictionary)
        ("김은", True),        # Valid name
        ("이은", True),        # Valid name
        ("전지현", True),      # Valid name ("지현" is in dictionary)
        ("정해인", True),      # Valid name ("해인" is in dictionary)
        ("연락처", False),      # Blacklist match
        ("주소는", False),      # Blacklist match
        ("성별은", False),      # Blacklist match
        ("독고탁", True),      # Compound surname (독고) + name
        ("남궁민", True),      # Compound surname (남궁) + name
        ("이순신", True),      # Historical name
    ]

    print(f"{'Value':<12} | {'Expected':<10} | {'Actual':<10} | {'Result'}")
    print("-" * 50)
    
    all_passed = True
    for val, expected in test_cases:
        actual = korean_name_valid(val)
        passed = actual == expected
        print(f"{val:<12} | {str(expected):<10} | {str(actual):<10} | {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_korean_name_valid()
