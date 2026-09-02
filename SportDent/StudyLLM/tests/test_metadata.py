import unittest

from app.metadata import GRADE_RULES, infer_demographics, validate_demographics


class DemographicsTest(unittest.TestCase):
    def test_school_controls_allowed_grades(self):
        self.assertEqual(GRADE_RULES["小"], ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(GRADE_RULES["中"], ["1", "2", "3"])
        self.assertEqual(GRADE_RULES["高"], ["1", "2", "3"])

    def test_grade_without_school_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_demographics(None, "2", None)

    def test_invalid_school_grade_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_demographics("中", "6", None)
        with self.assertRaises(ValueError):
            validate_demographics("高", "4", None)

    def test_explicit_school_and_grade_are_candidates(self):
        result = infer_demographics("小学三年生が休み時間に転倒した。")
        self.assertEqual(result["被災学校種"], "小")
        self.assertEqual(result["被災学年"], "3")


if __name__ == "__main__":
    unittest.main()
