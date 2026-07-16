#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3-6_歯牙障害_カテゴリ分類

Common/Config/設定_カテゴリ辞書.csvを使用する。
ジャッカード係数は使用しない。
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"

INPUT_MORPHEME = OUTPUT_DIR / "Step3-1_歯牙障害_形態素解析.csv"
INPUT_STOPWORD = OUTPUT_DIR / "Step3-5_歯牙障害_ストップワード除去.csv"
DICTIONARY = PROJECT_ROOT / "file" / "Common" / "Config" / "設定_カテゴリ辞書.csv"

OUTPUT_CLASSIFIED = OUTPUT_DIR / "Step3-6_歯牙障害_カテゴリ分類.csv"
OUTPUT_CATEGORY = OUTPUT_DIR / "Step3-6_歯牙障害_カテゴリ集計.csv"
OUTPUT_CASE = OUTPUT_DIR / "Step3-6_歯牙障害_事例別カテゴリ.csv"
OUTPUT_UNCLASSIFIED = OUTPUT_DIR / "Step3-6_歯牙障害_未分類語集計.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step3-6_歯牙障害_解析サマリー.csv"

def main():
    start = time.perf_counter()
    print("=" * 78)
    print("Step3-6_歯牙障害_カテゴリ分類")
    print("=" * 78)

    try:
        for path in (INPUT_MORPHEME, INPUT_STOPWORD, DICTIONARY):
            if not path.exists():
                raise FileNotFoundError(f"必要ファイルがありません: {path}")

        morpheme = pd.read_csv(INPUT_MORPHEME, encoding="utf-8-sig")
        stopword = pd.read_csv(INPUT_STOPWORD, encoding="utf-8-sig")
        dictionary = pd.read_csv(DICTIONARY, encoding="utf-8-sig")

        require_columns(morpheme, ["記号", "種別", "基本形", "品詞"])
        require_columns(stopword, ["記号", "解析用語集合"])
        require_columns(dictionary, ["語", "カテゴリ", "サブカテゴリ"])

        if (morpheme["種別"].fillna("").astype(str).str.strip() != "歯牙障害").any():
            raise ValueError("歯牙障害以外が含まれています。")

        work = morpheme.copy()
        work["基本形"] = work["基本形"].fillna("").astype(str).str.strip()
        work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()
        work = work[
            work["基本形"].ne("")
            & work["品詞"].isin({"名詞", "動詞", "形容詞"})
        ].copy()

        dictionary["語"] = dictionary["語"].fillna("").astype(str).str.strip()

        classified = work.merge(
            dictionary,
            left_on="基本形",
            right_on="語",
            how="left"
        )

        classified["辞書ヒット"] = classified["カテゴリ"].notna()
        classified["カテゴリ"] = classified["カテゴリ"].fillna("未分類")
        classified["サブカテゴリ"] = classified["サブカテゴリ"].fillna("未分類")

        classified = classified[
            ["記号", "基本形", "品詞", "カテゴリ", "サブカテゴリ", "辞書ヒット"]
        ]

        total_cases = classified["記号"].nunique(dropna=False)

        a = (
            classified.groupby(["カテゴリ", "サブカテゴリ"])
            .size().reset_index(name="出現回数")
        )
        b = (
            classified[["記号", "カテゴリ", "サブカテゴリ"]]
            .drop_duplicates()
            .groupby(["カテゴリ", "サブカテゴリ"])
            .size().reset_index(name="出現事例数")
        )
        category = a.merge(b, on=["カテゴリ", "サブカテゴリ"])
        category["事例出現率(%)"] = (
            category["出現事例数"] / total_cases * 100
        ).round(4)
        category = category.sort_values(
            ["出現事例数", "出現回数"],
            ascending=[False, False]
        ).reset_index(drop=True)
        category.insert(0, "順位", range(1, len(category) + 1))

        case_rows = []
        for case_id, group in classified.groupby("記号", dropna=False, sort=False):
            hit = group[group["辞書ヒット"]].copy()
            categories = list(dict.fromkeys(hit["カテゴリ"].astype(str)))
            subcategories = list(dict.fromkeys(hit["サブカテゴリ"].astype(str)))
            features = [
                f"{row['カテゴリ']}:{row['サブカテゴリ']}"
                for _, row in hit[["カテゴリ", "サブカテゴリ"]]
                .drop_duplicates().iterrows()
            ]
            case_rows.append({
                "記号": case_id,
                "カテゴリ数": len(categories),
                "サブカテゴリ数": len(subcategories),
                "カテゴリ集合": " | ".join(categories),
                "サブカテゴリ集合": " | ".join(subcategories),
                "カテゴリ特徴集合": " | ".join(features),
            })
        case_result = pd.DataFrame(case_rows)

        unclassified = classified[~classified["辞書ヒット"]].copy()
        if unclassified.empty:
            unclassified_result = pd.DataFrame(columns=[
                "順位", "品詞", "基本形", "出現回数", "出現事例数"
            ])
        else:
            ua = unclassified.groupby(["品詞", "基本形"]).size().reset_index(name="出現回数")
            ub = (
                unclassified[["記号", "品詞", "基本形"]]
                .drop_duplicates()
                .groupby(["品詞", "基本形"])
                .size().reset_index(name="出現事例数")
            )
            unclassified_result = ua.merge(ub, on=["品詞", "基本形"])
            unclassified_result = unclassified_result.sort_values(
                ["出現事例数", "出現回数"],
                ascending=[False, False]
            ).reset_index(drop=True)
            unclassified_result.insert(0, "順位", range(1, len(unclassified_result) + 1))

        elapsed = time.perf_counter() - start
        hit_count = int(classified["辞書ヒット"].sum())

        summary = pd.DataFrame([
            ("解析対象", "歯牙障害"),
            ("辞書登録語数", len(dictionary)),
            ("分類対象語レコード数", len(classified)),
            ("辞書ヒット件数", hit_count),
            ("未分類件数", len(classified) - hit_count),
            ("辞書ヒット率(%)", round(hit_count / len(classified) * 100, 4) if len(classified) else 0),
            ("対象事例数", total_cases),
            ("処理時間(秒)", round(elapsed, 3)),
            ("ジャッカード係数", "使用しない"),
            ("次のStep", "Step3-7_歯牙障害_特徴語抽出.py"),
        ], columns=["項目", "値"])

        save_csv(classified, OUTPUT_CLASSIFIED)
        save_csv(category, OUTPUT_CATEGORY)
        save_csv(case_result, OUTPUT_CASE)
        save_csv(unclassified_result, OUTPUT_UNCLASSIFIED)
        save_csv(summary, OUTPUT_SUMMARY)

        print(category.head(30).to_string(index=False))
        print("\n正常終了")
        print("次: Step3-7_歯牙障害_特徴語抽出.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
