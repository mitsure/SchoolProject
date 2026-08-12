"""Step7 Sub02：データ品質診断。"""
from __future__ import annotations

from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """空文字、前後空白、ID、入力元整合性を診断する。"""
    df: pd.DataFrame = settings["df"]
    dataset_name = str(settings["dataset_name"])
    logger = settings["logger"]
    quality_rows = []
    for column in df.columns:
        series = df[column]
        text = series.astype("string")
        empty = int(text.fillna("").str.strip().eq("").sum() - series.isna().sum())
        surrounding = int((text.notna() & text.ne(text.str.strip())).sum())
        quality_rows.append({
            "列名": column, "件数": len(df), "欠損数": int(series.isna().sum()),
            "空文字数": max(empty, 0), "前後空白あり": surrounding,
            "一意値数（欠損除外）": int(series.nunique(dropna=True)),
        })
    column_quality = pd.DataFrame(quality_rows)

    checks = []
    def add(name: str, value: int | str, status: str, detail: str) -> None:
        checks.append({"診断項目": name, "値": value, "判定": status, "詳細": detail})

    if "記号" in df.columns:
        ids = df["記号"].astype("string")
        missing = int(ids.isna().sum() + (ids.notna() & ids.str.strip().eq("")).sum())
        duplicated = int(ids.duplicated(keep=False).sum())
        add("ID欠損", missing, "OK" if missing == 0 else "要確認", "ID候補列：記号")
        add("ID重複候補行", duplicated, "OK" if duplicated == 0 else "要確認", "keep=Falseで計数")
    else:
        add("ID列", 0, "要確認", "記号列が存在しない")

    technical = {"Step7_入力元ファイル", "Step7_入力元カテゴリ", "Step7_歯牙障害フラグ"}
    original = [c for c in df.columns if c not in technical]
    duplicate_rows = int(df.duplicated(subset=original, keep=False).sum())
    add("完全一致重複候補行", duplicate_rows, "OK" if duplicate_rows == 0 else "要確認", "Step7補助列を除外")

    mismatch = 0
    if {"種別", "Step7_入力元カテゴリ"}.issubset(df.columns):
        mismatch = int(df["種別"].astype(str).str.strip().ne(df["Step7_入力元カテゴリ"].astype(str).str.strip()).sum())
    add("種別と入力元カテゴリの不一致", mismatch, "OK" if mismatch == 0 else "要確認", "行単位で照合")

    column_quality.to_csv(settings["table_dir"] / "Step7-02_列別データ品質.csv", index=False, encoding=settings["text_encoding"])
    pd.DataFrame(checks).to_csv(settings["summary_dir"] / "Step7-02_データ品質診断サマリー.csv", index=False, encoding=settings["text_encoding"])
    logger.info("[%s] Sub02診断完了 / 要確認=%d件", dataset_name, sum(x["判定"] != "OK" for x in checks))
