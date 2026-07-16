#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
Step5-6_論文掲載グラフ作成

【目的】
Step5で作成した表データから、論文・学会発表用のFigureを作成する。

【文字化け対策】
画像およびPDFにはHeiseiMin-W3を使用する。

次の順でフォントを探す。

1. 環境変数 HEISEIMIN_W3_PATH
2. プロジェクト内の font フォルダ
3. OSに登録済みのHeiseiMin-W3

HeiseiMin-W3が見つからない場合は、
文字化けした画像を生成せず、エラーで停止する。

【配置】
Meikai/file/Step5_結果整理/
└─ Step5-6_論文掲載グラフ作成.py

【フォント配置例】
Meikai/font/
└─ HeiseiMin-W3.otf

またはターミナルで、

export HEISEIMIN_W3_PATH="/フォントへの絶対パス/HeiseiMin-W3.otf"

を設定する。

【入力】
CreateData/Step5_結果整理/Tables/

【出力】
CreateData/Step5_結果整理/Figures/

【出力形式】
PNG
SVG
PDF

【必要ライブラリ】
python -m pip install pandas numpy matplotlib

【実行】
python file/Step5_結果整理/Step5-6_論文掲載グラフ作成.py
==============================================================================
"""

from __future__ import annotations

from pathlib import Path
import os
import sys
import time

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager


# ------------------------------------------------------------------------------
# パス設定
# ------------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv


STEP5_DIR = PROJECT_ROOT / "CreateData" / "Step5_結果整理"
TABLE_DIR = STEP5_DIR / "Tables"
FIGURE_DIR = STEP5_DIR / "Figures"

FIGURE_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------------------
# 入出力設定
# ------------------------------------------------------------------------------

IN_WORD = TABLE_DIR / "Table4_歯牙障害特徴語ランキング.csv"
IN_CATEGORY = TABLE_DIR / "Table5_歯牙障害特徴カテゴリランキング.csv"
IN_JACCARD = TABLE_DIR / "Table7_歯牙障害_Jaccard上位ペア.csv"
IN_PATTERN = TABLE_DIR / "Table8_歯牙障害_事故パターンランキング.csv"

OUT_INDEX = FIGURE_DIR / "Figure一覧.csv"
OUT_SUMMARY = STEP5_DIR / "Step5-6_解析サマリー.csv"

FONT_NAME = "HeiseiMin-W3"
TOP_N = 20


# ------------------------------------------------------------------------------
# 共通関数
# ------------------------------------------------------------------------------

def read_csv(path: Path) -> pd.DataFrame:
    """UTF-8-SIG形式のCSVを読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力CSVが見つかりません: {path}")

    return pd.read_csv(path, encoding="utf-8-sig")


def save_summary(
    items: list[tuple[str, object]],
    path: Path,
) -> None:
    """Step5-6の実行サマリーをCSVへ保存する。"""
    dataframe = pd.DataFrame(
        items,
        columns=["項目", "値"],
    )

    save_csv(dataframe, path)

# ------------------------------------------------------------------------------
# 日本語フォント検索
# ------------------------------------------------------------------------------

FONT_PRIORITY = [
    "Noto Serif CJK JP",
    "Noto Sans CJK JP",
    "IPAexMincho",
    "IPAexGothic",
    "IPAMincho",
    "IPAGothic",
    "Yu Mincho",
    "Yu Gothic",
    "Hiragino Mincho ProN",
    "Hiragino Sans",
]


def find_japanese_font() -> tuple[str, Path]:
    """
    使用可能な日本語フォントを優先順位に従って検索する。

    Meikaiなど過去のプロジェクト名には依存しない。
    """
    available_fonts: dict[str, Path] = {}

    for font_path in font_manager.findSystemFonts():
        try:
            font_property = font_manager.FontProperties(
                fname=font_path
            )

            font_name = font_property.get_name()

            if font_name:
                available_fonts.setdefault(
                    font_name,
                    Path(font_path).resolve(),
                )

        except Exception:
            continue

    for preferred_name in FONT_PRIORITY:
        if preferred_name in available_fonts:
            return (
                preferred_name,
                available_fonts[preferred_name],
            )

    # 環境によってフォント名が少し違う場合に部分一致も試す。
    for preferred_name in FONT_PRIORITY:
        preferred_lower = preferred_name.lower()

        for actual_name, font_path in available_fonts.items():
            if preferred_lower in actual_name.lower():
                return (
                    actual_name,
                    font_path,
                )

    raise FileNotFoundError(
        "\n日本語対応フォントが見つかりません。\n\n"
        "文字化けしたFigureを生成しないため、処理を停止しました。\n\n"
        "Codespacesでは次を実行してください。\n\n"
        "sudo apt update\n"
        "sudo apt install -y fonts-noto-cjk\n"
        "fc-cache -fv\n"
    )


