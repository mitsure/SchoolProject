#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-5_論文掲載表作成

Table1からTable9を論文掲載用に上位行へ整理し、
一覧表とTable目録を作成する。
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


TABLE_CONFIG = [
    ("Table1", "All vs 歯牙障害 頻出語比較", "Table1_All_vs歯牙障害_頻出語比較.csv", 30),
    ("Table2", "All vs 歯牙障害 特徴語比較", "Table2_All_vs歯牙障害_特徴語比較.csv", 30),
    ("Table3", "All vs 歯牙障害 カテゴリ比較", "Table3_All_vs歯牙障害_カテゴリ比較.csv", 30),
    ("Table4", "歯牙障害 特徴語ランキング", "Table4_歯牙障害特徴語ランキング.csv", 30),
    ("Table5", "歯牙障害 特徴カテゴリランキング", "Table5_歯牙障害特徴カテゴリランキング.csv", 30),
    ("Table6", "Jaccard上位ペア", "Table6_Jaccard上位ペア.csv", 30),
    ("Table7", "歯牙障害 Jaccard上位ペア", "Table7_歯牙障害_Jaccard上位ペア.csv", 30),
    ("Table8", "歯牙障害 事故パターンランキング", "Table8_歯牙障害_事故パターンランキング.csv", 20),
    ("Table9", "歯牙障害 パターン構成要素", "Table9_歯牙障害_パターン構成要素.csv", 20),
]

OUT_INDEX = TABLE_DIR / "Table一覧.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-5_解析サマリー.csv"


def main() -> None:
    start = time.perf_counter()
    try:
        index_rows = []

        for table_no, title, filename, top_n in TABLE_CONFIG:
            source = TABLE_DIR / filename
            df = read_csv(source)
            output = TABLE_DIR / f"論文用_{filename}"

            paper_df = df.head(top_n).copy()
            save_csv(paper_df, output)

            index_rows.append({
                "Table番号": table_no,
                "表題": title,
                "元ファイル": filename,
                "論文用ファイル": output.name,
                "掲載行数": len(paper_df),
            })

        index_df = pd.DataFrame(index_rows)
        save_csv(index_df, OUT_INDEX)

        elapsed = time.perf_counter() - start
        save_summary([
            ("作成Table数", len(index_df)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step5-6_論文掲載グラフ作成.py"),
        ], OUT_SUMMARY)

        print(index_df.to_string(index=False))
        print("\nStep5-5 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
