import unittest

from evaluation.metrics import (
    binary_screening_summary,
    empty_counts,
    summarize,
    update_counts,
    wilson_interval,
)


class MetricsTest(unittest.TestCase):
    def test_rates_separate_coverage_from_accuracy(self):
        counts = empty_counts()
        update_counts(counts, "A", "A")
        update_counts(counts, "B", "C")
        update_counts(counts, None, "A")
        update_counts(counts, None, None)
        result = summarize(counts)
        self.assertEqual(result["precision_vs_silver"], 0.5)
        self.assertEqual(result["recall_vs_silver"], round(1 / 3, 6))
        self.assertEqual(result["coverage"], 0.5)
        self.assertEqual(result["abstention_rate"], 0.5)

    def test_zero_denominator_is_not_reported_as_zero(self):
        result = summarize(empty_counts())
        self.assertIsNone(result["precision_vs_silver"])

    def test_binary_screening_metrics_and_confidence_intervals(self):
        result = binary_screening_summary(tp=80, fp=10, fn=20, tn=90)
        self.assertEqual(result["sensitivity"]["value"], 0.8)
        self.assertEqual(result["specificity"]["value"], 0.9)
        self.assertEqual(result["positive_predictive_value"]["value"], 0.888889)
        self.assertEqual(result["accuracy"]["value"], 0.85)
        lower, upper = result["sensitivity"]["ci95_wilson"]
        self.assertLess(lower, 0.8)
        self.assertGreater(upper, 0.8)

    def test_wilson_interval_handles_empty_and_invalid_counts(self):
        self.assertIsNone(wilson_interval(0, 0))
        with self.assertRaises(ValueError):
            wilson_interval(2, 1)


if __name__ == "__main__":
    unittest.main()
