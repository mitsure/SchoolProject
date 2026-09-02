import unittest

from app.extractor import RuleBasedExtractor
from app.validator import ResultValidator


class ExtractorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor = RuleBasedExtractor()
        cls.validator = ResultValidator()

    def extract(self, text):
        result = self.extractor.extract(text)
        self.validator.validate(text.strip(), result)
        return result

    def test_commute_without_location_guess(self):
        result = self.extract("自転車で登校中、バランスを崩して転倒した。")
        self.assertEqual(result["fields"]["場合別1"]["value"], "通学中")
        self.assertEqual(result["fields"]["通学方法"]["value"], "自転車")
        self.assertIsNone(result["fields"]["発生場所2"]["value"])

    def test_no_commute_method_guess(self):
        result = self.extract("登校中に転倒して前歯を打った。")
        self.assertIsNone(result["fields"]["通学方法"]["value"])

    def test_destination_is_not_accident_place(self):
        result = self.extract("体育館へ移動中、廊下で転倒した。")
        self.assertEqual(result["fields"]["発生場所2"]["value"], "廊下")

    def test_spectated_sport_is_rejected(self):
        result = self.extract("野球部の友人を見に行く途中、階段で転倒した。")
        self.assertIsNone(result["fields"]["競技種目"]["value"])

    def test_empty_and_multiple_incidents_stop(self):
        self.assertEqual(self.extractor.extract("")["error_code"], "EMPTY_INPUT")
        result = self.extract("昨日は校庭で転倒した。今日は教室で机にぶつかった。")
        self.assertEqual(result["error_code"], "MULTIPLE_INCIDENTS")

    def test_confirmed_value_must_be_allowed(self):
        result = self.extract("登校中に転倒して前歯を打った。")
        confirmed = {name: field["value"] for name, field in result["fields"].items()}
        self.validator.validate_confirmed(confirmed)
        confirmed["通学方法"] = "空飛ぶ車"
        with self.assertRaises(ValueError):
            self.validator.validate_confirmed(confirmed)

    def test_playground_equipment_is_in_result(self):
        result = self.extract("休み時間にブランコで遊んでいて落下した。")
        self.assertEqual(result["fields"]["遊具等"]["value"], "ぶらんこ")
        self.assertEqual(result["fields"]["遊具等"]["evidence_text"], "ブランコ")

    def test_unmentioned_sport_and_equipment_remain_null(self):
        result = self.extract("登校中に転倒した。")
        self.assertIsNone(result["fields"]["競技種目"]["value"])
        self.assertIsNone(result["fields"]["遊具等"]["value"])

    def test_other_location_detail_is_required_and_normalized(self):
        self.assertEqual(self.validator.validate_other_location("その他", "  校門横の通路  "), "校門横の通路")
        with self.assertRaises(ValueError):
            self.validator.validate_other_location("その他", "  ")
        self.assertIsNone(self.validator.validate_other_location("道路", "保存しない文字列"))


if __name__ == "__main__":
    unittest.main()
