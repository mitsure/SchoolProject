"""Research assessments are separate from ordinary DB confirmations."""
from __future__ import annotations

from collections import Counter
import hashlib

from evaluation.metrics import binary_screening_summary, rate_with_interval

from .metadata import GRADE_RULES, INJURY_TYPE_VALUES, SCHOOL_LABELS, validate_demographics
from .models import FIELD_NAMES


EVALUATION_FIELDS = ("種別", "被災学校種", "被災学年", "性別") + FIELD_NAMES
SPLITS = {"development": "開発用", "validation": "検証用", "test": "最終評価用（指定のみ）"}
SAMPLING = {"unspecified": "未記録", "consecutive": "連続登録", "random": "無作為抽出",
            "convenience": "任意選択", "error_audit": "誤答・層別監査"}
ERROR_CATEGORIES = ("未分類", "情報不足", "同義語・表記揺れ", "対象人物・場面の取り違え",
                    "否定・時系列", "カテゴリ対応", "過剰推測", "棄権・未検出", "その他")


def field_options(validator) -> dict:
    return {"種別": list(INJURY_TYPE_VALUES), "被災学校種": list(SCHOOL_LABELS),
            "被災学年": sorted({grade for grades in GRADE_RULES.values() for grade in grades}),
            "性別": ["男", "女"], **{key: sorted(values) for key, values in validator.allowed.items()}}


def parse_assessment(form, validator) -> dict:
    def bounded(name, limit, required=False):
        value = str(form.get(name, "")).strip()
        if len(value) > limit or (required and not value):
            raise ValueError(f"{name}の入力を確認してください")
        return value

    reviewer = bounded("reviewer", 100, True)
    dataset = bounded("dataset", 100, True)
    split, sampling = str(form.get("split", "")), str(form.get("sampling", ""))
    status = str(form.get("status", ""))
    note, exclusion = bounded("note", 2000), bounded("exclusion_reason", 500)
    if split not in SPLITS or sampling not in SAMPLING or status not in {"active", "excluded"}:
        raise ValueError("評価区分が不正です")
    if status == "excluded" and not exclusion:
        raise ValueError("除外理由を入力してください")
    labels, categories = {}, {}
    for index, (name, choices) in enumerate(field_options(validator).items()):
        raw = str(form.get(f"gold_{index}", ""))
        category = str(form.get(f"error_{index}", "未分類"))
        if category not in ERROR_CATEGORIES:
            raise ValueError("誤答分類が不正です")
        if raw == "":
            labels[name] = {"status": "unreviewed", "value": None}
        elif raw == "__unknown":
            labels[name] = {"status": "indeterminate", "value": None}
        elif raw == "__none" and name != "種別":
            labels[name] = {"status": "no_value", "value": None}
        elif raw in choices:
            labels[name] = {"status": "determinate", "value": raw}
        else:
            raise ValueError(f"{name}の正解値が不正です")
        categories[name] = category
    if all(labels[name]["status"] == "determinate" for name in ("被災学校種", "被災学年")):
        validate_demographics(labels["被災学校種"]["value"], labels["被災学年"]["value"], None)
    if status == "active" and all(item["status"] == "unreviewed" for item in labels.values()):
        raise ValueError("少なくとも1項目を評価してください")
    return {"reference_type": "single_review", "reviewer": reviewer, "dataset": dataset,
            "split": split, "sampling": sampling, "status": status, "exclusion_reason": exclusion,
            "note": note, "labels": labels, "error_categories": categories}


def predictions(record: dict) -> dict:
    if record["prediction"] is not None:
        return record["prediction"]
    # Historical data only supplies the seven actually saved fields; never re-run today's rules.
    return {name: field.get("value") for name, field in record["extracted"].get("fields", {}).items()}


def record_version(record: dict) -> str:
    return (record["metadata"] or {}).get("version", "legacy")


def summarize_records(records: list[dict]) -> dict:
    pending = sum(row["assessment"] is None for row in records)
    excluded = sum(row["assessment"] is not None and row["assessment"]["status"] == "excluded" for row in records)
    active = [row for row in records if row["assessment"] and row["assessment"]["status"] == "active"]
    # Same original text + version contributes once. Preserve all records and revisions in the DB.
    unique = {}
    for row in sorted(active, key=lambda r: (r["assessed_at"], r["assessment_id"])):
        key = (hashlib.sha256(row["input_text"].strip().encode()).hexdigest(), record_version(row))
        unique[key] = row
    evaluated = list(unique.values())
    field_summaries, errors = {}, []
    complete_count = complete_exact = 0
    for row in evaluated:
        labels, predicted = row["assessment"]["labels"], predictions(row)
        if all(name in predicted and labels[name]["status"] in {"determinate", "no_value"} for name in EVALUATION_FIELDS):
            complete_count += 1
            complete_exact += all(predicted[name] == labels[name]["value"] for name in EVALUATION_FIELDS)
    for name in EVALUATION_FIELDS:
        total = exact = present = correct_present = no_value = correct_empty = indeterminate = unreviewed = missing = 0
        for row in evaluated:
            label = row["assessment"]["labels"][name]
            predicted = predictions(row)
            if name not in predicted:
                missing += 1
                continue
            if label["status"] in {"unreviewed", "indeterminate"}:
                unreviewed += label["status"] == "unreviewed"
                indeterminate += label["status"] == "indeterminate"
                continue
            value, gold = predicted[name], label["value"]
            if label["status"] == "no_value":
                no_value += 1
                correct_empty += value is None
            else:
                total += 1
                exact += value == gold
            present += value is not None
            correct_present += value is not None and value == gold
            if value != gold:
                errors.append({"review_id": row["id"], "field": name, "predicted": value, "gold": gold,
                               "category": row["assessment"]["error_categories"][name], "text": row["input_text"],
                               "version": record_version(row), "reviewer": row["assessment"]["reviewer"]})
        field_summaries[name] = {"accuracy": rate_with_interval(exact, total),
                                "precision": rate_with_interval(correct_present, present),
                                "coverage": rate_with_interval(present, total + no_value),
                                "no_value": no_value, "correct_empty": correct_empty,
                                "indeterminate": indeterminate, "unreviewed": unreviewed, "missing": missing}
    confusion = Counter()
    screening_abstained = 0
    for row in evaluated:
        label, predicted = row["assessment"]["labels"]["種別"], predictions(row)
        if label["status"] != "determinate" or "種別" not in predicted:
            continue
        positive, detected = label["value"] == "歯牙障害", predicted["種別"] == "歯牙障害"
        confusion["tp" if positive and detected else "fn" if positive else "fp" if detected else "tn"] += 1
        screening_abstained += predicted["種別"] is None
    return {"total": len(records), "pending": pending, "excluded": excluded, "evaluated": len(evaluated),
            "duplicates": len(active) - len(evaluated), "fields": field_summaries,
            "complete_accuracy": rate_with_interval(complete_exact, complete_count),
            "screening": binary_screening_summary(**{key: confusion[key] for key in ("tp", "fp", "fn", "tn")}),
            "screening_abstained": screening_abstained, "errors": errors,
            "error_categories": dict(Counter(row["category"] for row in errors))}
