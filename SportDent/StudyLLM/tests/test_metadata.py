import unittest

from app.metadata import (
    GRADE_RULES,
    INJURY_TYPE_VALUES,
    infer_demographics,
    infer_injury_type,
    load_metadata_choices,
    validate_demographics,
    validate_injury_type,
)


class DemographicsTest(unittest.TestCase):
    def test_injury_type_choices_match_existing_database(self):
        self.assertEqual(set(INJURY_TYPE_VALUES), set(load_metadata_choices()["種別"]))

    def test_infer_dental_injury_type_from_front_tooth_description(self):
        result = infer_injury_type("中学2年生が電柱と激突し前歯をおった。")
        self.assertEqual(result["種別"], "歯牙障害")
        self.assertEqual(result["evidence"], "前歯")

    def test_unknown_injury_type_remains_empty_and_invalid_value_is_rejected(self):
        self.assertIsNone(infer_injury_type("登校中に転倒した。")["種別"])
        validate_injury_type("歯牙障害")
        with self.assertRaises(ValueError):
            validate_injury_type("候補にない障害")

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

    def test_full_school_name_and_subject_sex_are_candidates(self):
        result = infer_demographics("中学校2年生の男子生徒が、自転車で登校中に転倒した。")
        self.assertEqual(result["被災学校種"], "中")
        self.assertEqual(result["被災学年"], "2")
        self.assertEqual(result["性別"], "男")

    def test_middle_school_grade_variants_are_equivalent(self):
        variants = ("中2の生徒が転倒した。", "中２の生徒が転倒した。", "中二の生徒が転倒した。", "中学2年生が転倒した。", "中学校2年生が転倒した。")
        normalized = [(infer_demographics(text)["被災学校種"], infer_demographics(text)["被災学年"]) for text in variants]
        self.assertEqual(normalized, [("中", "2")] * len(variants))

    def test_unrelated_word_ending_in_middle_is_not_grade(self):
        result = infer_demographics("授業中2人の生徒が衝突した。")
        self.assertIsNone(result["被災学校種"])

    def test_victims_grade_wins_over_observed_younger_brothers_grade(self):
        text = "中2の男子生徒が、自転車で登校中、ブランコで遊んでいる小学校一年生の弟を見ていて衝突した。"
        result = infer_demographics(text)
        self.assertEqual(result["被災学校種"], "中")
        self.assertEqual(result["被災学年"], "2")
        self.assertEqual(result["性別"], "男")

    def test_observed_persons_earlier_grade_is_skipped(self):
        text = "小学校一年生の弟を見ていたところ、中2の男子生徒が転倒した。"
        result = infer_demographics(text)
        self.assertEqual((result["被災学校種"], result["被災学年"]), ("中", "2"))


if __name__ == "__main__":
    unittest.main()
