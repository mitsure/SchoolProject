import csv
import unittest
from pathlib import Path

from app.models import FIELD_NAMES
from app.validator import ResultValidator


DB_PATH = Path(__file__).resolve().parents[2] / "DB" / "shougai(2025.01.31).csv"


class CategoryCatalogTest(unittest.TestCase):
    def test_catalog_contains_every_observed_db_value(self):
        observed = {name: set() for name in FIELD_NAMES}
        with DB_PATH.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                for name in FIELD_NAMES:
                    value = row[name].strip()
                    if value:
                        observed[name].add(value)
        allowed = ResultValidator().allowed
        self.assertEqual(allowed, observed)

    def test_no_target_field_has_one_hundred_categories(self):
        allowed = ResultValidator().allowed
        self.assertLess(max(map(len, allowed.values())), 100)


if __name__ == "__main__":
    unittest.main()
