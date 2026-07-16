#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-5_All_ストップワード除去

【目的】
Step3-1で作成した形態素解析結果から、
Commonで管理するストップワードを除去し、
後続の特徴語抽出・ジャッカード解析で使用する事例別語集合を作成する。

【配置】
Meikai/file/Step3_All/
└─ Step3-5_All_ストップワード除去.py

【入力】
Meikai/CreateData/Step3_All/
└─ Step3-1_All_形態素解析.csv

Meikai/file/Common/Config/
└─ 設定_ストップワード.txt

【出力】
Meikai/CreateData/Step3_All/
├─ Step3-5_All_ストップワード除去.csv
├─ Step3-5_All_除去語集計.csv
├─ Step3-5_All_残存語集計.csv
└─ Step3-5_All_解析サマリー.csv

【出力内容】

1. Step3-5_All_ストップワード除去.csv
   事例ごとに以下を出力する。
   - 記号
   - 除去前語数
   - 除去後語数
   - 除去語数
   - 除去率
   - 解析用語列
   - 解析用語集合

2. Step3-5_All_除去語集計.csv
   実際に除去された語の件数・事例数を集計する。

3. Step3-5_All_残存語集計.csv
   除去後に残った語の件数・事例数を集計する。

4. Step3-5_All_解析サマリー.csv
   除去前後の語数、除去率、対象事例数等を出力する。

【解析方法】
テキスト前処理
- 対象品詞：名詞・動詞・形容詞
- 基本形を使用
- Commonのストップワード辞書を利用
- 事例別の語順保持版と重複除去版を作成

【ジャッカード係数】
使用しない。

【理由】
本Stepはジャッカード解析に使用する特徴集合を作る前処理であり、
類似度そのものは計算しないため。

【Common】
- file/Common/Config/設定_ストップワード.txt
- file/Common/Utils/output.py
- file/Common/Utils/text_utils.py
- file/Common/Utils/validation.py

【必要ライブラリ】
python -m pip install pandas

【上書き】
同名CSVがある場合は上書きする。

【実行】
python file/Step3_All/Step3-5_All_ストップワード除去.py

【次のStep】
Step3-6_All_カテゴリ分類.py
==============================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd


# =============================================================================
# パス設定
# =============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns
from Common.Utils.text_utils import load_stopwords


# =============================================================================
# 基本設定
# =============================================================================

INPUT_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step3_All"
    / "Step3-1_All_形態素解析.csv"
)

