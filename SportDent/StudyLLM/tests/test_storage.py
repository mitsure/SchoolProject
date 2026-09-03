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


if __name__ == "__main__":
    unittest.main()
