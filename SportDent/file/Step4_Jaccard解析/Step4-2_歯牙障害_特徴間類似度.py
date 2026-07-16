#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4-2_Jaccard解析_歯牙障害_特徴間類似度

Step3-7_歯牙障害の事例別特徴データから、特徴同士の出現事例集合を作り、
語特徴・カテゴリ特徴・統合特徴ごとにジャッカード係数を計算する。

ジャッカード係数:
使用する。
"""


from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step4_Jaccard解析"


def parse_feature_set(value: object) -> set[str]:
    """空白区切りと縦線区切りの特徴文字列を集合へ変換する。"""
    if pd.isna(value):
        return set()

    text = str(value).strip()
    if not text:
        return set()

    normalized = text.replace(" | ", " ").replace("|", " ")
    return {item.strip() for item in normalized.split() if item.strip()}


def jaccard(set_a: set[str], set_b: set[str]) -> float:
    """2集合のジャッカード係数を計算する。"""
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def build_binary_matrix(
    feature_sets: list[set[str]],
) -> tuple[csr_matrix, list[str]]:
    """特徴集合一覧から事例×特徴の二値疎行列を作成する。"""
    vocabulary = sorted(set().union(*feature_sets)) if feature_sets else []
    feature_to_index = {feature: i for i, feature in enumerate(vocabulary)}

    rows = []
    cols = []

    for row_index, features in enumerate(feature_sets):
        for feature in features:
            rows.append(row_index)
            cols.append(feature_to_index[feature])

    data = np.ones(len(rows), dtype=np.uint8)

    matrix = csr_matrix(
        (data, (rows, cols)),
        shape=(len(feature_sets), len(vocabulary)),
        dtype=np.uint8,
    )

    return matrix, vocabulary


def top_k_case_jaccard(
    ids: list[object],
    feature_sets: list[set[str]],
    top_k: int,
    minimum_score: float,
    block_size: int = 300,
) -> pd.DataFrame:
    """
    疎行列積を使い、各事例について上位K件の類似事例だけを返す。

    全N×N結果を保存しないため、全件データでもファイルが爆発しにくい。
    """
    matrix, _ = build_binary_matrix(feature_sets)
    sizes = np.asarray(matrix.sum(axis=1)).ravel().astype(np.int32)
    total = len(ids)
    rows = []

    for start in range(0, total, block_size):
        end = min(start + block_size, total)

        intersections = (
            matrix[start:end]
            .dot(matrix.T)
            .toarray()
            .astype(np.float32)
        )

        block_sizes = sizes[start:end, None]
        unions = block_sizes + sizes[None, :] - intersections

        scores = np.divide(
            intersections,
            unions,
            out=np.zeros_like(intersections, dtype=np.float32),
            where=unions > 0,
        )

        for local_index, source_index in enumerate(range(start, end)):
            scores[local_index, source_index] = -1.0

            valid_indices = np.where(
                scores[local_index] >= minimum_score
            )[0]

            if valid_indices.size == 0:
                continue

            if valid_indices.size > top_k:
                selected_local = np.argpartition(
                    scores[local_index, valid_indices],
                    -top_k,
                )[-top_k:]
                selected = valid_indices[selected_local]
            else:
                selected = valid_indices

            selected = selected[
                np.argsort(scores[local_index, selected])[::-1]
            ]

            for rank, target_index in enumerate(selected, start=1):
                source_features = feature_sets[source_index]
                target_features = feature_sets[target_index]
                common = sorted(source_features & target_features)

                rows.append(
                    {
                        "基準記号": ids[source_index],
                        "類似順位": rank,
                        "類似記号": ids[target_index],
                        "ジャッカード係数": round(
                            float(scores[local_index, target_index]),
                            6,
                        ),
                        "共通特徴数": len(common),
                        "和集合特徴数": len(
                            source_features | target_features
                        ),
                        "基準特徴数": len(source_features),
                        "類似特徴数": len(target_features),
                        "共通特徴": " | ".join(common),
                    }
                )

    return pd.DataFrame(rows)


def feature_pair_jaccard(
    ids: list[object],
    feature_sets: list[set[str]],
    minimum_cases: int,
    minimum_score: float,
) -> pd.DataFrame:
    """
    特徴ごとの出現事例集合を作り、特徴ペアのジャッカード係数を算出する。
    """
    inverted: dict[str, set[int]] = defaultdict(set)

    for case_index, features in enumerate(feature_sets):
        for feature in features:
            inverted[feature].add(case_index)

    eligible = {
        feature: cases
        for feature, cases in inverted.items()
        if len(cases) >= minimum_cases
    }

    features = sorted(eligible)
    rows = []

    for i, feature_a in enumerate(features):
        cases_a = eligible[feature_a]

        for feature_b in features[i + 1:]:
            cases_b = eligible[feature_b]
            intersection = len(cases_a & cases_b)

            if intersection == 0:
                continue

            union = len(cases_a | cases_b)
            score = intersection / union

            if score < minimum_score:
                continue

            rows.append(
                {
                    "特徴1": feature_a,
                    "特徴2": feature_b,
                    "ジャッカード係数": round(score, 6),
                    "共通出現事例数": intersection,
                    "特徴1出現事例数": len(cases_a),
                    "特徴2出現事例数": len(cases_b),
                    "和集合事例数": union,
                    "対象事例数": len(ids),
                }
            )

    result = pd.DataFrame(rows)

    if result.empty:
        return pd.DataFrame(
            columns=[
                "順位",
                "特徴1",
                "特徴2",
                "ジャッカード係数",
                "共通出現事例数",
                "特徴1出現事例数",
                "特徴2出現事例数",
                "和集合事例数",
                "対象事例数",
            ]
        )

    result = result.sort_values(
        ["ジャッカード係数", "共通出現事例数"],
        ascending=[False, False],
    ).reset_index(drop=True)

    result.insert(0, "順位", range(1, len(result) + 1))
    return result


INPUT_CSV = (
    PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"
    / "Step3-7_歯牙障害_事例別特徴データ.csv"
)

OUTPUT_WORD = OUTPUT_DIR / "Step4-2_歯牙障害_語特徴間Jaccard.csv"
OUTPUT_CATEGORY = OUTPUT_DIR / "Step4-2_歯牙障害_カテゴリ特徴間Jaccard.csv"
OUTPUT_COMBINED = OUTPUT_DIR / "Step4-2_歯牙障害_統合特徴間Jaccard.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step4-2_歯牙障害_解析サマリー.csv"

MIN_CASES = 3
MIN_SCORE = 0.05


def run_for_column(
    dataframe: pd.DataFrame,
    column: str,
    output_path: Path,
) -> pd.DataFrame:
    feature_sets = dataframe[column].map(parse_feature_set).tolist()

    result = feature_pair_jaccard(
        dataframe["記号"].tolist(),
        feature_sets,
        MIN_CASES,
        MIN_SCORE,
    )

    save_csv(result, output_path)
    return result


def main() -> None:
    start = time.perf_counter()
    print("=" * 78)
    print("Step4-2 歯牙障害 特徴間Jaccard")
    print("ジャッカード係数: 使用する")
    print("=" * 78)

    try:
        if not INPUT_CSV.exists():
            raise FileNotFoundError(f"入力CSVがありません: {INPUT_CSV}")

        df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
        require_columns(
            df,
            ["記号", "語特徴集合", "カテゴリ特徴集合", "統合特徴集合"],
        )

        word = run_for_column(df, "語特徴集合", OUTPUT_WORD)
        category = run_for_column(df, "カテゴリ特徴集合", OUTPUT_CATEGORY)
        combined = run_for_column(df, "統合特徴集合", OUTPUT_COMBINED)

        elapsed = time.perf_counter() - start

        summary = pd.DataFrame(
            [
                ("解析対象", "歯牙障害"),
                ("対象事例数", len(df)),
                ("最小出現事例数", MIN_CASES),
                ("最小Jaccard", MIN_SCORE),
                ("語特徴ペア数", len(word)),
                ("カテゴリ特徴ペア数", len(category)),
                ("統合特徴ペア数", len(combined)),
                ("処理時間(秒)", round(elapsed, 3)),
                ("ジャッカード係数", "使用する"),
                ("次のStep", "Step4-3_All_事例間類似度.py"),
            ],
            columns=["項目", "値"],
        )
        save_csv(summary, OUTPUT_SUMMARY)

        print("\n[統合特徴 上位30組]")
        print(combined.head(30).to_string(index=False))
        print("\n正常終了")
        print("次: Step4-3_All_事例間類似度.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
