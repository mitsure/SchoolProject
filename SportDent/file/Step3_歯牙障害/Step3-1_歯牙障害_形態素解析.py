#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step3-1_歯牙障害_形態素解析

【目的】
Step2-1で抽出した歯牙障害データの「災害発生時の状況」を
Janomeで形態素解析し、後続の頻出語・共起語・比較解析・
ジャッカード解析に使う基礎CSVを作成する。

【配置】
Meikai/file/Step3_歯牙障害/
└─ Step3-1_歯牙障害_形態素解析.py

【入力】
Meikai/CreateData/Step2_傷害カテゴリ別解析/
└─ カテゴリ別抽出データ/
   └─ Step2-1_傷害カテゴリ別解析_歯牙障害抽出.csv

【出力】
Meikai/CreateData/Step3_歯牙障害/
├─ Step3-1_歯牙障害_形態素解析.csv
├─ Step3-1_歯牙障害_解析サマリー.csv
├─ Step3-1_歯牙障害_解析異常一覧.csv
└─ Step3-1_歯牙障害_事例別解析文章.csv

【出力内容】

1. Step3-1_歯牙障害_形態素解析.csv
   1形態素を1行として出力する。
   - 元データ行番号
   - 記号
   - 形態素番号
   - 表層形
   - 基本形
   - 品詞
   - 品詞細分類
   - 活用型
   - 活用形
   - 読み
   - 発音

2. Step3-1_歯牙障害_解析サマリー.csv
   入力件数、解析成功件数、総形態素数、平均形態素数等を出力する。

3. Step3-1_歯牙障害_解析異常一覧.csv
   空欄、極端に短い文章、極端に長い文章等を出力する。

4. Step3-1_歯牙障害_事例別解析文章.csv
   事例ごとに名詞・動詞・形容詞の基本形を並べた文章を出力する。

【解析方法】
Janomeによる形態素解析

【ジャッカード係数】
使用しない。

【理由】
本Stepは、後続のジャッカード解析に使用する特徴を作る前処理であり、
類似度そのものは計算しないため。

【Common】
file/Common/Utilsの共通処理を使用する。

【必要ライブラリ】
python -m pip install pandas janome

【上書き】
同名CSVがある場合は上書きする。

【実行】
python file/Step3_歯牙障害/Step3-1_歯牙障害_形態素解析.py

【次のStep】
Step3-2_歯牙障害_品詞集計.py
==============================================================================
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import pandas as pd
from janome.tokenizer import Tokenizer


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