def configure_font() -> tuple[
    font_manager.FontProperties,
    Path,
]:
    """
    日本語フォントをmatplotlibへ登録し、
    FontPropertiesとフォントパスを返す。
    """
    font_name, font_path = find_japanese_font()

    font_manager.fontManager.addfont(
        str(font_path)
    )

    font_property = font_manager.FontProperties(
        fname=str(font_path)
    )

    plt.rcParams["font.family"] = font_property.get_name()
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"

    print(f"使用フォント: {font_property.get_name()}")
    print(f"フォントパス: {font_path}")

    return font_property, font_path

# ------------------------------------------------------------------------------
# Figure保存
# ------------------------------------------------------------------------------

def save_figure(
    figure,
    base_name: str,
) -> list[str]:
    """
    同じFigureをPNG、SVG、PDFで保存する。

    PNGは300dpiで出力する。
    """
    output_names: list[str] = []

    for extension in ("png", "svg", "pdf"):
        output_path = (
            FIGURE_DIR
            / f"{base_name}.{extension}"
        )

        figure.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )

        output_names.append(
            output_path.name
        )

    plt.close(figure)

    return output_names


def horizontal_bar(
    labels: list[str],
    values: list[float],
    title: str,
    xlabel: str,
    filename: str,
    font_property: font_manager.FontProperties,
) -> list[str]:
    """
    日本語横棒グラフを作成する。

    ラベルが多い場合でも読みやすいように、
    項目数に応じて高さを調整する。
    """
    figure_height = max(
        6.0,
        len(labels) * 0.42,
    )

    figure, axis = plt.subplots(
        figsize=(11, figure_height)
    )

    positions = np.arange(
        len(labels)
    )

    axis.barh(
        positions,
        values,
    )

    axis.set_yticks(
        positions
    )

    axis.set_yticklabels(
        labels,
        fontproperties=font_property,
        fontsize=9,
    )

    axis.invert_yaxis()

    axis.set_title(
        title,
        fontproperties=font_property,
        fontsize=15,
        pad=15,
    )

    axis.set_xlabel(
        xlabel,
        fontproperties=font_property,
        fontsize=11,
    )

    axis.tick_params(
        axis="x",
        labelsize=9,
    )

    # 目盛りにもHeiseiMin-W3を明示指定する
    for label in axis.get_xticklabels():
        label.set_fontproperties(
            font_property
        )

    # 値を棒の右端へ表示する
    for position, value in zip(
        positions,
        values,
    ):
        axis.text(
            value,
            position,
            f" {value:.2f}",
            va="center",
            fontproperties=font_property,
            fontsize=8,
        )

    figure.tight_layout()

    return save_figure(
        figure,
        filename,
    )


# ------------------------------------------------------------------------------
# メイン処理
# ------------------------------------------------------------------------------

