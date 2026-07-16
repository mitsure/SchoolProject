#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-3_Discussion候補作成

Step5-7の考察支援データを読み込み、
Discussionの論点候補、限界、注意事項を整理する。

注意:
外部文献との照合は行わない。
最終的なDiscussionには文献検索と先行研究比較が必要。
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


IN_SUPPORT = SUPPORT_DIR / "Step5-7_考察支援データ.csv"

OUT_MD = TEXT_DIR / "Step6-3_Discussion候補.md"
OUT_TXT = TEXT_DIR / "Step6-3_Discussion候補.txt"
OUT_POINTS = TEXT_DIR / "Step6-3_Discussion論点一覧.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step6-3_解析サマリー.csv"


def create_discussion() -> tuple[str, pd.DataFrame]:
    support = read_csv(IN_SUPPORT)

    required = ["根拠区分", "観察事項", "数値根拠", "考察時の確認項目"]
    missing = [column for column in required if column not in support.columns]

    if missing:
        raise ValueError(f"必要な列がありません: {missing}")

    grouped_sections = []
    point_rows = []

    for section_name, group in support.groupby("根拠区分", sort=False):
        lines = []

        for index, (_, row) in enumerate(group.head(10).iterrows(), start=1):
            lines.append(
                f"{index}. {row['観察事項']} "
                f"根拠: {row['数値根拠']} "
                f"確認事項: {row['考察時の確認項目']}"
            )

            point_rows.append({
                "論点区分": section_name,
                "順位": index,
                "観察事項": row["観察事項"],
                "数値根拠": row["数値根拠"],
                "確認事項": row["考察時の確認項目"],
            })

        grouped_sections.append(
            f"## {section_name}\n\n"
            + "\n".join(lines)
        )

    limitations = """
## 解析上の限界

1. 自由記述の語彙および記載量は事例ごとに異なるため、出現頻度は実際の発生頻度だけでなく記載傾向の影響を受ける。
2. 形態素解析では専門用語、複合語、表記揺れが分割または別語として扱われる可能性がある。
3. カテゴリ分類は辞書への完全一致に基づくため、辞書未登録語および同義語を十分に分類できない可能性がある。
4. ジャッカード係数は特徴の共通性を示すが、因果関係や時間的順序を示さない。
5. All群には歯牙障害事例も含まれるため、完全に独立した対照群との比較ではない。
6. 事故パターンの特徴順序は時系列順序ではなく、集合を表示上並べたものである。
7. 本解析はデータベースに登録された事例に限定され、未報告事例や軽症例を反映しない可能性がある。
"""

    future_work = """
## 今後の検討

- 歯牙障害を除いた非歯牙障害群との比較
- 学校種、学年、性別、発生場所、活動種別ごとの層別解析
- 同義語辞書および複合語辞書の追加
- 辞書分類精度の人手評価
- ジャッカード係数以外の類似度指標との比較
- 原文確認による高類似事例の妥当性評価
- 先行研究との一致点および相違点の検討
"""

    body = "\n\n".join(grouped_sections) + "\n\n" + limitations + "\n" + future_work

    return body, pd.DataFrame(point_rows)


def main() -> None:
    start = time.perf_counter()

    try:
        body, points = create_discussion()

        write_markdown(OUT_MD, "Discussion 候補", body)
        write_text(OUT_TXT, body.strip() + "\n")
        save_csv(points, OUT_POINTS)

        elapsed = time.perf_counter() - start

        save_summary([
            ("Discussion論点数", len(points)),
            ("外部文献照合", "未実施"),
            ("処理時間(秒)", round(elapsed, 3)),
            ("次のStep", "Step6-4_抄録下書き作成.py"),
        ], OUT_SUMMARY)

        print(body)
        print("\nStep6-3 正常終了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
