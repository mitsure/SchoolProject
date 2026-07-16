#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-4_抄録下書き作成

Methods、Results、Discussion候補を統合し、
構造化抄録の下書きを作成する。
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


IN_METHODS = TEXT_DIR / "Step6-1_Methods下書き.txt"
IN_RESULTS = TEXT_DIR / "Step6-2_Results下書き.txt"
IN_DISCUSSION = TEXT_DIR / "Step6-3_Discussion候補.txt"

OUT_MD = TEXT_DIR / "Step6-4_抄録下書き.md"
OUT_TXT = TEXT_DIR / "Step6-4_抄録下書き.txt"
OUT_SUMMARY = OUTPUT_DIR / "Step6-4_解析サマリー.csv"

MAX_RESULTS_CHARS = 1200


def extract_results_summary(text: str) -> str:
    clean = " ".join(text.split())
    if len(clean) > MAX_RESULTS_CHARS:
        return clean[:MAX_RESULTS_CHARS] + "..."
    return clean


def create_abstract() -> str:
    for path in (IN_METHODS, IN_RESULTS, IN_DISCUSSION):
        if not path.exists():
            raise FileNotFoundError(f"必要ファイルがありません: {path}")

    results_text = IN_RESULTS.read_text(encoding="utf-8")
    results_summary = extract_results_summary(results_text)

    return f"""
## 目的

学校管理下における事故データを対象として、自由記述のテキストマイニングおよびジャッカード係数を用い、
歯牙障害事例に特徴的な語、カテゴリおよび事故パターンを明らかにすることを目的とした。

## 方法

学校等事故事例データを対象に、全事例および歯牙障害事例を抽出した。
自由記述欄をJanomeで形態素解析し、名詞、動詞および形容詞の基本形を対象として頻出語、共起語およびTF-IDFを算出した。
ストップワード除去後、語特徴および辞書分類によるカテゴリ特徴を作成した。
特徴間および事例間の類似性はジャッカード係数を用いて評価し、全事例と歯牙障害事例の出現率差を比較した。

## 結果

{results_summary}

## 結論

自由記述のテキストマイニングとジャッカード解析を組み合わせることで、
歯牙障害事例に特徴的な語およびカテゴリの組合せを定量的に抽出できる可能性が示された。
ただし、結果は自由記述の品質、形態素解析およびカテゴリ辞書の精度に依存するため、
原文確認および辞書改善を含む妥当性評価が必要である。
"""


def main() -> None:
    start = time.perf_counter()

    try:
        body = create_abstract()

        write_markdown(OUT_MD, "構造化抄録 下書き", body)
        write_text(OUT_TXT, body.strip() + "\n")

        elapsed = time.perf_counter() - start

        save_summary([
            ("抄録形式", "目的・方法・結果・結論"),
            ("結果要約最大文字数", MAX_RESULTS_CHARS),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step6-5_Table_Figureキャプション作成.py"),
        ], OUT_SUMMARY)

        print(body)
        print("\nStep6-4 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