INPUT_CSV = (
    PROJECT_ROOT
    / "CreateData"
    / "Step2_傷害カテゴリ別解析"
    / "カテゴリ別抽出データ"
    / "Step2-1_傷害カテゴリ別解析_歯牙障害抽出.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"

OUTPUT_MORPHEME_CSV = (
    OUTPUT_DIR / "Step3-1_歯牙障害_形態素解析.csv"
)

OUTPUT_SUMMARY_CSV = (
    OUTPUT_DIR / "Step3-1_歯牙障害_解析サマリー.csv"
)

OUTPUT_ERROR_CSV = (
    OUTPUT_DIR / "Step3-1_歯牙障害_解析異常一覧.csv"
)

OUTPUT_CASE_TEXT_CSV = (
    OUTPUT_DIR / "Step3-1_歯牙障害_事例別解析文章.csv"
)

ID_COLUMN = "記号"
TEXT_COLUMN = "災害発生時の状況"
INJURY_COLUMN = "種別"

TARGET_POS = {"名詞", "動詞", "形容詞"}

SHORT_TEXT_LENGTH = 10
SHORT_MORPHEME_COUNT = 2
LONG_TEXT_LENGTH = 250
LONG_MORPHEME_COUNT = 150


# ------------------------------------------------------------------------------
# 前処理
# ------------------------------------------------------------------------------

def normalize_text(value: object) -> str:
    """NaN・改行・タブ・連続空白を整える。"""
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")

    return " ".join(text.split()).strip()


def clean_janome_value(value: str) -> str:
    """Janomeの未設定値「*」を空文字へ変換する。"""
    return "" if value == "*" else value


# ------------------------------------------------------------------------------
# 入力確認
# ------------------------------------------------------------------------------

def validate_dental_data(dataframe: pd.DataFrame) -> None:
    """
    必要列と傷害種別を確認する。
    """
    require_columns(
        dataframe,
        [
            ID_COLUMN,
            TEXT_COLUMN,
            INJURY_COLUMN,
        ],
    )

    injury_values = (
        dataframe[INJURY_COLUMN]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    unexpected = dataframe.loc[
        injury_values != "歯牙障害",
        INJURY_COLUMN,
    ]

    if not unexpected.empty:
        unexpected_values = sorted(
            set(unexpected.astype(str))
        )

        raise ValueError(
            "入力CSVに歯牙障害以外の種別が含まれています。"
            f"確認値: {unexpected_values}"
        )


# ------------------------------------------------------------------------------
# 形態素解析
# ------------------------------------------------------------------------------

def analyze_dental_cases(
    dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    歯牙障害事例を形態素解析する。
    """
    tokenizer = Tokenizer()

    morpheme_rows: list[dict] = []
    case_text_rows: list[dict] = []
    error_rows: list[dict] = []

    for row_index, row in dataframe.iterrows():
        case_id = row[ID_COLUMN]
        text = normalize_text(row[TEXT_COLUMN])

        if not text:
            case_text_rows.append(
                {
                    "元データ行番号": row_index + 2,
                    "記号": case_id,
                    "種別": "歯牙障害",
                    "元文章": "",
                    "文字数": 0,
                    "総形態素数": 0,
                    "解析対象語数": 0,
                    "解析済み文章": "",
                }
            )

            error_rows.append(
                {
                    "元データ行番号": row_index + 2,
                    "記号": case_id,
                    "種別": "歯牙障害",
                    "異常区分": "文章空欄",
                    "文字数": 0,
                    "形態素数": 0,
                    "元文章": "",
                    "確認内容": "災害発生時の状況が空欄です。",
                }
            )
            continue

        tokens = list(tokenizer.tokenize(text))
        analysis_words: list[str] = []

        for token_number, token in enumerate(tokens, start=1):
            pos = token.part_of_speech.split(",")

            base_form = (
                token.surface
                if token.base_form == "*"
                else token.base_form
            )

            pos_main = pos[0] if len(pos) > 0 else ""
            pos_sub1 = pos[1] if len(pos) > 1 else ""
            pos_sub2 = pos[2] if len(pos) > 2 else ""
            pos_sub3 = pos[3] if len(pos) > 3 else ""

            morpheme_rows.append(
                {
                    "元データ行番号": row_index + 2,
                    "記号": case_id,
                    "種別": "歯牙障害",
                    "形態素番号": token_number,
                    "表層形": token.surface,
                    "基本形": base_form,
                    "品詞": pos_main,
                    "品詞細分類1": pos_sub1,
                    "品詞細分類2": pos_sub2,
                    "品詞細分類3": pos_sub3,
                    "活用型": clean_janome_value(token.infl_type),
                    "活用形": clean_janome_value(token.infl_form),
                    "読み": clean_janome_value(token.reading),
                    "発音": clean_janome_value(token.phonetic),
                }
            )

            if pos_main in TARGET_POS and base_form:
                analysis_words.append(base_form)

        morpheme_count = len(tokens)

        case_text_rows.append(
            {
                "元データ行番号": row_index + 2,
                "記号": case_id,
                "種別": "歯牙障害",
                "元文章": text,
                "文字数": len(text),
                "総形態素数": morpheme_count,
                "解析対象語数": len(analysis_words),
                "解析済み文章": " ".join(analysis_words),
            }
        )

        abnormal_items: list[tuple[str, str]] = []

        if morpheme_count == 0:
            abnormal_items.append(
                (
                    "形態素数0",
                    "文章はありますが形態素が抽出されませんでした。",
                )
            )

        if len(text) <= SHORT_TEXT_LENGTH:
            abnormal_items.append(
                (
                    "文章が短い",
                    f"{SHORT_TEXT_LENGTH}文字以下です。",
                )
            )

        if 0 < morpheme_count <= SHORT_MORPHEME_COUNT:
            abnormal_items.append(
                (
                    "形態素数が少ない",
                    f"{SHORT_MORPHEME_COUNT}形態素以下です。",
                )
            )

        if len(text) >= LONG_TEXT_LENGTH:
            abnormal_items.append(
                (
                    "文章が長い",
                    f"{LONG_TEXT_LENGTH}文字以上です。",
                )
            )

        if morpheme_count >= LONG_MORPHEME_COUNT:
            abnormal_items.append(
                (
                    "形態素数が多い",
                    f"{LONG_MORPHEME_COUNT}形態素以上です。",
                )
            )

        if not analysis_words:
            abnormal_items.append(
                (
                    "解析対象語なし",
                    "名詞・動詞・形容詞が抽出されませんでした。",
                )
            )

        for abnormal_type, message in abnormal_items:
            error_rows.append(
                {
                    "元データ行番号": row_index + 2,
                    "記号": case_id,
                    "種別": "歯牙障害",
                    "異常区分": abnormal_type,
                    "文字数": len(text),
                    "形態素数": morpheme_count,
                    "元文章": text,
                    "確認内容": message,
                }
            )

    morpheme_df = pd.DataFrame(morpheme_rows)

    case_text_df = pd.DataFrame(
        case_text_rows,
        columns=[
            "元データ行番号",
            "記号",
            "種別",
            "元文章",
            "文字数",
            "総形態素数",
            "解析対象語数",
            "解析済み文章",
        ],
    )

    error_df = pd.DataFrame(
        error_rows,
        columns=[
            "元データ行番号",
            "記号",
            "種別",
            "異常区分",
            "文字数",
            "形態素数",
            "元文章",
            "確認内容",
        ],
    )

    return morpheme_df, case_text_df, error_df


# ------------------------------------------------------------------------------
# サマリー
# ------------------------------------------------------------------------------

def create_summary(
    source_df: pd.DataFrame,
    morpheme_df: pd.DataFrame,
    case_text_df: pd.DataFrame,
    error_df: pd.DataFrame,
    elapsed_seconds: float,
) -> pd.DataFrame:
    """解析結果の要約表を作成する。"""
    input_count = len(source_df)

    success_count = int(
        (case_text_df["総形態素数"] > 0).sum()
    )

    failed_count = input_count - success_count

    summary_rows = [
        ("解析対象", "歯牙障害"),
        ("入力ファイル", str(INPUT_CSV)),
        ("入力件数", input_count),
        ("解析成功件数", success_count),
        ("解析失敗件数", failed_count),
        (
            "解析成功率(%)",
            round(
                success_count / input_count * 100,
                3,
            )
            if input_count
            else 0,
        ),
        ("総形態素数", len(morpheme_df)),
        (
            "平均形態素数",
            round(
                case_text_df["総形態素数"].mean(),
                3,
            ),
        ),
        (
            "形態素数中央値",
            round(
                case_text_df["総形態素数"].median(),
                3,
            ),
        ),
        (
            "最小形態素数",
            int(case_text_df["総形態素数"].min()),
        ),
        (
            "最大形態素数",
            int(case_text_df["総形態素数"].max()),
        ),
        (
            "平均文字数",
            round(
                case_text_df["文字数"].mean(),
                3,
            ),
        ),
        (
            "文字数中央値",
            round(
                case_text_df["文字数"].median(),
                3,
            ),
        ),
        ("異常候補レコード数", len(error_df)),
        (
            "異常候補事例数",
            int(
                error_df["記号"].nunique(dropna=False)
            )
            if not error_df.empty
            else 0,
        ),
        ("処理時間(秒)", round(elapsed_seconds, 3)),
        ("ジャッカード係数", "使用しない"),
        (
            "次のStep",
            "Step3-2_歯牙障害_品詞集計.py",
        ),
    ]

    return pd.DataFrame(
        summary_rows,
        columns=["項目", "値"],
    )


# ------------------------------------------------------------------------------
# コンソール表示
# ------------------------------------------------------------------------------

def print_pos_preview(
    morpheme_df: pd.DataFrame,
) -> None:
    """主要品詞件数を表示する。"""
    print("\n[品詞速報]")

    if morpheme_df.empty:
        print("形態素データがありません。")
        return

    counts = morpheme_df["品詞"].value_counts(
        dropna=False
    )

    for pos_name in (
        "名詞",
        "動詞",
        "形容詞",
        "助詞",
        "助動詞",
        "副詞",
        "連体詞",
        "接続詞",
        "記号",
    ):
        print(
            f"{pos_name:<6}: "
            f"{int(counts.get(pos_name, 0)):>10,}件"
        )


def print_error_preview(
    error_df: pd.DataFrame,
) -> None:
    """異常候補内訳を表示する。"""
    print("\n[解析異常候補]")

    if error_df.empty:
        print("異常候補はありません。")
        return

    counts = (
        error_df["異常区分"]
        .value_counts(dropna=False)
        .rename_axis("異常区分")
        .reset_index(name="件数")
    )

    print(counts.to_string(index=False))


# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step3-1_歯牙障害_形態素解析を開始します")
    print("解析対象      : 歯牙障害")
    print("解析方法      : Janomeによる形態素解析")
    print("ジャッカード  : 使用しない")
    print("=" * 78)

    if not INPUT_CSV.exists():
        print(f"\n入力CSVが見つかりません: {INPUT_CSV}")
        print(
            "先にStep2-1_傷害カテゴリ別解析_歯牙障害抽出.pyを"
            "実行してください。"
        )
        sys.exit(1)

    try:
        source_df = load_csv(INPUT_CSV)

        validate_dental_data(source_df)

        (
            morpheme_df,
            case_text_df,
            error_df,
        ) = analyze_dental_cases(source_df)

        if morpheme_df.empty:
            raise ValueError(
                "形態素解析結果が0件です。"
            )

        elapsed_seconds = (
            time.perf_counter() - start_time
        )

        summary_df = create_summary(
            source_df,
            morpheme_df,
            case_text_df,
            error_df,
            elapsed_seconds,
        )

        save_csv(
            morpheme_df,
            OUTPUT_MORPHEME_CSV,
        )

        save_csv(
            summary_df,
            OUTPUT_SUMMARY_CSV,
        )

        save_csv(
            error_df,
            OUTPUT_ERROR_CSV,
        )

        save_csv(
            case_text_df,
            OUTPUT_CASE_TEXT_CSV,
        )

        print("\n[形態素解析結果: 先頭20行]")
        print(
            morpheme_df
            .head(20)
            .to_string(index=False)
        )

        print_pos_preview(morpheme_df)
        print_error_preview(error_df)

        success_count = int(
            (case_text_df["総形態素数"] > 0).sum()
        )

        print("\n" + "-" * 78)
        print(
            "Step3-1_歯牙障害_形態素解析 "
            "正常終了"
        )
        print("-" * 78)
        print(
            f"入力件数              : "
            f"{len(source_df):,}件"
        )
        print(
            f"解析成功件数          : "
            f"{success_count:,}件"
        )
        print(
            f"解析失敗件数          : "
            f"{len(source_df) - success_count:,}件"
        )
        print(
            f"総形態素数            : "
            f"{len(morpheme_df):,}件"
        )
        print(
            f"平均形態素数          : "
            f"{case_text_df['総形態素数'].mean():.2f}件/事例"
        )
        print(
            f"最小形態素数          : "
            f"{int(case_text_df['総形態素数'].min()):,}件"
        )
        print(
            f"最大形態素数          : "
            f"{int(case_text_df['総形態素数'].max()):,}件"
        )
        print(
            f"異常候補レコード数    : "
            f"{len(error_df):,}件"
        )
        print(
            f"処理時間              : "
            f"{elapsed_seconds:.2f}秒"
        )
        print()
        print(
            f"形態素解析CSV         : "
            f"{OUTPUT_MORPHEME_CSV}"
        )
        print(
            f"解析サマリーCSV       : "
            f"{OUTPUT_SUMMARY_CSV}"
        )
        print(
            f"解析異常一覧CSV       : "
            f"{OUTPUT_ERROR_CSV}"
        )
        print(
            f"事例別解析文章CSV     : "
            f"{OUTPUT_CASE_TEXT_CSV}"
        )
        print()
        print("同名CSVは上書きしています。")
        print("ジャッカード係数は使用していません。")
        print(
            "次のStep: "
            "Step3-2_歯牙障害_品詞集計.py"
        )
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
