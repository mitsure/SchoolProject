#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v1.0 学校事故データ：事例間ジャッカード類似度解析
VSCodeでそのまま実行する単体Pythonファイルです。

解析条件
1. 構造化データのみ
2. 自由記述テキストのみ
3. 構造化データ + テキスト特徴

出力
- 解析対象件数
- 使用特徴数
- 指定した事例に類似する上位事例
- 構造化のみ／テキストのみ／統合後の比較
- 条件指定による最多傷害の集計例

CSV出力処理は末尾に残していますが、初期状態ではコメントアウトしています。

必要ライブラリ
    pip install pandas numpy scipy scikit-learn

実行例
    python file/v1.1_school_accident_jaccard_console.py

CSVファイルを別の場所に置く場合は、INPUT_CSVを書き換えてください。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.preprocessing import MultiLabelBinarizer, OneHotEncoder


VERSION = "v1.1"

# ============================================================
# 設定
# ============================================================

# 想定フォルダ構成:
# /workspaces/Meikai/
# ├─ DB/shougai(2025.01.31).csv
# └─ file/このPythonファイル
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_CSV = PROJECT_ROOT / "DB" / "shougai(2025.01.31).csv"

ID_COLUMN = "記号"
TEXT_COLUMN = "災害発生時の状況"

# 類似事故を表示したい事例ID。
# Noneの場合は先頭行を使用します。
TARGET_CASE_ID: str | None = None

# 各解析で表示する類似事例数
TOP_K = 10

# 類似事例の説明時に表示する列
DISPLAY_COLUMNS = [
    "記号",
    "種別",
    "被災学校種",
    "被災学年",
    "性別",
    "場合別1",
    "場合別2",
    "競技種目",
    "通学方法",
    "発生場所1",
    "発生場所2",
    "災害発生時の状況",
]

# 構造化データの類似度に使用する列。
# 年度を入れると「同じ時期」が類似性に反映されるため、初期設定では除外。
STRUCTURED_COLUMNS = [
    "種別",
    "被災学校種",
    "被災学年",
    "性別",
    "場合別1",
    "場合別2",
    "競技種目",
    "通学方法",
    "発生場所1",
    "発生場所2",
    "遊具等",
]

# 自由記述から抽出する意味カテゴリー。
# 必要に応じて追加・修正してください。
TEXT_RULES: Dict[str, List[str]] = {
    # 移動手段・場面
    "移動手段:自転車": [r"自転車", r"チャリ"],
    "移動手段:徒歩": [r"徒歩", r"歩いて", r"歩行中"],
    "場面:登校": [r"登校"],
    "場面:下校": [r"下校"],
    "場面:通学": [r"通学"],
    "場面:授業": [r"授業中", r"授業の"],
    "場面:部活動": [r"部活動", r"部活中", r"練習中"],
    "場面:休憩": [r"休み時間", r"休憩時間"],

    # 事故現象
    "事故現象:転倒": [r"転倒", r"転ん", r"倒れ"],
    "事故現象:転落": [r"転落", r"落下", r"落ち"],
    "事故現象:衝突": [r"衝突", r"ぶつか", r"ぶつけ"],
    "事故現象:接触": [r"接触"],
    "事故現象:挟まれ": [r"挟ま", r"はさま"],
    "事故現象:切創": [r"切っ", r"切創", r"裂傷"],
    "事故現象:熱傷": [r"火傷", r"熱傷", r"やけど"],

    # 誘因・背景
    "誘因:段差": [r"段差", r"縁石"],
    "誘因:滑る": [r"滑っ", r"滑り", r"スリップ"],
    "誘因:つまずき": [r"つまず", r"躓"],
    "誘因:バランス喪失": [r"バランスを崩", r"体勢を崩"],
    "誘因:前方不注意": [r"前方不注意", r"よそ見", r"脇見"],
    "誘因:回避行動": [r"避けよう", r"避けた", r"かわそう"],
    "誘因:急ブレーキ": [r"急ブレーキ", r"ブレーキをかけ"],
    "誘因:他者との接触": [r"友人.*接触", r"児童.*接触", r"生徒.*接触"],

    # 衝突対象
    "対象:地面": [r"地面"],
    "対象:床": [r"床"],
    "対象:壁": [r"壁"],
    "対象:柱": [r"柱"],
    "対象:階段": [r"階段"],
    "対象:ボール": [r"ボール", r"球"],
    "対象:遊具": [r"遊具", r"鉄棒", r"ブランコ", r"滑り台"],
    "対象:自転車": [r"自転車"],
    "対象:自動車": [r"自動車", r"車両", r"乗用車", r"トラック"],
    "対象:ハンドル": [r"ハンドル"],

    # 受傷部位
    "部位:顔面": [r"顔面", r"顔を", r"顔が"],
    "部位:頭部": [r"頭部", r"頭を", r"後頭部"],
    "部位:顎": [r"顎", r"あご"],
    "部位:口腔": [r"口腔", r"口内", r"口の中"],
    "部位:歯": [r"前歯", r"歯牙", r"歯を", r"歯が"],
    "部位:手": [r"右手", r"左手", r"手指", r"手を"],
    "部位:眼": [r"眼", r"目を", r"目に"],

    # 傷害結果
    "傷害:歯牙破折": [r"歯.*破折", r"前歯.*折", r"歯が折"],
    "傷害:歯牙脱臼": [r"歯.*脱臼", r"歯牙脱臼"],
    "傷害:歯牙欠損": [r"歯.*欠損", r"歯を失"],
    "傷害:骨折": [r"骨折"],
    "傷害:脱臼": [r"脱臼"],
    "傷害:切創": [r"切創", r"裂傷"],
    "傷害:熱傷": [r"火傷", r"熱傷", r"やけど"],
}


