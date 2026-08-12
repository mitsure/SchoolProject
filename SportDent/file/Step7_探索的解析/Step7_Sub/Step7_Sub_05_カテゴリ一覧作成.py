"""Step7 Sub05：カテゴリ一覧作成。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """各カテゴリ列の値を、推測ではなく実データから列挙する。"""
    df: pd.DataFrame = settings["df"]
    excluded = {"記号", "災害発生時の状況", "Step7_入力元ファイル"}
    rows = []
    for column in [c for c in df.columns if c not in excluded]:
        clean = df[column].astype("string").str.strip().replace("", pd.NA)
        counts = clean.value_counts(dropna=False)
        for rank, (value, count) in enumerate(counts.items(), 1):
            display = "（欠損）" if pd.isna(value) else str(value)
            rows.append({"列名": column, "値": display, "件数": int(count),
                         "割合（％）": round(count / len(df) * 100, 4), "列内順位": rank})
    result = pd.DataFrame(rows)
    result.to_csv(settings["table_dir"] / "Step7-05_カテゴリ一覧.csv", index=False, encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub05 / %dカテゴリ値", settings["dataset_name"], len(result))
