from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterable

from app.metadata import INJURY_TYPE_RULE_VERSION, INJURY_TYPE_VALUES, infer_injury_type
from evaluation.metrics import binary_screening_summary, rate_with_interval


DEFAULT_DB = Path(__file__).resolve().parents[2] / "DB" / "shougai(2025.01.31).csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "evaluation_output" / "injury_screening"
TEXT_COLUMN = "災害発生時の状況"
LABEL_COLUMN = "種別"
LEGACY_DENTAL_PATTERN = re.compile(
    r"前歯|奥歯|永久歯|乳歯|歯牙|歯折|歯の破折|歯(?:を|が)(?:折|欠|脱|損傷|打|ぶつけ)"
)
DENTAL_WORDS = re.compile(r"前歯|奥歯|永久歯|乳歯|歯牙|歯根|歯冠|歯槽|歯科|歯|補綴|義歯|抜歯")
ORAL_FACIAL_WORDS = re.compile(r"口腔|口内|口元|口唇|唇|顎|あご|顔面|頬|鼻")
OTHER_PERSON_WORDS = re.compile(r"弟|妹|兄|姉|友人|友達|同級生|他の(?:児童|生徒|園児)")


def clean(value: object) -> str | None:
    normalized = str(value or "").strip()
    return None if not normalized or normalized.lower() in {"null", "nan"} else normalized


def screening_outcome(gold: str | None, predicted: str | None, target: str) -> str:
    gold_positive = gold == target
    predicted_positive = predicted == target
    if gold_positive and predicted_positive:
        return "TP"
    if not gold_positive and predicted_positive:
        return "FP"
    if gold_positive and not predicted_positive:
        return "FN"
    return "TN"


def screening_summary(details: Iterable[dict], target: str, prediction_key: str = "predicted_type") -> dict:
    outcomes = Counter(
        screening_outcome(row["silver_label"], row[prediction_key], target)
        for row in details
    )
    return binary_screening_summary(
        tp=outcomes["TP"], fp=outcomes["FP"], fn=outcomes["FN"], tn=outcomes["TN"]
    )


def error_hint(error_type: str, text: str, predicted: str | None) -> str:
    """人手分類前の検索補助。最終的なエラー原因とはみなさない。"""
    if error_type == "FN":
        if DENTAL_WORDS.search(text):
            return "歯科・歯牙関連語はあるが現行規則で未検出"
        if ORAL_FACIAL_WORDS.search(text):
            return "口腔・顎顔面表現のみ"
        if predicted is not None:
            return "別の種別候補を優先"
        return "歯牙障害を直接示す記載なし"
    if OTHER_PERSON_WORDS.search(text):
        return "他者・複数人物文脈の可能性"
    if ORAL_FACIAL_WORDS.search(text):
        return "歯牙表現とDB登録種別の不一致"
    return "歯牙候補規則の過剰検出またはDBラベル疑義"


def evaluate_rows(rows: list[dict], target: str = "歯牙障害") -> tuple[dict, list[dict]]:
    if target not in INJURY_TYPE_VALUES:
        raise ValueError("targetは既存DBの種別から選択してください")
    details: list[dict] = []
    for row_number, row in enumerate(rows, 1):
        text = clean(row.get(TEXT_COLUMN)) or ""
        gold = clean(row.get(LABEL_COLUMN))
        inferred = infer_injury_type(text)
        predicted = inferred["種別"]
        legacy = "歯牙障害" if LEGACY_DENTAL_PATTERN.search(text) else None
        outcome = screening_outcome(gold, predicted, target)
        details.append(
            {
                "evaluation_id": f"E{row_number:06d}",
                "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
                "era": clean(row.get("和暦")),
                "benefit_year": clean(row.get("給付年度")),
                "silver_label": gold,
                "predicted_type": predicted,
                "evidence": inferred["evidence"],
                "legacy_prediction": legacy,
                "screening_outcome": outcome,
                "automated_error_hint": error_hint(outcome, text, predicted) if outcome in {"FP", "FN"} else "",
                "text": text,
            }
        )

    current = screening_summary(details, target)
    legacy = screening_summary(details, target, "legacy_prediction") if target == "歯牙障害" else None
    by_era = {}
    for era in sorted({row["era"] for row in details if row["era"]}):
        by_era[era] = screening_summary((row for row in details if row["era"] == era), target)
    report = {
        "report_type": "development_diagnostic_against_silver_labels",
        "warning": (
            "既存DBの種別はsilver labelであり、事故文だけから再現できるgold standardではない。"
            "同じDBを規則開発にも参照しているため、学会発表で最終的な外部性能として扱わない。"
        ),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "rule_version": INJURY_TYPE_RULE_VERSION,
        "target": target,
        "rows": len(details),
        "current": current,
        "legacy_dental_rule": legacy,
        "by_era": by_era,
        "multiclass": multiclass_summary(details),
    }
    return report, details


