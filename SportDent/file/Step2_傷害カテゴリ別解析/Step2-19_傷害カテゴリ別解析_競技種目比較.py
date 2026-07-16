#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==========================================================
Step2-19_傷害カテゴリ別解析_競技種目比較

【目的】
各傷害カテゴリについて、競技種目ごとの件数・割合・順位を比較する。

【入力】
DB/shougai(2025.01.31).csv

【使用列】
種別
競技種目

【出力】
CreateData/Step2_傷害カテゴリ別解析/カテゴリ比較集計/
└─ Step2-19_傷害カテゴリ別解析_競技種目比較.csv

【解析方法】
記述統計・クロス集計
- 傷害カテゴリ別件数
- カテゴリ内割合
- 全体割合
- カテゴリ内順位
- 欠損値確認

【ジャッカード係数】
使用しない。

【理由】
カテゴリ別の分布を比較する記述統計であり、
類似性を評価する段階ではないため。

【上書き】
同名CSVが存在する場合は上書きする。

【次の処理】
Step2-20_傷害カテゴリ別解析_年度別比較.py
==========================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
INPUT_CSV = PROJECT_ROOT / "DB" / "shougai(2025.01.31).csv"
OUTPUT_ROOT = PROJECT_ROOT / "CreateData" / "Step2_傷害カテゴリ別解析"


def load_csv(path: Path) -> pd.DataFrame:
    """日本語CSVを複数の文字コード候補で読み込む。"""
    last_error = None
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=encoding)
            print(f"入力ファイル：{path}")
            print(f"文字コード　：{encoding}")
            return df
        except Exception as error:
            last_error = error
    raise RuntimeError(f"CSVを読み込めませんでした：{last_error}")


def normalize(series: pd.Series) -> pd.Series:
    """欠損値と空文字を『欠損』へ統一する。"""
    return (
        series.fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """出力フォルダを自動生成し、同名CSVを上書きする。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")

GROUP_COLUMNS = ['種別', '競技種目']
OUTPUT_CSV = (
    OUTPUT_ROOT
    / "カテゴリ比較集計"
    / "Step2-19_傷害カテゴリ別解析_競技種目比較.csv"
)


def main() -> None:
    start = time.perf_counter()
    print("=" * 78)
    print("Step2-19 傷害カテゴリ別解析：競技種目比較")
    print("解析方法：記述統計・クロス集計")
    print("ジャッカード係数：使用しない")
    print("=" * 78)

    if not INPUT_CSV.exists():
        print(f"入力CSVが見つかりません：{INPUT_CSV}")
        sys.exit(1)

    try:
        df = load_csv(INPUT_CSV)

        missing = [c for c in GROUP_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"必要な列がありません：{missing}")

        work = df[GROUP_COLUMNS].copy()
        work["種別"] = normalize(work["種別"])
        work["競技種目"] = normalize(work["競技種目"])

        result = (
            work.groupby(GROUP_COLUMNS, dropna=False)
            .size()
            .reset_index(name="件数")
        )

        category_total = (
            result.groupby("種別")["件数"].transform("sum")
        )

        result["カテゴリ内割合（％）"] = (
            result["件数"] / category_total * 100
        ).round(2)

        result["全体割合（％）"] = (
            result["件数"] / len(df) * 100
        ).round(2)

        result["カテゴリ内順位"] = (
            result.groupby("種別")["件数"]
            .rank(method="min", ascending=False)
            .astype(int)
        )

        result["カテゴリ合計件数"] = category_total
        result["全体件数"] = len(df)

        result = result.sort_values(
            ["種別", "カテゴリ内順位"] + GROUP_COLUMNS[1:],
            ascending=True,
        ).reset_index(drop=True)

        save_csv(result, OUTPUT_CSV)

        print(f"入力件数：{len(df):,}件")
        print(f"出力行数：{len(result):,}行")
        print(f"集計件数：{int(result['件数'].sum()):,}件")
        print("\n【先頭30行】")
        print(result.head(30).to_string(index=False))

    except Exception as error:
        print(f"エラー：{error}")
        sys.exit(1)

    elapsed = time.perf_counter() - start
    print("\n" + "━" * 78)
    print("正常終了")
    print(f"出力：{OUTPUT_CSV}")
    print(f"処理時間：{elapsed:.2f}秒")
    print("同名CSVは上書きしています。")
    print("ジャッカード係数：使用しない")
    print("次：Step2-20_傷害カテゴリ別解析_年度別比較.py")
    print("━" * 78)


if __name__ == "__main__":
    main()
