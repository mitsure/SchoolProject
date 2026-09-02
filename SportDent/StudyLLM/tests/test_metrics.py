import unittest

from evaluation.metrics import empty_counts, summarize, update_counts


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


if __name__ == "__main__":
    unittest.main()
