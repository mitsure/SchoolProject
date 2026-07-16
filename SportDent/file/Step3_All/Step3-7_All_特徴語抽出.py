#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-7_All_特徴語抽出

【目的】
Step3-5で作成したストップワード除去後の解析用語集合と、
Step3-6で作成したカテゴリ分類結果を使用し、
傷害種別ごとの特徴語および特徴カテゴリを抽出する。

【配置】
Meikai/file/Step3_All/
└─ Step3-7_All_特徴語抽出.py

【入力】
Meikai/DB/
└─ shougai(2025.01.31).csv

Meikai/CreateData/Step3_All/
├─ Step3-5_All_ストップワード除去.csv
├─ Step3-6_All_カテゴリ分類.csv
└─ Step3-6_All_事例別カテゴリ.csv

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-7_All_傷害種別別特徴語.csv
├─ Step3-7_All_全体特徴語.csv
├─ Step3-7_All_傷害種別別特徴カテゴリ.csv
├─ Step3-7_All_事例別特徴データ.csv
└─ Step3-7_All_解析サマリー.csv

【解析方法】
1. TF-IDFによる傷害種別別特徴語抽出
2. 全体TF-IDF平均による全体特徴語抽出
3. 傷害種別別カテゴリ出現率集計
4. Step4用の事例別特徴集合生成

【ジャッカード係数】
使用しない。

【理由】
本Stepはジャッカード解析へ渡す特徴データを作成する段階であり、
類似度そのものは計算しないため。

【必要ライブラリ】
python -m pip install pandas numpy scikit-learn

【上書き】
同名CSVがある場合は上書きする。

【実行】
python file/Step3_All/Step3-7_All_特徴語抽出.py

【次のStep】
Step3-1_歯牙障害_形態素解析.py
==============================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


# ------------------------------------------------------------------------------
# パス設定
# ------------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.csv_reader import load_csv
from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns


# ------------------------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------------------------

INPUT_ORIGINAL_CSV = (
    PROJECT_ROOT
    / "DB"
    / "shougai(2025.01.31).csv"
)

INPUT_CLEAN_WORDS_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-5_All_ストップワード除去.csv"
)

INPUT_CLASSIFIED_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-6_All_カテゴリ分類.csv"
)

INPUT_CASE_CATEGORY_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-6_All_事例別カテゴリ.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_All"

OUTPUT_CATEGORY_WORDS_CSV = (
    OUTPUT_DIR / "Step3-7_All_傷害種別別特徴語.csv"
)

OUTPUT_ALL_WORDS_CSV = (
    OUTPUT_DIR / "Step3-7_All_全体特徴語.csv"
)

OUTPUT_CATEGORY_FEATURES_CSV = (
    OUTPUT_DIR / "Step3-7_All_傷害種別別特徴カテゴリ.csv"
)

OUTPUT_CASE_FEATURES_CSV = (
    OUTPUT_DIR / "Step3-7_All_事例別特徴データ.csv"
)

OUTPUT_SUMMARY_CSV = (
    OUTPUT_DIR / "Step3-7_All_解析サマリー.csv"
)

ID_COLUMN = "記号"
INJURY_COLUMN = "種別"
CLEAN_WORDS_COLUMN = "解析用語集合"

TOP_N_WORDS_PER_INJURY = 100
TOP_N_ALL_WORDS = 300

MIN_DOCUMENT_FREQUENCY = 2


# ------------------------------------------------------------------------------
# 入力確認
# ------------------------------------------------------------------------------

def validate_files() -> None:
    """必要な入力ファイルが揃っているか確認する。"""
    required_files = [
        INPUT_ORIGINAL_CSV,
        INPUT_CLEAN_WORDS_CSV,
        INPUT_CLASSIFIED_CSV,
        INPUT_CASE_CATEGORY_CSV,
    ]

    missing_files = [
        path
        for path in required_files
        if not path.exists()
    ]

    if missing_files:
        message = "\n".join(str(path) for path in missing_files)

        raise FileNotFoundError(
            "必要な入力ファイルが見つかりません。\n"
            f"{message}\n"
            "Step3-5およびStep3-6まで完了しているか確認してください。"
        )


