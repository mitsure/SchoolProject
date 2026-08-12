"""Step7 Sub04：重複データ確認。"""
from __future__ import annotations
from typing import Any
import pandas as pd


def run(settings: dict[str, Any]) -> None:
    """ID重複と元15列の完全一致重複を、削除せずに出力する。"""
    df: pd.DataFrame = settings["df"]
    logger = settings["logger"]
    technical = [c for c in df.columns if c.startswith("Step7_")]
    original = [c for c in df.columns if c not in technical]
    exact_mask = df.duplicated(subset=original, keep=False)
    exact = df.loc[exact_mask].copy()
    id_column = "記号" if "記号" in df.columns else None
    id_dup = df.loc[df.duplicated(subset=[id_column], keep=False)].copy() if id_column else pd.DataFrame()
    exact.to_csv(settings["csv_dir"] / "Step7-04_完全一致重複候補.csv", index=False, encoding=settings["text_encoding"])
    id_dup.to_csv(settings["csv_dir"] / "Step7-04_ID重複候補.csv", index=False, encoding=settings["text_encoding"])
    summary = pd.DataFrame([
        {"項目": "対象件数", "値": len(df), "判定": "参考"},
        {"項目": "完全一致重複候補行数", "値": int(exact_mask.sum()), "判定": "OK" if exact.empty else "要確認"},
        {"項目": "ID重複候補行数", "値": len(id_dup), "判定": "OK" if id_dup.empty else "要確認"},
        {"項目": "自動削除行数", "値": 0, "判定": "OK"},
    ])
    summary.to_csv(settings["summary_dir"] / "Step7-04_重複データ確認サマリー.csv", index=False, encoding=settings["text_encoding"])
    logger.info("[%s] Sub04 / 完全一致=%d / ID重複=%d", settings["dataset_name"], len(exact), len(id_dup))
