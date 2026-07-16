#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-2_All_品詞集計

【目的】
Step3-1で作成した形態素解析結果を読み込み、
品詞および品詞細分類ごとの件数・割合・順位を集計する。

【Pythonファイルの配置先】
Meikai/file/Step3_All/
└─ Step3-2_All_品詞集計.py

【入力】
Meikai/CreateData/Step3_All/
└─ Step3-1_All_形態素解析.csv

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-2_All_品詞集計.csv
├─ Step3-2_All_主要品詞集計.csv
└─ Step3-2_All_解析サマリー.csv

【出力内容】

1. Step3-2_All_品詞集計.csv
   品詞と品詞細分類1の組合せごとの件数・割合・順位。

2. Step3-2_All_主要品詞集計.csv
   品詞大分類ごとの件数・割合・順位。

3. Step3-2_All_解析サマリー.csv
   入力形態素数、品詞カテゴリ数、主要品詞件数等の要約。

【解析方法】
記述統計
- 件数集計
- 割合計算
- 順位付け
- 品詞大分類・細分類の集計
- 整合性確認

【ジャッカード係数】
使用しない。

【理由】
本Stepは形態素解析結果の分布確認であり、
特徴間または事例間の類似性を評価する解析ではないため。

【Common】
以下の共通処理を利用する。
- file/Common/Utils/output.py
- file/Common/Utils/validation.py

【必要ライブラリ】
python -m pip install pandas

【上書き】
同名CSVがある場合は上書きする。

【実行例】
python file/Step3_All/Step3-2_All_品詞集計.py

【次のStep】
Step3-3_All_頻出語集計.py
==============================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd


# =============================================================================
# パス設定
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns


# =============================================================================
# 基本設定
# =============================================================================

INPUT_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-1_All_形態素解析.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_All"

OUTPUT_DETAIL_CSV = OUTPUT_DIR / "Step3-2_All_品詞集計.csv"
OUTPUT_MAIN_CSV = OUTPUT_DIR / "Step3-2_All_主要品詞集計.csv"
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / "Step3-2_All_解析サマリー.csv"

REQUIRED_COLUMNS = [
    "記号",
    "形態素番号",
    "表層形",
    "基本形",
    "品詞",
    "品詞細分類1",
]


# =============================================================================
# 入力読込
# =============================================================================

def load_morpheme_csv(path: Path) -> pd.DataFrame:
    """
    Step3-1の形態素解析CSVを読み込む。
    """
    if not path.exists():
        raise FileNotFoundError(
            f"入力CSVが見つかりません：{path}\n"
            "先にStep3-1_All_形態素解析.pyを実行してください。"
        )

    dataframe = pd.read_csv(
        path,
        encoding="utf-8-sig",
    )

    require_columns(
        dataframe,
        REQUIRED_COLUMNS,
    )

    if dataframe.empty:
        raise ValueError("形態素解析CSVが0件です。")

    return dataframe


# =============================================================================
# データ前処理
# =============================================================================

def normalize_pos_value(value: object) -> str:
    """
    品詞・品詞細分類の欠損値や空文字を「未設定」へ統一する。
    """
    if pd.isna(value):
        return "未設定"

    text = str(value).strip()

    if not text or text == "*":
        return "未設定"

    return text


