#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-3_Jaccard結果整理

Step4のJaccard結果から、論文掲載候補を抽出する。
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


INPUTS = {
    "All_語特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-1_All_語特徴間Jaccard.csv",
    "All_カテゴリ特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-1_All_カテゴリ特徴間Jaccard.csv",
    "All_統合特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-1_All_統合特徴間Jaccard.csv",
    "歯牙障害_語特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-2_歯牙障害_語特徴間Jaccard.csv",
    "歯牙障害_カテゴリ特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-2_歯牙障害_カテゴリ特徴間Jaccard.csv",
    "歯牙障害_統合特徴": PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析" / "Step4-2_歯牙障害_統合特徴間Jaccard.csv",
}

OUT_TOP = TABLE_DIR / "Table6_Jaccard上位ペア.csv"
OUT_DENTAL = TABLE_DIR / "Table7_歯牙障害_Jaccard上位ペア.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-3_解析サマリー.csv"

MIN_SCORE = 0.10
TOP_N_PER_SOURCE = 50


def main() -> None:
    start = time.perf_counter()
    try:
        frames = []

        for source_name, path in INPUTS.items():
            df = read_csv(path)
            require_columns(df, ["特徴1", "特徴2", "ジャッカード係数"])

            filtered = df[df["ジャッカード係数"] >= MIN_SCORE].copy()
            filtered.insert(0, "解析区分", source_name)
            frames.append(filtered.head(TOP_N_PER_SOURCE))

        result = pd.concat(frames, ignore_index=True)
        result = result.sort_values(
            ["ジャッカード係数", "共通出現事例数"],
            ascending=[False, False],
        ).reset_index(drop=True)

        result.insert(0, "総合順位", range(1, len(result) + 1))

        dental = result[result["解析区分"].str.startswith("歯牙障害")].copy()
        dental = dental.reset_index(drop=True)
        dental["歯牙障害内順位"] = range(1, len(dental) + 1)

        save_csv(result, OUT_TOP)
        save_csv(dental, OUT_DENTAL)

        elapsed = time.perf_counter() - start
        save_summary([
            ("Jaccard掲載候補数", len(result)),
            ("歯牙障害掲載候補数", len(dental)),
            ("最低Jaccard", MIN_SCORE),
            ("各入力上位件数", TOP_N_PER_SOURCE),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step5-4_事故パターン分析.py"),
        ], OUT_SUMMARY)

        print(dental.head(30).to_string(index=False))
        print("\nStep5-3 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
