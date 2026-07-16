#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-4_All_共起語解析

【目的】
Step3-1で作成した形態素解析結果を使用し、
同じ事故事例内に同時出現した語の組合せを集計する。

【配置】
Meikai/file/Step3_All/
└─ Step3-4_All_共起語解析.py

【入力】
Meikai/CreateData/Step3_All/
└─ Step3-1_All_形態素解析.csv

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-4_All_共起語解析.csv
├─ Step3-4_All_共起語上位.csv
└─ Step3-4_All_解析サマリー.csv

【出力内容】

1. Step3-4_All_共起語解析.csv
   - 全体順位
   - 語1
   - 語2
   - 語1の品詞
   - 語2の品詞
   - 共起事例数
   - 共起事例率
   - 語1出現事例数
   - 語2出現事例数

2. Step3-4_All_共起語上位.csv
   共起事例数の上位500組を出力する。

3. Step3-4_All_解析サマリー.csv
   対象事例数、対象語数、共起組数等を出力する。

【解析方法】
共起分析
- 1事例内で同時出現した語の組合せを作成
- 同一事例内の重複語は1回として扱う
- 共起事例数を集計
- 共起事例率を計算

【ジャッカード係数】
使用しない。

【理由】
本Stepでは共起件数のみを作成し、
ジャッカード係数はStep4で計算するため。

【Common】
file/Common/Utils/output.py
file/Common/Utils/validation.py

【必要ライブラリ】
python -m pip install pandas

【上書き】
同名CSVがある場合は上書きする。

【実行】
python file/Step3_All/Step3-4_All_共起語解析.py

【次のStep】
Step3-5_All_ストップワード除去.py
==============================================================================
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
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
OUTPUT_COOCCURRENCE_CSV = OUTPUT_DIR / "Step3-4_All_共起語解析.csv"
OUTPUT_TOP_CSV = OUTPUT_DIR / "Step3-4_All_共起語上位.csv"
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / "Step3-4_All_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}

# 共起事例数がこの値未満の組合せは除外する
MIN_COOCCURRENCE_CASES = 5

# 上位出力件数
TOP_N = 500

REQUIRED_COLUMNS = [
    "記号",
    "基本形",
    "品詞",
]


def load_morpheme_csv(path: Path) -> pd.DataFrame:
    """Step3-1の形態素解析CSVを読み込む。"""
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
    """基本形を安全な文字列へ統一する。"""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text or text == "*":
        return ""

    return text