def load_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """全入力CSVを読み込む。"""
    original = load_csv(INPUT_ORIGINAL_CSV)

    clean_words = pd.read_csv(
        INPUT_CLEAN_WORDS_CSV,
        encoding="utf-8-sig",
    )

    classified = pd.read_csv(
        INPUT_CLASSIFIED_CSV,
        encoding="utf-8-sig",
    )

    case_category = pd.read_csv(
        INPUT_CASE_CATEGORY_CSV,
        encoding="utf-8-sig",
    )

    require_columns(
        original,
        [ID_COLUMN, INJURY_COLUMN],
    )

    require_columns(
        clean_words,
        [ID_COLUMN, CLEAN_WORDS_COLUMN],
    )

    require_columns(
        classified,
        [
            ID_COLUMN,
            "基本形",
            "品詞",
            "カテゴリ",
            "サブカテゴリ",
            "辞書ヒット",
        ],
    )

    require_columns(
        case_category,
        [
            ID_COLUMN,
            "カテゴリ集合",
            "サブカテゴリ集合",
            "カテゴリ特徴集合",
        ],
    )

    return original, clean_words, classified, case_category


# ------------------------------------------------------------------------------
# データ統合
# ------------------------------------------------------------------------------

def create_base_data(
    original: pd.DataFrame,
    clean_words: pd.DataFrame,
    case_category: pd.DataFrame,
) -> pd.DataFrame:
    """
    元データ、解析用語集合、カテゴリ集合を記号で結合する。
    """
    base = (
        original[
            [
                ID_COLUMN,
                INJURY_COLUMN,
            ]
        ]
        .merge(
            clean_words[
                [
                    ID_COLUMN,
                    CLEAN_WORDS_COLUMN,
                    "除去前語数",
                    "除去後語数",
                    "解析用語異なり語数",
                ]
            ],
            on=ID_COLUMN,
            how="left",
        )
        .merge(
            case_category[
                [
                    ID_COLUMN,
                    "カテゴリ集合",
                    "サブカテゴリ集合",
                    "カテゴリ特徴集合",
                ]
            ],
            on=ID_COLUMN,
            how="left",
        )
    )

    base[INJURY_COLUMN] = (
        base[INJURY_COLUMN]
        .fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )

    base[CLEAN_WORDS_COLUMN] = (
        base[CLEAN_WORDS_COLUMN]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    for column in (
        "カテゴリ集合",
        "サブカテゴリ集合",
        "カテゴリ特徴集合",
    ):
        base[column] = (
            base[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return base


# ------------------------------------------------------------------------------
# TF-IDF
# ------------------------------------------------------------------------------

def create_tfidf(
    texts: pd.Series,
) -> tuple[TfidfVectorizer, object]:
    """
    空白区切りの解析用語集合からTF-IDF行列を作成する。
    """
    vectorizer = TfidfVectorizer(
        tokenizer=str.split,
        preprocessor=None,
        token_pattern=None,
        lowercase=False,
        min_df=MIN_DOCUMENT_FREQUENCY,
        norm="l2",
        use_idf=True,
        smooth_idf=True,
        sublinear_tf=False,
    )

    matrix = vectorizer.fit_transform(
        texts.fillna("")
    )

    return vectorizer, matrix


def create_injury_feature_words(
    base: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    matrix: object,
) -> pd.DataFrame:
    """
    傷害種別ごとに平均TF-IDF上位語を抽出する。
    """
    terms = np.array(
        vectorizer.get_feature_names_out()
    )

    rows: list[dict] = []

    for injury_type, indices in base.groupby(
        INJURY_COLUMN,
        dropna=False,
    ).groups.items():
        index_list = list(indices)

        category_matrix = matrix[index_list]

        mean_scores = np.asarray(
            category_matrix.mean(axis=0)
        ).ravel()

        document_frequency = np.asarray(
            (category_matrix > 0).sum(axis=0)
        ).ravel()

        order = mean_scores.argsort()[::-1]

        rank = 0

        for term_index in order:
            score = float(mean_scores[term_index])

            if score <= 0:
                continue

            rank += 1

            rows.append(
                {
                    "傷害種別": injury_type,
                    "順位": rank,
                    "特徴語": terms[term_index],
                    "平均TF-IDF": round(score, 8),
                    "出現事例数": int(
                        document_frequency[term_index]
                    ),
                    "カテゴリ事例数": len(index_list),
                    "カテゴリ内出現率(%)": round(
                        document_frequency[term_index]
                        / len(index_list)
                        * 100,
                        4,
                    ),
                }
            )

            if rank >= TOP_N_WORDS_PER_INJURY:
                break

    return pd.DataFrame(rows)


def create_all_feature_words(
    base: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    matrix: object,
) -> pd.DataFrame:
    """
    全事例を対象に平均TF-IDF上位語を抽出する。
    """
    terms = np.array(
        vectorizer.get_feature_names_out()
    )

    mean_scores = np.asarray(
        matrix.mean(axis=0)
    ).ravel()

    document_frequency = np.asarray(
        (matrix > 0).sum(axis=0)
    ).ravel()

    order = mean_scores.argsort()[::-1]

    rows: list[dict] = []

    rank = 0

    for term_index in order:
        score = float(mean_scores[term_index])

        if score <= 0:
            continue

        rank += 1

        rows.append(
            {
                "順位": rank,
                "特徴語": terms[term_index],
                "平均TF-IDF": round(score, 8),
                "出現事例数": int(
                    document_frequency[term_index]
                ),
                "対象事例数": len(base),
                "事例出現率(%)": round(
                    document_frequency[term_index]
                    / len(base)
                    * 100,
                    4,
                ),
            }
        )

        if rank >= TOP_N_ALL_WORDS:
            break

    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------
# 傷害種別別カテゴリ特徴
# ------------------------------------------------------------------------------

def create_injury_category_features(
    original: pd.DataFrame,
    classified: pd.DataFrame,
) -> pd.DataFrame:
    """
    傷害種別ごとにカテゴリ・サブカテゴリの
    出現回数、出現事例数、カテゴリ内出現率を集計する。
    """
    injury_data = original[
        [
            ID_COLUMN,
            INJURY_COLUMN,
        ]
    ].copy()

    work = classified[
        classified["辞書ヒット"] == True
    ].copy()

    work = work.merge(
        injury_data,
        on=ID_COLUMN,
        how="left",
    )

    work[INJURY_COLUMN] = (
        work[INJURY_COLUMN]
        .fillna("欠損")
        .astype(str)
        .str.strip()
        .replace("", "欠損")
    )

    token_counts = (
        work
        .groupby(
            [
                INJURY_COLUMN,
                "カテゴリ",
                "サブカテゴリ",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="出現回数")
    )

    case_counts = (
        work[
            [
                ID_COLUMN,
                INJURY_COLUMN,
                "カテゴリ",
                "サブカテゴリ",
            ]
        ]
        .drop_duplicates()
        .groupby(
            [
                INJURY_COLUMN,
                "カテゴリ",
                "サブカテゴリ",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="出現事例数")
    )

    result = token_counts.merge(
        case_counts,
        on=[
            INJURY_COLUMN,
            "カテゴリ",
            "サブカテゴリ",
        ],
        how="inner",
    )

    injury_totals = (
        injury_data
        .groupby(INJURY_COLUMN)
        .size()
        .to_dict()
    )

    result["カテゴリ事例数"] = (
        result[INJURY_COLUMN]
        .map(injury_totals)
        .fillna(0)
        .astype(int)
    )

    result["カテゴリ内出現率(%)"] = np.where(
        result["カテゴリ事例数"] > 0,
        (
            result["出現事例数"]
            / result["カテゴリ事例数"]
            * 100
        ).round(4),
        0,
    )

    result["傷害種別内順位"] = (
        result
        .groupby(INJURY_COLUMN)["出現事例数"]
        .rank(
            method="min",
            ascending=False,
        )
        .astype(int)
    )

    result = result.sort_values(
        [
            INJURY_COLUMN,
            "傷害種別内順位",
            "出現事例数",
            "出現回数",
        ],
        ascending=[
            True,
            True,
            False,
            False,
        ],
    ).reset_index(drop=True)

    result = result.rename(
        columns={
            INJURY_COLUMN: "傷害種別",
        }
    )

    return result[
        [
            "傷害種別",
            "傷害種別内順位",
            "カテゴリ",
            "サブカテゴリ",
            "出現回数",
            "出現事例数",
            "カテゴリ事例数",
            "カテゴリ内出現率(%)",
        ]
    ]


# ------------------------------------------------------------------------------
# Step4用の事例別特徴データ
# ------------------------------------------------------------------------------

def create_case_feature_data(
    base: pd.DataFrame,
) -> pd.DataFrame:
    """
    Step4のジャッカード解析へ渡す事例別特徴データを作成する。
    """
    result = base.copy()

    result["語特徴集合"] = result[CLEAN_WORDS_COLUMN]

    result["統合特徴集合"] = result.apply(
        lambda row: " | ".join(
            item
            for item in (
                row["語特徴集合"],
                row["カテゴリ特徴集合"],
            )
            if item
        ),
        axis=1,
    )

    return result[
        [
            ID_COLUMN,
            INJURY_COLUMN,
            "除去前語数",
            "除去後語数",
            "解析用語異なり語数",
            "語特徴集合",
            "カテゴリ集合",
            "サブカテゴリ集合",
            "カテゴリ特徴集合",
            "統合特徴集合",
        ]
    ].rename(
        columns={
            INJURY_COLUMN: "傷害種別",
        }
    )


# ------------------------------------------------------------------------------
# サマリー
# ------------------------------------------------------------------------------

def create_analysis_summary(
    base: pd.DataFrame,
    injury_words: pd.DataFrame,
    all_words: pd.DataFrame,
    injury_categories: pd.DataFrame,
    case_features: pd.DataFrame,
    vectorizer: TfidfVectorizer,
    elapsed_seconds: float,
) -> pd.DataFrame:
    """
    Step3-7の解析概要を作成する。
    """
    empty_word_cases = int(
        base[CLEAN_WORDS_COLUMN].eq("").sum()
    )

    empty_category_cases = int(
        base["カテゴリ特徴集合"].eq("").sum()
    )

    summary_rows = [
        ("元データ入力件数", len(base)),
        (
            "傷害種別数",
            int(base[INJURY_COLUMN].nunique(dropna=False)),
        ),
        (
            "TF-IDF対象語数",
            len(vectorizer.get_feature_names_out()),
        ),
        (
            "傷害種別別特徴語出力行数",
            len(injury_words),
        ),
        ("全体特徴語出力行数", len(all_words)),
        (
            "傷害種別別特徴カテゴリ出力行数",
            len(injury_categories),
        ),
        ("事例別特徴データ出力件数", len(case_features)),
        (
            "解析用語集合が空の事例数",
            empty_word_cases,
        ),
        (
            "カテゴリ特徴集合が空の事例数",
            empty_category_cases,
        ),
        (
            "傷害種別別特徴語上限",
            TOP_N_WORDS_PER_INJURY,
        ),
        (
            "全体特徴語上限",
            TOP_N_ALL_WORDS,
        ),
        (
            "TF-IDF最小文書頻度",
            MIN_DOCUMENT_FREQUENCY,
        ),
        (
            "処理時間(秒)",
            round(elapsed_seconds, 3),
        ),
        ("ジャッカード係数", "使用しない"),
        (
            "次のStep",
            "Step3-1_歯牙障害_形態素解析.py",
        ),
    ]

    return pd.DataFrame(
        summary_rows,
        columns=["項目", "値"],
    )


# ------------------------------------------------------------------------------
# コンソール表示
# ------------------------------------------------------------------------------

def print_injury_word_preview(
    injury_words: pd.DataFrame,
    top_n: int = 10,
) -> None:
    """
    傷害種別ごとの特徴語上位を表示する。
    """
    print(
        f"\n[傷害種別別特徴語: 各上位{top_n}語]"
    )

    for injury_type, group in injury_words.groupby(
        "傷害種別",
        sort=False,
    ):
        print(f"\n--- {injury_type} ---")

        print(
            group
            .head(top_n)
            .to_string(
                index=False,
                formatters={
                    "平均TF-IDF": (
                        lambda value: f"{float(value):.8f}"
                    ),
                    "出現事例数": (
                        lambda value: f"{int(value):,}"
                    ),
                    "カテゴリ事例数": (
                        lambda value: f"{int(value):,}"
                    ),
                    "カテゴリ内出現率(%)": (
                        lambda value: f"{float(value):.4f}"
                    ),
                },
            )
        )


# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-7_All_特徴語抽出を開始します")
    print("解析方法      : TF-IDFおよびカテゴリ出現率")
    print("ジャッカード  : 使用しない")
    print("=" * 78)

    try:
        validate_files()

        (
            original,
            clean_words,
            classified,
            case_category,
        ) = load_inputs()

        base = create_base_data(
            original,
            clean_words,
            case_category,
        )

        if base[CLEAN_WORDS_COLUMN].eq("").all():
            raise ValueError(
                "すべての解析用語集合が空です。"
                "Step3-5の出力を確認してください。"
            )

        vectorizer, matrix = create_tfidf(
            base[CLEAN_WORDS_COLUMN],
        )

        injury_words = create_injury_feature_words(
            base,
            vectorizer,
            matrix,
        )

        all_words = create_all_feature_words(
            base,
            vectorizer,
            matrix,
        )

        injury_categories = create_injury_category_features(
            original,
            classified,
        )

        case_features = create_case_feature_data(
            base,
        )

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            base,
            injury_words,
            all_words,
            injury_categories,
            case_features,
            vectorizer,
            elapsed_seconds,
        )

        save_csv(
            injury_words,
            OUTPUT_CATEGORY_WORDS_CSV,
        )

        save_csv(
            all_words,
            OUTPUT_ALL_WORDS_CSV,
        )

        save_csv(
            injury_categories,
            OUTPUT_CATEGORY_FEATURES_CSV,
        )

        save_csv(
            case_features,
            OUTPUT_CASE_FEATURES_CSV,
        )

        save_csv(
            analysis_summary,
            OUTPUT_SUMMARY_CSV,
        )

        print_injury_word_preview(
            injury_words,
            top_n=10,
        )

        print("\n[全体特徴語: 上位30語]")
        print(
            all_words
            .head(30)
            .to_string(
                index=False,
                formatters={
                    "平均TF-IDF": (
                        lambda value: f"{float(value):.8f}"
                    ),
                    "出現事例数": (
                        lambda value: f"{int(value):,}"
                    ),
                    "対象事例数": (
                        lambda value: f"{int(value):,}"
                    ),
                    "事例出現率(%)": (
                        lambda value: f"{float(value):.4f}"
                    ),
                },
            )
        )

        print("\n" + "-" * 78)
        print("Step3-7_All_特徴語抽出 正常終了")
        print("-" * 78)
        print(f"対象事例数               : {len(base):,}件")
        print(
            f"傷害種別数               : "
            f"{base[INJURY_COLUMN].nunique(dropna=False):,}種類"
        )
        print(
            f"TF-IDF対象語数           : "
            f"{len(vectorizer.get_feature_names_out()):,}語"
        )
        print(
            f"傷害種別別特徴語行数     : "
            f"{len(injury_words):,}行"
        )
        print(
            f"全体特徴語行数           : "
            f"{len(all_words):,}行"
        )
        print(
            f"傷害種別別特徴カテゴリ数 : "
            f"{len(injury_categories):,}行"
        )
        print(
            f"事例別特徴データ件数     : "
            f"{len(case_features):,}件"
        )
        print(f"処理時間                 : {elapsed_seconds:.2f}秒")
        print()
        print(f"傷害種別別特徴語CSV       : {OUTPUT_CATEGORY_WORDS_CSV}")
        print(f"全体特徴語CSV             : {OUTPUT_ALL_WORDS_CSV}")
        print(
            f"傷害種別別特徴カテゴリCSV : "
            f"{OUTPUT_CATEGORY_FEATURES_CSV}"
        )
        print(f"事例別特徴データCSV       : {OUTPUT_CASE_FEATURES_CSV}")
        print(f"解析サマリーCSV           : {OUTPUT_SUMMARY_CSV}")
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep: Step3-1_歯牙障害_形態素解析.py")
        print("-" * 78)

    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(1)

    except Exception as error:
        print("\n[処理中にエラーが発生しました]")
        print(f"{type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
