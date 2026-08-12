"""Step7 Sub48：複数の関連指標を統合した重要因子ランキング。"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.metrics import mutual_info_score

from Step7_Utils.statistics import FLAG, columns, comparable, table, two_by_two


def _bias_corrected_cramers_v(observed: np.ndarray) -> tuple[float, float, np.ndarray]:
    """小標本・多カテゴリの上方バイアスを補正したCramér's Vを返す。"""
    chi2, p_value, _, expected = chi2_contingency(observed, correction=False)
    n = observed.sum()
    rows, cols = observed.shape
    phi2 = chi2 / n
    phi2_corrected = max(0.0, phi2 - ((cols - 1) * (rows - 1)) / (n - 1))
    rows_corrected = rows - ((rows - 1) ** 2) / (n - 1)
    cols_corrected = cols - ((cols - 1) ** 2) / (n - 1)
    denominator = min(rows_corrected - 1, cols_corrected - 1)
    value = math.sqrt(phi2_corrected / denominator) if denominator > 0 else 0.0
    return value, p_value, expected


def run(settings: dict[str, Any]) -> None | str:
    """歯牙障害との関連を列単位で評価し、探索的な総合順位を出力する。"""
    df = settings["df"]
    logger = settings["logger"]
    dataset_name = settings["dataset_name"]
    if not comparable(df):
        logger.info("[%s] Sub48解析不能：歯牙障害・非歯牙障害の2群なし", dataset_name)
        return "skipped"

    target = df[FLAG].astype(int)
    rows: list[dict[str, Any]] = []
    for column in columns(df):
        contingency = table(df, column)
        if contingency.shape[0] < 2 or contingency.shape[1] != 2:
            continue

        observed = contingency.to_numpy(dtype=float)
        cramers_v, p_value, expected = _bias_corrected_cramers_v(observed)
        n = observed.sum()
        row_rate = observed.sum(axis=1)[:, None] / n
        col_rate = observed.sum(axis=0)[None, :] / n
        denominator = np.sqrt(expected * (1 - row_rate) * (1 - col_rate))
        residuals = np.divide(observed - expected, denominator,
                              out=np.zeros_like(expected), where=denominator > 0)

        clean = df[column].astype("string").str.strip().fillna("（欠損）").replace("", "（欠損）")
        mutual_information = float(mutual_info_score(clean, target))
        max_abs_log2_or = 0.0
        qualifying_categories = 0
        for category in contingency.index:
            a, b, c, d = two_by_two(df, column, str(category))
            # 合計件数だけでは片群0〜2件の極端なORが順位を支配するため、
            # Sub49と同様に両群3件以上も要求して安定性を確保する。
            if a + b < 20 or min(a, b) < 3:
                continue
            qualifying_categories += 1
            # ゼロセルがあっても無限大にせず、Haldane–Anscombe補正を適用する。
            if min(a, b, c, d) == 0:
                a, b, c, d = a + .5, b + .5, c + .5, d + .5
            max_abs_log2_or = max(max_abs_log2_or, abs(math.log2((a * d) / (b * c))))

        rows.append({
            "因子": column,
            "カテゴリ数": len(contingency),
            "安定性基準適合カテゴリ数": qualifying_categories,
            "CramersV（バイアス補正）": cramers_v,
            "相互情報量": mutual_information,
            "最大絶対調整済み標準化残差": float(np.abs(residuals).max()),
            "最大絶対log2OR（合計20件・両群3件以上）": max_abs_log2_or,
            "p値（カイ二乗）": p_value,
        })

    result = pd.DataFrame(rows)
    if result.empty:
        logger.info("[%s] Sub48解析不能：評価可能な因子なし", dataset_name)
        return "skipped"

    metrics = ["CramersV（バイアス補正）", "相互情報量", "最大絶対調整済み標準化残差", "最大絶対log2OR（合計20件・両群3件以上）"]
    # 尺度の異なる4指標を直接加算せず、各指標内の百分位順位を等ウェイトで統合する。
    score_columns = []
    for metric in metrics:
        score_column = f"順位点_{metric}"
        result[score_column] = result[metric].rank(method="average", pct=True) * 100
        score_columns.append(score_column)
    result["総合重要度スコア"] = result[score_columns].mean(axis=1)
    result = result.sort_values(["総合重要度スコア", "CramersV（バイアス補正）"], ascending=False).reset_index(drop=True)
    result.insert(0, "順位", np.arange(1, len(result) + 1))
    result["解釈上の注意"] = "探索的関連順位（因果的重要度・交絡調整済み効果ではない）"

    detail_path = settings["table_dir"] / "Step7-48_重要因子ランキング_詳細.csv"
    summary_path = settings["summary_dir"] / "Step7-48_重要因子ランキング.csv"
    result.to_csv(detail_path, index=False, encoding=settings["text_encoding"])
    result.head(10)[["順位", "因子", "総合重要度スコア", *metrics, "解釈上の注意"]].to_csv(
        summary_path, index=False, encoding=settings["text_encoding"]
    )
    logger.info("[%s] Sub48 / 評価因子=%d / 首位=%s", dataset_name, len(result), result.iloc[0]["因子"])
