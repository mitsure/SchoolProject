#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-6_All_カテゴリ分類

【目的】
Step3-5で作成した残存語を、
Commonで管理するカテゴリ辞書と照合し、
語ごと・事例ごとに意味カテゴリを付与する。

【配置】
Meikai/file/Step3_All/
└─ Step3-6_All_カテゴリ分類.py

【入力】
Meikai/CreateData/Step3_All/
├─ Step3-1_All_形態素解析.csv
└─ Step3-5_All_ストップワード除去.csv

Meikai/file/Common/Config/
└─ 設定_カテゴリ辞書.csv

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-6_All_カテゴリ分類.csv
├─ Step3-6_All_カテゴリ集計.csv
├─ Step3-6_All_事例別カテゴリ.csv
├─ Step3-6_All_未分類語集計.csv
└─ Step3-6_All_解析サマリー.csv

【解析方法】
辞書照合によるカテゴリ分類

【ジャッカード係数】
使用しない。

【理由】
本Stepはカテゴリ特徴を作成する前処理であり、
類似度そのものはStep4で計算するため。

【必要ライブラリ】
python -m pip install pandas

【実行】
python file/Step3_All/Step3-6_All_カテゴリ分類.py

【次のStep】
Step3-7_All_特徴語抽出.py
==============================================================================
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


INPUT_MORPHEME_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-1_All_形態素解析.csv"
)

INPUT_STOPWORD_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-5_All_ストップワード除去.csv"
)

