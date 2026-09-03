import unittest

from app.review_comment import COMMENT_MAX_LENGTH, normalize_comment


class ReviewCommentTest(unittest.TestCase):
    def test_blank_comment_is_allowed_and_saved_as_none(self):
        self.assertIsNone(normalize_comment("   "))
        self.assertIsNone(normalize_comment(None))

    def test_comment_is_trimmed(self):
        self.assertEqual(
            normalize_comment("  候補を再確認する  "),
            "候補を再確認する",
        )

    def test_comment_length_is_limited(self):
        with self.assertRaises(ValueError):
            normalize_comment("あ" * (COMMENT_MAX_LENGTH + 1))


if __name__ == "__main__":
    unittest.main()