def multiclass_summary(details: list[dict]) -> dict:
    labels = list(INJURY_TYPE_VALUES)
    total = len(details)
    predicted_rows = [row for row in details if row["predicted_type"] is not None]
    exact = sum(row["silver_label"] == row["predicted_type"] for row in details)
    conditional_exact = sum(row["silver_label"] == row["predicted_type"] for row in predicted_rows)
    per_category = {
        label: screening_summary(details, label)
        for label in labels
    }
    f1_values = [per_category[label]["f1"]["value"] or 0.0 for label in labels]
    gold_counts = Counter(row["silver_label"] for row in details)
    weighted_f1 = sum((per_category[label]["f1"]["value"] or 0.0) * gold_counts[label] for label in labels)
    weighted_f1 = round(weighted_f1 / total, 6) if total else None

    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in details:
        confusion[row["silver_label"] or "（DB空欄）"][row["predicted_type"] or "（棄権）"] += 1

    kappa = None
    if predicted_rows:
        count = len(predicted_rows)
        observed = conditional_exact / count
        gold_nonnull = Counter(row["silver_label"] for row in predicted_rows)
        predicted_counts = Counter(row["predicted_type"] for row in predicted_rows)
        expected = sum(gold_nonnull[label] * predicted_counts[label] for label in labels) / (count * count)
        if expected < 1:
            kappa = round((observed - expected) / (1 - expected), 6)
    return {
        "overall_accuracy_including_abstention": rate_with_interval(exact, total),
        "coverage": rate_with_interval(len(predicted_rows), total),
        "conditional_accuracy_when_candidate_present": rate_with_interval(conditional_exact, len(predicted_rows)),
        "macro_f1": round(sum(f1_values) / len(labels), 6),
        "weighted_f1": weighted_f1,
        "cohen_kappa_among_non_abstained": kappa,
        "per_category_one_vs_rest": per_category,
        "confusion_matrix": {gold: dict(predictions) for gold, predictions in confusion.items()},
    }


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metric_rows(report: dict) -> list[dict]:
    result = []
    groups = [("current_all", report["current"])]
    if report["legacy_dental_rule"] is not None:
        groups.append(("legacy_all", report["legacy_dental_rule"]))
    groups.extend((f"current_{era}", summary) for era, summary in report["by_era"].items())
    metrics = (
        "sensitivity", "specificity", "positive_predictive_value",
        "negative_predictive_value", "accuracy", "f1", "prevalence",
    )
    for group, summary in groups:
        for metric in metrics:
            value = summary[metric]
            interval = value["ci95_wilson"] or [None, None]
            result.append(
                {
                    "group": group,
                    "metric": metric,
                    "numerator": value["numerator"],
                    "denominator": value["denominator"],
                    "value": value["value"],
                    "ci95_lower": interval[0],
                    "ci95_upper": interval[1],
                }
            )
        result.append(
            {
                "group": group,
                "metric": "balanced_accuracy",
                "numerator": None,
                "denominator": None,
                "value": summary["balanced_accuracy"],
                "ci95_lower": None,
                "ci95_upper": None,
            }
        )
    return result


