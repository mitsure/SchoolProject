#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-4_事故パターン分析

歯牙障害の事例別カテゴリ特徴集合から事故パターンを集計する。
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


INPUT_CASE = (
    PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"
    / "Step3-7_歯牙障害_事例別特徴データ.csv"
)

OUT_PATTERN = TABLE_DIR / "Table8_歯牙障害_事故パターンランキング.csv"
OUT_COMPONENT = TABLE_DIR / "Table9_歯牙障害_パターン構成要素.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-4_解析サマリー.csv"

MIN_COMPONENTS = 2
TOP_N = 100


def parse_pipe(value: object) -> list[str]:
    if pd.isna(value):
        return []
    return [x.strip() for x in str(value).split("|") if x.strip()]


def main() -> None:
    start = time.perf_counter()
    try:
        df = read_csv(INPUT_CASE)
        require_columns(df, ["記号", "カテゴリ特徴集合"])

        rows = []
        component_rows = []

        for _, row in df.iterrows():
            features = parse_pipe(row["カテゴリ特徴集合"])
            features = sorted(set(features))

            if len(features) < MIN_COMPONENTS:
                continue

            pattern = " -> ".join(features)

            rows.append({
                "記号": row["記号"],
                "事故パターン": pattern,
                "構成要素数": len(features),
            })

            for feature in features:
                if ":" in feature:
                    category, subcategory = feature.split(":", 1)
                else:
                    category, subcategory = feature, ""
                component_rows.append({
                    "記号": row["記号"],
                    "カテゴリ": category,
                    "サブカテゴリ": subcategory,
                    "特徴": feature,
                })

        pattern_cases = pd.DataFrame(rows)
        components = pd.DataFrame(component_rows)

        if pattern_cases.empty:
            pattern_result = pd.DataFrame(columns=[
                "順位", "事故パターン", "構成要素数", "件数", "事例割合(%)"
            ])
        else:
            pattern_result = (
                pattern_cases.groupby(["事故パターン", "構成要素数"])
                .size()
                .reset_index(name="件数")
            )
            pattern_result["事例割合(%)"] = (
                pattern_result["件数"] / len(df) * 100
            ).round(4)
            pattern_result = pattern_result.sort_values(
                ["件数", "構成要素数"],
                ascending=[False, False],
            ).head(TOP_N).reset_index(drop=True)
            pattern_result.insert(0, "順位", range(1, len(pattern_result) + 1))

        if components.empty:
            component_result = pd.DataFrame(columns=[
                "順位", "カテゴリ", "サブカテゴリ", "特徴", "出現事例数", "事例出現率(%)"
            ])
        else:
            component_result = (
                components.drop_duplicates(["記号", "特徴"])
                .groupby(["カテゴリ", "サブカテゴリ", "特徴"])
                .size()
                .reset_index(name="出現事例数")
            )
            component_result["事例出現率(%)"] = (
                component_result["出現事例数"] / len(df) * 100
            ).round(4)
            component_result = component_result.sort_values(
                "出現事例数", ascending=False
            ).reset_index(drop=True)
            component_result.insert(0, "順位", range(1, len(component_result) + 1))

        save_csv(pattern_result, OUT_PATTERN)
        save_csv(component_result, OUT_COMPONENT)

        elapsed = time.perf_counter() - start
        save_summary([
            ("歯牙障害事例数", len(df)),
            ("パターン化対象事例数", len(pattern_cases)),
            ("異なり事故パターン数", len(pattern_result)),
            ("最低構成要素数", MIN_COMPONENTS),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step5-5_論文掲載表作成.py"),
        ], OUT_SUMMARY)

        print(pattern_result.head(30).to_string(index=False))
        print("\nStep5-4 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