# ============================================================
# 読み込み
# ============================================================

def load_csv(path: Path) -> pd.DataFrame:
    """日本語CSVを複数の文字コード候補で読み込む。"""
    candidates = ["utf-8-sig", "cp932", "shift_jis", "utf-8"]
    last_error: Exception | None = None

    for encoding in candidates:
        try:
            df = pd.read_csv(path, encoding=encoding)
            print(f"[読み込み] {path}")
            print(f"[文字コード] {encoding}")
            return df
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"CSVを読み込めませんでした: {last_error}")


def validate_columns(df: pd.DataFrame) -> None:
    required = set(STRUCTURED_COLUMNS + [ID_COLUMN, TEXT_COLUMN])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"必要な列がありません: {missing}")


# ============================================================
# 特徴量作成
# ============================================================

def build_structured_features(
    df: pd.DataFrame,
) -> Tuple[sparse.csr_matrix, List[str]]:
    """
    構造化カテゴリ列をOne-Hot Encodingして二値特徴にする。
    欠損は「欠損」として1カテゴリーにする。
    """
    source = df[STRUCTURED_COLUMNS].copy().fillna("欠損").astype(str)

    try:
        encoder = OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=True,
            dtype=np.uint8,
        )
    except TypeError:
        # 古いscikit-learn用
        encoder = OneHotEncoder(
            handle_unknown="ignore",
            sparse=True,
            dtype=np.uint8,
        )

    matrix = encoder.fit_transform(source).tocsr()
    names = encoder.get_feature_names_out(STRUCTURED_COLUMNS).tolist()
    return matrix, names


def extract_text_labels(text: object) -> List[str]:
    """1件の文章から、ルール辞書に一致する意味特徴を抽出する。"""
    value = "" if pd.isna(text) else str(text)
    labels: List[str] = []

    for label, patterns in TEXT_RULES.items():
        if any(re.search(pattern, value) for pattern in patterns):
            labels.append(label)

    return labels


def build_text_features(
    df: pd.DataFrame,
) -> Tuple[sparse.csr_matrix, List[str], List[List[str]]]:
    """
    自由記述を意味カテゴリーの集合に変換し、二値特徴行列にする。
    """
    label_lists = df[TEXT_COLUMN].map(extract_text_labels).tolist()

    mlb = MultiLabelBinarizer(sparse_output=True)
    matrix = mlb.fit_transform(label_lists).astype(np.uint8).tocsr()
    names = [f"TEXT_{name}" for name in mlb.classes_.tolist()]

    return matrix, names, label_lists


# ============================================================
# ジャッカード類似度
# ============================================================

def jaccard_against_target(
    matrix: sparse.csr_matrix,
    target_index: int,
) -> np.ndarray:
    """
    1つの対象事例と全事例の二値ジャッカード係数を計算する。

    J(A,B) = |A∩B| / |A∪B|
    """
    matrix = matrix.astype(bool).astype(np.uint8).tocsr()
    target = matrix.getrow(target_index)

    intersections = matrix.multiply(target).sum(axis=1).A1.astype(float)
    row_counts = matrix.sum(axis=1).A1.astype(float)
    target_count = float(target.sum())
    unions = row_counts + target_count - intersections

    scores = np.divide(
        intersections,
        unions,
        out=np.zeros_like(intersections, dtype=float),
        where=unions != 0,
    )

    # 自分自身は検索対象から外す
    scores[target_index] = -1.0
    return scores


