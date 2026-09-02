from __future__ import annotations

import csv
from pathlib import Path

from .extractor import BASE_DIR
from .models import FIELD_NAMES


class ValidationError(ValueError):
    pass


class ResultValidator:
    OTHER_LOCATION_MAX_LENGTH = 100

    def __init__(self, data_dir: Path = BASE_DIR):
        self.allowed = self._allowed_values(data_dir)

    @staticmethod
    def _allowed_values(data_dir: Path) -> dict[str, set[str]]:
        allowed = {name: set() for name in FIELD_NAMES}
        with (data_dir / "02_上下位カテゴリ対応表.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                prefix = "場合別" if row["項目"] == "場合別" else "発生場所"
                allowed[prefix + "1"].add(row["観測上位値"])
                if row["観測下位値"] != "null":
                    allowed[prefix + "2"].add(row["観測下位値"])
        with (data_dir / "04_観測選択肢辞書.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["項目"] in allowed:
                    allowed[row["項目"]].add(row["観測値"])
        return allowed

    def validate(self, text: str, result: dict) -> None:
        if result.get("processing_status") == "error":
            if result.get("fields") or not result.get("error_code"):
                raise ValidationError("エラー応答には空のfieldsとerror_codeが必要です")
            return
        fields = result.get("fields", {})
        if set(fields) != set(FIELD_NAMES):
            raise ValidationError("成功応答の項目が不足しています")
        for name, field in fields.items():
            value = field["value"]
            if value is not None and value not in self.allowed[name]:
                raise ValidationError(f"{name}の許容外値: {value}")
            if value is not None:
                start, end = field["evidence_start"], field["evidence_end"]
                if start is None or end is None or text[start:end] != field["evidence_text"]:
                    raise ValidationError(f"{name}の根拠位置が不正です")

    def validate_confirmed(self, confirmed: dict[str, str | None]) -> None:
        if set(confirmed) != set(FIELD_NAMES):
            raise ValidationError("確認値の項目が不足しています")
        for name, value in confirmed.items():
            if value is not None and value not in self.allowed[name]:
                raise ValidationError(f"{name}の確認値が許容範囲外です: {value}")

    def validate_other_location(self, selected: str | None, detail: str) -> str | None:
        """発生場所2が「その他」の場合だけ、自由入力した詳細を保持する。"""
        if selected != "その他":
            return None
        normalized = detail.strip()
        if not normalized:
            raise ValidationError("発生場所で「その他」を選んだ場合は、場所の詳細を入力してください")
        if len(normalized) > self.OTHER_LOCATION_MAX_LENGTH:
            raise ValidationError(f"発生場所の詳細は{self.OTHER_LOCATION_MAX_LENGTH}文字以内で入力してください")
        return normalized
