import csv
import unittest
from pathlib import Path

from app.extractor import RuleBasedExtractor
from app.validator import ResultValidator


CASES = Path(__file__).resolve().parent.parent / "10_安全性試験ケース.csv"


class SafetyCasesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extractor = RuleBasedExtractor()
        cls.validator = ResultValidator()
        with CASES.open(encoding="utf-8-sig", newline="") as source:
            cls.cases = {row["test_id"]: row["架空入力文"] for row in csv.DictReader(source)}

    def result(self, test_id):
        text = self.cases[test_id]
        result = self.extractor.extract(text)
        self.validator.validate(text.strip(), result)
        return result

    def value(self, result, field):
        return result["fields"][field]["value"]

    def test_all_csv_cases_are_covered(self):
        self.assertEqual(set(self.cases), {f"T{i:03d}" for i in range(1, 15)})

    def test_t001_commute_does_not_imply_road(self):
        r = self.result("T001"); self.assertEqual(self.value(r, "通学方法"), "自転車"); self.assertIsNone(self.value(r, "発生場所2"))

    def test_t002_unmentioned_commute_method_is_null(self):
        self.assertIsNone(self.value(self.result("T002"), "通学方法"))

    def test_t003_spectated_sport_is_null(self):
        r = self.result("T003"); self.assertIsNone(self.value(r, "競技種目")); self.assertEqual(self.value(r, "発生場所2"), "階段")

    def test_t004_destination_is_not_place(self):
        self.assertEqual(self.value(self.result("T004"), "発生場所2"), "廊下")

    def test_t005_destination_toilet_is_not_place(self):
        self.assertEqual(self.value(self.result("T005"), "発生場所2"), "廊下")

    def test_t006_off_campus_gym_and_sport(self):
        r = self.result("T006"); self.assertEqual(self.value(r, "発生場所1"), "学校外（園外）"); self.assertEqual(self.value(r, "発生場所2"), "学校外体育館"); self.assertEqual(self.value(r, "競技種目"), "バスケットボール")

    def test_t007_multiple_incidents_stop(self):
        self.assertEqual(self.result("T007")["error_code"], "MULTIPLE_INCIDENTS")

    def test_t008_negated_bicycle_selects_walking(self):
        self.assertEqual(self.value(self.result("T008"), "通学方法"), "徒歩")

    def test_t009_injection_is_not_obeyed(self):
        self.assertEqual(self.result("T009")["error_code"], "PROMPT_INJECTION_SUSPECTED")

    def test_t010_near_equipment_is_not_use(self):
        self.assertIsNone(self.value(self.result("T010"), "遊具等"))

    def test_t011_equipment_use_not_sport(self):
        r = self.result("T011"); self.assertEqual(self.value(r, "遊具等"), "鉄棒"); self.assertIsNone(self.value(r, "競技種目"))

    def test_t012_unspecified_club_is_ambiguous(self):
        r = self.result("T012"); self.assertEqual(r["fields"]["場合別2"]["status"], "ambiguous"); self.assertEqual(r["fields"]["競技種目"]["status"], "ambiguous")

    def test_t013_road_does_not_imply_commute(self):
        r = self.result("T013"); self.assertEqual(self.value(r, "発生場所2"), "道路"); self.assertIsNone(self.value(r, "場合別1"))

    def test_t014_empty_input_stops(self):
        self.assertEqual(self.result("T014")["error_code"], "EMPTY_INPUT")


if __name__ == "__main__":
    unittest.main()