STOPWORDS_FILE = (
    PROJECT_ROOT
    / "file"
    / "Common"
    / "Config"
    / "設定_ストップワード.txt"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_All"

OUTPUT_CASE_CSV = OUTPUT_DIR / "Step3-5_All_ストップワード除去.csv"
OUTPUT_REMOVED_CSV = OUTPUT_DIR / "Step3-5_All_除去語集計.csv"
OUTPUT_REMAINING_CSV = OUTPUT_DIR / "Step3-5_All_残存語集計.csv"
OUTPUT_SUMMARY_CSV = OUTPUT_DIR / "Step3-5_All_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}

REQUIRED_COLUMNS = [
    "記号",
    "形態素番号",
    "基本形",
    "品詞",
]


# =============================================================================
# 入力読込
# =============================================================================

def load_morpheme_csv(path: Path) -> pd.DataFrame:
    """Step3-1の形態素解析CSVを読み込む。"""
    if not path.exists():
        raise FileNotFoundError(
            f"入力CSVが見つかりません：{path}\n"
            "先にStep3-1_All_形態素解析.pyを実行してください。"
        )

    dataframe = pd.read_csv(path, encoding="utf-8-sig")
    require_columns(dataframe, REQUIRED_COLUMNS)

    if dataframe.empty:
        raise ValueError("形態素解析CSVが0件です。")

    return dataframe


# =============================================================================
# 前処理
# =============================================================================

def normalize_word(value: object) -> str:
    """基本形を安全な文字列へ統一する。"""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text or text == "*":
        return ""

    return text


def prepare_target_words(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    名詞・動詞・形容詞のみを抽出し、
    ストップワード判定用データを作る。
    """
    work = dataframe.copy()

    work["基本形"] = work["基本形"].map(normalize_word)
    work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()

    work = work[
        work["品詞"].isin(TARGET_POS)
        & work["基本形"].ne("")
    ].copy()

    if work.empty:
        raise ValueError("ストップワード除去対象の語がありません。")

    work = work.sort_values(
        ["記号", "形態素番号"],
        ascending=[True, True],
    ).reset_index(drop=True)

    return work


# =============================================================================
# ストップワード除去
# =============================================================================

def add_stopword_flag(
    dataframe: pd.DataFrame,
    stopwords: set[str],
) -> pd.DataFrame:
    """各語がストップワードかどうかを判定する。"""
    work = dataframe.copy()
    work["ストップワード"] = work["基本形"].isin(stopwords)
    return work


def create_case_summary(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    事例ごとに除去前後の語数と解析用語を作成する。

    解析用語列：
        語順と重複を保持する。

    解析用語集合：
        重複を除去し、最初に出現した順序を保持する。
        Step4の集合型ジャッカードで利用できる。
    """
    rows = []

    for case_id, group in dataframe.groupby("記号", dropna=False, sort=False):
        all_words = group["基本形"].astype(str).tolist()

        remaining_words = (
            group.loc[
                ~group["ストップワード"],
                "基本形",
            ]
            .astype(str)
            .tolist()
        )

        removed_words = (
            group.loc[
                group["ストップワード"],
                "基本形",
            ]
            .astype(str)
            .tolist()
        )

        # 順序を維持しながら重複を除去する
        unique_remaining_words = list(dict.fromkeys(remaining_words))

        before_count = len(all_words)
        after_count = len(remaining_words)
        removed_count = len(removed_words)

        removal_rate = (
            removed_count / before_count * 100
            if before_count
            else 0
        )

        rows.append(
            {
                "記号": case_id,
                "除去前語数": before_count,
                "除去後語数": after_count,
                "除去語数": removed_count,
                "除去率（％）": round(removal_rate, 4),
                "除去語列": " ".join(removed_words),
                "解析用語列": " ".join(remaining_words),
                "解析用語集合": " ".join(unique_remaining_words),
                "解析用語異なり語数": len(unique_remaining_words),
            }
        )

    return pd.DataFrame(rows)


# =============================================================================
# 語別集計
# =============================================================================

def create_word_summary(
    dataframe: pd.DataFrame,
    stopword_flag: bool,
) -> pd.DataFrame:
    """
    除去語または残存語について、
    出現回数・出現事例数を集計する。
    """
    work = dataframe[
        dataframe["ストップワード"] == stopword_flag
    ].copy()

    columns = [
        "順位",
        "品詞",
        "基本形",
        "出現回数",
        "出現事例数",
        "事例出現率（％）",
    ]

    if work.empty:
        return pd.DataFrame(columns=columns)

    total_cases = int(
        dataframe["記号"].nunique(dropna=False)
    )

    token_counts = (
        work
        .groupby(["品詞", "基本形"], dropna=False)
        .size()
        .reset_index(name="出現回数")
    )

    case_counts = (
        work[["記号", "品詞", "基本形"]]
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

    result["事例出現率（％）"] = (
        result["出現事例数"] / total_cases * 100
    ).round(4)

    result = result.sort_values(
        ["出現事例数", "出現回数", "基本形"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    result.insert(0, "順位", range(1, len(result) + 1))

    return result[columns]


# =============================================================================
# サマリー
# =============================================================================

def create_analysis_summary(
    source_df: pd.DataFrame,
    target_df: pd.DataFrame,
    case_summary: pd.DataFrame,
    removed_summary: pd.DataFrame,
    remaining_summary: pd.DataFrame,
    stopwords: set[str],
    elapsed_seconds: float,
) -> pd.DataFrame:
    """Step3-5の解析概要を作成する。"""
    before_total = int(case_summary["除去前語数"].sum())
    after_total = int(case_summary["除去後語数"].sum())
    removed_total = int(case_summary["除去語数"].sum())

    overall_removal_rate = (
        removed_total / before_total * 100
        if before_total
        else 0
    )

    zero_remaining_cases = int(
        (case_summary["除去後語数"] == 0).sum()
    )

    summary_rows = [
        ("入力ファイル", str(INPUT_CSV)),
        ("ストップワードファイル", str(STOPWORDS_FILE)),
        ("登録ストップワード数", len(stopwords)),
        ("入力形態素数", len(source_df)),
        ("対象形態素数", len(target_df)),
        (
            "対象事例数",
            int(target_df["記号"].nunique(dropna=False)),
        ),
        ("除去前語数合計", before_total),
        ("除去後語数合計", after_total),
        ("除去語数合計", removed_total),
        ("全体除去率（％）", round(overall_removal_rate, 4)),
        (
            "1事例当たり平均除去前語数",
            round(case_summary["除去前語数"].mean(), 4),
        ),
        (
            "1事例当たり平均除去後語数",
            round(case_summary["除去後語数"].mean(), 4),
        ),
        (
            "1事例当たり平均除去語数",
            round(case_summary["除去語数"].mean(), 4),
        ),
        ("除去後語数0の事例数", zero_remaining_cases),
        ("実際に除去された異なり語数", len(removed_summary)),
        ("残存異なり語数", len(remaining_summary)),
        ("処理時間（秒）", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        ("次のStep", "Step3-6_All_カテゴリ分類.py"),
    ]

    return pd.DataFrame(summary_rows, columns=["項目", "値"])


# =============================================================================
# コンソール表示
# =============================================================================

def print_word_preview(
    title: str,
    summary: pd.DataFrame,
    top_n: int = 30,
) -> None:
    """語別集計の上位を表示する。"""
    print(f"\n【{title}：上位{top_n}語】")

    if summary.empty:
        print("該当語はありません。")
        return

    print(
        summary
        .head(top_n)
        .to_string(
            index=False,
            formatters={
                "出現回数": lambda value: f"{int(value):,}",
                "出現事例数": lambda value: f"{int(value):,}",
                "事例出現率（％）": lambda value: f"{float(value):.4f}",
            },
        )
    )


# =============================================================================
# メイン処理
# =============================================================================

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-5_All_ストップワード除去を開始します")
    print("解析対象　　　：名詞・動詞・形容詞")
    print("設定ファイル　：Common/Config/設定_ストップワード.txt")
    print("ジャッカード　：使用しない")
    print("=" * 78)

    try:
        source_df = load_morpheme_csv(INPUT_CSV)
        stopwords = load_stopwords(STOPWORDS_FILE)

        target_df = prepare_target_words(source_df)
        flagged_df = add_stopword_flag(target_df, stopwords)

        case_summary = create_case_summary(flagged_df)
        removed_summary = create_word_summary(flagged_df, True)
        remaining_summary = create_word_summary(flagged_df, False)

        elapsed_seconds = time.perf_counter() - start_time

        analysis_summary = create_analysis_summary(
            source_df,
            target_df,
            case_summary,
            removed_summary,
            remaining_summary,
            stopwords,
            elapsed_seconds,
        )

        save_csv(case_summary, OUTPUT_CASE_CSV)
        save_csv(removed_summary, OUTPUT_REMOVED_CSV)
        save_csv(remaining_summary, OUTPUT_REMAINING_CSV)
        save_csv(analysis_summary, OUTPUT_SUMMARY_CSV)

        print("\n【事例別除去結果：先頭20行】")
        print(case_summary.head(20).to_string(index=False))

        print_word_preview(
            "実際に除去された語",
            removed_summary,
            top_n=30,
        )

        print_word_preview(
            "除去後に残った語",
            remaining_summary,
            top_n=30,
        )

        before_total = int(case_summary["除去前語数"].sum())
        after_total = int(case_summary["除去後語数"].sum())
        removed_total = int(case_summary["除去語数"].sum())

        print("\n【整合性確認】")
        print(f"除去前語数合計　　　：{before_total:,}語")
        print(f"除去後語数合計　　　：{after_total:,}語")
        print(f"除去語数合計　　　　：{removed_total:,}語")
        print(
            f"前後＋除去の整合性　："
            f"{after_total + removed_total:,}語"
        )
        print(
            f"対象事例数　　　　　："
            f"{target_df['記号'].nunique(dropna=False):,}件"
        )
        print(
            f"出力事例数　　　　　："
            f"{len(case_summary):,}件"
        )

        print("\n" + "━" * 78)
        print("Step3-5_All_ストップワード除去　正常終了")
        print("━" * 78)
        print(f"登録ストップワード数：{len(stopwords):,}語")
        print(f"除去前語数　　　　　：{before_total:,}語")
        print(f"除去後語数　　　　　：{after_total:,}語")
        print(f"除去語数　　　　　　：{removed_total:,}語")
        print(
            f"全体除去率　　　　　："
            f"{removed_total / before_total * 100:.4f}％"
            if before_total
            else "全体除去率　　　　　：0.0000％"
        )
        print(
            f"除去後語数0の事例数 ："
            f"{int((case_summary['除去後語数'] == 0).sum()):,}件"
        )
        print(f"処理時間　　　　　　：{elapsed_seconds:.2f}秒")
        print()
        print(f"事例別結果CSV　　　　：{OUTPUT_CASE_CSV}")
        print(f"除去語集計CSV　　　　：{OUTPUT_REMOVED_CSV}")
        print(f"残存語集計CSV　　　　：{OUTPUT_REMAINING_CSV}")
        print(f"解析サマリーCSV　　　：{OUTPUT_SUMMARY_CSV}")
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print("次のStep：Step3-6_All_カテゴリ分類.py")
        print("━" * 78)

    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(1)

    except Exception as error:
        print("\n【処理中にエラーが発生しました】")
        print(f"{type(error).__name__}: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
