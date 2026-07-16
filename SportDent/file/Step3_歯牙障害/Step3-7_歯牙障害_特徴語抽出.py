#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3-7_歯牙障害_特徴語抽出

歯牙障害内の特徴語、カテゴリ特徴、事例別特徴集合を作る。
ジャッカード係数は使用しない。
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import pandas as pd
import unicodedata

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

EXPECTED_INPUT_NAME = (
    "Step2-1_傷害カテゴリ別解析_歯牙障害抽出.csv"
)

EXPECTED_INPUT_NAME_NFC = unicodedata.normalize(
    "NFC",
    EXPECTED_INPUT_NAME,
)

INPUT_CANDIDATES = [
    path
    for path in (
        PROJECT_ROOT
        / "CreateData"
    ).rglob("*.csv")
    if unicodedata.normalize(
        "NFC",
        path.name,
    ) == EXPECTED_INPUT_NAME_NFC
]

if len(INPUT_CANDIDATES) == 1:
    INPUT_ORIGINAL = INPUT_CANDIDATES[0]

elif len(INPUT_CANDIDATES) == 0:
    raise FileNotFoundError(
        "歯牙障害抽出CSVが見つかりません。"
        f"検索開始位置: {PROJECT_ROOT / 'CreateData'}"
    )

else:
    raise RuntimeError(
        "歯牙障害抽出CSVが複数見つかりました。"
        f"候補: {[str(path) for path in INPUT_CANDIDATES]}"
    )

if len(INPUT_CANDIDATES) == 1:
    INPUT_ORIGINAL = INPUT_CANDIDATES[0]
elif len(INPUT_CANDIDATES) == 0:
    raise FileNotFoundError(
        f"歯牙障害抽出CSVが見つかりません: {INPUT_DIR}"
    )
else:
    raise RuntimeError(
        f"歯牙障害抽出CSVが複数見つかりました: {INPUT_CANDIDATES}"
    )

INPUT_CLEAN = OUTPUT_DIR / "Step3-5_歯牙障害_ストップワード除去.csv"
INPUT_CLASSIFIED = OUTPUT_DIR / "Step3-6_歯牙障害_カテゴリ分類.csv"
INPUT_CASE_CATEGORY = OUTPUT_DIR / "Step3-6_歯牙障害_事例別カテゴリ.csv"

OUTPUT_WORDS = OUTPUT_DIR / "Step3-7_歯牙障害_特徴語.csv"
OUTPUT_CATEGORY = OUTPUT_DIR / "Step3-7_歯牙障害_特徴カテゴリ.csv"
OUTPUT_CASE = OUTPUT_DIR / "Step3-7_歯牙障害_事例別特徴データ.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step3-7_歯牙障害_解析サマリー.csv"

TOP_N = 300
MIN_DF = 2

