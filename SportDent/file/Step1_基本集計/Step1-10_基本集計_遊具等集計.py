#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==========================================================
Step1-10_基本集計_遊具等集計

【目的】
「遊具等」ごとの件数・割合・順位を集計し、遊具・設備関連事例の分布を確認する。

【Pythonファイルの配置先】
Meikai/file/Step1_基本集計/
└─ Step1-10_基本集計_遊具等集計.py

【入力】
Meikai/DB/shougai(2025.01.31).csv

【出力】
Meikai/CreateData/Step1_基本集計/
└─ Step1-10_基本集計_遊具等集計.csv

【使用列】
遊具等

【解析方法】
記述統計
- 件数集計
- 割合計算
- 順位付け
- 欠損値確認

【ジャッカード係数】
使用しない。

【理由】
このStepは元データの基本分布を確認する記述統計であり、
特徴間または事例間の類似性を評価する解析ではないため。

【上書き】
同名CSVが存在する場合は上書きする。

【実行例】
python file/Step1_基本集計/Step1-10_基本集計_遊具等集計.py

【次のStep】
Step2-1_傷害カテゴリ別解析_歯牙障害.py
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
OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step1_基本集計"


def load_csv(csv_path: Path) -> pd.DataFrame:
    """日本語CSVを複数の文字コード候補で読み込む。"""
    last_error = None
    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            print(f"入力ファイル：{csv_path}")
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


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    """出力先を自動生成し、同名CSVを上書き保存する。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

TARGET_COLUMN = "遊具等"
OUTPUT_CSV = OUTPUT_DIR / "Step1-10_基本集計_遊具等集計.csv"


def main() -> None:
    start = time.perf_counter()
    print("=" * 70)
    print("Step1-10_基本集計_遊具等集計")
    print("解析方法：記述統計")
    print("ジャッカード係数：使用しない")
    print("=" * 70)

    if not INPUT_CSV.exists():
        print(f"入力CSVが見つかりません：{INPUT_CSV}")
        sys.exit(1)

    try:
        df = load_csv(INPUT_CSV)

        if TARGET_COLUMN not in df.columns:
            raise ValueError(f"必要な列がありません：{TARGET_COLUMN}")

        values = normalize(df[TARGET_COLUMN])

        result = (
            values.value_counts(dropna=False)
            .rename_axis(TARGET_COLUMN)
            .reset_index(name="件数")
        )

        result.insert(0, "順位", range(1, len(result) + 1))
        result["割合（％）"] = (result["件数"] / len(df) * 100).round(2)
        result["全体件数"] = len(df)

        save_csv(result, OUTPUT_CSV)

        print(result.to_string(index=False))
        print("\n【整合性確認】")
        print(f"入力件数：{len(df):,}件")
        print(f"集計件数：{int(result['件数'].sum()):,}件")
        print(f"割合合計：{result['割合（％）'].sum():.2f}％")

    except Exception as error:
        print(f"エラー：{error}")
        sys.exit(1)

    elapsed = time.perf_counter() - start
    print("\n" + "━" * 70)
    print("Step1-10_基本集計_遊具等集計 完了")
    print(f"出力：{OUTPUT_CSV}")
    print(f"処理時間：{elapsed:.2f}秒")
    print("同名CSVは上書きしています。")
    print("ジャッカード係数：使用しない")
    print("次：Step2-1_傷害カテゴリ別解析_歯牙障害.py")
    print("━" * 70)


if __name__ == "__main__":
    main()