def make_janome_tokenizer() -> Callable[[str], list[str]]:
    try:
        from janome.tokenizer import Tokenizer
    except ModuleNotFoundError as exc:
        raise RuntimeError("Janomeがありません。python -m pip install -r evaluation/requirements.txt を実行してください") from exc
    stopword_path = Path(__file__).resolve().parents[2] / "file" / "Common" / "Config" / "設定_ストップワード.txt"
    stopwords = {
        line.strip() for line in stopword_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    tokenizer = Tokenizer()

    def tokenize(text: str) -> list[str]:
        words = []
        for token in tokenizer.tokenize(text):
            parts = token.part_of_speech.split(",")
            part, detail = parts[0], parts[1]
            word = token.base_form if token.base_form != "*" else token.surface
            word = word.strip()
            if part not in {"名詞", "動詞", "形容詞"} or not word or word in stopwords:
                continue
            if part == "名詞" and detail in {"非自立", "代名詞", "数"}:
                continue
            if word.isdigit():
                continue
            words.append(word)
        return words

    return tokenize


def bigram_counts(texts: Iterable[str], tokenize: Callable[[str], list[str]]) -> tuple[Counter, Counter, int]:
    occurrences: Counter = Counter()
    documents: Counter = Counter()
    count = 0
    for text in texts:
        count += 1
        words = tokenize(text)
        grams = [tuple(words[index:index + 2]) for index in range(len(words) - 1)]
        occurrences.update(grams)
        documents.update(set(grams))
    return occurrences, documents, count


def compare_bigrams(
    error_rows: list[dict],
    reference_rows: list[dict],
    comparison: str,
    tokenize: Callable[[str], list[str]],
    minimum_error_documents: int = 3,
    limit: int = 100,
) -> list[dict]:
    error_occurrences, error_documents, error_count = bigram_counts((row["text"] for row in error_rows), tokenize)
    _, reference_documents, reference_count = bigram_counts((row["text"] for row in reference_rows), tokenize)
    result = []
    for gram, error_document_count in error_documents.items():
        if error_document_count < minimum_error_documents:
            continue
        reference_document_count = reference_documents[gram]
        error_rate = error_document_count / error_count if error_count else 0.0
        reference_rate = reference_document_count / reference_count if reference_count else 0.0
        result.append(
            {
                "comparison": comparison,
                "2-gram": " ".join(gram),
                "error_group_cases": error_count,
                "error_group_occurrences": error_occurrences[gram],
                "error_group_documents": error_document_count,
                "error_group_document_rate": round(error_rate, 6),
                "reference_group_cases": reference_count,
                "reference_group_documents": reference_document_count,
                "reference_group_document_rate": round(reference_rate, 6),
                "rate_difference": round(error_rate - reference_rate, 6),
            }
        )
    result.sort(key=lambda row: (row["rate_difference"], row["error_group_documents"]), reverse=True)
    return result[:limit]


def ngram_error_analysis(details: list[dict]) -> list[dict]:
    tokenize = make_janome_tokenizer()
    groups = {name: [row for row in details if row["screening_outcome"] == name] for name in ("TP", "FP", "FN", "TN")}
    return (
        compare_bigrams(groups["FN"], groups["TP"], "FN_vs_TP", tokenize)
        + compare_bigrams(groups["FP"], groups["TN"], "FP_vs_TN", tokenize)
    )


def make_review_sample(details: list[dict], per_stratum: int, seed: int) -> tuple[list[dict], list[dict]]:
    randomizer = random.Random(seed)
    selected = []
    for outcome in ("TP", "FP", "FN", "TN"):
        candidates = [row for row in details if row["screening_outcome"] == outcome]
        selected.extend(randomizer.sample(candidates, min(per_stratum, len(candidates))))
    randomizer.shuffle(selected)
    blind = [
        {
            "review_id": f"R{index:04d}",
            "災害発生時の状況": row["text"],
            "原文から歯牙障害を判定可能": "",
            "人手判定（歯牙障害／非歯牙障害／判定不能）": "",
            "確信度（高／中／低）": "",
            "コメント": "",
        }
        for index, row in enumerate(selected, 1)
    ]
    key = [
        {
            "review_id": f"R{index:04d}",
            "evaluation_id": row["evaluation_id"],
            "silver_label": row["silver_label"],
            "system_prediction": row["predicted_type"],
            "screening_outcome_vs_silver": row["screening_outcome"],
        }
        for index, row in enumerate(selected, 1)
    ]
    return blind, key


def write_outputs(output_dir: Path, report: dict, details: list[dict], skip_ngrams: bool, review_per_stratum: int, seed: int) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = [row for row in details if row["screening_outcome"] in {"FP", "FN"}]
    error_rows = [
        {
            **row,
            "manual_error_category": "",
            "adjudicated_gold": "",
            "reviewer_note": "",
        }
        for row in errors
    ]
    write_csv(
        output_dir / "dental_screening_errors.csv",
        error_rows,
        [
            "evaluation_id", "text_hash", "screening_outcome", "silver_label", "predicted_type",
            "evidence", "automated_error_hint", "era", "benefit_year", "text",
            "manual_error_category", "adjudicated_gold", "reviewer_note",
        ],
    )
    metrics = metric_rows(report)
    write_csv(
        output_dir / "dental_screening_metrics.csv",
        metrics,
        ["group", "metric", "numerator", "denominator", "value", "ci95_lower", "ci95_upper"],
    )
    confusion_rows = []
    for gold, predictions in report["multiclass"]["confusion_matrix"].items():
        for predicted, count in predictions.items():
            confusion_rows.append({"silver_label": gold, "predicted_type": predicted, "count": count})
    write_csv(output_dir / "injury_type_confusion_matrix.csv", confusion_rows, ["silver_label", "predicted_type", "count"])

    blind, key = make_review_sample(details, review_per_stratum, seed)
    write_csv(
        output_dir / "dental_stratified_error_audit_blinded.csv",
        blind,
        [
            "review_id", "災害発生時の状況", "原文から歯牙障害を判定可能",
            "人手判定（歯牙障害／非歯牙障害／判定不能）", "確信度（高／中／低）", "コメント",
        ],
    )
    write_csv(
        output_dir / "dental_stratified_error_audit_key.csv",
        key,
        ["review_id", "evaluation_id", "silver_label", "system_prediction", "screening_outcome_vs_silver"],
    )
    report["stratified_error_audit"] = {
        "seed": seed,
        "requested_cases_per_silver_outcome": review_per_stratum,
        "cases": len(blind),
        "warning": (
            "TP・FP・FN・TNを均等抽出した誤答監査用標本であり、単純集計から母集団の感度・特異度は算出しない。"
            "最終性能には別途、確率抽出または抽出確率を考慮したgold standard評価を用いる。"
        ),
    }

    if skip_ngrams:
        report["ngram_analysis"] = {"status": "skipped_by_option"}
    else:
        try:
            ngrams = ngram_error_analysis(details)
        except RuntimeError as exc:
            report["ngram_analysis"] = {"status": "skipped_missing_dependency", "reason": str(exc)}
        else:
            write_csv(
                output_dir / "dental_error_2grams.csv",
                ngrams,
                [
                    "comparison", "2-gram", "error_group_cases", "error_group_occurrences",
                    "error_group_documents", "error_group_document_rate", "reference_group_cases",
                    "reference_group_documents", "reference_group_document_rate", "rate_difference",
                ],
            )
            report["ngram_analysis"] = {
                "status": "completed",
                "method": "Janomeの名詞・動詞・形容詞の基本形による連続2語。Step7と同じ除外規則。",
                "comparisons": ["FN_vs_TP", "FP_vs_TN"],
                "rows": len(ngrams),
            }
    (output_dir / "injury_screening_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="種別判定と歯牙障害スクリーニングを既存DBのsilver labelで開発診断する")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target", choices=("歯牙障害",), default="歯牙障害")
    parser.add_argument("--skip-ngrams", action="store_true")
    parser.add_argument("--review-per-stratum", type=int, default=25)
    parser.add_argument("--seed", type=int, default=20260904)
    args = parser.parse_args()
    if args.review_per_stratum < 1:
        parser.error("--review-per-stratumは1以上にしてください")
    report, details = evaluate_rows(load_rows(args.db), args.target)
    write_outputs(args.output_dir, report, details, args.skip_ngrams, args.review_per_stratum, args.seed)
    current = report["current"]
    print(json.dumps({
        "warning": report["warning"],
        "output_dir": str(args.output_dir),
        "rule_version": report["rule_version"],
        "target": args.target,
        "confusion_matrix": current["confusion_matrix"],
        "sensitivity": current["sensitivity"],
        "specificity": current["specificity"],
        "positive_predictive_value": current["positive_predictive_value"],
        "accuracy": current["accuracy"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
