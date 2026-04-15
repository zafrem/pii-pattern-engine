import sys
import os
import importlib.util
spec = importlib.util.spec_from_file_location("v_core", os.path.abspath(os.path.join(os.path.dirname(__file__), '../verification/python/verification.py')))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

def test_chinese_names():
    print("Testing Chinese Names...")
    assert v.chinese_name_valid("王小明") == True
    assert v.chinese_name_valid("张伟") == True
    assert v.chinese_name_valid("張偉") == True
    assert v.chinese_name_valid("陳志強") == True
    print("Chinese names passed!")

def test_japanese_names():
    print("Testing Japanese Names...")
    names = [
        ("佐藤太郎", True),
        ("田中", True),
        ("さとうたろう", True),
        ("たなか", True),
        ("サトウタロウ", True),
        ("タナカ", True),
        ("渡边太郎", True)
    ]
    for name, expected in names:
        result = v.japanese_name_kanji_valid(name)
        assert result == expected
    print("Japanese names passed!")

def test_english_names():
    print("Testing English Names...")
    names = [
        ("James Smith", True),
        ("Mary Johnson", True),
        ("John Doe", True),
        ("Robert Williams", True),
        ("michael brown", False), # lowercase
        ("A", False), # too short
        ("John", False), # no last name
    ]
    for name, expected in names:
        result = v.english_name_valid(name)
        print(f"Name: {name}, Expected: {expected}, Got: {result}")
        assert result == expected
    print("English names passed!")

if __name__ == "__main__":
    try:
        test_chinese_names()
        test_japanese_names()
        test_english_names()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
