import os
import sys
from pathlib import Path

# Enable vector verification for this test
os.environ["ENABLE_KOREAN_VECTOR_VERIFICATION"] = "true"

# Add verification module to path
sys.path.insert(0, str(Path(__file__).parent.parent / "verification" / "python"))

from verification import korean_name_valid, get_vector_similarity_score

def test_vector_verification():
    print("Testing Vector Similarity-Based Filtering (ENABLED)")
    print("-" * 50)
    
    # These are in our mock datas/ko_w2v.vec
    test_cases = [
        ("전화", False), 
        ("번호", False), 
        ("김철수", True), 
    ]
    
    all_passed = True
    for val, expected in test_cases:
        score = get_vector_similarity_score(val)
        actual = korean_name_valid(val)
        passed = actual == expected
        print(f"{val:<8} | Sim Score: {score:.4f} | Expected: {str(expected):<5} | Actual: {str(actual):<5} | {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\nVector test passed!")
    else:
        print("\nVector test failed!")
        sys.exit(1)

if __name__ == "__main__":
    test_vector_verification()
