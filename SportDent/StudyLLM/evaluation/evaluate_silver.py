from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from app.extractor import RuleBasedExtractor
from app.models import FIELD_NAMES
from evaluation.metrics import empty_counts, summarize, update_counts


DEFAULT_DB = Path(__file__).resolve().parents[2] / "DB" / "shougai(2025.01.31).csv"


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return None if not value or value.lower() in {"null", "nan"} else value


def evaluate(db_path: Path, limit: int | None = None) -> dict:
    extractor = RuleBasedExtractor()
    counts = {field: empty_counts() for field in FIELD_NAMES}
    processing = {"success": 0, "error": 0}
    error_codes: dict[str, int] = {}
    rows = 0
    with db_path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if limit is not None and rows >= limit:
                break
            rows += 1
            result = extractor.extract(row["災害発生時の状況"])
            status = result["processing_status"]
            processing[status] += 1
            if status == "error":
                code = result["error_code"]
                error_codes[code] = error_codes.get(code, 0) + 1
                for field in FIELD_NAMES:
                    update_counts(counts[field], None, clean(row.get(field)))
                continue
            for field in FIELD_NAMES:
                update_counts(counts[field], result["fields"][field]["value"], clean(row.get(field)))
    return {
        "report_type": "development_diagnostic_against_silver_labels",
        "warning": "既存DB値はsilver labelであり、原文から判定可能なgold standardではない。最終性能として使用しない。",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_file": db_path.name,
        "rows": rows,
        "processing": processing,
        "error_codes": error_codes,
        "fields": {field: summarize(value) for field, value in counts.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="ローカル規則抽出器を既存DBのsilver labelと比較する")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.db, args.limit)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
