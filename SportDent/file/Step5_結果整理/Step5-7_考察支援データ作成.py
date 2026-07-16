#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step5-7_考察支援データ作成

結果を考察へつなげるための観察事項と確認項目をCSV化する。
LLMへ渡す前の根拠データとして使用する。
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


IN_WORD = TABLE_DIR / "Table4_歯牙障害特徴語ランキング.csv"
IN_CATEGORY = TABLE_DIR / "Table5_歯牙障害特徴カテゴリランキング.csv"
IN_JACCARD = TABLE_DIR / "Table7_歯牙障害_Jaccard上位ペア.csv"
IN_PATTERN = TABLE_DIR / "Table8_歯牙障害_事故パターンランキング.csv"

OUT_SUPPORT = SUPPORT_DIR / "Step5-7_考察支援データ.csv"
OUT_LLM = SUPPORT_DIR / "Step5-7_LLM入力用結果要約.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step5-7_解析サマリー.csv"

TOP_N = 20


def main() -> None:
    start = time.perf_counter()
    try:
        word = read_csv(IN_WORD).head(TOP_N)
        category = read_csv(IN_CATEGORY).head(TOP_N)
        jaccard_df = read_csv(IN_JACCARD).head(TOP_N)
        pattern = read_csv(IN_PATTERN).head(TOP_N)

        rows = []

        for _, row in word.iterrows():
            rows.append({
                "根拠区分": "特徴語",
                "順位": row.get("総合順位", ""),
                "観察事項": (
                    f"「{row['基本形']}」は歯牙障害で"
                    f"Allより{row['出現率差_歯牙障害-All']}ポイント高い。"
                ),
                "数値根拠": (
                    f"歯牙障害={row['歯牙障害事例出現率(%)']}%, "
                    f"All={row['All事例出現率(%)']}%"
                ),
                "考察時の確認項目": "事故場面・受傷機転・記載方法による影響を確認する。",
            })

        for _, row in category.iterrows():
            rows.append({
                "根拠区分": "特徴カテゴリ",
                "順位": row.get("総合順位", ""),
                "観察事項": (
                    f"カテゴリ「{row['カテゴリ']}:{row['サブカテゴリ']}」は"
                    f"歯牙障害で相対的に多い。"
                ),
                "数値根拠": (
                    f"歯牙障害={row['歯牙障害事例出現率(%)']}%, "
                    f"All={row['All事例出現率(%)']}%"
                ),
                "考察時の確認項目": "辞書分類精度と未分類語の影響を確認する。",
            })

        for _, row in jaccard_df.iterrows():
            rows.append({
                "根拠区分": "Jaccard",
                "順位": row.get("歯牙障害内順位", ""),
                "観察事項": (
                    f"「{row['特徴1']}」と「{row['特徴2']}」は"
                    f"同一事例に共存しやすい。"
                ),
                "数値根拠": f"Jaccard={row['ジャッカード係数']}",
                "考察時の確認項目": "共起は因果関係を意味しない点に注意する。",
            })

        for _, row in pattern.iterrows():
            rows.append({
                "根拠区分": "事故パターン",
                "順位": row["順位"],
                "観察事項": f"事故パターン「{row['事故パターン']}」が確認された。",
                "数値根拠": f"件数={row['件数']}, 割合={row['事例割合(%)']}%",
                "考察時の確認項目": "構成要素の順序は時系列を示さない点に注意する。",
            })

        support = pd.DataFrame(rows)
        save_csv(support, OUT_SUPPORT)

        llm_rows = [
            ("特徴語上位", " | ".join(word["基本形"].astype(str).head(10))),
            (
                "特徴カテゴリ上位",
                " | ".join(
                    (
                        category["カテゴリ"].astype(str)
                        + ":"
                        + category["サブカテゴリ"].astype(str)
                    ).head(10)
                ),
            ),
            (
                "Jaccard上位",
                " | ".join(
                    (
                        jaccard_df["特徴1"].astype(str)
                        + "×"
                        + jaccard_df["特徴2"].astype(str)
                        + "="
                        + jaccard_df["ジャッカード係数"].astype(str)
                    ).head(10)
                ),
            ),
            (
                "事故パターン上位",
                " | ".join(pattern["事故パターン"].astype(str).head(10)),
            ),
            (
                "解釈上の注意",
                "共起・Jaccardは因果関係を示さず、辞書分類と自由記述の品質に依存する。",
            ),
        ]

        llm = pd.DataFrame(llm_rows, columns=["項目", "内容"])
        save_csv(llm, OUT_LLM)

        elapsed = time.perf_counter() - start
        save_summary([
            ("考察支援行数", len(support)),
            ("LLM入力項目数", len(llm)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("Step5", "完了"),
        ], OUT_SUMMARY)

        print(support.head(30).to_string(index=False))
        print("\nStep5 完了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
