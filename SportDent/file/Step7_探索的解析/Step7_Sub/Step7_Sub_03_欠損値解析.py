"""Step7 Sub03：欠損値解析。"""
from __future__ import annotations

from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """列別欠損と事例単位の欠損パターンを出力する。"""
    df: pd.DataFrame = settings["df"]
    dataset_name = str(settings["dataset_name"])
    logger = settings["logger"]
    technical = [c for c in df.columns if c.startswith("Step7_")]
    target_columns = [c for c in df.columns if c not in technical]
    target = df[target_columns].copy()
    # CSV上の空文字も実質欠損として扱う。元DataFrameは変更しない。
    for column in target.columns:
        if pd.api.types.is_object_dtype(target[column]) or pd.api.types.is_string_dtype(target[column]):
            target[column] = target[column].replace(r"^\s*$", pd.NA, regex=True)

    missing = target.isna()
    column_result = pd.DataFrame({
        "列名": target_columns,
        "全件数": len(target),
        "欠損数": [int(missing[c].sum()) for c in target_columns],
        "欠損率（％）": [round(float(missing[c].mean() * 100), 4) for c in target_columns],
        "非欠損数": [int(target[c].notna().sum()) for c in target_columns],
    }).sort_values(["欠損率（％）", "列名"], ascending=[False, True])

    patterns = missing.apply(lambda row: " | ".join(row.index[row].tolist()) if row.any() else "欠損なし", axis=1)
    pattern_result = patterns.value_counts(dropna=False).rename_axis("欠損パターン").reset_index(name="件数")
    pattern_result["割合（％）"] = (pattern_result["件数"] / len(target) * 100).round(4)
    complete = int((~missing.any(axis=1)).sum())
    summary = pd.DataFrame([
        {"項目": "対象件数", "値": len(target)},
        {"項目": "解析対象列数（Step7補助列除外）", "値": len(target_columns)},
        {"項目": "完全データ件数", "値": complete},
        {"項目": "完全データ率（％）", "値": round(complete / len(target) * 100, 4)},
        {"項目": "欠損がある列数", "値": int((missing.sum() > 0).sum())},
    ])
    column_result.to_csv(settings["table_dir"] / "Step7-03_列別欠損値.csv", index=False, encoding=settings["text_encoding"])
    pattern_result.to_csv(settings["table_dir"] / "Step7-03_欠損パターン.csv", index=False, encoding=settings["text_encoding"])
    summary.to_csv(settings["summary_dir"] / "Step7-03_欠損値解析サマリー.csv", index=False, encoding=settings["text_encoding"])
    logger.info("[%s] Sub03完了 / 完全データ=%d/%d", dataset_name, complete, len(target))
