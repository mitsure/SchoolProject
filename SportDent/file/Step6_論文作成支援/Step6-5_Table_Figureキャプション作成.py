#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-5_Table_Figureキャプション作成

Step5のTable一覧・Figure一覧から、
論文用キャプションの下書きを生成する。
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


IN_TABLE_INDEX = TABLE_DIR / "Table一覧.csv"
IN_FIGURE_INDEX = FIGURE_DIR / "Figure一覧.csv"

OUT_TABLE = CAPTION_DIR / "Tableキャプション.csv"
OUT_FIGURE = CAPTION_DIR / "Figureキャプション.csv"
OUT_MD = CAPTION_DIR / "Table_Figureキャプション一覧.md"
OUT_SUMMARY = OUTPUT_DIR / "Step6-5_解析サマリー.csv"


def main() -> None:
    start = time.perf_counter()

    try:
        table_index = read_csv(IN_TABLE_INDEX)
        figure_index = read_csv(IN_FIGURE_INDEX)

        table_rows = []
        for _, row in table_index.iterrows():
            table_rows.append({
                "Table番号": row["Table番号"],
                "表題": row["表題"],
                "キャプション案": (
                    f"{row['Table番号']}. {row['表題']}。"
                    "各値は解析対象データから算出した。"
                ),
            })

        figure_rows = []
        for _, row in figure_index.iterrows():
            figure_rows.append({
                "Figure番号": row["Figure番号"],
                "図題": row["図題"],
                "キャプション案": (
                    f"{row['Figure番号']}. {row['図題']}。"
                    "図中の値はStep5で整理した解析結果に基づく。"
                ),
            })

        table_caption = pd.DataFrame(table_rows)
        figure_caption = pd.DataFrame(figure_rows)

        save_csv(table_caption, OUT_TABLE)
        save_csv(figure_caption, OUT_FIGURE)

        lines = ["## Table キャプション", ""]
        lines.extend(
            f"- {row['キャプション案']}"
            for _, row in table_caption.iterrows()
        )
        lines.extend(["", "## Figure キャプション", ""])
        lines.extend(
            f"- {row['キャプション案']}"
            for _, row in figure_caption.iterrows()
        )

        write_markdown(
            OUT_MD,
            "Table・Figure キャプション一覧",
            "\n".join(lines),
        )

        elapsed = time.perf_counter() - start

        save_summary([
            ("Tableキャプション数", len(table_caption)),
            ("Figureキャプション数", len(figure_caption)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step6-6_論文構成案作成.py"),
        ], OUT_SUMMARY)

        print(table_caption.to_string(index=False))
        print(figure_caption.to_string(index=False))
        print("\nStep6-5 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
