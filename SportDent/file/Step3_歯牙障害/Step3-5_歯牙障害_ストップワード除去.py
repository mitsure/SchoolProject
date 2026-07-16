#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step3-5_歯牙障害_ストップワード除去

Common/Config/設定_ストップワード.txtを使用する。
ジャッカード係数は使用しない。
"""

from __future__ import annotations

from pathlib import Path
import sys
import time
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "file"))

from Common.Utils.output import save_csv
from Common.Utils.validation import require_columns

OUTPUT_DIR = PROJECT_ROOT / "CreateData" / "Step3_歯牙障害"

INPUT_CSV = OUTPUT_DIR / "Step3-1_歯牙障害_形態素解析.csv"
STOPWORDS_FILE = PROJECT_ROOT / "file" / "Common" / "Config" / "設定_ストップワード.txt"

OUTPUT_CASE = OUTPUT_DIR / "Step3-5_歯牙障害_ストップワード除去.csv"
OUTPUT_REMOVED = OUTPUT_DIR / "Step3-5_歯牙障害_除去語集計.csv"
OUTPUT_REMAINING = OUTPUT_DIR / "Step3-5_歯牙障害_残存語集計.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "Step3-5_歯牙障害_解析サマリー.csv"

TARGET_POS = {"名詞", "動詞", "形容詞"}

def load_stopwords():
    if not STOPWORDS_FILE.exists():
        raise FileNotFoundError(f"ストップワードがありません: {STOPWORDS_FILE}")
    return {
        line.strip()
        for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

def word_summary(df, flag):
    work = df[df["ストップワード"] == flag].copy()
    if work.empty:
        return pd.DataFrame(columns=[
            "順位", "品詞", "基本形", "出現回数", "出現事例数", "事例出現率(%)"
        ])

    total_cases = df["記号"].nunique(dropna=False)
    a = work.groupby(["品詞", "基本形"]).size().reset_index(name="出現回数")
    b = (
        work[["記号", "品詞", "基本形"]]
        .drop_duplicates()
        .groupby(["品詞", "基本形"])
        .size()
        .reset_index(name="出現事例数")
    )
    result = a.merge(b, on=["品詞", "基本形"])
    result["事例出現率(%)"] = (
        result["出現事例数"] / total_cases * 100
    ).round(4)
    result = result.sort_values(
        ["出現事例数", "出現回数", "基本形"],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    result.insert(0, "順位", range(1, len(result) + 1))
    return result

def main():
    start = time.perf_counter()
    print("=" * 78)
    print("Step3-5_歯牙障害_ストップワード除去")
    print("=" * 78)

    try:
        if not INPUT_CSV.exists():
            raise FileNotFoundError(f"入力CSVがありません: {INPUT_CSV}")

        df = pd.read_csv(INPUT_CSV, encoding="utf-8-sig")
        require_columns(df, ["記号", "種別", "形態素番号", "基本形", "品詞"])

        if (df["種別"].fillna("").astype(str).str.strip() != "歯牙障害").any():
            raise ValueError("歯牙障害以外が含まれています。")

        stopwords = load_stopwords()

        work = df.copy()
        work["基本形"] = work["基本形"].fillna("").astype(str).str.strip()
        work["品詞"] = work["品詞"].fillna("").astype(str).str.strip()
        work = work[
            work["品詞"].isin(TARGET_POS)
            & work["基本形"].ne("")
            & work["基本形"].ne("*")
        ].copy()

        work = work.sort_values(["記号", "形態素番号"]).reset_index(drop=True)
        work["ストップワード"] = work["基本形"].isin(stopwords)

        rows = []
        for case_id, group in work.groupby("記号", dropna=False, sort=False):
            before = group["基本形"].astype(str).tolist()
            remaining = group.loc[~group["ストップワード"], "基本形"].astype(str).tolist()
            removed = group.loc[group["ストップワード"], "基本形"].astype(str).tolist()
            unique_remaining = list(dict.fromkeys(remaining))

            rows.append({
                "記号": case_id,
                "除去前語数": len(before),
                "除去後語数": len(remaining),
                "除去語数": len(removed),
                "除去率(%)": round(len(removed) / len(before) * 100, 4) if before else 0,
                "除去語列": " ".join(removed),
                "解析用語列": " ".join(remaining),
                "解析用語集合": " ".join(unique_remaining),
                "解析用語異なり語数": len(unique_remaining),
            })

        case_result = pd.DataFrame(rows)
        removed_result = word_summary(work, True)
        remaining_result = word_summary(work, False)

        elapsed = time.perf_counter() - start
        before_total = int(case_result["除去前語数"].sum())
        removed_total = int(case_result["除去語数"].sum())

        summary = pd.DataFrame([
            ("解析対象", "歯牙障害"),
            ("登録ストップワード数", len(stopwords)),
            ("入力形態素数", len(df)),
            ("対象形態素数", len(work)),
            ("対象事例数", work["記号"].nunique(dropna=False)),
            ("除去前語数合計", before_total),
            ("除去語数合計", removed_total),
            ("除去後語数合計", int(case_result["除去後語数"].sum())),
            ("全体除去率(%)", round(removed_total / before_total * 100, 4) if before_total else 0),
            ("処理時間(秒)", round(elapsed, 3)),
            ("ジャッカード係数", "使用しない"),
            ("次のStep", "Step3-6_歯牙障害_カテゴリ分類.py"),
        ], columns=["項目", "値"])

        save_csv(case_result, OUTPUT_CASE)
        save_csv(removed_result, OUTPUT_REMOVED)
        save_csv(remaining_result, OUTPUT_REMAINING)
        save_csv(summary, OUTPUT_SUMMARY)

        print(case_result.head(20).to_string(index=False))
        print("\n正常終了")
        print("次: Step3-6_歯牙障害_カテゴリ分類.py")

    except Exception as error:
        print(f"エラー: {type(error).__name__}: {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
