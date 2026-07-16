#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-2_歯牙障害特徴ランキング

Step5-1の比較結果から、歯牙障害で相対的に高い語・カテゴリを抽出する。
"""


from __future__ import annotations

from pathlib import Path
import sys
import time
import math

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step5_結果整理"
TABLE_DIR = OUTPUT_DIR / "Tables"
FIGURE_DIR = OUTPUT_DIR / "Figures"
SUPPORT_DIR = OUTPUT_DIR / "考察支援"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
SUPPORT_DIR.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"入力CSVが見つかりません: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return numerator / denominator


def save_summary(items: list[tuple[str, object]], path: Path) -> None:
    save_csv(pd.DataFrame(items, columns=["項目", "値"]), path)


IN_FREQ = TABLE_DIR / "Table1_All_vs歯牙障害_頻出語比較.csv"
IN_FEATURE = TABLE_DIR / "Table2_All_vs歯牙障害_特徴語比較.csv"
IN_CATEGORY = TABLE_DIR / "Table3_All_vs歯牙障害_カテゴリ比較.csv"

OUT_WORD = TABLE_DIR / "Table4_歯牙障害特徴語ランキング.csv"
OUT_CATEGORY = TABLE_DIR / "Table5_歯牙障害特徴カテゴリランキング.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-2_解析サマリー.csv"

MIN_DENTAL_RATE = 1.0
MIN_RATE_DIFFERENCE = 0.5
TOP_N = 100


def main() -> None:
    start = time.perf_counter()
    try:
        freq = read_csv(IN_FREQ)
        feature = read_csv(IN_FEATURE)
        category = read_csv(IN_CATEGORY)

        word = freq[
            (freq["歯牙障害事例出現率(%)"] >= MIN_DENTAL_RATE)
            & (freq["出現率差_歯牙障害-All"] >= MIN_RATE_DIFFERENCE)
        ].copy()

        word = word.merge(
            feature[["特徴語", "歯牙障害平均TF-IDF", "TF-IDF差_歯牙障害-All"]],
            left_on="基本形",
            right_on="特徴語",
            how="left",
        )

        word["総合特徴スコア"] = (
            word["出現率差_歯牙障害-All"].fillna(0)
            + word["歯牙障害事例出現率(%)"].fillna(0) * 0.2
            + word["TF-IDF差_歯牙障害-All"].fillna(0) * 100
        ).round(6)

        word = word.sort_values(
            ["総合特徴スコア", "歯牙障害事例出現率(%)"],
            ascending=[False, False],
        ).head(TOP_N).reset_index(drop=True)

        word.insert(0, "総合順位", range(1, len(word) + 1))

        category_rank = category[
            (category["歯牙障害事例出現率(%)"] >= MIN_DENTAL_RATE)
            & (category["出現率差_歯牙障害-All"] >= MIN_RATE_DIFFERENCE)
        ].copy()

        category_rank["総合特徴スコア"] = (
            category_rank["出現率差_歯牙障害-All"]
            + category_rank["歯牙障害事例出現率(%)"] * 0.2
        ).round(6)

        category_rank = category_rank.sort_values(
            ["総合特徴スコア", "歯牙障害事例出現率(%)"],
            ascending=[False, False],
        ).head(TOP_N).reset_index(drop=True)

        category_rank.insert(0, "総合順位", range(1, len(category_rank) + 1))

        save_csv(word, OUT_WORD)
        save_csv(category_rank, OUT_CATEGORY)

        elapsed = time.perf_counter() - start
        save_summary([
            ("特徴語ランキング件数", len(word)),
            ("特徴カテゴリランキング件数", len(category_rank)),
            ("最低歯牙障害出現率(%)", MIN_DENTAL_RATE),
            ("最低出現率差", MIN_RATE_DIFFERENCE),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step5-3_Jaccard結果整理.py"),
        ], OUT_SUMMARY)

        print(word.head(30).to_string(index=False))
        print("\nStep5-2 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
