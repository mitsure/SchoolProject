#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-3_All_頻出語集計

【目的】
Step3-1で作成した形態素解析結果を使用し、
名詞・動詞・形容詞の基本形について頻出語を集計する。

【配置】
Meikai/file/Step3_All/Step3-3_All_頻出語集計.py

【入力】
Meikai/CreateData/Step3_All/Step3-1_All_形態素解析.csv

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-3_All_頻出語集計.csv
├─ Step3-3_All_品詞別頻出語上位.csv
└─ Step3-3_All_解析サマリー.csv

【解析方法】
記述統計
- 基本形による語の統合
- 出現回数
- 出現事例数
- 事例出現率
- 全体順位
- 品詞別順位

【ジャッカード係数】
使用しない。

【Common】
file/Common/Utils/output.py
file/Common/Utils/validation.py

【実行】
python file/Step3_All/Step3-3_All_頻出語集計.py

【次のStep】
Step3-4_All_共起語解析.py
==============================================================================
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


INPUT_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-1_All_形態素解析.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_All"
OUTPUT_FREQUENCY_CSV = OUTPUT_DIR / "Step3-3_All_頻出語集計.csv"
OUTPUT_TOP_CSV = OUTPUT_DIR / "Step3-3_All_品詞別頻出語上位.csv"
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / "Step3-3_All_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}
TOP_N_PER_POS = 100

REQUIRED_COLUMNS = [
    "記号",
    "基本形",
    "品詞",
    "品詞細分類1",
]


def load_morpheme_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"入力CSVが見つかりません：{path}\n"
            "先にStep3-1_All_形態素解析.pyを実行してください。"
        )

    dataframe = pd.read_csv(path, encoding="utf-8-sig")
    require_columns(dataframe, REQUIRED_COLUMNS)

    if dataframe.empty:
        raise ValueError("形態素解析CSVが0件です。")

    return dataframe


