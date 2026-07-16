#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-1_全体比較集計

Allと歯牙障害の頻出語、特徴語、カテゴリ出現率を比較する。

出力:
Table1_All_vs歯牙障害_頻出語比較.csv
Table2_All_vs歯牙障害_特徴語比較.csv
Table3_All_vs歯牙障害_カテゴリ比較.csv
Step5-1_解析サマリー.csv

ジャッカード係数:
このStepでは新規計算しない。
Step4の結果は後続Stepで整理する。
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


ALL_FREQ = PROJECT_ROOT / "CreateData" / "Step3_All" / "Step3-3_All_頻出語集計.csv"
DENTAL_FREQ = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害" / "Step3-3_歯牙障害_頻出語集計.csv"

ALL_FEATURE = PROJECT_ROOT / "CreateData" / "Step3_All" / "Step3-7_All_全体特徴語.csv"
DENTAL_FEATURE = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害" / "Step3-7_歯牙障害_特徴語.csv"

ALL_CATEGORY = PROJECT_ROOT / "CreateData" / "Step3_All" / "Step3-6_All_カテゴリ集計.csv"
DENTAL_CATEGORY = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害" / "Step3-6_歯牙障害_カテゴリ集計.csv"

OUT_FREQ = TABLE_DIR / "Table1_All_vs歯牙障害_頻出語比較.csv"
OUT_FEATURE = TABLE_DIR / "Table2_All_vs歯牙障害_特徴語比較.csv"
OUT_CATEGORY = TABLE_DIR / "Table3_All_vs歯牙障害_カテゴリ比較.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-1_解析サマリー.csv"


def compare_frequency(all_df: pd.DataFrame, dental_df: pd.DataFrame) -> pd.DataFrame:
    require_columns(all_df, ["品詞", "基本形", "出現回数", "出現事例数", "事例出現率（％）"])
    # 歯牙障害版は半角括弧の列名
    dental_rate_col = "事例出現率(%)" if "事例出現率(%)" in dental_df.columns else "事例出現率（％）"
    require_columns(dental_df, ["品詞", "基本形", "出現回数", "出現事例数", dental_rate_col])

    all_part = all_df[
        ["品詞", "基本形", "出現回数", "出現事例数", "事例出現率（％）"]
    ].rename(columns={
        "出現回数": "All出現回数",
        "出現事例数": "All出現事例数",
        "事例出現率（％）": "All事例出現率(%)",
    })

    dental_part = dental_df[
        ["品詞", "基本形", "出現回数", "出現事例数", dental_rate_col]
    ].rename(columns={
        "出現回数": "歯牙障害出現回数",
        "出現事例数": "歯牙障害出現事例数",
        dental_rate_col: "歯牙障害事例出現率(%)",
    })

    result = all_part.merge(
        dental_part,
        on=["品詞", "基本形"],
        how="outer",
    ).fillna(0)

    result["出現率差_歯牙障害-All"] = (
        result["歯牙障害事例出現率(%)"] - result["All事例出現率(%)"]
    ).round(4)

    result["出現率倍率_歯牙障害_All"] = result.apply(
        lambda row: round(
            safe_ratio(
                row["歯牙障害事例出現率(%)"],
                row["All事例出現率(%)"],
            ),
            4,
        ),
        axis=1,
    )

    result = result.sort_values(
        ["出現率差_歯牙障害-All", "歯牙障害事例出現率(%)"],
        ascending=[False, False],
    ).reset_index(drop=True)

    result.insert(0, "歯牙障害特徴順位", range(1, len(result) + 1))
    return result


