from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class ReviewStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                input_text TEXT NOT NULL, input_hash TEXT NOT NULL,
                extracted_json TEXT NOT NULL, confirmed_json TEXT NOT NULL
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(reviews)")}
            for name in ("prediction_json", "prediction_metadata_json"):
                if name not in columns:
                    db.execute(f"ALTER TABLE reviews ADD COLUMN {name} TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS research_assessments (
                id INTEGER PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                assessment_json TEXT NOT NULL
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS assessments_review ON research_assessments(review_id, id)")

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def save(self, text: str, result: dict, confirmed: dict, *, prediction: dict | None = None,
             metadata: dict | None = None) -> int:
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO reviews(input_text,input_hash,extracted_json,confirmed_json,prediction_json,prediction_metadata_json) VALUES(?,?,?,?,?,?)",
                (text, result["input_hash"], json.dumps(result, ensure_ascii=False), json.dumps(confirmed, ensure_ascii=False),
                 json.dumps(prediction, ensure_ascii=False) if prediction is not None else None,
                 json.dumps(metadata, ensure_ascii=False) if metadata is not None else None),
            )
            return int(cur.lastrowid)

    def research_records(self, review_id: int | None = None) -> list[dict]:
        query = """SELECT r.id, r.created_at, r.input_text, r.input_hash, r.extracted_json,
                   r.confirmed_json, r.prediction_json, r.prediction_metadata_json,
                   a.id, a.created_at, a.assessment_json
                   FROM reviews r LEFT JOIN research_assessments a ON a.id =
                   (SELECT MAX(id) FROM research_assessments WHERE review_id = r.id)"""
        params = ()
        if review_id is not None:
            query += " WHERE r.id = ?"
            params = (review_id,)
        with self._connect() as db:
            rows = db.execute(query + " ORDER BY r.id DESC", params).fetchall()
        records = []
        for row in rows:
            records.append(dict(zip(
                ("id", "created_at", "input_text", "input_hash", "extracted", "confirmed",
                 "prediction", "metadata", "assessment_id", "assessed_at", "assessment"),
                [json.loads(value) if value is not None and index in (4, 5, 6, 7, 10) else value
                 for index, value in enumerate(row)],
            )))
        return records

    def save_assessment(self, review_id: int, assessment: dict, *, expected_id: int | None) -> int:
        """Keep every revision; reject stale forms so concurrent reviewers cannot silently overwrite."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT id FROM reviews WHERE id = ?", (review_id,)).fetchone() is None:
                raise KeyError(review_id)
            latest = db.execute("SELECT MAX(id) FROM research_assessments WHERE review_id = ?", (review_id,)).fetchone()[0]
            if latest != expected_id:
                raise ValueError("別の評価が保存されています。画面を再読み込みしてください。")
            cursor = db.execute(
                "INSERT INTO research_assessments(review_id, assessment_json) VALUES(?,?)",
                (review_id, json.dumps(assessment, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def assessment_history(self, review_id: int) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, created_at, assessment_json FROM research_assessments WHERE review_id = ? ORDER BY id DESC",
                (review_id,),
            ).fetchall()
        return [{"id": row[0], "created_at": row[1], "assessment": json.loads(row[2])} for row in rows]

    def list_confirmed(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, created_at, confirmed_json FROM reviews ORDER BY id DESC"
            ).fetchall()
        return [
            {"id": int(review_id), "created_at": created_at, "confirmed": json.loads(confirmed_json)}
            for review_id, created_at, confirmed_json in rows
        ]

    def get_confirmed(self, review_id: int) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT id, created_at, confirmed_json FROM reviews WHERE id = ?",
                (review_id,),
            ).fetchone()
        if row is None:
            return None
        record_id, created_at, confirmed_json = row
        return {"id": int(record_id), "created_at": created_at, "confirmed": json.loads(confirmed_json)}

    def update_confirmed(self, review_id: int, confirmed: dict) -> bool:
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE reviews SET confirmed_json = ? WHERE id = ?",
                (json.dumps(confirmed, ensure_ascii=False), review_id),
            )
            return cursor.rowcount == 1

    def delete(self, review_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            return cursor.rowcount == 1
