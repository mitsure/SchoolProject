#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3-4_歯牙障害_共起語解析

同一事例内の語ペアを集計する。
ジャッカード係数はまだ使用しない。
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

from collections import Counter
from itertools import combinations

INPUT_CSV = OUTPUT_DIR / "Step3-1_歯牙障害_形態素解析.csv"
OUTPUT_ALL = OUTPUT_DIR / "Step3-4_歯牙障害_共起語解析.csv"
OUTPUT_TOP = OUTPUT_DIR / "Step3-4_歯牙障害_共起語上位.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step3-4_歯牙障害_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}
MIN_CASES = 3
TOP_N = 500

def main():
    start = time.perf_counter()
    print("=" * 78)
    print("Step3-4_歯牙障害_共起語解析")
    print("ジャッカード係数: 使用しない")
    print("=" * 78)

    try:
        if not INPUT_CSV.exists():
            raise FileNotFoundError(f"入力CSVがありません: {INPUT_CSV}")

        df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
        require_columns(df, ["記号", "種別", "基本形", "品詞"])

        if (df["種別"].fillna("").astype(str).str.strip() != "歯牙障害").any():
            raise ValueError("歯牙障害以外が含まれています。")

        work = df.copy()
        work["基本形"] = work["基本形"].fillna("").astype(str).str.strip()
        work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()
        work = work[
            work["品詞"].isin(TARGET_POS)
            & work["基本形"].ne("")
            & work["基本形"].ne("*")
        ].copy()

        word_case_counts = (
            work[["記号", "基本形", "品詞"]]
            .drop_duplicates()
            .groupby(["基本形", "品詞"])
            .size()
            .to_dict()
        )

        counter = Counter()

        for _, group in work.groupby("記号", dropna=False):
            words = sorted({
                (str(row["基本形"]), str(row["品詞"]))
                for _, row in group.iterrows()
            })
            for a, b in combinations(words, 2):
                counter[(a, b)] += 1

        total_cases = work["記号"].nunique(dropna=False)
        rows = []

        for (a, b), count in counter.items():
            if count < MIN_CASES:
                continue

            rows.append({
                "語1": a[0],
                "語1品詞": a[1],
                "語2": b[0],
                "語2品詞": b[1],
                "共起事例数": count,
                "共起事例率(%)": round(count / total_cases * 100, 4),
                "語1出現事例数": int(word_case_counts.get(a, 0)),
                "語2出現事例数": int(word_case_counts.get(b, 0)),
                "対象事例数": total_cases,
            })

        result = pd.DataFrame(rows)

        if result.empty:
            result = pd.DataFrame(columns=[
                "全体順位", "語1", "語1品詞", "語2", "語2品詞",
                "共起事例数", "共起事例率(%)",
                "語1出現事例数", "語2出現事例数", "対象事例数"
            ])
        else:
            result = result.sort_values(
                ["共起事例数", "語1", "語2"],
                ascending=[False, True, True]
            ).reset_index(drop=True)
            result.insert(0, "全体順位", range(1, len(result) + 1))

        top = result.head(TOP_N).copy()
        elapsed = time.perf_counter() - start

        summary = pd.DataFrame([
            ("解析対象", "歯牙障害"),
            ("入力形態素数", len(df)),
            ("対象形態素数", len(work)),
            ("対象事例数", total_cases),
            ("最小共起事例数", MIN_CASES),
            ("出力共起組数", len(result)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("ジャッカード係数", "使用しない"),
            ("次のStep", "Step3-5_歯牙障害_ストップワード除去.py"),
        ], columns=["項目", "値"])

        save_csv(result, OUTPUT_ALL)
        save_csv(top, OUTPUT_TOP)
        save_csv(summary, OUTPUT_SUMMARY)

        print(result.head(30).to_string(index=False))
        print("\n正常終了")
        print(f"次: Step3-5_歯牙障害_ストップワード除去.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
