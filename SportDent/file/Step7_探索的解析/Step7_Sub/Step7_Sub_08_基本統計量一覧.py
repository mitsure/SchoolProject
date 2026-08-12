"""Step7 Sub08：基本統計量一覧。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """数値変換できる実質数値列に限定して記述統計を出力する。"""
    df: pd.DataFrame = settings["df"]
    rows = []
    for column in df.columns:
        if column.startswith("Step7_") or column == "記号": continue
        original_nonmissing = int(df[column].notna().sum())
        numeric = pd.to_numeric(df[column], errors="coerce")
        converted = int(numeric.notna().sum())
        # 文字カテゴリを無理に数値解析しない。
        if original_nonmissing == 0 or converted / original_nonmissing < 0.95: continue
        valid = numeric.dropna()
        rows.append({"列名": column, "有効数": len(valid), "数値化不能数": original_nonmissing - converted,
                     "平均": valid.mean(), "標準偏差": valid.std(), "最小": valid.min(),
                     "25%点": valid.quantile(.25), "中央値": valid.median(), "75%点": valid.quantile(.75), "最大": valid.max()})
    result = pd.DataFrame(rows)
    result.to_csv(settings["table_dir"] / "Step7-08_基本統計量一覧.csv", index=False, encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub08 / 実質数値列=%d", settings["dataset_name"], len(result))
