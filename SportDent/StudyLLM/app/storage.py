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

    def _connect(self):
        return sqlite3.connect(self.path)

    def save(self, text: str, result: dict, confirmed: dict) -> int:
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO reviews(input_text,input_hash,extracted_json,confirmed_json) VALUES(?,?,?,?)",
                (text, result["input_hash"], json.dumps(result, ensure_ascii=False), json.dumps(confirmed, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

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
