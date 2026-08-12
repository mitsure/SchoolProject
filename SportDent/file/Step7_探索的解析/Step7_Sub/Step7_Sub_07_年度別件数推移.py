"""Step7 Sub07：年度別件数推移。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """給付年度別の件数、割合、前年度差を算出する。"""
    df: pd.DataFrame = settings["df"]
    if "給付年度" not in df.columns:
        settings["logger"].warning("[%s] Sub07スキップ：給付年度列なし", settings["dataset_name"]); return
    year = pd.to_numeric(df["給付年度"], errors="coerce")
    result = year.value_counts(dropna=False).rename_axis("給付年度").reset_index(name="件数")
    result["数値年度"] = pd.to_numeric(result["給付年度"], errors="coerce")
    result = result.sort_values("数値年度", na_position="last").drop(columns="数値年度")
    result["割合（％）"] = (result["件数"] / len(df) * 100).round(4)
    result["前年度差"] = result["件数"].diff()
    result["前年度比（％）"] = result["件数"].pct_change().mul(100).round(4)
    result.to_csv(settings["table_dir"] / "Step7-07_年度別件数推移.csv", index=False, encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub07 / 年度数=%d / 数値化不能=%d", settings["dataset_name"], year.nunique(), year.isna().sum())
