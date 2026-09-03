from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


METADATA_NAMES = ("和暦", "給付年度", "記号", "種別", "被災学校種", "被災学年", "性別")
FIELD_NAMES = ("場合別1", "場合別2", "競技種目", "通学方法", "発生場所1", "発生場所2", "遊具等")
DB_COLUMNS = METADATA_NAMES + FIELD_NAMES + ("災害発生時の状況", "コメント")


@dataclass(frozen=True)
class FieldResult:
    value: str | None
    status: Literal[
        "explicit", "derived", "not_mentioned", "ambiguous", "conflict",
        "unsupported", "validation_rejected", "not_applicable"
    ]
    reason_code: str | None
    evidence_text: str | None
    evidence_start: int | None
    evidence_end: int | None
    provenance: Literal["llm_explicit", "synonym_rule", "derived_hierarchy", "user_corrected", "none"]
    derived_from: str | None
    rule_id: str | None
    validator_status: Literal["passed", "rejected", "not_run"]

    def as_dict(self) -> dict:
        return asdict(self)


def empty_field(status: str = "not_mentioned", reason: str = "NO_MENTION") -> FieldResult:
    return FieldResult(None, status, reason, None, None, None, "none", None, None, "passed")
