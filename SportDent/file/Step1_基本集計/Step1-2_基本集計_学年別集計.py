#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==========================================================
Step1-2_基本集計_学年集計

【目的】
元データ全体について、「被災学校種」と「被災学年」の組合せごとに、
件数・学校種内割合・全体割合・順位を集計する。

【Pythonファイルの配置先】
Meikai/file/Step1-2_基本集計_学年集計.py

【入力】
Meikai/DB/shougai(2025.01.31).csv

【出力】
Meikai/CreateData/Step1_基本集計/
└─ Step1-2_基本集計_学年集計.csv

【フォルダ生成】
CreateDataが空でも、以下を自動生成する。
- CreateData/Step1_基本集計/

【上書き】
同名CSVが存在する場合は上書きする。

【解析方法】
記述統計
- 学校種・学年別件数集計
- 学校種内割合計算
- 全体割合計算
- 学校種内順位付け
- 欠損値確認

【ジャッカード係数】
使用しない。

【理由】
このStepは学校種・学年ごとの基本分布を確認する記述統計であり、
特徴間または事例間の類似性を評価する解析ではないため。

【必要ライブラリ】
pandas

【実行例】
python file/Step1-2_基本集計_学年集計.py
==========================================================
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


# ==========================================================
# 基本設定
# ==========================================================

STEP_NAME = "Step1-2"
PROGRAM_NAME = "基本集計_学年集計"

SCHOOL_COLUMN = "被災学校種"
GRADE_COLUMN = "被災学年"

# Pythonファイルの配置場所
SCRIPT_DIR = Path(__file__).resolve().parent

# プロジェクト直下
PROJECT_ROOT = SCRIPT_DIR.parent

# 入力CSV
INPUT_CSV = PROJECT_ROOT / "DB" / "shougai(2025.01.31).csv"

# 出力先
OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step1_基本集計"
OUTPUT_CSV = OUTPUT_DIR / "Step1-2_基本集計_学年集計.csv"


# ==========================================================
# CSV読み込み
# ==========================================================

def load_csv(csv_path: Path) -> pd.DataFrame:
    """日本語CSVを複数の文字コード候補で読み込む。"""
    encoding_candidates = ["utf-8-sig", "cp932", "shift_jis", "utf-8"]
    last_error: Exception | None = None

    for encoding in encoding_candidates:
        try:
            dataframe = pd.read_csv(csv_path, encoding=encoding)
            print(f"入力ファイル：{csv_path}")
            print(f"文字コード　：{encoding}")
            return dataframe
        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"CSVを読み込めませんでした。\n"
        f"対象ファイル：{csv_path}\n"
        f"最終エラー　：{last_error}"
    )


# ==========================================================
# 入力確認
# ==========================================================

def validate_input(dataframe: pd.DataFrame) -> None:
    """必要な列とデータ件数を確認する。"""
    required_columns = [SCHOOL_COLUMN, GRADE_COLUMN]
    missing_columns = [
        column for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"必要な列が見つかりません：{missing_columns}\n"
            f"現在の列名：{list(dataframe.columns)}"
        )

    if dataframe.empty:
        raise ValueError("入力CSVにデータ行がありません。")


# ==========================================================
# 学年集計
# ==========================================================

