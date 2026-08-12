"""Step7 Sub01：解析対象項目棚卸し。"""
from __future__ import annotations

from typing import Any
import pandas as pd


def _classify(column: str, series: pd.Series) -> tuple[str, str]:
    """実データと既知の列の意味から、解析上の役割と用途を整理する。"""
    if column == "記号":
        return "ID候補", "重複・追跡・データ結合"
    if column == "災害発生時の状況":
        return "テキスト", "文長・N-gram・既存テキスト成果との比較"
    if column.startswith("Step7_"):
        return "技術補助列", "入力追跡または比較群の定義"
    if column in {"給付年度", "被災学年"}:
        return "順序・数値候補", "年度推移または学年比較（型変換の要確認）"
    unique = int(series.nunique(dropna=True))
    if pd.api.types.is_numeric_dtype(series) and unique > 20:
        return "数値", "記述統計・分布確認"
    return "カテゴリ", "件数・割合・クロス集計・群間比較"


def run(settings: dict[str, Any]) -> None:
    """各1列の型、欠損、一意値数、解析用途を1表に出力する。"""
    df: pd.DataFrame = settings["df"]
    dataset_name = str(settings["dataset_name"])
    logger = settings["logger"]
    rows = []
    for column in df.columns:
        series = df[column]
        nonmissing = series.dropna()
        role, purpose = _classify(column, series)
        examples = nonmissing.astype(str).drop_duplicates().head(5).tolist()
        rows.append({
            "データセット": dataset_name, "列順": df.columns.get_loc(column) + 1,
            "列名": column, "pandas型": str(series.dtype), "解析上の種類": role,
            "全件数": len(df), "非欠損数": int(series.notna().sum()),
            "欠損数": int(series.isna().sum()),
            "欠損率（％）": round(float(series.isna().mean() * 100), 4),
            "一意値数": int(series.nunique(dropna=True)), "値例": " | ".join(examples),
            "推奨解析用途": purpose,
        })
    result = pd.DataFrame(rows)
    output = settings["table_dir"] / "Step7-01_解析対象項目棚卸し.csv"
    result.to_csv(output, index=False, encoding=settings["text_encoding"])
    logger.info("[%s] Sub01出力: %s / %d列", dataset_name, output, len(result))
