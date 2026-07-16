#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3-3_歯牙障害_頻出語集計

入力:
CreateData/Step3_歯牙障害/Step3-1_歯牙障害_形態素解析.csv

出力:
Step3-3_歯牙障害_頻出語集計.csv
Step3-3_歯牙障害_品詞別頻出語上位.csv
Step3-3_歯牙障害_解析サマリー.csv

ジャッカード係数:
使用しない。
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"

INPUT_CSV = OUTPUT_DIR / "Step3-1_歯牙障害_形態素解析.csv"
OUTPUT_FREQ = OUTPUT_DIR / "Step3-3_歯牙障害_頻出語集計.csv"
OUTPUT_TOP = OUTPUT_DIR / "Step3-3_歯牙障害_品詞別頻出語上位.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step3-3_歯牙障害_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}
TOP_N = 100

def load_input():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"入力CSVがありません: {INPUT_CSV}")
    df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
    require_columns(df, ["記号", "種別", "基本形", "品詞"])
    if df.empty:
        raise ValueError("入力CSVが0件です。")
    return df

def main():
    start = time.perf_counter()
    print("=" * 78)
    print("Step3-3_歯牙障害_頻出語集計")
    print("ジャッカード係数: 使用しない")
    print("=" * 78)

    try:
        df = load_input()

        injury = df["種別"].fillna("").astype(str).str.strip()
        if (injury != "歯牙障害").any():
            raise ValueError("入力CSVに歯牙障害以外が含まれています。")

        work = df.copy()
        work["基本形"] = work["基本形"].fillna("").astype(str).str.strip()
        work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()
        work = work[
            work["品詞"].isin(TARGET_POS)
            & work["基本形"].ne("")
            & work["基本形"].ne("*")
        ].copy()

        token_counts = (
            work.groupby(["基本形", "品詞"])
            .size()
            .reset_index(name="出現回数")
        )

        case_counts = (
            work[["記号", "基本形", "品詞"]]
            .drop_duplicates()
            .groupby(["基本形", "品詞"])
            .size()
            .reset_index(name="出現事例数")
        )

        result = token_counts.merge(case_counts, on=["基本形", "品詞"])
        total_cases = work["記号"].nunique(dropna=False)

        result["事例出現率(%)"] = (
            result["出現事例数"] / total_cases * 100
        ).round(4)

        result["1事例当たり平均出現回数"] = (
            result["出現回数"] / result["出現事例数"]
        ).round(4)

        result = result.sort_values(
            ["出現事例数", "出現回数", "基本形"],
            ascending=[False, False, True]
        ).reset_index(drop=True)

        result.insert(0, "全体順位", range(1, len(result) + 1))
        result["品詞別順位"] = (
            result.groupby("品詞")["出現事例数"]
            .rank(method="min", ascending=False)
            .astype(int)
        )
        result["対象事例数"] = total_cases

        result = result[
            [
                "全体順位", "品詞", "品詞別順位", "基本形",
                "出現回数", "出現事例数", "事例出現率(%)",
                "1事例当たり平均出現回数", "対象事例数"
            ]
        ]

        top = (
            result.sort_values(
                ["品詞", "品詞別順位", "出現事例数", "出現回数"],
                ascending=[True, True, False, False]
            )
            .groupby("品詞", group_keys=False)
            .head(TOP_N)
            .reset_index(drop=True)
        )

        elapsed = time.perf_counter() - start

        summary = pd.DataFrame([
            ("解析対象", "歯牙障害"),
            ("入力形態素数", len(df)),
            ("集計対象形態素数", len(work)),
            ("対象事例数", total_cases),
            ("異なり語数", len(result)),
            ("品詞別上位抽出数", TOP_N),
            ("処理時間(秒)", round(elapsed, 3)),
            ("ジャッカード係数", "使用しない"),
            ("次のStep", "Step3-4_歯牙障害_共起語解析.py"),
        ], columns=["項目", "値"])

        save_csv(result, OUTPUT_FREQ)
        save_csv(top, OUTPUT_TOP)
        save_csv(summary, OUTPUT_SUMMARY)

        for pos in ("名詞", "動詞", "形容詞"):
            print(f"\n[{pos}: 上位20語]")
            print(
                result[result["品詞"] == pos]
                .head(20)
                .to_string(index=False)
            )

        print("\n正常終了")
        print(f"出力: {OUTPUT_FREQ}")
        print(f"次: Step3-4_歯牙障害_共起語解析.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