def compare_features(all_df: pd.DataFrame, dental_df: pd.DataFrame) -> pd.DataFrame:
    require_columns(all_df, ["特徴語", "平均TF-IDF", "出現事例数"])
    require_columns(dental_df, ["特徴語", "平均TF-IDF", "出現事例数"])

    all_part = all_df[["特徴語", "平均TF-IDF", "出現事例数"]].rename(
        columns={
            "平均TF-IDF": "All平均TF-IDF",
            "出現事例数": "All出現事例数",
        }
    )

    dental_part = dental_df[["特徴語", "平均TF-IDF", "出現事例数"]].rename(
        columns={
            "平均TF-IDF": "歯牙障害平均TF-IDF",
            "出現事例数": "歯牙障害出現事例数",
        }
    )

    result = all_part.merge(dental_part, on="特徴語", how="outer").fillna(0)
    result["TF-IDF差_歯牙障害-All"] = (
        result["歯牙障害平均TF-IDF"] - result["All平均TF-IDF"]
    ).round(8)

    result = result.sort_values(
        ["TF-IDF差_歯牙障害-All", "歯牙障害平均TF-IDF"],
        ascending=[False, False],
    ).reset_index(drop=True)

    result.insert(0, "歯牙障害特徴順位", range(1, len(result) + 1))
    return result


def compare_categories(all_df: pd.DataFrame, dental_df: pd.DataFrame) -> pd.DataFrame:
    all_rate_col = "事例出現率(%)" if "事例出現率(%)" in all_df.columns else "事例出現率（％）"
    dental_rate_col = "事例出現率(%)" if "事例出現率(%)" in dental_df.columns else "事例出現率（％）"

    require_columns(all_df, ["カテゴリ", "サブカテゴリ", "出現事例数", all_rate_col])
    require_columns(dental_df, ["カテゴリ", "サブカテゴリ", "出現事例数", dental_rate_col])

    a = all_df[["カテゴリ", "サブカテゴリ", "出現事例数", all_rate_col]].rename(
        columns={
            "出現事例数": "All出現事例数",
            all_rate_col: "All事例出現率(%)",
        }
    )
    d = dental_df[["カテゴリ", "サブカテゴリ", "出現事例数", dental_rate_col]].rename(
        columns={
            "出現事例数": "歯牙障害出現事例数",
            dental_rate_col: "歯牙障害事例出現率(%)",
        }
    )

    result = a.merge(d, on=["カテゴリ", "サブカテゴリ"], how="outer").fillna(0)
    result["出現率差_歯牙障害-All"] = (
        result["歯牙障害事例出現率(%)"] - result["All事例出現率(%)"]
    ).round(4)

    result["出現率倍率_歯牙障害_All"] = result.apply(
        lambda row: round(
            safe_ratio(
                row["歯牙障害事例出現率(%)"],
                row["All事例出現率(%)"],
            ),
            4,
        ),
        axis=1,
    )

    result = result.sort_values(
        ["出現率差_歯牙障害-All", "歯牙障害事例出現率(%)"],
        ascending=[False, False],
    ).reset_index(drop=True)

    result.insert(0, "歯牙障害特徴順位", range(1, len(result) + 1))
    return result


def main() -> None:
    start = time.perf_counter()
    try:
        freq = compare_frequency(read_csv(ALL_FREQ), read_csv(DENTAL_FREQ))
        feature = compare_features(read_csv(ALL_FEATURE), read_csv(DENTAL_FEATURE))
        category = compare_categories(read_csv(ALL_CATEGORY), read_csv(DENTAL_CATEGORY))

        save_csv(freq, OUT_FREQ)
        save_csv(feature, OUT_FEATURE)
        save_csv(category, OUT_CATEGORY)

        elapsed = time.perf_counter() - start
        save_summary([
            ("頻出語比較行数", len(freq)),
            ("特徴語比較行数", len(feature)),
            ("カテゴリ比較行数", len(category)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step5-2_歯牙障害特徴ランキング.py"),
        ], OUT_SUMMARY)

        print(freq.head(30).to_string(index=False))
        print("\nStep5-1 正常終了")
        print("次: Step5-2_歯牙障害特徴ランキング.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
