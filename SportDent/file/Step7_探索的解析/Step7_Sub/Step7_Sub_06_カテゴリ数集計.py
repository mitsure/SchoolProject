"""Step7 Sub06：カテゴリ数集計。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """列ごとのカテゴリ数と希少カテゴリ数を整理する。"""
    df: pd.DataFrame = settings["df"]
    excluded = {"記号", "災害発生時の状況", "Step7_入力元ファイル"}
    rows = []
    for column in [c for c in df.columns if c not in excluded]:
        clean = df[column].astype("string").str.strip().replace("", pd.NA)
        counts = clean.value_counts(dropna=True)
        rows.append({"列名": column, "カテゴリ数（欠損除外）": len(counts),
                     "欠損数": int(clean.isna().sum()), "1件のカテゴリ数": int((counts == 1).sum()),
                     "5件未満のカテゴリ数": int((counts < 5).sum()),
                     "最小カテゴリ件数": int(counts.min()) if len(counts) else 0,
                     "最大カテゴリ件数": int(counts.max()) if len(counts) else 0})
    result = pd.DataFrame(rows)
    result.to_csv(settings["summary_dir"] / "Step7-06_カテゴリ数集計.csv", index=False, encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub06 / %d列", settings["dataset_name"], len(result))