def main():
    start = time.perf_counter()
    print("=" * 78)
    print("Step3-7_歯牙障害_特徴語抽出")
    print("ジャッカード係数: 使用しない")
    print("=" * 78)

    try:
        for path in (INPUT_ORIGINAL, INPUT_CLEAN, INPUT_CLASSIFIED, INPUT_CASE_CATEGORY):
            if not path.exists():
                raise FileNotFoundError(f"必要ファイルがありません: {path}")

        original = pd.read_csv(INPUT_ORIGINAL, encoding="utf-8-sig")
        clean = pd.read_csv(INPUT_CLEAN, encoding="utf-8-sig")
        classified = pd.read_csv(INPUT_CLASSIFIED, encoding="utf-8-sig")
        case_category = pd.read_csv(INPUT_CASE_CATEGORY, encoding="utf-8-sig")

        require_columns(original, ["記号", "種別"])
        require_columns(clean, ["記号", "解析用語集合", "除去前語数", "除去後語数", "解析用語異なり語数"])
        require_columns(classified, ["記号", "カテゴリ", "サブカテゴリ", "辞書ヒット"])
        require_columns(case_category, ["記号", "カテゴリ集合", "サブカテゴリ集合", "カテゴリ特徴集合"])

        if (original["種別"].fillna("").astype(str).str.strip() != "歯牙障害").any():
            raise ValueError("歯牙障害以外が含まれています。")

        base = (
            original[["記号", "種別"]]
            .merge(clean, on="記号", how="left")
            .merge(case_category, on="記号", how="left")
        )

        base["解析用語集合"] = base["解析用語集合"].fillna("").astype(str)
        base["カテゴリ集合"] = base["カテゴリ集合"].fillna("").astype(str)
        base["サブカテゴリ集合"] = base["サブカテゴリ集合"].fillna("").astype(str)
        base["カテゴリ特徴集合"] = base["カテゴリ特徴集合"].fillna("").astype(str)

        if base["解析用語集合"].eq("").all():
            raise ValueError("解析用語集合がすべて空です。")

        vectorizer = TfidfVectorizer(
            tokenizer=str.split,
            preprocessor=None,
            token_pattern=None,
            lowercase=False,
            min_df=MIN_DF
        )
        matrix = vectorizer.fit_transform(base["解析用語集合"])
        terms = np.array(vectorizer.get_feature_names_out())

        mean_scores = np.asarray(matrix.mean(axis=0)).ravel()
        doc_freq = np.asarray((matrix > 0).sum(axis=0)).ravel()
        order = mean_scores.argsort()[::-1]

        rows = []
        rank = 0
        for idx in order:
            if mean_scores[idx] <= 0:
                continue
            rank += 1
            rows.append({
                "順位": rank,
                "特徴語": terms[idx],
                "平均TF-IDF": round(float(mean_scores[idx]), 8),
                "出現事例数": int(doc_freq[idx]),
                "対象事例数": len(base),
                "事例出現率(%)": round(doc_freq[idx] / len(base) * 100, 4),
            })
            if rank >= TOP_N:
                break

        feature_words = pd.DataFrame(rows)

        hit = classified[classified["辞書ヒット"] == True].copy()
        a = hit.groupby(["カテゴリ", "サブカテゴリ"]).size().reset_index(name="出現回数")
        b = (
            hit[["記号", "カテゴリ", "サブカテゴリ"]]
            .drop_duplicates()
            .groupby(["カテゴリ", "サブカテゴリ"])
            .size().reset_index(name="出現事例数")
        )
        category = a.merge(b, on=["カテゴリ", "サブカテゴリ"])
        category["事例出現率(%)"] = (
            category["出現事例数"] / len(base) * 100
        ).round(4)
        category = category.sort_values(
            ["出現事例数", "出現回数"],
            ascending=[False, False]
        ).reset_index(drop=True)
        category.insert(0, "順位", range(1, len(category) + 1))

        case_features = base.copy()
        case_features["語特徴集合"] = case_features["解析用語集合"]
        case_features["統合特徴集合"] = case_features.apply(
            lambda row: " | ".join(
                x for x in (
                    row["語特徴集合"],
                    row["カテゴリ特徴集合"]
                ) if x
            ),
            axis=1
        )
        case_features = case_features[
            [
                "記号", "種別", "除去前語数", "除去後語数",
                "解析用語異なり語数", "語特徴集合",
                "カテゴリ集合", "サブカテゴリ集合",
                "カテゴリ特徴集合", "統合特徴集合"
            ]
        ]

        elapsed = time.perf_counter() - start

        summary = pd.DataFrame([
            ("解析対象", "歯牙障害"),
            ("対象事例数", len(base)),
            ("TF-IDF対象語数", len(terms)),
            ("特徴語出力行数", len(feature_words)),
            ("特徴カテゴリ出力行数", len(category)),
            ("事例別特徴データ件数", len(case_features)),
            ("処理時間(秒)", round(elapsed, 3)),
            ("ジャッカード係数", "使用しない"),
            ("次のStep", "Step4_Jaccard解析"),
        ], columns=["項目", "値"])

        save_csv(feature_words, OUTPUT_WORDS)
        save_csv(category, OUTPUT_CATEGORY)
        save_csv(case_features, OUTPUT_CASE)
        save_csv(summary, OUTPUT_SUMMARY)

        print(feature_words.head(30).to_string(index=False))
        print("\n正常終了")
        print("Step3_歯牙障害 完了")
        print("次: Step4_Jaccard解析")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
