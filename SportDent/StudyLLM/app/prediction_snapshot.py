"""Freeze the predictions shown to the user, before any manual corrections."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .llm_extractor import PROMPT_VERSION
from .metadata import INJURY_TYPE_RULE_VERSION


def build_metadata(extractor, elapsed_ms: int) -> dict:
    base = Path(__file__).resolve().parent.parent
    sources = [base / "app" / name for name in (
        "extractor.py", "llm_extractor.py", "metadata.py", "validator.py", "ollama_client.py", "models.py",
    )] + [base / name for name in (
        "02_上下位カテゴリ対応表.csv", "04_観測選択肢辞書.csv", "05_同義語候補辞書.csv", "07_項目依存ルール.csv",
    )]
    fingerprint = hashlib.sha256()
    for source in sources:
        fingerprint.update(source.name.encode())
        fingerprint.update(source.read_bytes())
    client = getattr(extractor, "client", None)
    configuration = {
        "extractor": "ollama" if client else "rules",
        "model": client.model if client else None,
        "model_revision": os.environ.get("SPORTDENT_OLLAMA_MODEL_REVISION") if client else None,
        "prompt_version": PROMPT_VERSION if client else None,
        "temperature": 0 if client else None,
        "injury_rule_version": INJURY_TYPE_RULE_VERSION,
        "source_fingerprint": fingerprint.hexdigest(),
    }
    version = hashlib.sha256(json.dumps(configuration, sort_keys=True).encode()).hexdigest()[:16]
    return {**configuration, "version": version, "executed_at": datetime.now(UTC).isoformat(),
            "elapsed_ms": elapsed_ms, "processing_status": "success"}


def sign_snapshot(snapshot: dict, secret: bytes) -> tuple[str, str]:
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    return payload, hmac.new(secret, b"prediction:" + payload.encode(), hashlib.sha256).hexdigest()


def verify_snapshot(payload: str, signature: str, secret: bytes) -> dict:
    expected = hmac.new(secret, b"prediction:" + payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("解析結果の確認に失敗しました。再度解析してください。")
    return json.loads(payload)