def prepare_target_words(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    名詞・動詞・形容詞のみを抽出し、
    共起分析用データを作成する。
    """
    work = dataframe.copy()

    work["基本形"] = work["基本形"].map(normalize_word)
    work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()

    work = work[
        work["品詞"].isin(TARGET_POS)
        & work["基本形"].ne("")
    ].copy()

    if work.empty:
        raise ValueError("共起分析対象の語がありません。")

    return work


def create_word_case_counts(
    dataframe: pd.DataFrame,
) -> dict[tuple[str, str], int]:
    """
    各語について、出現した事例数を計算する。

    キー：
    (基本形, 品詞)
    """
    unique_case_words = dataframe[
        ["記号", "基本形", "品詞"]
    ].drop_duplicates()

    counts = (
        unique_case_words
        .groupby(["基本形", "品詞"])
        .size()
    )

    return {
        (word, pos): int(count)
        for (word, pos), count in counts.items()
    }


def create_cooccurrence_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    事例内の語集合から共起ペアを作成し、
    共起事例数を集計する。
    """
    pair_counter: Counter = Counter()

    total_cases = int(
        dataframe["記号"].nunique(dropna=False)
    )

    # 事例ごとに、同じ語は1回にまとめる
    for _, group in dataframe.groupby("記号", dropna=False):
        case_words = sorted(
            {
                (str(row["基本形"]), str(row["品詞"]))
                for _, row in group.iterrows()
            }
        )

        for item_a, item_b in combinations(case_words, 2):
            pair_counter[(item_a, item_b)] += 1

    word_case_counts = create_word_case_counts(dataframe)

    rows = []

    for (item_a, item_b), co_count in pair_counter.items():
        if co_count < MIN_COOCCURRENCE_CASES:
            continue

        word_a, pos_a = item_a
        word_b, pos_b = item_b

        rows.append(
            {
                "語1": word_a,
                "語1品詞": pos_a,
                "語2": word_b,
                "語2品詞": pos_b,
                "共起事例数": int(co_count),
                "共起事例率（％）": round(
                    co_count / total_cases * 100,
                    4,
                ),
                "語1出現事例数": word_case_counts.get(item_a, 0),
                "語2出現事例数": word_case_counts.get(item_b, 0),
                "対象事例数": total_cases,
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "全体順位",
                "語1",
                "語1品詞",
                "語2",
                "語2品詞",
                "共起事例数",
                "共起事例率（％）",
                "語1出現事例数",
                "語2出現事例数",
                "対象事例数",
            ]
        )

    result = result.sort_values(
        by=[
            "共起事例数",
            "語1",
            "語2",
        ],
        ascending=[
            False,
            True,
            True,
        ],
    ).reset_index(drop=True)

    result.insert(
        0,
        "全体順位",
        range(1, len(result) + 1),
    )

    return result


def create_top_pairs(
    cooccurrence_summary: pd.DataFrame,
) -> pd.DataFrame:
    """共起事例数の上位N組を抽出する。"""
    return cooccurrence_summary.head(TOP_N).copy()


def create_analysis_summary(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    cooccurrence_summary: pd.DataFrame,
    elapsed_seconds: float,
) -> pd.DataFrame:
    """Step3-4の解析概要を作成する。"""
    summary_rows = [
        ("入力ファイル", str(INPUT_CSV)),
        ("入力形態素数", len(source_df)),
        (
            "入力事例数",
            int(source_df["記号"].nunique(dropna=False)),
        ),
        ("共起分析対象形態素数", len(target_df)),
        (
            "共起分析対象事例数",
            int(target_df["記号"].nunique(dropna=False)),
        ),
        (
            "共起分析対象異なり語数",
            int(
                target_df[
                    ["基本形", "品詞"]
                ].drop_duplicates().shape[0]
            ),
        ),
        ("最小共起事例数", MIN_COOCCURRENCE_CASES),
        ("出力共起組数", len(cooccurrence_summary)),
        ("上位出力件数", min(TOP_N, len(cooccurrence_summary))),
        ("処理時間（秒）", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        ("次のStep", "Step3-5_All_ストップワード除去.py"),
    ]

    return pd.DataFrame(summary_rows, columns=["項目", "値"])


def print_top_pairs(
    cooccurrence_summary: pd.DataFrame,
    top_n: int = 30,
) -> None:
    """上位共起語をコンソールへ表示する。"""
    print(f"\n【共起語：上位{top_n}組】")

    if cooccurrence_summary.empty:
        print("条件を満たす共起語がありません。")
        return

    print(
        cooccurrence_summary
        .head(top_n)
        [
            [
                "全体順位",
                "語1",
                "語1品詞",
                "語2",
                "語2品詞",
                "共起事例数",
                "共起事例率（％）",
            ]
        ]
        .to_string(
            index=False,
            formatters={
                "共起事例数": lambda value: f"{int(value):,}",
                "共起事例率（％）": lambda value: f"{float(value):.4f}",
            },
        )
    )


def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-4_All_共起語解析を開始します")
    print("解析対象　　　：名詞・動詞・形容詞")
    print("解析方法　　　：事例単位の共起集計")
    print("ジャッカード　：使用しない")
    print("=" * 78)

    try:
        source_df = load_morpheme_csv(INPUT_CSV)
        target_df = prepare_target_words(source_df)

        cooccurrence_summary = create_cooccurrence_summary(
            target_df,
        )

        top_pairs = create_top_pairs(
            cooccurrence_summary,
        )

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            source_df,
            target_df,
            cooccurrence_summary,
            elapsed_seconds,
        )

        save_csv(
            cooccurrence_summary,
            OUTPUT_COOCCURRENCE_CSV,
        )

        save_csv(
            top_pairs,
            OUTPUT_TOP_CSV,
        )

        save_csv(
            analysis_summary,
            OUTPUT_SUMMARY_CSV,
        )

        print_top_pairs(
            cooccurrence_summary,
            top_n=30,
        )

        print("\n【整合性確認】")
        print(f"入力形態素数　　　　：{len(source_df):,}件")
        print(f"共起分析対象形態素数：{len(target_df):,}件")
        print(
            f"共起分析対象事例数　："
            f"{target_df['記号'].nunique(dropna=False):,}件"
        )
        print(
            f"共起分析対象語数　　："
            f"{target_df[['基本形', '品詞']].drop_duplicates().shape[0]:,}語"
        )
        print(f"出力共起組数　　　　：{len(cooccurrence_summary):,}組")

        print("\n" + "━" * 78)
        print("Step3-4_All_共起語解析　正常終了")
        print("━" * 78)
        print(f"出力共起組数　　　　：{len(cooccurrence_summary):,}組")
        print(f"上位共起組出力数　　：{len(top_pairs):,}組")
        print(f"最小共起事例数　　　：{MIN_COOCCURRENCE_CASES:,}件")
        print(f"処理時間　　　　　　：{elapsed_seconds:.2f}秒")
        print()
        print(f"共起語解析CSV　　　　：{OUTPUT_COOCCURRENCE_CSV}")
        print(f"共起語上位CSV　　　　：{OUTPUT_TOP_CSV}")
        print(f"解析サマリーCSV　　　：{OUTPUT_SUMMARY_CSV}")
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep：Step3-5_All_ストップワード除去.py")
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