CATEGORY_DICTIONARY_CSV = (
    PROJECT_ROOT
    / "file"
    / "Common"
    / "Config"
    / "設定_カテゴリ辞書.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_All"

OUTPUT_CLASSIFIED_CSV = OUTPUT_DIR / "Step3-6_All_カテゴリ分類.csv"
OUTPUT_CATEGORY_SUMMARY_CSV = OUTPUT_DIR / "Step3-6_All_カテゴリ集計.csv"
OUTPUT_CASE_CATEGORY_CSV = OUTPUT_DIR / "Step3-6_All_事例別カテゴリ.csv"
OUTPUT_UNCLASSIFIED_CSV = OUTPUT_DIR / "Step3-6_All_未分類語集計.csv"
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / "Step3-6_All_解析サマリー.csv"


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """必要な3ファイルを読み込む。"""
    for path in (
        INPUT_MORPHEME_CSV,
        INPUT_STOPWORD_CSV,
        CATEGORY_DICTIONARY_CSV,
    ):
        if not path.exists():
            raise FileNotFoundError(f"必要なファイルが見つかりません: {path}")

    morpheme = pd.read_csv(INPUT_MORPHEME_CSV, encoding="utf-8-sig")
    stopword = pd.read_csv(INPUT_STOPWORD_CSV, encoding="utf-8-sig")
    dictionary = pd.read_csv(CATEGORY_DICTIONARY_CSV, encoding="utf-8-sig")

    require_columns(morpheme, ["記号", "基本形", "品詞"])
    require_columns(stopword, ["記号", "解析用語集合"])
    require_columns(dictionary, ["語", "カテゴリ", "サブカテゴリ"])

    return morpheme, stopword, dictionary


def prepare_words(morpheme: pd.DataFrame) -> pd.DataFrame:
    """
    Step3-5の解析用語集合に含まれる語だけを抽出する。
    """
    work = morpheme.copy()

    work["基本形"] = (
        work["基本形"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    work["品詞"] = (
        work["品詞"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    work = work[
        work["基本形"].ne("")
        & work["品詞"].isin({"名詞", "動詞", "形容詞"})
    ].copy()

    return work


def classify_words(
    words: pd.DataFrame,
    dictionary: pd.DataFrame,
) -> pd.DataFrame:
    """
    基本形をカテゴリ辞書へ完全一致させる。
    """
    dictionary = dictionary.copy()

    dictionary["語"] = (
        dictionary["語"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result = words.merge(
        dictionary,
        left_on="基本形",
        right_on="語",
        how="left",
    )

    result["辞書ヒット"] = result["カテゴリ"].notna()

    result["カテゴリ"] = result["カテゴリ"].fillna("未分類")
    result["サブカテゴリ"] = result["サブカテゴリ"].fillna("未分類")

    return result[
        [
            "記号",
            "基本形",
            "品詞",
            "カテゴリ",
            "サブカテゴリ",
            "辞書ヒット",
        ]
    ]


def create_category_summary(
    classified: pd.DataFrame,
) -> pd.DataFrame:
    """
    カテゴリ・サブカテゴリ別の件数と事例数を集計する。
    """
    total_cases = int(classified["記号"].nunique(dropna=False))

    token_counts = (
        classified
        .groupby(["カテゴリ", "サブカテゴリ"], dropna=False)
        .size()
        .reset_index(name="出現回数")
    )

    case_counts = (
        classified[
            ["記号", "カテゴリ", "サブカテゴリ"]
        ]
        .drop_duplicates()
        .groupby(["カテゴリ", "サブカテゴリ"], dropna=False)
        .size()
        .reset_index(name="出現事例数")
    )

    result = token_counts.merge(
        case_counts,
        on=["カテゴリ", "サブカテゴリ"],
        how="inner",
    )

    result["事例出現率(%)"] = (
        result["出現事例数"] / total_cases * 100
    ).round(4)

    result = result.sort_values(
        ["出現事例数", "出現回数", "カテゴリ", "サブカテゴリ"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    result.insert(0, "順位", range(1, len(result) + 1))
    result["対象事例数"] = total_cases

    return result


def create_case_category(
    classified: pd.DataFrame,
) -> pd.DataFrame:
    """
    事例ごとのカテゴリ集合を作成する。
    Step4のカテゴリ単位ジャッカードで使用できる。
    """
    rows = []

    for case_id, group in classified.groupby("記号", dropna=False, sort=False):
        hit_group = group[group["辞書ヒット"]].copy()

        categories = list(dict.fromkeys(hit_group["カテゴリ"].astype(str)))
        subcategories = list(
            dict.fromkeys(hit_group["サブカテゴリ"].astype(str))
        )

        category_features = [
            f"{row['カテゴリ']}:{row['サブカテゴリ']}"
            for _, row in hit_group[
                ["カテゴリ", "サブカテゴリ"]
            ].drop_duplicates().iterrows()
        ]

        rows.append(
            {
                "記号": case_id,
                "カテゴリ数": len(categories),
                "サブカテゴリ数": len(subcategories),
                "カテゴリ集合": " | ".join(categories),
                "サブカテゴリ集合": " | ".join(subcategories),
                "カテゴリ特徴集合": " | ".join(category_features),
            }
        )

    return pd.DataFrame(rows)


def create_unclassified_summary(
    classified: pd.DataFrame,
) -> pd.DataFrame:
    """
    未分類語の件数と事例数を集計する。
    辞書改善用に使用する。
    """
    work = classified[~classified["辞書ヒット"]].copy()

    if work.empty:
        return pd.DataFrame(
            columns=[
                "順位",
                "品詞",
                "基本形",
                "出現回数",
                "出現事例数",
            ]
        )

    token_counts = (
        work
        .groupby(["品詞", "基本形"], dropna=False)
        .size()
        .reset_index(name="出現回数")
    )

    case_counts = (
        work[
            ["記号", "品詞", "基本形"]
        ]
        .drop_duplicates()
        .groupby(["品詞", "基本形"], dropna=False)
        .size()
        .reset_index(name="出現事例数")
    )

    result = token_counts.merge(
        case_counts,
        on=["品詞", "基本形"],
        how="inner",
    )

    result = result.sort_values(
        ["出現事例数", "出現回数", "基本形"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    result.insert(0, "順位", range(1, len(result) + 1))

    return result


def create_analysis_summary(
    classified: pd.DataFrame,
    category_summary: pd.DataFrame,
    case_category: pd.DataFrame,
    unclassified_summary: pd.DataFrame,
    dictionary: pd.DataFrame,
    elapsed_seconds: float,
) -> pd.DataFrame:
    """解析サマリーを作成する。"""
    total_rows = len(classified)
    hit_rows = int(classified["辞書ヒット"].sum())
    miss_rows = total_rows - hit_rows

    hit_rate = (
        hit_rows / total_rows * 100
        if total_rows > 0
        else 0
    )

    summary_rows = [
        ("カテゴリ辞書登録語数", len(dictionary)),
        ("分類対象語レコード数", total_rows),
        ("辞書ヒット語レコード数", hit_rows),
        ("未分類語レコード数", miss_rows),
        ("辞書ヒット率(%)", round(hit_rate, 4)),
        (
            "対象事例数",
            int(classified["記号"].nunique(dropna=False)),
        ),
        (
            "カテゴリ付与事例数",
            int((case_category["カテゴリ数"] > 0).sum()),
        ),
        (
            "カテゴリ未付与事例数",
            int((case_category["カテゴリ数"] == 0).sum()),
        ),
        ("カテゴリ・サブカテゴリ組数", len(category_summary)),
        ("未分類異なり語数", len(unclassified_summary)),
        ("処理時間(秒)", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        ("次のStep", "Step3-7_All_特徴語抽出.py"),
    ]

    return pd.DataFrame(summary_rows, columns=["項目", "値"])


def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-6_All_カテゴリ分類を開始します")
    print("解析方法      : Commonカテゴリ辞書との完全一致")
    print("ジャッカード  : 使用しない")
    print("=" * 78)

    try:
        morpheme, stopword, dictionary = load_inputs()

        words = prepare_words(morpheme)
        classified = classify_words(words, dictionary)

        category_summary = create_category_summary(classified)
        case_category = create_case_category(classified)
        unclassified_summary = create_unclassified_summary(classified)

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            classified,
            category_summary,
            case_category,
            unclassified_summary,
            dictionary,
            elapsed_seconds,
        )

        save_csv(classified, OUTPUT_CLASSIFIED_CSV)
        save_csv(category_summary, OUTPUT_CATEGORY_SUMMARY_CSV)
        save_csv(case_category, OUTPUT_CASE_CATEGORY_CSV)
        save_csv(unclassified_summary, OUTPUT_UNCLASSIFIED_CSV)
        save_csv(analysis_summary, OUTPUT_SUMMARY_CSV)

        print("\n[カテゴリ集計: 上位30行]")
        print(category_summary.head(30).to_string(index=False))

        print("\n[未分類語: 上位30語]")
        print(unclassified_summary.head(30).to_string(index=False))

        hit_rows = int(classified["辞書ヒット"].sum())
        total_rows = len(classified)

        print("\n" + "-" * 78)
        print("Step3-6_All_カテゴリ分類 正常終了")
        print("-" * 78)
        print(f"辞書登録語数         : {len(dictionary):,}語")
        print(f"分類対象語レコード数 : {total_rows:,}件")
        print(f"辞書ヒット件数       : {hit_rows:,}件")
        print(f"未分類件数           : {total_rows - hit_rows:,}件")

        if total_rows > 0:
            print(f"辞書ヒット率         : {hit_rows / total_rows * 100:.4f}%")
        else:
            print("辞書ヒット率         : 0.0000%")

        print(f"対象事例数           : {classified['記号'].nunique(dropna=False):,}件")
        print(f"処理時間             : {elapsed_seconds:.2f}秒")
        print()
        print(f"カテゴリ分類CSV      : {OUTPUT_CLASSIFIED_CSV}")
        print(f"カテゴリ集計CSV      : {OUTPUT_CATEGORY_SUMMARY_CSV}")
        print(f"事例別カテゴリCSV    : {OUTPUT_CASE_CATEGORY_CSV}")
        print(f"未分類語集計CSV      : {OUTPUT_UNCLASSIFIED_CSV}")
        print(f"解析サマリーCSV      : {OUTPUT_SUMMARY_CSV}")
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep: Step3-7_All_特徴語抽出.py")
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
