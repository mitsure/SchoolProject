import unittest

from evaluation.evaluate_injury_screening import (
    LABEL_COLUMN,
    TEXT_COLUMN,
    compare_bigrams,
    evaluate_rows,
    make_review_sample,
    screening_outcome,
)


class InjuryScreeningEvaluationTest(unittest.TestCase):
    def test_screening_outcomes(self):
        target = "歯牙障害"
        self.assertEqual(screening_outcome(target, target, target), "TP")
        self.assertEqual(screening_outcome("聴力障害", target, target), "FP")
        self.assertEqual(screening_outcome(target, None, target), "FN")
        self.assertEqual(screening_outcome("聴力障害", None, target), "TN")

    def test_evaluation_returns_binary_and_multiclass_metrics(self):
        rows = [
            {LABEL_COLUMN: "歯牙障害", TEXT_COLUMN: "転倒して前歯を折った。", "和暦": "令和", "給付年度": "5"},
            {LABEL_COLUMN: "歯牙障害", TEXT_COLUMN: "転倒して口元を負傷した。", "和暦": "令和", "給付年度": "5"},
            {LABEL_COLUMN: "聴力障害", TEXT_COLUMN: "大きな音で難聴になった。", "和暦": "令和", "給付年度": "5"},
            {LABEL_COLUMN: "聴力障害", TEXT_COLUMN: "前歯を折った。", "和暦": "令和", "給付年度": "5"},
        ]
        report, details = evaluate_rows(rows)
        self.assertEqual(report["current"]["confusion_matrix"], {"tp": 1, "fp": 1, "fn": 1, "tn": 1, "total": 4})
        self.assertEqual(report["current"]["sensitivity"]["value"], 0.5)
        self.assertEqual(report["multiclass"]["coverage"]["value"], 0.75)
        self.assertEqual([row["screening_outcome"] for row in details], ["TP", "FN", "TN", "FP"])

    def test_review_sample_keeps_predictions_out_of_blinded_file(self):
        rows = [
            {
                "evaluation_id": "E000001",
                "silver_label": "歯牙障害",
                "predicted_type": "歯牙障害",
                "screening_outcome": "TP",
                "text": "前歯を折った。",
            }
        ]
        blind, key = make_review_sample(rows, per_stratum=1, seed=1)
        self.assertNotIn("system_prediction", blind[0])
        self.assertEqual(key[0]["system_prediction"], "歯牙障害")

    def test_bigram_comparison_uses_case_level_rates(self):
        tokenize = lambda text: text.split()
        rows = compare_bigrams(
            [{"text": "歯 負傷"}, {"text": "歯 負傷"}],
            [{"text": "顔 負傷"}, {"text": "歯 負傷"}],
            "FN_vs_TP",
            tokenize,
            minimum_error_documents=1,
        )
        dental = next(row for row in rows if row["2-gram"] == "歯 負傷")
        self.assertEqual(dental["error_group_document_rate"], 1.0)
        self.assertEqual(dental["reference_group_document_rate"], 0.5)
        self.assertEqual(dental["rate_difference"], 0.5)


if __name__ == "__main__":
    unittest.main()
