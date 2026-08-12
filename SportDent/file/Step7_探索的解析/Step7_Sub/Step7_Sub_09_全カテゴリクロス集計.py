"""Step7 Sub09：歯牙障害フラグと全カテゴリ列のクロス集計。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """比較群が両方存在する「全体」だけで、件数と列カテゴリ内割合を出力する。"""
    df: pd.DataFrame = settings["df"]
    flag = "Step7_歯牙障害フラグ"
    if flag not in df.columns or df[flag].nunique(dropna=True) < 2:
        settings["logger"].info("[%s] Sub09解析不能：比較群が2種類未満", settings["dataset_name"]); return "skipped"
    excluded = {"記号", "災害発生時の状況", "種別", flag, "Step7_入力元ファイル", "Step7_入力元カテゴリ"}
    rows = []
    for column in [c for c in df.columns if c not in excluded]:
        values = df[column].astype("string").str.strip().fillna("（欠損）").replace("", "（欠損）")
        table = pd.crosstab(values, df[flag])
        for value, counts in table.iterrows():
            tooth = int(counts.get(1, 0)); other = int(counts.get(0, 0)); total = tooth + other
            rows.append({"列名": column, "カテゴリ": value, "歯牙障害件数": tooth,
                         "歯牙障害以外件数": other, "合計": total,
                         "カテゴリ内歯牙障害割合（％）": round(tooth / total * 100, 4) if total else pd.NA})
    result = pd.DataFrame(rows)
    result.to_csv(settings["table_dir"] / "Step7-09_歯牙障害_vs_歯牙障害以外_クロス集計.csv", index=False, encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub09 / %dクロス集計行", settings["dataset_name"], len(result))
