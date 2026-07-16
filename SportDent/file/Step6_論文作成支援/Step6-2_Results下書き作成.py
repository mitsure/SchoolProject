#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-2_Results下書き作成

Step5で作成したTableを読み込み、
論文のResults節に使用する数値記述の下書きを作成する。

注意:
数値を自動で文章化するが、最終的な採用結果は人が確認する。
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


IN_WORD = TABLE_DIR / "Table4_歯牙障害特徴語ランキング.csv"
IN_CATEGORY = TABLE_DIR / "Table5_歯牙障害特徴カテゴリランキング.csv"
IN_JACCARD = TABLE_DIR / "Table7_歯牙障害_Jaccard上位ペア.csv"
IN_PATTERN = TABLE_DIR / "Table8_歯牙障害_事故パターンランキング.csv"

OUT_MD = TEXT_DIR / "Step6-2_Results下書き.md"
OUT_TXT = TEXT_DIR / "Step6-2_Results下書き.txt"
OUT_EVIDENCE = TEXT_DIR / "Step6-2_Results根拠一覧.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step6-2_解析サマリー.csv"

TOP_WORDS = 10
TOP_CATEGORIES = 10
TOP_JACCARD = 10
TOP_PATTERNS = 10


def create_results() -> tuple[str, pd.DataFrame]:
    word = read_csv(IN_WORD).head(TOP_WORDS)
    category = read_csv(IN_CATEGORY).head(TOP_CATEGORIES)
    jaccard_df = read_csv(IN_JACCARD).head(TOP_JACCARD)
    pattern = read_csv(IN_PATTERN).head(TOP_PATTERNS)

    paragraphs = []
    evidence_rows = []

    if not word.empty:
        word_sentences = []

        for _, row in word.iterrows():
            sentence = (
                f"「{row['基本形']}」の事例出現率は、"
                f"歯牙障害で{format_percent(row['歯牙障害事例出現率(%)'])}、"
                f"全事例で{format_percent(row['All事例出現率(%)'])}であり、"
                f"差は{format_number(row['出現率差_歯牙障害-All'], 1)}ポイントであった"
            )
            word_sentences.append(sentence)

            evidence_rows.append({
                "結果区分": "特徴語",
                "項目": row["基本形"],
                "主要数値": row["出現率差_歯牙障害-All"],
                "文章": sentence,
            })

        paragraphs.append(
            "## 特徴語\n\n"
            + "。".join(word_sentences[:5])
            + "。"
        )

    if not category.empty:
        category_sentences = []

        for _, row in category.iterrows():
            name = f"{row['カテゴリ']}:{row['サブカテゴリ']}"
            sentence = (
                f"カテゴリ「{name}」の事例出現率は、"
                f"歯牙障害で{format_percent(row['歯牙障害事例出現率(%)'])}、"
                f"全事例で{format_percent(row['All事例出現率(%)'])}であった"
            )
            category_sentences.append(sentence)

            evidence_rows.append({
                "結果区分": "特徴カテゴリ",
                "項目": name,
                "主要数値": row["出現率差_歯牙障害-All"],
                "文章": sentence,
            })

        paragraphs.append(
            "## 特徴カテゴリ\n\n"
            + "。".join(category_sentences[:5])
            + "。"
        )

    if not jaccard_df.empty:
        jaccard_sentences = []

        for _, row in jaccard_df.iterrows():
            sentence = (
                f"「{row['特徴1']}」と「{row['特徴2']}」の"
                f"ジャッカード係数は{format_number(row['ジャッカード係数'], 3)}であった"
            )
            jaccard_sentences.append(sentence)

            evidence_rows.append({
                "結果区分": "Jaccard",
                "項目": f"{row['特徴1']} × {row['特徴2']}",
                "主要数値": row["ジャッカード係数"],
                "文章": sentence,
            })

        paragraphs.append(
            "## ジャッカード解析\n\n"
            + "。".join(jaccard_sentences[:5])
            + "。"
        )

    if not pattern.empty:
        pattern_sentences = []

        for _, row in pattern.iterrows():
            sentence = (
                f"事故パターン「{row['事故パターン']}」は"
                f"{int(row['件数'])}件"
                f"（{format_percent(row['事例割合(%)'])}）認められた"
            )
            pattern_sentences.append(sentence)

            evidence_rows.append({
                "結果区分": "事故パターン",
                "項目": row["事故パターン"],
                "主要数値": row["件数"],
                "文章": sentence,
            })

        paragraphs.append(
            "## 事故パターン\n\n"
            + "。".join(pattern_sentences[:5])
            + "。"
        )

    body = "\n\n".join(paragraphs)
    evidence = pd.DataFrame(evidence_rows)

    return body, evidence


def main() -> None:
    start = time.perf_counter()

    try:
        body, evidence = create_results()

        write_markdown(OUT_MD, "Results 下書き", body)
        write_text(OUT_TXT, body.strip() + "\n")
        save_csv(evidence, OUT_EVIDENCE)

        elapsed = time.perf_counter() - start

        save_summary([
            ("Results根拠行数", len(evidence)),
            ("特徴語採用上限", TOP_WORDS),
            ("特徴カテゴリ採用上限", TOP_CATEGORIES),
            ("Jaccard採用上限", TOP_JACCARD),
            ("事故パターン採用上限", TOP_PATTERNS),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step6-3_Discussion候補作成.py"),
        ], OUT_SUMMARY)

        print(body)
        print("\nStep6-2 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
