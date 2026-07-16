#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step6-6_論文構成案作成

Methods、Results、Discussion、抄録、キャプションを
1つの論文構成案へまとめる。
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


INPUT_FILES = {
    "Methods": TEXT_DIR / "Step6-1_Methods下書き.md",
    "Results": TEXT_DIR / "Step6-2_Results下書き.md",
    "Discussion": TEXT_DIR / "Step6-3_Discussion候補.md",
    "Abstract": TEXT_DIR / "Step6-4_抄録下書き.md",
    "Captions": CAPTION_DIR / "Table_Figureキャプション一覧.md",
}

OUT_MD = STRUCTURE_DIR / "Step6-6_論文構成案.md"
OUT_JSON = STRUCTURE_DIR / "Step6-6_論文構成案.json"
OUT_CHECKLIST = STRUCTURE_DIR / "Step6-6_論文完成チェックリスト.csv"
OUT_SUMMARY = OUTPUT_DIR / "Step6-6_解析サマリー.csv"


def read_section(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"必要ファイルがありません: {path}")
    return path.read_text(encoding="utf-8").strip()


def main() -> None:
    start = time.perf_counter()

    try:
        sections = {
            name: read_section(path)
            for name, path in INPUT_FILES.items()
        }

        manuscript = f"""
# 論文構成案

## 表題

学校事故事例データにおける歯牙障害の特徴抽出：
テキストマイニングおよびジャッカード係数を用いた探索的解析

## 抄録

{sections['Abstract']}

## 1. 緒言

- 学校管理下における歯・口の外傷の重要性
- 事故発生時の状況を定量化する必要性
- 自由記述データへテキストマイニングを適用する意義
- ジャッカード係数を用いて特徴の共通性を評価する意義
- 本研究の目的

## 2. 方法

{sections['Methods']}

## 3. 結果

{sections['Results']}

## 4. 考察

{sections['Discussion']}

## 5. 結論

本解析パイプラインにより、学校事故事例データの自由記述から、
歯牙障害に特徴的な語、カテゴリおよび特徴の組合せを抽出できた。
今後は辞書精度の改善、原文確認および層別解析を行い、
事故予防および安全教育へ利用可能な知見として検証する必要がある。

## 図表キャプション

{sections['Captions']}

## 参考文献

- 使用データベースの出典
- 学校歯科外傷に関する先行研究
- テキストマイニングに関する方法論
- ジャッカード係数に関する方法論
"""

        write_text(OUT_MD, manuscript.strip() + "\n")

        json_data = {
            "title": "学校事故事例データにおける歯牙障害の特徴抽出",
            "sections": sections,
            "notes": {
                "literature_review_required": True,
                "human_validation_required": True,
                "causality_claim_allowed": False,
            },
        }

        write_text(
            OUT_JSON,
            json.dumps(json_data, ensure_ascii=False, indent=2),
        )

        checklist = pd.DataFrame([
            ("表題", "未確認", "研究対象・解析法・探索的研究であることを反映"),
            ("緒言", "未作成", "背景、先行研究、目的を文献付きで記載"),
            ("方法", "下書き作成済み", "対象期間・対象件数・除外基準を追記"),
            ("結果", "下書き作成済み", "採用するTable・Figureに合わせて修正"),
            ("考察", "候補作成済み", "先行研究との比較と臨床的意義を追記"),
            ("結論", "下書き作成済み", "結果の範囲内で簡潔に記載"),
            ("抄録", "下書き作成済み", "文字数制限に合わせて調整"),
            ("Table", "候補作成済み", "必要な表のみ採用"),
            ("Figure", "候補作成済み", "文字化け・フォント・解像度を確認"),
            ("参考文献", "未作成", "引用形式を統一"),
            ("倫理", "未確認", "倫理審査・公開データ利用条件を確認"),
            ("統計記載", "未確認", "閾値・ソフトウェア・バージョンを明記"),
        ], columns=["項目", "状態", "確認内容"])

        save_csv(checklist, OUT_CHECKLIST)

        elapsed = time.perf_counter() - start

        save_summary([
            ("統合セクション数", len(sections)),
            ("出力形式", "Markdown・JSON・CSV"),
            ("処理時間(秒)", round(elapsed, 3)),
            ("Step6", "完了"),
        ], OUT_SUMMARY)

        print(manuscript)
        print("\nStep6 完了")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
