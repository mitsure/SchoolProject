import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.extractor import RuleBasedExtractor
from app.prediction_snapshot import build_metadata, sign_snapshot, verify_snapshot
from app.research import EVALUATION_FIELDS, parse_assessment, summarize_records
from app.research_views import assessment_page, dashboard_page
from app.storage import ReviewStore
from app.validator import ResultValidator


def assessment(gold="歯牙障害", **overrides):
    form = {"reviewer": "r1", "dataset": "pilot", "split": "development", "sampling": "consecutive",
            "status": "active", "gold_0": gold, **overrides}
    return parse_assessment(form, ResultValidator())


def record(identifier, predicted, gold="歯牙障害"):
    return {"id": identifier, "created_at": "2026-09-07", "input_text": f"架空例{identifier}", "input_hash": str(identifier),
            "prediction": {name: predicted if name == "種別" else None for name in EVALUATION_FIELDS},
            "extracted": {"fields": {}}, "confirmed": {}, "metadata": {"version": "v1"},
            "assessment": assessment(gold), "assessment_id": identifier, "assessed_at": "2026-09-07"}


class ResearchMetricsTest(unittest.TestCase):
    def test_confusion_abstention_and_unknown_references(self):
        other = "聴力障害"
        rows = [record(1, "歯牙障害"), record(2, None), record(3, "歯牙障害", other), record(4, other, other),
                record(5, None, "__unknown"), record(6, "歯牙障害")]
        rows[-1]["assessment"] = None  # Ordinary confirmation must not become research ground truth.
        report = summarize_records(rows)
        self.assertEqual(report["screening"]["confusion_matrix"], {"tp": 1, "fn": 1, "fp": 1, "tn": 1, "total": 4})
        for metric in ("sensitivity", "specificity", "positive_predictive_value", "accuracy"):
            self.assertEqual(report["screening"][metric]["value"], 0.5)
        self.assertEqual(report["screening_abstained"], 1)
        self.assertEqual(report["fields"]["種別"]["indeterminate"], 1)
        self.assertEqual(report["pending"], 1)
        self.assertEqual(len(report["errors"]), 2)

    def test_zero_denominator_legacy_and_exclusion(self):
        legacy = record(1, "歯牙障害")
        legacy["prediction"] = legacy["metadata"] = None
        legacy["extracted"] = {"fields": {"性別": {"value": "男"}}}
        excluded = record(2, "歯牙障害")
        excluded["assessment"] = assessment(status="excluded", exclusion_reason="対象外")
        report = summarize_records([legacy, excluded])
        self.assertIsNone(report["screening"]["sensitivity"]["value"])
        self.assertEqual(report["fields"]["種別"]["missing"], 1)
        self.assertEqual(report["excluded"], 1)
        self.assertIsNone(summarize_records([])["complete_accuracy"]["value"])

    def test_repeated_text_uses_latest_assessment_and_preserves_versions(self):
        first, second = record(1, "歯牙障害"), record(2, "歯牙障害", "聴力障害")
        second["input_text"] = "  " + first["input_text"] + "  "
        report = summarize_records([first, second])
        self.assertEqual(report["duplicates"], 1)
        self.assertEqual(report["screening"]["confusion_matrix"]["fp"], 1)
        second["metadata"]["version"] = "v2"
        self.assertEqual(summarize_records([first, second])["evaluated"], 2)

    def test_no_value_is_separate_from_value_accuracy_and_complete_case(self):
        row = record(1, "歯牙障害")
        for name in EVALUATION_FIELDS[1:]:
            row["assessment"]["labels"][name] = {"status": "no_value", "value": None}
        report = summarize_records([row])
        self.assertEqual(report["complete_accuracy"]["value"], 1)
        self.assertIsNone(report["fields"]["性別"]["accuracy"]["value"])
        self.assertEqual(report["fields"]["性別"]["correct_empty"], 1)
        row["prediction"]["性別"] = "男"
        report = summarize_records([row])
        self.assertEqual(report["fields"]["性別"]["precision"]["value"], 0)
        self.assertEqual(report["complete_accuracy"]["value"], 0)

    def test_assessment_validation(self):
        for overrides in ({"reviewer": ""}, {"dataset": ""}, {"split": "invalid"}, {"sampling": "invalid"},
                          {"status": "excluded"}, {"gold_0": "__none"}, {"gold_0": "invalid"},
                          {"gold_0": ""}, {"error_0": "invalid"}, {"gold_1": "高", "gold_2": "6"}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                assessment(**overrides)
        self.assertEqual(assessment("__unknown")["labels"]["種別"]["status"], "indeterminate")

    def test_html_escapes_text_and_blind_form_does_not_prefill_predictions(self):
        row = record(1, "歯牙障害")
        row["input_text"] = "<script>alert(1)</script>"
        row["assessment"] = None
        row["assessment_id"] = None
        form = assessment_page(row, ResultValidator(), [])
        self.assertNotIn("<script>", form)
        self.assertNotIn("value='歯牙障害' selected", form)
        page = dashboard_page([row], [row], summarize_records([row]), dict(version="v1", dataset="", split="", sampling=""))
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("算出不可", page)


class ResearchStorageTest(unittest.TestCase):
    def test_migration_history_immutable_prediction_and_cascade(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reviews.sqlite3"
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE reviews (id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, input_text TEXT, input_hash TEXT, extracted_json TEXT, confirmed_json TEXT)")
                db.execute("INSERT INTO reviews(input_text,input_hash,extracted_json,confirmed_json) VALUES('legacy','hash','{}','{}')")
            store = ReviewStore(path)
            ReviewStore(path)  # Migration is idempotent.
            self.assertIsNone(store.research_records(1)[0]["prediction"])
            identifier = store.save("原文", {"input_hash": "h"}, {"種別": "聴力障害"},
                                    prediction={"種別": "歯牙障害"}, metadata={"version": "v1"})
            first = store.save_assessment(identifier, assessment(), expected_id=None)
            with self.assertRaises(ValueError):
                store.save_assessment(identifier, assessment(), expected_id=None)
            store.save_assessment(identifier, assessment("聴力障害", reviewer="r2"), expected_id=first)
            store.update_confirmed(identifier, {"災害発生時の状況": "編集された原文"})
            row = store.research_records(identifier)[0]
            self.assertEqual(row["input_text"], "原文")
            self.assertEqual(row["prediction"]["種別"], "歯牙障害")
            self.assertEqual(row["assessment"]["reviewer"], "r2")
            self.assertEqual(len(store.assessment_history(identifier)), 2)
            store.delete(identifier)
            self.assertEqual(store.assessment_history(identifier), [])
            with self.assertRaises(KeyError):
                store.save_assessment(identifier, assessment(), expected_id=None)

    def test_snapshot_tamper_and_version_stability(self):
        first = build_metadata(RuleBasedExtractor(), 10)
        second = build_metadata(RuleBasedExtractor(), 20)
        self.assertEqual(first["version"], second["version"])
        snapshot = {"text": "原文", "prediction": {"種別": None}, "metadata": first}
        payload, signature = sign_snapshot(snapshot, b"secret")
        self.assertEqual(verify_snapshot(payload, signature, b"secret"), snapshot)
        for altered, key in ((payload.replace("原文", "改変"), b"secret"), (payload, b"wrong")):
            with self.assertRaises(ValueError):
                verify_snapshot(altered, signature, key)


if __name__ == "__main__":
    unittest.main()
