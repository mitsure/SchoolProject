#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==========================================================
Step2-11_傷害カテゴリ別解析_足指切断・機能障害抽出

【目的】
元データから「種別」が「足指切断・機能障害」の事例だけを抽出し、
後続解析に使用するカテゴリ別データを作成する。

【入力】
DB/shougai(2025.01.31).csv

【出力】
CreateData/Step2_傷害カテゴリ別解析/カテゴリ別抽出データ/
└─ Step2-11_傷害カテゴリ別解析_足指切断・機能障害抽出.csv

【解析方法】
条件抽出
- 種別列による完全一致抽出
- 元の15列を維持
- 抽出件数と割合を確認

【ジャッカード係数】
使用しない。

【理由】
この処理はカテゴリ別データの抽出であり、
類似度の計算ではないため。

【上書き】
同名CSVが存在する場合は上書きする。

【実行例】
python file/Step2_傷害カテゴリ別解析/Step2-11_傷害カテゴリ別解析_足指切断・機能障害抽出.py
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

CATEGORY = "足指切断・機能障害"
OUTPUT_CSV = (
    OUTPUT_ROOT
    / "カテゴリ別抽出データ"
    / "Step2-11_傷害カテゴリ別解析_足指切断・機能障害抽出.csv"
)


def main() -> None:
    start = time.perf_counter()
    print("=" * 76)
    print("Step2-11 傷害カテゴリ別解析：足指切断・機能障害抽出")
    print("解析方法：条件抽出")
    print("ジャッカード係数：使用しない")
    print("=" * 76)

    if not INPUT_CSV.exists():
        print(f"入力CSVが見つかりません：{INPUT_CSV}")
        sys.exit(1)

    try:
        df = load_csv(INPUT_CSV)

        if "種別" not in df.columns:
            raise ValueError("必要な列「種別」がありません。")

        category_values = normalize(df["種別"])
        extracted = df.loc[category_values == CATEGORY].copy()

        if extracted.empty:
            raise ValueError(f"「{CATEGORY}」に該当するデータがありません。")

        save_csv(extracted, OUTPUT_CSV)

        count = len(extracted)
        ratio = count / len(df) * 100

        print(f"全体件数：{len(df):,}件")
        print(f"抽出件数：{count:,}件")
        print(f"全体割合：{ratio:.2f}％")
        print(f"列数　　：{len(extracted.columns)}列")

    except Exception as error:
        print(f"エラー：{error}")
        sys.exit(1)

    elapsed = time.perf_counter() - start
    print("\n" + "━" * 76)
    print("正常終了")
    print(f"出力：{OUTPUT_CSV}")
    print(f"処理時間：{elapsed:.2f}秒")
    print("同名CSVは上書きしています。")
    print("ジャッカード係数：使用しない")
    print("━" * 76)


if __name__ == "__main__":
    main()
