"""Step11の調停前A/B回答から、評価者間一致を非公開領域へ集計する。"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import Step11_ReviewWorkflow as workflow
import Step11_PostReviewWorkflow as postreview


BOOTSTRAP_SEED = 20260811
BOOTSTRAP_REPETITIONS = 10_000


class AnalysisError(RuntimeError):
    """未完了回答や不正な入力を結果へ変換しないための停止。"""


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return math.nan, math.nan
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    half_width = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def unweighted_kappa(first: np.ndarray, second: np.ndarray) -> float:
    if len(first) == 0:
        return math.nan
    categories = sorted(set(first.tolist()) | set(second.tolist()))
    if len(categories) < 2:
        return math.nan
    observed = float(np.mean(first == second))
    expected = 0.0
    for category in categories:
        expected += float(np.mean(first == category) * np.mean(second == category))
    if math.isclose(1 - expected, 0.0):
        return math.nan
    return (observed - expected) / (1 - expected)


def bootstrap_kappa(first: np.ndarray, second: np.ndarray, seed_offset: int) -> tuple[float, float, int]:
    generator = np.random.default_rng(BOOTSTRAP_SEED + seed_offset)
    estimates: list[float] = []
    for _ in range(BOOTSTRAP_REPETITIONS):
        indices = generator.integers(0, len(first), size=len(first))
        estimate = unweighted_kappa(first[indices], second[indices])
        if math.isfinite(estimate):
            estimates.append(estimate)
    if not estimates:
        return math.nan, math.nan, 0
    lower, upper = np.percentile(estimates, [2.5, 97.5])
    return float(lower), float(upper), len(estimates)


def numeric_or_nan(value: float) -> float:
    return value if math.isfinite(value) else math.nan


def load_complete_pair(phase: str) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str], dict[str, object]]:
    """編集可能な作業本ではなく、先に固定済みのA/B原本だけを読む。"""
    try:
        first, second, frozen_root, manifest = postreview._load_frozen_frames(phase)
    except postreview.PostReviewError as error:
        raise AnalysisError(str(error)) from error
    hashes = {
        reviewer: str(manifest["workbooks"][reviewer]["sha256"])
        for reviewer in ["A", "B"]
    }
    for reviewer, frame in [("A", first), ("B", second)]:
        if len(frame) != workflow.EXPECTED_ROWS:
            raise AnalysisError(f"凍結評価者{reviewer}原本が100件ではありません")
        for _, row in frame.iterrows():
            values = {column: str(row[column]).strip() for column in workflow.INPUT_COLUMNS}
            if any(not values[column] for column in workflow.REQUIRED_COLUMNS):
                raise AnalysisError(f"凍結評価者{reviewer}原本に未入力があります")
            problems = workflow.row_problems(values)
            if problems:
                raise AnalysisError(f"凍結評価者{reviewer}原本に回答矛盾があります: {' / '.join(problems)}")
    if any(
        workflow.sha256(frozen_root / str(manifest["workbooks"][reviewer]["file"])) != hashes[reviewer]
        for reviewer in ["A", "B"]
    ):
        raise AnalysisError("解析直前に凍結A/B原本のハッシュが変化しました")
    return first, second, hashes, manifest


def f1_binary(first: np.ndarray, second: np.ndarray) -> tuple[float, int, int, int, int]:
    true_positive = int(np.sum(first & second))
    false_positive = int(np.sum(~first & second))
    false_negative = int(np.sum(first & ~second))
    true_negative = int(np.sum(~first & ~second))
    denominator = 2 * true_positive + false_positive + false_negative
    return (
        math.nan if denominator == 0 else 2 * true_positive / denominator,
        true_positive, false_positive, false_negative, true_negative,
    )


def analyse(phase: str) -> None:
    first, second, input_hashes, frozen_manifest = load_complete_pair(phase)
    frozen_root = postreview.frozen_dir(phase)
    frozen_manifest_path = frozen_root / "manifest.json"
    frozen_manifest_hash = workflow.sha256(frozen_manifest_path)
    analysis_hash = workflow.sha256(Path(__file__).resolve())
    workflow_hash = workflow.sha256(Path(workflow.__file__).resolve())
    approval_hash = str(frozen_manifest["approval_sha256"])
    codebook_hash = str(frozen_manifest["codebook_sha256"])
    codebook_version = str(frozen_manifest["codebook_version"])
    output = workflow.INTERNAL / "AgreementResults" / phase
    if output.exists():
        raise AnalysisError(f"既存の一致度結果を上書きしません: {output}")
    agreement_root = workflow.INTERNAL / "AgreementResults"
    agreement_root.mkdir(parents=True, exist_ok=True)
    agreement_root.chmod(0o700)

    summary_rows: list[dict[str, object]] = []
    distribution_rows: list[dict[str, object]] = []
    confusion_rows: list[dict[str, object]] = []
    fields = [field for field in workflow.CHOICES if field != workflow.CONFIRM_COLUMN]
    for field_index, field in enumerate(fields):
        a = first[field].astype(str).to_numpy()
        b = second[field].astype(str).to_numpy()
        matches = int(np.sum(a == b))
        lower, upper = wilson_interval(matches, len(a))
        kappa = unweighted_kappa(a, b)
        kappa_lower, kappa_upper, valid_bootstraps = bootstrap_kappa(a, b, field_index)
        a_uncertain = int(np.sum(a == "判定不能"))
        b_uncertain = int(np.sum(b == "判定不能"))
        any_uncertain = int(np.sum((a == "判定不能") | (b == "判定不能")))
        summary_rows.append({
            "評価段階": phase,
            "項目": field,
            "対象件数": len(a),
            "一致件数": matches,
            "完全一致率": matches / len(a),
            "一致率95%CI下限（Wilson）": lower,
            "一致率95%CI上限（Wilson）": upper,
            "評価者A判定不能件数": a_uncertain,
            "評価者B判定不能件数": b_uncertain,
            "片方以上判定不能件数": any_uncertain,
            "両者判定可能件数": len(a) - any_uncertain,
            "Cohenκ（非加重）": numeric_or_nan(kappa),
            "κ算出状態": "算出済み" if math.isfinite(kappa) else "算出不能",
            "κ95%CI下限（ペアbootstrap）": numeric_or_nan(kappa_lower),
            "κ95%CI上限（ペアbootstrap）": numeric_or_nan(kappa_upper),
            "有効bootstrap回数": valid_bootstraps,
            "無効bootstrap回数": BOOTSTRAP_REPETITIONS - valid_bootstraps,
            "κCI算出状態": (
                "算出不能" if valid_bootstraps == 0
                else "要注意（有効再標本95%未満）" if valid_bootstraps < 0.95 * BOOTSTRAP_REPETITIONS
                else "算出済み"
            ),
        })
        categories = workflow.CHOICES[field]
        for reviewer, values in [("A", a), ("B", b)]:
            for category in categories:
                distribution_rows.append({
                    "評価段階": phase, "項目": field, "評価者": reviewer,
                    "カテゴリ": category, "件数": int(np.sum(values == category)),
                })
        for a_category in categories:
            for b_category in categories:
                confusion_rows.append({
                    "評価段階": phase, "項目": field,
                    "評価者A": a_category, "評価者B": b_category,
                    "件数": int(np.sum((a == a_category) & (b == b_category))),
                })

    site_a_three_state = first[workflow.SITE_COLUMNS].astype(str).to_numpy()
    site_b_three_state = second[workflow.SITE_COLUMNS].astype(str).to_numpy()
    exact_matches = int(np.sum(np.all(site_a_three_state == site_b_three_state, axis=1)))
    exact_lower, exact_upper = wilson_interval(exact_matches, len(site_a_three_state))
    complete_cases = np.all(
        (site_a_three_state != "判定不能") & (site_b_three_state != "判定不能"), axis=1
    )
    site_a = site_a_three_state[complete_cases] == "記載あり"
    site_b = site_b_three_state[complete_cases] == "記載あり"
    set_matches = int(np.sum(np.all(site_a == site_b, axis=1))) if len(site_a) else 0
    set_lower, set_upper = wilson_interval(set_matches, len(site_a))
    label_f1: list[float] = []
    label_rows: list[dict[str, object]] = []
    total_tp = total_fp = total_fn = 0
    for index, field in enumerate(workflow.SITE_COLUMNS):
        valid = (site_a_three_state[:, index] != "判定不能") & (site_b_three_state[:, index] != "判定不能")
        a_binary = site_a_three_state[valid, index] == "記載あり"
        b_binary = site_b_three_state[valid, index] == "記載あり"
        f1, tp, fp, fn, tn = f1_binary(a_binary, b_binary)
        if math.isfinite(f1):
            label_f1.append(f1)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        label_rows.append({
            "評価段階": phase, "部位項目": field, "判定可能ペア件数": int(valid.sum()),
            "判定不能により除外した件数": int((~valid).sum()),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "F1": numeric_or_nan(f1), "F1算出状態": "算出済み" if math.isfinite(f1) else "算出不能",
        })
    micro_denominator = 2 * total_tp + total_fp + total_fn
    micro_f1 = math.nan if micro_denominator == 0 else 2 * total_tp / micro_denominator
    multilabel = pd.DataFrame([{
        "評価段階": phase,
        "全対象件数": len(site_a_three_state),
        "三値ベクトル完全一致件数（判定不能含む）": exact_matches,
        "三値ベクトル完全一致率（判定不能含む）": exact_matches / len(site_a_three_state),
        "三値完全一致率95%CI下限（Wilson）": exact_lower,
        "三値完全一致率95%CI上限（Wilson）": exact_upper,
        "全6部位が両者判定可能な件数": int(complete_cases.sum()),
        "完全ケースの陽性集合一致件数": set_matches,
        "完全ケースの陽性集合一致率": math.nan if len(site_a) == 0 else set_matches / len(site_a),
        "陽性集合一致率95%CI下限（Wilson）": set_lower,
        "陽性集合一致率95%CI上限（Wilson）": set_upper,
        "Micro-F1": numeric_or_nan(micro_f1),
        "Macro-F1（算出可能ラベル平均）": numeric_or_nan(float(np.mean(label_f1)) if label_f1 else math.nan),
        "Macro-F1算出ラベル数": len(label_f1),
        "全ラベル数": len(workflow.SITE_COLUMNS),
        "注記": "F1は両者が当該部位を判定可能なペアだけで算出し、判定不能を記載なしへ置換しない。",
    }])

    summary = pd.DataFrame(summary_rows)
    distributions = pd.DataFrame(distribution_rows)
    confusion = pd.DataFrame(confusion_rows)
    files = {
        "Step11-23_評価者間一致サマリー.csv": summary,
        "Step11-24_評価者別カテゴリ分布.csv": distributions,
        "Step11-25_評価者間混同行列_長形式.csv": confusion,
        "Step11-26_受傷部位マルチラベル一致.csv": multilabel,
        "Step11-26A_受傷部位項目別F1.csv": pd.DataFrame(label_rows),
    }
    for frame in files.values():
        frame.insert(0, "コードブック版", codebook_version)
    temporary_root = Path(tempfile.mkdtemp(prefix=".agreement-", dir=agreement_root))
    temporary_root.chmod(0o700)
    for filename, frame in files.items():
        path = temporary_root / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        path.chmod(0o600)
    report = temporary_root / "Step11-27_評価者間一致レポート.md"
    report.write_text(
        "# Step11 評価者間一致レポート（内部用）\n\n"
        f"- 評価段階：{phase}\n"
        f"- 対象：A/Bが独立評価した{len(first)}件\n"
        f"- bootstrap：事例ペア単位{BOOTSTRAP_REPETITIONS:,}回、seed={BOOTSTRAP_SEED}\n"
        f"- コードブック版：{codebook_version}\n"
        f"- コードブック SHA-256：`{codebook_hash}`\n"
        f"- 承認記録 SHA-256：`{approval_hash}`\n"
        f"- 解析コード SHA-256：`{analysis_hash}`\n"
        f"- 検査コード SHA-256：`{workflow_hash}`\n"
        f"- 評価者A Excel SHA-256：`{input_hashes['A']}`\n"
        f"- 評価者B Excel SHA-256：`{input_hashes['B']}`\n\n"
        "評価者間一致は調停前のA/B回答から算出した。ここでは歯牙障害区分・自動回答を参照していない。"
        "κは判定不能を独立カテゴリとして含む100件で算出した。判定可能・不能の分母をサマリーへ併記した。"
        "κのbootstrap CIはκが定義できた再標本のpercentile区間であり、有効率95%未満は要注意とした。"
        "κが算出不能な項目は0や1へ置換せず、カテゴリ分布と一致率を確認する。"
        "本フォルダは原文を含まないが、個票由来の内部解析結果として公開しない。\n",
        encoding="utf-8",
    )
    report.chmod(0o600)
    if any(
        workflow.sha256(frozen_root / str(frozen_manifest["workbooks"][reviewer]["file"])) != input_hashes[reviewer]
        for reviewer in ["A", "B"]
    ) or workflow.sha256(frozen_manifest_path) != frozen_manifest_hash:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise AnalysisError("解析中にA/B原本または凍結manifestのハッシュが変化しました")
    try:
        postreview._frozen_manifest(phase)
    except postreview.PostReviewError as error:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise AnalysisError(f"解析完了前の凍結一式再検査に失敗しました: {error}") from error
    try:
        os.replace(temporary_root, output)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    workflow.secure_tree(output)
    print(f"ANALYSIS_OK: {phase} / A/B各{len(first)}件 / 出力={output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["開発用", "最終評価用"], default="開発用")
    args = parser.parse_args()
    try:
        analyse(args.phase)
    except (AnalysisError, workflow.WorkflowError) as error:
        raise SystemExit(f"ANALYSIS_STOP: {error}") from error


if __name__ == "__main__":
    main()