def main() -> None:
    start_time = time.perf_counter()

    print("\n" + "=" * 78)
    print("Step5-6_論文掲載グラフ作成を開始します")
    print(f"指定フォント: {FONT_NAME}")
    print("=" * 78)

    try:
        font_property, font_path = configure_font()

        figure_index_rows: list[dict] = []

        # ------------------------------------------------------------------
        # Figure1 特徴語
        # ------------------------------------------------------------------
        word = read_csv(IN_WORD).head(TOP_N)

        figure1_files = horizontal_bar(
            labels=word["基本形"].astype(str).tolist()[::-1],
            values=word[
                "出現率差_歯牙障害-All"
            ].astype(float).tolist()[::-1],
            title="歯牙障害で相対的に多い特徴語",
            xlabel="出現率差（歯牙障害 - All）",
            filename="Figure1_歯牙障害特徴語Top20",
            font_property=font_property,
        )

        figure_index_rows.append(
            {
                "Figure番号": "Figure1",
                "図題": "歯牙障害特徴語Top20",
                "使用フォント": FONT_NAME,
                "出力ファイル": " | ".join(
                    figure1_files
                ),
            }
        )

        # ------------------------------------------------------------------
        # Figure2 特徴カテゴリ
        # ------------------------------------------------------------------
        category = read_csv(IN_CATEGORY).head(TOP_N)

        category_labels = (
            category["カテゴリ"].astype(str)
            + ":"
            + category["サブカテゴリ"].astype(str)
        )

        figure2_files = horizontal_bar(
            labels=category_labels.tolist()[::-1],
            values=category[
                "出現率差_歯牙障害-All"
            ].astype(float).tolist()[::-1],
            title="歯牙障害で相対的に多い特徴カテゴリ",
            xlabel="出現率差（歯牙障害 - All）",
            filename="Figure2_歯牙障害特徴カテゴリTop20",
            font_property=font_property,
        )

        figure_index_rows.append(
            {
                "Figure番号": "Figure2",
                "図題": "歯牙障害特徴カテゴリTop20",
                "使用フォント": FONT_NAME,
                "出力ファイル": " | ".join(
                    figure2_files
                ),
            }
        )

        # ------------------------------------------------------------------
        # Figure3 Jaccard
        # ------------------------------------------------------------------
        jaccard_data = read_csv(
            IN_JACCARD
        ).head(TOP_N)

        jaccard_labels = (
            jaccard_data["特徴1"].astype(str)
            + " × "
            + jaccard_data["特徴2"].astype(str)
        )

        figure3_files = horizontal_bar(
            labels=jaccard_labels.tolist()[::-1],
            values=jaccard_data[
                "ジャッカード係数"
            ].astype(float).tolist()[::-1],
            title="歯牙障害のJaccard係数上位ペア",
            xlabel="Jaccard係数",
            filename="Figure3_歯牙障害Jaccard上位ペア",
            font_property=font_property,
        )

        figure_index_rows.append(
            {
                "Figure番号": "Figure3",
                "図題": "歯牙障害Jaccard上位ペア",
                "使用フォント": FONT_NAME,
                "出力ファイル": " | ".join(
                    figure3_files
                ),
            }
        )

        # ------------------------------------------------------------------
        # Figure4 事故パターン
        # ------------------------------------------------------------------
        pattern = read_csv(
            IN_PATTERN
        ).head(15)

        figure4_files = horizontal_bar(
            labels=pattern[
                "事故パターン"
            ].astype(str).tolist()[::-1],
            values=pattern[
                "件数"
            ].astype(float).tolist()[::-1],
            title="歯牙障害の事故パターン",
            xlabel="事例数",
            filename="Figure4_歯牙障害事故パターンTop15",
            font_property=font_property,
        )

        figure_index_rows.append(
            {
                "Figure番号": "Figure4",
                "図題": "歯牙障害事故パターンTop15",
                "使用フォント": FONT_NAME,
                "出力ファイル": " | ".join(
                    figure4_files
                ),
            }
        )

        # ------------------------------------------------------------------
        # 一覧およびサマリー
        # ------------------------------------------------------------------
        figure_index = pd.DataFrame(
            figure_index_rows
        )

        save_csv(
            figure_index,
            OUT_INDEX,
        )

        elapsed_seconds = (
            time.perf_counter()
            - start_time
        )

        save_summary(
            [
                (
                    "作成Figure数",
                    len(figure_index),
                ),
                (
                    "出力形式",
                    "PNG・SVG・PDF",
                ),
                (
                    "指定フォント",
                    FONT_NAME,
                ),
                (
                    "使用フォントファイル",
                    str(font_path),
                ),
                (
                    "処理時間(秒)",
                    round(
                        elapsed_seconds,
                        3,
                    ),
                ),
                (
                    "次のStep",
                    "Step5-7_考察支援データ作成.py",
                ),
            ],
            OUT_SUMMARY,
        )

        print("\n" + "-" * 78)
        print("Step5-6 正常終了")
        print("-" * 78)
        print(
            figure_index.to_string(
                index=False
            )
        )
        print()
        print(f"出力先: {FIGURE_DIR}")
        print(f"使用フォント: {FONT_NAME}")
        print(f"フォントファイル: {font_path}")
        print(
            f"処理時間: "
            f"{elapsed_seconds:.2f}秒"
        )

    except KeyboardInterrupt:
        print("\n処理が中断されました。")
        sys.exit(1)

    except Exception as error:
        print("\n[処理中にエラーが発生しました]")
        print(
            f"{type(error).__name__}: "
            f"{error}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
