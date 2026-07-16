#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-1_Methods下書き作成

目的:
Step1からStep5までの解析工程をもとに、
論文のMethods節の下書きを自動生成する。

注意:
このファイルは解析を行わない。
既に実行済みの解析手順を文章化する。

出力:
CreateData/Step6_論文作成支援/Text/
├─ Step6-1_Methods下書き.md
└─ Step6-1_Methods下書き.txt
"""


from __future__ import annotations

from pathlib import Path
import sys
import time
import json

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv

STEP5_DIR = PROJECT_ROOT / "CreateData" / "Step5_結果整理"
TABLE_DIR = STEP5_DIR / "Tables"
FIGURE_DIR = STEP5_DIR / "Figures"
SUPPORT_DIR = STEP5_DIR / "考察支援"

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step6_論文作成支援"
TEXT_DIR = OUTPUT_DIR / "Text"
CAPTION_DIR = OUTPUT_DIR / "Captions"
STRUCTURE_DIR = OUTPUT_DIR / "Structure"

for directory in (OUTPUT_DIR, TEXT_DIR, CAPTION_DIR, STRUCTURE_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"入力CSVが見つかりません: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_markdown(path: Path, title: str, body: str) -> None:
    content = f"# {title}\n\n{body.strip()}\n"
    write_text(path, content)


def save_summary(items: list[tuple[str, object]], path: Path) -> None:
    save_csv(pd.DataFrame(items, columns=["項目", "値"]), path)


def format_percent(value: object, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}%"
    except Exception:
        return str(value)


def format_number(value: object, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


OUT_MD = TEXT_DIR / "Step6-1_Methods下書き.md"
OUT_TXT = TEXT_DIR / "Step6-1_Methods下書き.txt"
OUT_SUMMARY = OUTPUT_DIR / "Step6-1_解析サマリー.csv"


def create_methods_text() -> str:
    return """
## 対象データ

日本スポーツ振興センターが提供する学校等事故事例データを解析対象とした。
解析対象データには、傷害種別、学校種、学年、性別、発生場所、発生時の状況等の項目が含まれていた。

## データ前処理

解析前に、CSVファイルの文字コード、列名、欠損値および自由記述欄の改行・空白を確認した。
傷害種別に基づいて全事例データと歯牙障害事例データを作成し、それぞれを独立して解析した。

## 形態素解析

自由記述欄である「災害発生時の状況」を対象として、Pythonの日本語形態素解析ライブラリJanomeを用いて形態素解析を実施した。
各形態素について表層形、基本形、品詞、品詞細分類、活用型、活用形、読みおよび発音を取得した。
頻出語解析では、名詞、動詞および形容詞の基本形を対象とした。

## ストップワード処理

解析上の意味が乏しい一般語を除外するため、事前に作成したストップワード辞書を用いた。
ストップワード除去後、各事例について語順保持データと重複除去済み特徴集合を作成した。

## カテゴリ分類

受傷部位、受傷機転、原因物、衝突対象、行動、環境要因および傷害結果等のカテゴリ辞書を作成し、
自由記述から抽出された基本形と完全一致で照合した。
辞書に一致しなかった語は未分類として記録し、辞書改善のための確認対象とした。

## 頻出語および特徴語解析

各語について出現回数、出現事例数および事例出現率を算出した。
特徴語抽出にはTF-IDFを用い、全事例および歯牙障害事例について平均TF-IDFを算出した。

## 共起解析

同一事例内に同時出現した語の組合せを共起語として集計した。
同一事例内で同じ語が複数回出現した場合は、共起事例数の計算では1回として扱った。

## ジャッカード解析

語特徴、カテゴリ特徴および統合特徴について、ジャッカード係数を算出した。
ジャッカード係数は、2集合の共通要素数を和集合要素数で除して求めた。
特徴間解析では、各特徴が出現した事例集合を比較した。
事例間解析では、各事例が保有する特徴集合を比較し、各事例について類似度上位の事例を抽出した。

## Allと歯牙障害の比較

全事例と歯牙障害事例について、頻出語、TF-IDF、カテゴリ出現率および代表特徴集合を比較した。
歯牙障害における出現率から全事例における出現率を減じ、出現率差を算出した。
また、両群の代表特徴集合についてジャッカード係数を算出した。

## 結果整理

論文掲載候補として、歯牙障害で相対的に多い特徴語、特徴カテゴリ、ジャッカード係数上位ペアおよび事故パターンを抽出した。
図表作成時には、上位項目を抽出し、表番号および図番号を付与した。

## 使用環境

解析はPythonを用いて実施した。
主要ライブラリとしてpandas、NumPy、SciPy、scikit-learn、Janomeおよびmatplotlibを使用した。
"""


def main() -> None:
    start = time.perf_counter()

    try:
        text = create_methods_text()

        write_markdown(OUT_MD, "Methods 下書き", text)
        write_text(OUT_TXT, text.strip() + "\n")

        elapsed = time.perf_counter() - start

        save_summary([
            ("出力内容", "Methods下書き"),
            ("出力形式", "Markdown・テキスト"),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step6-2_Results下書き作成.py"),
        ], OUT_SUMMARY)

        print(text)
        print("\nStep6-1 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
