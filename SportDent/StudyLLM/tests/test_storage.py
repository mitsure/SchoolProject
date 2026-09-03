import tempfile
import unittest
from pathlib import Path

from app.storage import ReviewStore


class ReviewStoreTest(unittest.TestCase):
    def test_saved_confirmation_can_be_listed_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.sqlite3")
            result = {"input_hash": "hash"}
            first_id = store.save("一件目", result, {"被災学校種": "小"})
            second_id = store.save("二件目", result, {"被災学校種": "中"})

            reviews = store.list_confirmed()

            self.assertEqual([row["id"] for row in reviews], [second_id, first_id])
            self.assertEqual(reviews[0]["confirmed"]["被災学校種"], "中")

    def test_confirmation_can_be_updated_and_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.sqlite3")
            review_id = store.save("原文", {"input_hash": "hash"}, {"性別": "男"})

            self.assertTrue(store.update_confirmed(review_id, {"性別": "女"}))
            self.assertEqual(store.get_confirmed(review_id)["confirmed"]["性別"], "女")
            self.assertFalse(store.update_confirmed(review_id + 1, {"性別": "男"}))

            self.assertTrue(store.delete(review_id))
            self.assertIsNone(store.get_confirmed(review_id))
            self.assertFalse(store.delete(review_id))

    def test_optional_comment_is_saved_and_updated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReviewStore(Path(directory) / "reviews.sqlite3")
            review_id = store.save("原文", {"input_hash": "hash"}, {"コメント": None})

            self.assertIsNone(store.get_confirmed(review_id)["confirmed"]["コメント"])
            self.assertTrue(store.update_confirmed(review_id, {"コメント": "要再確認"}))
            self.assertEqual(store.get_confirmed(review_id)["confirmed"]["コメント"], "要再確認")


if __name__ == "__main__":
    unittest.main()
