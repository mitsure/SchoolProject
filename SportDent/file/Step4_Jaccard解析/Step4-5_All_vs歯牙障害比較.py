#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step4-5_Jaccard解析_All_vs歯牙障害比較

All全体の代表特徴集合と歯牙障害の代表特徴集合を作り、
語特徴・カテゴリ特徴・統合特徴ごとにジャッカード係数を比較する。

ジャッカード係数を使用する。
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


INPUT_ALL = (
    PROJECT_ROOT / "CreateData" / "Step3_All"
    / "Step3-7_All_事例別特徴データ.csv"
)

INPUT_DENTAL = (
    PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"
    / "Step3-7_歯牙障害_事例別特徴データ.csv"
)

OUTPUT_COMPARISON = OUTPUT_DIR / "Step4-5_All_vs歯牙障害_Jaccard比較.csv"
OUTPUT_DIFFERENCE = OUTPUT_DIR / "Step4-5_All_vs歯牙障害_特徴差分.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step4-5_All_vs歯牙障害_解析サマリー.csv"

MIN_PREVALENCE = 0.05


def representative_features(
    dataframe: pd.DataFrame,
    column: str,
) -> tuple[set[str], dict[str, float]]:
    """
    対象事例のMIN_PREVALENCE以上に出現する特徴を代表集合とする。
    """
    counts: dict[str, int] = defaultdict(int)

    for value in dataframe[column]:
        for feature in parse_feature_set(value):
            counts[feature] += 1

    prevalence = {
        feature: count / len(dataframe)
        for feature, count in counts.items()
    }

    selected = {
        feature
        for feature, rate in prevalence.items()
        if rate >= MIN_PREVALENCE
    }

    return selected, prevalence


def main() -> None:
    start = time.perf_counter()
    print("=" * 78)
    print("Step4-5 All vs 歯牙障害 Jaccard比較")
    print("=" * 78)

    try:
        for path in (INPUT_ALL, INPUT_DENTAL):
            if not path.exists():
                raise FileNotFoundError(f"入力CSVがありません: {path}")

        all_df = pd.read_csv(INPUT_ALL, encoding="utf-8-sig")
        dental_df = pd.read_csv(INPUT_DENTAL, encoding="utf-8-sig")

        columns = ["語特徴集合", "カテゴリ特徴集合", "統合特徴集合"]
        require_columns(all_df, columns)
        require_columns(dental_df, columns)

        comparison_rows = []
        difference_rows = []

        for column in columns:
            all_set, all_prevalence = representative_features(all_df, column)
            dental_set, dental_prevalence = representative_features(dental_df, column)

            common = all_set & dental_set
            all_only = all_set - dental_set
            dental_only = dental_set - all_set

            comparison_rows.append(
                {
                    "特徴種別": column,
                    "All代表特徴数": len(all_set),
                    "歯牙障害代表特徴数": len(dental_set),
                    "共通特徴数": len(common),
                    "和集合特徴数": len(all_set | dental_set),
                    "ジャッカード係数": round(
                        jaccard(all_set, dental_set),
                        6,
                    ),
                    "最小出現率": MIN_PREVALENCE,
                    "共通特徴": " | ".join(sorted(common)),
                }
            )

            all_features = sorted(all_set | dental_set)

            for feature in all_features:
                all_rate = all_prevalence.get(feature, 0.0)
                dental_rate = dental_prevalence.get(feature, 0.0)

                if feature in common:
                    status = "共通"
                elif feature in dental_only:
                    status = "歯牙障害のみ"
                else:
                    status = "Allのみ"

                difference_rows.append(
                    {
                        "特徴種別": column,
                        "特徴": feature,
                        "区分": status,
                        "All出現率(%)": round(all_rate * 100, 4),
                        "歯牙障害出現率(%)": round(dental_rate * 100, 4),
                        "出現率差_歯牙障害-All": round(
                            (dental_rate - all_rate) * 100,
                            4,
                        ),
                    }
                )

        comparison = pd.DataFrame(comparison_rows)

        differences = pd.DataFrame(difference_rows).sort_values(
            ["特徴種別", "出現率差_歯牙障害-All"],
            ascending=[True, False],
        ).reset_index(drop=True)

        elapsed = time.perf_counter() - start

        summary = pd.DataFrame(
            [
                ("All事例数", len(all_df)),
                ("歯牙障害事例数", len(dental_df)),
                ("代表特徴の最小出現率", MIN_PREVALENCE),
                ("比較特徴種別数", len(columns)),
                ("特徴差分出力行数", len(differences)),
                ("処理時間(秒)", round(elapsed, 3)),
                ("ジャッカード係数", "使用する"),
                ("次のStep", "Step5_比較評価"),
            ],
            columns=["項目", "値"],
        )

        save_csv(comparison, OUTPUT_COMPARISON)
        save_csv(differences, OUTPUT_DIFFERENCE)
        save_csv(summary, OUTPUT_SUMMARY)

        print("\n[All vs 歯牙障害]")
        print(comparison.to_string(index=False))

        print("\n[歯牙障害で高い特徴 上位30]")
        print(
            differences
            .sort_values(
                "出現率差_歯牙障害-All",
                ascending=False,
            )
            .head(30)
            .to_string(index=False)
        )

        print("\nStep4 完了")
        print("次: Step5_比較評価")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