def normalize_word(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text or text == "*":
        return ""

    return text


def prepare_target_words(dataframe: pd.DataFrame) -> pd.DataFrame:
    work = dataframe.copy()

    work["基本形"] = work["基本形"].map(normalize_word)
    work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()
    work["品詞細分類1"] = (
        work["品詞細分類1"]
        .fillna("未設定")
        .astype(str)
        .str.strip()
        .replace("", "未設定")
    )

    work = work[
        work["品詞"].isin(TARGET_POS)
        & work["基本形"].ne("")
    ].copy()

    if work.empty:
        raise ValueError("名詞・動詞・形容詞に該当する語がありません。")

    return work


def create_frequency_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    total_cases = int(dataframe["記号"].nunique(dropna=False))

    token_counts = (
        dataframe
        .groupby(["基本形", "品詞"], dropna=False)
        .size()
        .reset_index(name="出現回数")
    )

    case_counts = (
        dataframe[["記号", "基本形", "品詞"]]
        .drop_duplicates()
        .groupby(["基本形", "品詞"], dropna=False)
        .size()
        .reset_index(name="出現事例数")
    )

    result = token_counts.merge(
        case_counts,
        on=["基本形", "品詞"],
        how="inner",
    )

    result["事例出現率（％）"] = (
        result["出現事例数"] / total_cases * 100
    ).round(4)

    result["1事例当たり平均出現回数"] = (
        result["出現回数"] / result["出現事例数"]
    ).round(4)

    result = result.sort_values(
        by=["出現事例数", "出現回数", "基本形"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    result.insert(0, "全体順位", range(1, len(result) + 1))

    result["品詞別順位"] = (
        result
        .groupby("品詞")["出現事例数"]
        .rank(method="min", ascending=False)
        .astype(int)
    )

    result["対象事例数"] = total_cases

    return result[
        [
            "全体順位",
            "品詞",
            "品詞別順位",
            "基本形",
            "出現回数",
            "出現事例数",
            "事例出現率（％）",
            "1事例当たり平均出現回数",
            "対象事例数",
        ]
    ]


def create_top_words_by_pos(
    frequency_summary: pd.DataFrame,
) -> pd.DataFrame:
    return (
        frequency_summary
        .sort_values(
            by=[
                "品詞",
                "品詞別順位",
                "出現事例数",
                "出現回数",
                "基本形",
            ],
            ascending=[True, True, False, False, True],
        )
        .groupby("品詞", group_keys=False)
        .head(TOP_N_PER_POS)
        .reset_index(drop=True)
    )


def create_analysis_summary(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    frequency_summary: pd.DataFrame,
    elapsed_seconds: float,
) -> pd.DataFrame:
    def unique_word_count(pos_name: str) -> int:
        return int(
            frequency_summary.loc[
                frequency_summary["品詞"] == pos_name,
                "基本形",
            ].nunique()
        )

    def token_count(pos_name: str) -> int:
        return int((target_df["品詞"] == pos_name).sum())

    summary_rows = [
        ("入力ファイル", str(INPUT_CSV)),
        ("入力形態素数", len(source_df)),
        ("入力事例数", int(source_df["記号"].nunique(dropna=False))),
        ("集計対象形態素数", len(target_df)),
        ("集計対象事例数", int(target_df["記号"].nunique(dropna=False))),
        ("集計対象品詞", "名詞・動詞・形容詞"),
        ("異なり語数", len(frequency_summary)),
        ("名詞異なり語数", unique_word_count("名詞")),
        ("動詞異なり語数", unique_word_count("動詞")),
        ("形容詞異なり語数", unique_word_count("形容詞")),
        ("名詞出現回数", token_count("名詞")),
        ("動詞出現回数", token_count("動詞")),
        ("形容詞出現回数", token_count("形容詞")),
        (
            "対象形態素割合（％）",
            round(len(target_df) / len(source_df) * 100, 4),
        ),
        ("品詞別上位抽出数", TOP_N_PER_POS),
        ("処理時間（秒）", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        ("次のStep", "Step3-4_All_共起語解析.py"),
    ]

    return pd.DataFrame(summary_rows, columns=["項目", "値"])


def print_top_words(
    frequency_summary: pd.DataFrame,
    top_n: int = 20,
) -> None:
    for pos_name in ("名詞", "動詞", "形容詞"):
        print(f"\n【{pos_name}：上位{top_n}語】")

        subset = (
            frequency_summary[
                frequency_summary["品詞"] == pos_name
            ]
            .sort_values(
                by=["品詞別順位", "出現事例数", "出現回数"],
                ascending=[True, False, False],
            )
            .head(top_n)
        )

        if subset.empty:
            print("該当語はありません。")
            continue

        print(
            subset[
                [
                    "品詞別順位",
                    "基本形",
                    "出現回数",
                    "出現事例数",
                    "事例出現率（％）",
                    "1事例当たり平均出現回数",
                ]
            ].to_string(
                index=False,
                formatters={
                    "出現回数": lambda value: f"{int(value):,}",
                    "出現事例数": lambda value: f"{int(value):,}",
                    "事例出現率（％）": lambda value: f"{float(value):.4f}",
                    "1事例当たり平均出現回数": (
                        lambda value: f"{float(value):.4f}"
                    ),
                },
            )
        )


def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-3_All_頻出語集計を開始します")
    print("解析対象　　　：名詞・動詞・形容詞")
    print("解析方法　　　：頻度・出現事例数集計")
    print("ジャッカード　：使用しない")
    print("=" * 78)

    try:
        source_df = load_morpheme_csv(INPUT_CSV)
        target_df = prepare_target_words(source_df)

        frequency_summary = create_frequency_summary(target_df)
        top_words_by_pos = create_top_words_by_pos(frequency_summary)

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            source_df,
            target_df,
            frequency_summary,
            elapsed_seconds,
        )

        save_csv(frequency_summary, OUTPUT_FREQUENCY_CSV)
        save_csv(top_words_by_pos, OUTPUT_TOP_CSV)
        save_csv(analysis_summary, OUTPUT_SUMMARY_CSV)

        print_top_words(frequency_summary, top_n=20)

        print("\n【整合性確認】")
        print(f"入力形態素数　　　　：{len(source_df):,}件")
        print(f"集計対象形態素数　　：{len(target_df):,}件")
        print(
            f"出現回数合計　　　　："
            f"{int(frequency_summary['出現回数'].sum()):,}件"
        )
        print(
            f"入力事例数　　　　　："
            f"{source_df['記号'].nunique(dropna=False):,}件"
        )
        print(
            f"集計対象事例数　　　："
            f"{target_df['記号'].nunique(dropna=False):,}件"
        )

        print("\n" + "━" * 78)
        print("Step3-3_All_頻出語集計　正常終了")
        print("━" * 78)
        print(f"入力形態素数　　　　：{len(source_df):,}件")
        print(f"集計対象形態素数　　：{len(target_df):,}件")
        print(f"異なり語数　　　　　：{len(frequency_summary):,}語")
        print(f"品詞別上位語出力行数：{len(top_words_by_pos):,}行")
        print(f"処理時間　　　　　　：{elapsed_seconds:.2f}秒")
        print()
        print(f"頻出語集計CSV　　　　：{OUTPUT_FREQUENCY_CSV}")
        print(f"品詞別上位語CSV　　　：{OUTPUT_TOP_CSV}")
        print(f"解析サマリーCSV　　　：{OUTPUT_SUMMARY_CSV}")
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep：Step3-4_All_共起語解析.py")
        print("━" * 78)

    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(1)

    except Exception as error:
        print("\n【処理中にエラーが発生しました】")
        print(f"{type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
