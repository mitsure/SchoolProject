from __future__ import annotations

import csv
import hashlib
import hmac
import os
from pathlib import Path
from typing import Protocol

from .models import FIELD_NAMES, FieldResult, empty_field


BASE_DIR = Path(__file__).resolve().parent.parent


class Extractor(Protocol):
    def extract(self, text: str) -> dict: ...


class RuleBasedExtractor:
    """架空例でUIと検証を開発するための、保守的なローカル抽出器。"""

    def __init__(self, data_dir: Path = BASE_DIR):
        self.data_dir = data_dir
        self.synonyms = self._load_synonyms()
        self.hierarchy = self._load_hierarchy()

    def _load_synonyms(self) -> list[dict[str, str]]:
        with (self.data_dir / "05_同義語候補辞書.csv").open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _load_hierarchy(self) -> dict[tuple[str, str], tuple[str, str]]:
        result: dict[tuple[str, str], tuple[str, str]] = {}
        with (self.data_dir / "02_上下位カテゴリ対応表.csv").open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["下位から上位を自動補完"] == "可":
                    prefix = "場合別" if row["項目"] == "場合別" else "発生場所"
                    result[(prefix, row["観測下位値"])] = (row["観測上位値"], "CASE_001" if prefix == "場合別" else "PLACE_001")
        return result

    @staticmethod
    def _error(code: str) -> dict:
        return {"schema_version": "1.0.1", "processing_status": "error", "input_hash": "not-stored", "error_code": code, "fields": {}}

    @staticmethod
    def _input_hash(text: str) -> str:
        key = os.environ.get("SPORTDENT_HMAC_KEY", "local-development-only").encode()
        return hmac.new(key, text.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _explicit(text: str, evidence: str, value: str, rule_id: str) -> FieldResult:
        start = text.index(evidence)
        return FieldResult(value, "explicit", None, evidence, start, start + len(evidence), "synonym_rule", None, rule_id, "passed")

    def extract(self, text: str) -> dict:
        text = text.strip()
        if not text:
            return self._error("EMPTY_INPUT")
        if len(text) > 5000:
            return self._error("INPUT_TOO_LONG")
        # MVPでは複数の日・複数事故の混在を安全側に倒す。
        if ("昨日" in text and "今日" in text) or text.count("転倒") + text.count("衝突") + text.count("落下") >= 2:
            return self._error("MULTIPLE_INCIDENTS")
        if "指示を無視" in text or "全項目を" in text:
            return self._error("PROMPT_INJECTION_SUSPECTED")

        fields = {name: empty_field() for name in FIELD_NAMES}
        candidates: dict[str, list[tuple[int, dict[str, str]]]] = {}
        for row in self.synonyms:
            phrase = row["原文表現"]
            start = text.find(phrase)
            if start >= 0:
                candidates.setdefault(row["項目"], []).append((start, row))

        # 事故地点は「へ向かう/移動中」の目的地を除き、後半の明示場所を優先。
        for field, items in candidates.items():
            usable = items
            if field == "発生場所2":
                usable = [(p, r) for p, r in items if not any(x in text[max(0, p - 3):p + len(r["原文表現"]) + 6] for x in ("へ移動", "へ向か"))]
            if field == "競技種目" and any(x in text for x in ("友人を見", "観戦", "見に行")):
                usable = []
            # 「AではなくB」はAを候補から除外する。
            usable = [(p, r) for p, r in usable if f"{r['原文表現']}ではなく" not in text[p:p + len(r['原文表現']) + 4]]
            if not usable:
                continue
            values = {r["DB候補値"] for _, r in usable}
            if len(values) > 1:
                fields[field] = empty_field("ambiguous", "MULTIPLE_CANDIDATES")
                continue
            pos, row = max(usable, key=lambda item: item[0])
            fields[field] = self._explicit(text, row["原文表現"], row["DB候補値"], row["rule_id"])

        # 辞書にないがMVP安全性試験で必要な直接表現。
        direct_places = {"階段": "階段", "廊下": "廊下", "道路": "道路"}
        for phrase, value in direct_places.items():
            if phrase in text and (fields["発生場所2"].value is None or text.rfind(phrase) > (fields["発生場所2"].evidence_start or -1)):
                fields["発生場所2"] = self._explicit(text, phrase, value, "DIRECT_PLACE")

        # 鉄棒は「近く」ではなく、本人が使用している連続表現がある場合だけ遊具とする。
        if "鉄棒" in text and any(phrase in text for phrase in ("鉄棒で遊", "鉄棒を使用", "鉄棒から落")):
            fields["遊具等"] = self._explicit(text, "鉄棒", "鉄棒", "DIRECT_PLAY_USE")

        # 種類が示されない部活動は、運動部・文化部を推測せず曖昧として残す。
        if "部活動の練習中" in text and fields["場合別2"].value is None:
            fields["場合別2"] = empty_field("ambiguous", "ACTIVITY_TYPE_AMBIGUOUS")
            fields["競技種目"] = empty_field("ambiguous", "SPORT_NOT_SPECIFIED")

        # 通学の上位値は下位分類からのみ派生。
        for prefix, lower_name, upper_name in (("場合別", "場合別2", "場合別1"), ("発生場所", "発生場所2", "発生場所1")):
            lower = fields[lower_name]
            mapping = self.hierarchy.get((prefix, lower.value or ""))
            if lower.status == "explicit" and mapping:
                upper_value, rule_id = mapping
                fields[upper_name] = FieldResult(upper_value, "derived", None, lower.evidence_text, lower.evidence_start, lower.evidence_end, "derived_hierarchy", lower_name, rule_id, "passed")

        # 「校外」は発生場所1の直接根拠として階層派生より優先。
        if "校外" in text:
            fields["発生場所1"] = self._explicit(text, "校外", "学校外（園外）", "DIRECT_PLACE_CONTEXT")
            if "体育館" in text:
                fields["発生場所2"] = self._explicit(text, "体育館", "学校外体育館", "DIRECT_PLACE_CONTEXT")

        # 通学方法は通学中が確定した場合だけ保持する。否定表現も除外する。
        if fields["場合別1"].value != "通学中":
            fields["通学方法"] = empty_field("not_applicable", "NOT_COMMUTING")
        elif "自転車ではなく" in text and fields["通学方法"].value == "自転車":
            fields["通学方法"] = empty_field("validation_rejected", "NEGATED_EVIDENCE")

        # 競技は本人が実施中と読める限定的な文脈だけ採用する。
        sport = fields["競技種目"]
        if sport.value and not any(x in text for x in ("試合中", "練習中", "授業中", "プレー中")):
            fields["競技種目"] = empty_field("validation_rejected", "ACTIVITY_NOT_ESTABLISHED")

        return {"schema_version": "1.0.1", "processing_status": "success", "input_hash": self._input_hash(text), "error_code": None, "fields": {k: v.as_dict() for k, v in fields.items()}}