def prepare_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    品詞集計に使用する列を整える。
    """
    work = dataframe.copy()

    work["品詞"] = work["品詞"].map(normalize_pos_value)
    work["品詞細分類1"] = work["品詞細分類1"].map(normalize_pos_value)

    return work


# =============================================================================
# 品詞詳細集計
# =============================================================================

def create_detail_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    品詞×品詞細分類1ごとの件数・割合・順位を作成する。
    """
    total_count = len(dataframe)

    result = (
        dataframe
        .groupby(
            ["品詞", "品詞細分類1"],
            dropna=False,
        )
        .size()
        .reset_index(name="件数")
        .sort_values(
            ["件数", "品詞", "品詞細分類1"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )

    result.insert(
        0,
        "全体順位",
        range(1, len(result) + 1),
    )

    result["全体割合（％）"] = (
        result["件数"] / total_count * 100
    ).round(4)

    pos_totals = (
        result
        .groupby("品詞")["件数"]
        .transform("sum")
    )

    result["品詞内割合（％）"] = (
        result["件数"] / pos_totals * 100
    ).round(4)

    result["品詞合計件数"] = pos_totals
    result["全形態素数"] = total_count

    result["品詞内順位"] = (
        result
        .groupby("品詞")["件数"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    result = result[
        [
            "全体順位",
            "品詞",
            "品詞細分類1",
            "品詞内順位",
            "件数",
            "品詞内割合（％）",
            "全体割合（％）",
            "品詞合計件数",
            "全形態素数",
        ]
    ]

    return result


# =============================================================================
# 主要品詞集計
# =============================================================================

def create_main_pos_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    品詞大分類ごとの件数・割合・順位を作成する。
    """
    total_count = len(dataframe)

    result = (
        dataframe["品詞"]
        .value_counts(dropna=False)
        .rename_axis("品詞")
        .reset_index(name="件数")
    )

    result.insert(
        0,
        "順位",
        range(1, len(result) + 1),
    )

    result["割合（％）"] = (
        result["件数"] / total_count * 100
    ).round(4)

    result["全形態素数"] = total_count

    return result


# =============================================================================
# サマリー
# =============================================================================

def create_analysis_summary(
    dataframe: pd.DataFrame,
    detail_summary: pd.DataFrame,
    main_summary: pd.DataFrame,
    elapsed_seconds: float,
) -> pd.DataFrame:
    """
    Step3-2の解析概要を作成する。
    """
    unique_case_count = int(
        dataframe["記号"].nunique(dropna=False)
    )

    noun_count = int(
        main_summary.loc[
            main_summary["品詞"] == "名詞",
            "件数",
        ].sum()
    )

    verb_count = int(
        main_summary.loc[
            main_summary["品詞"] == "動詞",
            "件数",
        ].sum()
    )

    adjective_count = int(
        main_summary.loc[
            main_summary["品詞"] == "形容詞",
            "件数",
        ].sum()
    )

    summary_rows = [
        ("入力ファイル", str(INPUT_CSV)),
        ("入力形態素数", len(dataframe)),
        ("対象事例数", unique_case_count),
        ("品詞大分類数", int(main_summary["品詞"].nunique())),
        (
            "品詞・細分類組合せ数",
            len(detail_summary),
        ),
        ("名詞件数", noun_count),
        ("動詞件数", verb_count),
        ("形容詞件数", adjective_count),
        (
            "名詞・動詞・形容詞合計",
            noun_count + verb_count + adjective_count,
        ),
        (
            "名詞・動詞・形容詞割合（％）",
            round(
                (
                    noun_count
                    + verb_count
                    + adjective_count
                )
                / len(dataframe)
                * 100,
                4,
            ),
        ),
        ("処理時間（秒）", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        ("次のStep", "Step3-3_All_頻出語集計.py"),
    ]

    return pd.DataFrame(
        summary_rows,
        columns=["項目", "値"],
    )


# =============================================================================
# コンソール表示
# =============================================================================

def print_main_summary(
    main_summary: pd.DataFrame,
) -> None:
    """
    主要品詞集計をコンソールへ表示する。
    """
    print("\n【主要品詞集計】")

    print(
        main_summary.to_string(
            index=False,
            formatters={
                "件数": lambda value: f"{int(value):,}",
                "割合（％）": lambda value: f"{float(value):.4f}",
                "全形態素数": lambda value: f"{int(value):,}",
            },
        )
    )


def print_detail_preview(
    detail_summary: pd.DataFrame,
) -> None:
    """
    品詞詳細集計の上位30行を表示する。
    """
    print("\n【品詞・細分類集計：上位30行】")

    print(
        detail_summary
        .head(30)
        .to_string(
            index=False,
            formatters={
                "件数": lambda value: f"{int(value):,}",
                "品詞内割合（％）": lambda value: f"{float(value):.4f}",
                "全体割合（％）": lambda value: f"{float(value):.4f}",
                "品詞合計件数": lambda value: f"{int(value):,}",
                "全形態素数": lambda value: f"{int(value):,}",
            },
        )
    )


# =============================================================================
# メイン処理
# =============================================================================

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-2_All_品詞集計を開始します")
    print("解析対象　　　：Step3-1の全形態素")
    print("解析方法　　　：記述統計")
    print("ジャッカード　：使用しない")
    print("=" * 78)

    try:
        morpheme_df = load_morpheme_csv(
            INPUT_CSV,
        )

        prepared_df = prepare_data(
            morpheme_df,
        )

        detail_summary = create_detail_summary(
            prepared_df,
        )

        main_summary = create_main_pos_summary(
            prepared_df,
        )

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            dataframe=prepared_df,
            detail_summary=detail_summary,
            main_summary=main_summary,
            elapsed_seconds=elapsed_seconds,
        )

        save_csv(
            detail_summary,
            OUTPUT_DETAIL_CSV,
        )

        save_csv(
            main_summary,
            OUTPUT_MAIN_CSV,
        )

        save_csv(
            analysis_summary,
            OUTPUT_SUMMARY_CSV,
        )

        print_main_summary(
            main_summary,
        )

        print_detail_preview(
            detail_summary,
        )

        print("\n【整合性確認】")
        print(
            f"入力形態素数　　　："
            f"{len(prepared_df):,}件"
        )
        print(
            f"主要品詞件数合計　："
            f"{int(main_summary['件数'].sum()):,}件"
        )
        print(
            f"詳細集計件数合計　："
            f"{int(detail_summary['件数'].sum()):,}件"
        )
        print(
            f"主要品詞割合合計　："
            f"{main_summary['割合（％）'].sum():.4f}％"
        )
        print(
            f"詳細全体割合合計　："
            f"{detail_summary['全体割合（％）'].sum():.4f}％"
        )

        print("\n" + "━" * 78)
        print("Step3-2_All_品詞集計　正常終了")
        print("━" * 78)
        print(
            f"入力形態素数　　　　："
            f"{len(prepared_df):,}件"
        )
        print(
            f"対象事例数　　　　　："
            f"{prepared_df['記号'].nunique(dropna=False):,}件"
        )
        print(
            f"品詞大分類数　　　　："
            f"{len(main_summary):,}種類"
        )
        print(
            f"品詞・細分類組合せ　："
            f"{len(detail_summary):,}種類"
        )
        print(
            f"処理時間　　　　　　："
            f"{elapsed_seconds:.2f}秒"
        )
        print()
        print(
            f"品詞詳細集計CSV　　　："
            f"{OUTPUT_DETAIL_CSV}"
        )
        print(
            f"主要品詞集計CSV　　　："
            f"{OUTPUT_MAIN_CSV}"
        )
        print(
            f"解析サマリーCSV　　　："
            f"{OUTPUT_SUMMARY_CSV}"
        )
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep：Step3-3_All_頻出語集計.py")
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