def get_top_k_indices(scores: np.ndarray, top_k: int) -> np.ndarray:
    valid_count = int(np.sum(scores >= 0))
    k = min(top_k, valid_count)

    if k <= 0:
        return np.array([], dtype=int)

    candidate = np.argpartition(-scores, k - 1)[:k]
    return candidate[np.argsort(-scores[candidate])]


def common_feature_names(
    matrix: sparse.csr_matrix,
    feature_names: List[str],
    index_a: int,
    index_b: int,
    max_features: int = 12,
) -> List[str]:
    """2事例で共通して1になっている特徴名を返す。"""
    common = matrix.getrow(index_a).multiply(matrix.getrow(index_b))
    indices = common.indices
    names = [feature_names[i] for i in indices]
    return names[:max_features]


# ============================================================
# 表示
# ============================================================

def resolve_target_index(df: pd.DataFrame, case_id: str | None) -> int:
    if case_id is None:
        return 0

    matches = df.index[df[ID_COLUMN].astype(str) == str(case_id)].tolist()
    if not matches:
        raise ValueError(f"指定した事例IDが見つかりません: {case_id}")
    return int(matches[0])


def compact_text(value: object, max_length: int = 120) -> str:
    text = "" if pd.isna(value) else str(value).replace("\n", " ")
    if len(text) <= max_length:
        return text
    return text[:max_length] + "…"


def print_target_case(df: pd.DataFrame, target_index: int) -> None:
    row = df.iloc[target_index]
    print("\n" + "=" * 80)
    print("対象事例")
    print("=" * 80)

    for column in DISPLAY_COLUMNS:
        if column not in df.columns:
            continue
        value = row[column]
        if column == TEXT_COLUMN:
            value = compact_text(value, 300)
        print(f"{column}: {value}")


def print_top_cases(
    title: str,
    df: pd.DataFrame,
    matrix: sparse.csr_matrix,
    feature_names: List[str],
    scores: np.ndarray,
    target_index: int,
    top_k: int,
) -> pd.DataFrame:
    indices = get_top_k_indices(scores, top_k)

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

    rows = []
    for rank, idx in enumerate(indices, start=1):
        row = df.iloc[idx]
        common = common_feature_names(
            matrix,
            feature_names,
            target_index,
            idx,
        )

        print(f"\n[{rank}位] 類似度={scores[idx]:.4f}")
        print(f"事例ID: {row[ID_COLUMN]}")
        print(
            f"種別={row.get('種別', '')} / "
            f"学校種={row.get('被災学校種', '')} / "
            f"学年={row.get('被災学年', '')} / "
            f"性別={row.get('性別', '')}"
        )
        print(
            f"場合別1={row.get('場合別1', '')} / "
            f"場合別2={row.get('場合別2', '')} / "
            f"通学方法={row.get('通学方法', '')}"
        )
        print(f"共通特徴: {', '.join(common) if common else 'なし'}")
        print(f"状況: {compact_text(row[TEXT_COLUMN])}")

        rows.append(
            {
                "順位": rank,
                "対象事例ID": df.iloc[target_index][ID_COLUMN],
                "類似事例ID": row[ID_COLUMN],
                "Jaccard": scores[idx],
                "共通特徴": " | ".join(common),
                "種別": row.get("種別", ""),
                "被災学校種": row.get("被災学校種", ""),
                "被災学年": row.get("被災学年", ""),
                "場合別1": row.get("場合別1", ""),
                "場合別2": row.get("場合別2", ""),
                "状況": row.get(TEXT_COLUMN, ""),
            }
        )

    return pd.DataFrame(rows)


def print_comparison(
    df: pd.DataFrame,
    structured_scores: np.ndarray,
    text_scores: np.ndarray,
    combined_scores: np.ndarray,
    top_k: int,
) -> None:
    """
    3条件の上位候補をまとめて比較する。
    """
    candidate_indices = set(get_top_k_indices(structured_scores, top_k))
    candidate_indices.update(get_top_k_indices(text_scores, top_k))
    candidate_indices.update(get_top_k_indices(combined_scores, top_k))

    comparison = []
    for idx in candidate_indices:
        comparison.append(
            {
                "事例ID": df.iloc[idx][ID_COLUMN],
                "構造化J": structured_scores[idx],
                "テキストJ": text_scores[idx],
                "統合J": combined_scores[idx],
                "種別": df.iloc[idx].get("種別", ""),
                "学校種": df.iloc[idx].get("被災学校種", ""),
                "学年": df.iloc[idx].get("被災学年", ""),
            }
        )

    result = pd.DataFrame(comparison).sort_values(
        "統合J",
        ascending=False,
    )

    print("\n" + "=" * 80)
    print("3条件の比較")
    print("=" * 80)

    if result.empty:
        print("比較対象がありません。")
        return

    print(
        result.to_string(
            index=False,
            formatters={
                "構造化J": lambda x: f"{x:.4f}",
                "テキストJ": lambda x: f"{x:.4f}",
                "統合J": lambda x: f"{x:.4f}",
            },
        )
    )


