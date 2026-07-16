#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==========================================================
Step1-3_基本集計_性別集計

【目的】
元データ全体について、「性別」ごとの件数・割合・順位を集計する。

【Pythonファイルの配置先】
Meikai/file/Step1_基本集計/
└─ Step1-3_基本集計_性別集計.py

【入力】
Meikai/DB/shougai(2025.01.31).csv

【出力】
Meikai/CreateData/Step1_基本集計/
└─ Step1-3_基本集計_性別集計.csv

【フォルダ生成】
CreateDataが空でも、必要なフォルダを自動生成する。

【上書き】
同名CSVが存在する場合は上書きする。

【解析方法】
記述統計
- 件数集計
- 割合計算
- 順位付け
- 欠損値確認

【ジャッカード係数】
使用しない。

【理由】
このStepは性別ごとの基本分布を確認する記述統計であり、
特徴間または事例間の類似性を評価する解析ではないため。

【必要ライブラリ】
pandas

【実行例】
python file/Step1_基本集計/Step1-3_基本集計_性別集計.py
==========================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd


# ==========================================================
# 基本設定
# ==========================================================

STEP_NAME = "Step1-3"
PROGRAM_NAME = "基本集計_性別集計"
TARGET_COLUMN = "性別"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

INPUT_CSV = PROJECT_ROOT / "DB" / "shougai(2025.01.31).csv"

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step1_基本集計"
OUTPUT_CSV = OUTPUT_DIR / "Step1-3_基本集計_性別集計.csv"


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
    if TARGET_COLUMN not in dataframe.columns:
        raise ValueError(
            f"必要な列「{TARGET_COLUMN}」が見つかりません。\n"
            f"現在の列名：{list(dataframe.columns)}"
        )

    if dataframe.empty:
        raise ValueError("入力CSVにデータ行がありません。")


# ==========================================================
# 性別集計
# ==========================================================

def create_summary(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    性別ごとの件数・割合・順位を作成する。
    欠損値や空文字は除外せず「欠損」として集計する。
    """
    total_count = len(dataframe)

    values = (
        dataframe[TARGET_COLUMN]
        .fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )

    summary = (
        values
        .value_counts(dropna=False)
        .rename_axis(TARGET_COLUMN)
        .reset_index(name="件数")
    )

    summary.insert(0, "順位", range(1, len(summary) + 1))
    summary["割合（％）"] = (
        summary["件数"] / total_count * 100
    ).round(2)
    summary["全体件数"] = total_count

    return summary


# ==========================================================
# CSV出力
# ==========================================================

def save_csv(summary: pd.DataFrame) -> None:
    """
    出力先フォルダを自動生成し、CSVを保存する。
    同名ファイルがある場合は上書きする。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    missing_count = int(dataframe[TARGET_COLUMN].isna().sum())

    print("\n" + "=" * 70)
    print(f"{STEP_NAME}　{PROGRAM_NAME}")
    print("=" * 70)
    print("解析方法　　　：記述統計")
    print("ジャッカード　：使用しない")
    print(f"入力総件数　　：{len(dataframe):,}件")
    print(f"元データ欠損　：{missing_count:,}件")
    print(f"出力カテゴリ数：{len(summary):,}種類")

    print("\n【性別集計結果】")
    print(
        summary.to_string(
            index=False,
            formatters={
                "件数": lambda value: f"{int(value):,}",
                "割合（％）": lambda value: f"{float(value):.2f}",
                "全体件数": lambda value: f"{int(value):,}",
            },
        )
    )

    print("\n【整合性確認】")
    print(f"集計件数合計：{int(summary['件数'].sum()):,}件")
    print(f"割合合計　　：{summary['割合（％）'].sum():.2f}％")


# ==========================================================
# メイン処理
# ==========================================================

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 70)
    print(f"{STEP_NAME}　{PROGRAM_NAME}を開始します")
    print("=" * 70)

    if not INPUT_CSV.exists():
        print("\n【エラー】入力CSVが見つかりません。")
        print(f"確認先：{INPUT_CSV}")
        print(
            "\n想定構成：\n"
            "Meikai/\n"
            "├─ DB/\n"
            "│  └─ shougai(2025.01.31).csv\n"
            "├─ file/\n"
            "│  └─ Step1_基本集計/\n"
            "│     └─ Step1-3_基本集計_性別集計.py\n"
            "└─ CreateData/  ← 空で問題ありません"
        )
        sys.exit(1)

    try:
        dataframe = load_csv(INPUT_CSV)
        validate_input(dataframe)

        summary = create_summary(dataframe)
        print_summary(dataframe, summary)
        save_csv(summary)

    except Exception as error:
        print("\n【処理中にエラーが発生しました】")
        print(error)
        sys.exit(1)

    elapsed = time.perf_counter() - start_time

    print("\n" + "━" * 70)
    print(f"{STEP_NAME}　完了")
    print(f"プログラム　　：Step1-3_基本集計_性別集計.py")
    print("解析方法　　　：記述統計")
    print("ジャッカード　：使用しない")
    print(f"入力件数　　　：{len(dataframe):,}件")
    print(f"出力件数　　　：{len(summary):,}行")
    print(f"処理時間　　　：{elapsed:.2f}秒")
    print(f"出力ファイル　：{OUTPUT_CSV}")
    print("同名CSVは上書きしています。")
    print("次のStep　　　：Step1-4_基本集計_傷害種別集計.py")
    print("━" * 70)


if __name__ == "__main__":
    main()