def create_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    学校種×学年ごとの件数・学校種内割合・全体割合・順位を作成する。
    欠損値は除外せず「欠損」として集計する。
    """
    total_count = len(dataframe)

    working = dataframe[[SCHOOL_COLUMN, GRADE_COLUMN]].copy()

    working[SCHOOL_COLUMN] = (
        working[SCHOOL_COLUMN]
        .fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )

    working[GRADE_COLUMN] = (
        working[GRADE_COLUMN]
        .fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )

    summary = (
        working
        .groupby(
            [SCHOOL_COLUMN, GRADE_COLUMN],
            dropna=False,
        )
        .size()
        .reset_index(name="件数")
    )

    school_totals = (
        summary
        .groupby(SCHOOL_COLUMN)["件数"]
        .transform("sum")
    )

    summary["学校種内割合（％）"] = (
        summary["件数"] / school_totals * 100
    ).round(2)

    summary["全体割合（％）"] = (
        summary["件数"] / total_count * 100
    ).round(2)

    summary["学校種内順位"] = (
        summary
        .groupby(SCHOOL_COLUMN)["件数"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    summary["学校種合計件数"] = school_totals
    summary["全体件数"] = total_count

    # 学校種、順位、学年の順で見やすく並べる
    summary = summary.sort_values(
        by=[
            SCHOOL_COLUMN,
            "学校種内順位",
            GRADE_COLUMN,
        ],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    # 列順を整理
    summary = summary[
        [
            SCHOOL_COLUMN,
            GRADE_COLUMN,
            "学校種内順位",
            "件数",
            "学校種内割合（％）",
            "全体割合（％）",
            "学校種合計件数",
            "全体件数",
        ]
    ]

    return summary


# ==========================================================
# CSV出力
# ==========================================================

def save_csv(summary: pd.DataFrame) -> None:
    """
    CreateDataが空でも必要なフォルダを自動生成する。
    同名CSVがある場合は上書きする。
    """
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )


# ==========================================================
# コンソール表示
# ==========================================================

def print_summary(
    dataframe: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    """集計結果と整合性確認をコンソールへ表示する。"""
    school_missing = int(dataframe[SCHOOL_COLUMN].isna().sum())
    grade_missing = int(dataframe[GRADE_COLUMN].isna().sum())

    print("\n" + "=" * 80)
    print(f"{STEP_NAME}　{PROGRAM_NAME}")
    print("=" * 80)
    print("解析方法　　　　：記述統計")
    print("ジャッカード　　：使用しない")
    print(f"入力総件数　　　：{len(dataframe):,}件")
    print(f"学校種の欠損件数：{school_missing:,}件")
    print(f"学年の欠損件数　：{grade_missing:,}件")
    print(f"出力行数　　　　：{len(summary):,}行")

    print("\n【学校種×学年 集計結果】")
    print(
        summary.to_string(
            index=False,
            formatters={
                "件数": lambda value: f"{int(value):,}",
                "学校種内割合（％）": lambda value: f"{float(value):.2f}",
                "全体割合（％）": lambda value: f"{float(value):.2f}",
                "学校種合計件数": lambda value: f"{int(value):,}",
                "全体件数": lambda value: f"{int(value):,}",
            },
        )
    )

    print("\n【整合性確認】")
    print(f"集計件数合計：{int(summary['件数'].sum()):,}件")
    print(f"全体割合合計：{summary['全体割合（％）'].sum():.2f}％")


# ==========================================================
# メイン処理
# ==========================================================

def main() -> None:
    print("\n" + "=" * 80)
    print(f"{STEP_NAME}　{PROGRAM_NAME}を開始します")
    print("=" * 80)

    if not INPUT_CSV.exists():
        print("\n【エラー】入力CSVが見つかりません。")
        print(f"確認先：{INPUT_CSV}")
        print(
            "\n想定構成：\n"
            "Meikai/\n"
            "├─ DB/\n"
            "│  └─ shougai(2025.01.31).csv\n"
            "├─ file/\n"
            "│  └─ Step1-2_基本集計_学年集計.py\n"
            "└─ CreateData/  ← 空で問題ありません"
        )
        sys.exit(1)

    try:
        dataframe = load_csv(INPUT_CSV)
        validate_input(dataframe)

        summary = create_summary(dataframe)

        print_summary(
            dataframe,
            summary,
        )

        save_csv(summary)

    except Exception as error:
        print("\n【処理中にエラーが発生しました】")
        print(error)
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"{STEP_NAME}　正常終了")
    print(f"出力ファイル：{OUTPUT_CSV}")
    print("同名CSVが存在した場合は上書きしています。")
    print("ジャッカード係数は使用していません。")
    print("=" * 80)


if __name__ == "__main__":
    main()