# ============================================================
# 単純集計の例
# ============================================================

def print_most_common_injury_example(df: pd.DataFrame) -> None:
    """
    LLMから
    「小学校1年生で一番多い傷害は？」
    と質問された場合に相当する集計例。
    """
    subset = df[
        (df["被災学校種"].astype(str) == "小")
        & (df["被災学年"].astype(str) == "1")
    ]

    print("\n" + "=" * 80)
    print("単純集計例：小学校1年生で一番多い傷害")
    print("=" * 80)

    if subset.empty:
        print("該当データがありません。")
        return

    counts = subset["種別"].value_counts(dropna=False)
    top_name = counts.index[0]
    top_count = int(counts.iloc[0])
    total = len(subset)
    percentage = top_count / total * 100

    print(f"対象件数: {total}件")
    print(f"最多傷害: {top_name}")
    print(f"件数: {top_count}件")
    print(f"割合: {percentage:.1f}%")
    print("\n上位一覧")
    print(counts.head(10).to_string())


# ============================================================
# メイン処理
# ============================================================

def main() -> None:
    if not INPUT_CSV.exists():
        print(f"[エラー] CSVが見つかりません: {INPUT_CSV.resolve()}")
        print("想定配置は file/ にPython、DB/ にCSVです。ファイル名または配置を確認してください。")
        raise SystemExit(1)

    df = load_csv(INPUT_CSV)
    validate_columns(df)

    # 行番号を0から振り直して、行列の行番号と一致させる
    df = df.reset_index(drop=True)

    structured_matrix, structured_names = build_structured_features(df)
    text_matrix, text_names, text_labels = build_text_features(df)

    combined_matrix = sparse.hstack(
        [structured_matrix, text_matrix],
        format="csr",
    )
    combined_names = structured_names + text_names

    target_index = resolve_target_index(df, TARGET_CASE_ID)

    print("\n" + "=" * 80)
    print(f"{VERSION} 学校事故データ：事例間ジャッカード類似度解析")
    print("=" * 80)
    print(f"事例数: {len(df):,}")
    print(f"構造化特徴数: {structured_matrix.shape[1]:,}")
    print(f"テキスト特徴数: {text_matrix.shape[1]:,}")
    print(f"統合特徴数: {combined_matrix.shape[1]:,}")
    print(f"対象事例ID: {df.iloc[target_index][ID_COLUMN]}")
    print(f"対象事例のテキスト特徴: {', '.join(text_labels[target_index]) or 'なし'}")

    print_target_case(df, target_index)

    structured_scores = jaccard_against_target(
        structured_matrix,
        target_index,
    )
    text_scores = jaccard_against_target(
        text_matrix,
        target_index,
    )
    combined_scores = jaccard_against_target(
        combined_matrix,
        target_index,
    )

    structured_result = print_top_cases(
        "解析1：構造化データのみの類似事故",
        df,
        structured_matrix,
        structured_names,
        structured_scores,
        target_index,
        TOP_K,
    )

    text_result = print_top_cases(
        "解析2：テキスト特徴のみの類似事故",
        df,
        text_matrix,
        text_names,
        text_scores,
        target_index,
        TOP_K,
    )

    combined_result = print_top_cases(
        "解析3：構造化データ＋テキスト特徴の類似事故",
        df,
        combined_matrix,
        combined_names,
        combined_scores,
        target_index,
        TOP_K,
    )

    print_comparison(
        df,
        structured_scores,
        text_scores,
        combined_scores,
        TOP_K,
    )

    print_most_common_injury_example(df)

    # ========================================================
    # CSV出力
    # 必要になった場合は、以下のコメントを外してください。
    # ========================================================

    # output_dir = Path("output_jaccard")
    # output_dir.mkdir(parents=True, exist_ok=True)
    #
    # structured_result.to_csv(
    #     output_dir / f"{VERSION}_structured_top_cases.csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )
    #
    # text_result.to_csv(
    #     output_dir / f"{VERSION}_text_top_cases.csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )
    #
    # combined_result.to_csv(
    #     output_dir / f"{VERSION}_combined_top_cases.csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )

    print("\n解析が完了しました。")


if __name__ == "__main__":
    main()
