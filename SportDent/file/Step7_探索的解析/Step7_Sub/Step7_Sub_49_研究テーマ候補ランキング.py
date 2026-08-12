"""Step7 Sub49：カテゴリ別関連から研究テーマ候補を優先順位付けする。"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from Step7_Utils.statistics import FLAG, bh_adjust, columns, comparable, effect, table, two_by_two


def run(settings: dict[str, Any]) -> None | str:
    """効果量、割合差、統計的確実性、件数を統合して候補を作成する。"""
    df = settings["df"]
    logger = settings["logger"]
    dataset_name = settings["dataset_name"]
    if not comparable(df):
        logger.info("[%s] Sub49解析不能：歯牙障害・非歯牙障害の2群なし", dataset_name)
        return "skipped"

    tooth_total = int(df[FLAG].eq(1).sum())
    other_total = int(df[FLAG].eq(0).sum())
    rows: list[dict[str, Any]] = []
    for column in columns(df):
        for category in table(df, column).index:
            category = str(category)
            a, b, c, d = two_by_two(df, column, category)
            total = a + b
            # 極端に少数のカテゴリはテーマ選定が不安定で、再識別にもつながり得るため除外する。
            if category == "（欠損）" or total < 20 or min(a, b) < 3:
                continue
            estimate = effect(a, b, c, d)
            p_value = float(fisher_exact([[a, b], [c, d]], alternative="two-sided").pvalue)
            tooth_pct = a / tooth_total * 100
            other_pct = b / other_total * 100
            log2_or = math.log2(float(estimate["OR"]))
            direction = "歯牙障害で多い" if log2_or > 0 else "歯牙障害で少ない"
            rows.append({
                "因子": column, "カテゴリ": category,
                "研究テーマ候補": f"{column}「{category}」と歯牙障害の関連（{direction}）",
                "方向": direction, "歯牙障害件数": a, "歯牙障害以外件数": b, "合計件数": total,
                "歯牙障害群内割合（％）": tooth_pct, "歯牙障害以外群内割合（％）": other_pct,
                "割合差（pt）": tooth_pct - other_pct, "オッズ比": estimate["OR"],
                "95%CI下限": estimate["OR_CI_LOW"], "95%CI上限": estimate["OR_CI_HIGH"],
                "絶対log2OR": abs(log2_or), "Fisher_p値": p_value,
            })

    result = pd.DataFrame(rows)
    if result.empty:
        logger.info("[%s] Sub49解析不能：基準を満たすカテゴリなし", dataset_name)
        return "skipped"

    result["BH補正p値"] = bh_adjust(result["Fisher_p値"].tolist())
    # 指標の単位差をなくすため百分位順位へ変換し、研究テーマとしての実用性も件数で評価する。
    result["効果量点"] = result["絶対log2OR"].rank(method="average", pct=True) * 100
    result["割合差点"] = result["割合差（pt）"].abs().rank(method="average", pct=True) * 100
    evidence = -np.log10(result["BH補正p値"].clip(lower=np.finfo(float).tiny))
    result["統計的確実性点"] = evidence.rank(method="average", pct=True) * 100
    result["対象規模点"] = np.log1p(result["合計件数"]).rank(method="average", pct=True) * 100
    result["研究優先度スコア"] = (
        result["効果量点"] * .35 + result["割合差点"] * .25
        + result["統計的確実性点"] * .25 + result["対象規模点"] * .15
    )
    result["解釈上の注意"] = "仮説生成用（因果関係を示さず、交絡調整・研究デザイン検討が必要）"
    result = result.sort_values(["研究優先度スコア", "合計件数"], ascending=False).reset_index(drop=True)
    result.insert(0, "全候補内順位", np.arange(1, len(result) + 1))

    # 上位表が一つの因子だけで占有されないよう、各因子最大2候補に制限する。
    selected_indices: list[int] = []
    factor_counts: dict[str, int] = {}
    for index, row in result.iterrows():
        factor = str(row["因子"])
        if factor_counts.get(factor, 0) >= 2:
            continue
        selected_indices.append(index)
        factor_counts[factor] = factor_counts.get(factor, 0) + 1
        if len(selected_indices) == 10:
            break
    summary = result.loc[selected_indices].copy().reset_index(drop=True)
    summary.insert(0, "推奨順位", np.arange(1, len(summary) + 1))

    result.to_csv(settings["table_dir"] / "Step7-49_研究テーマ候補_全評価.csv", index=False,
                  encoding=settings["text_encoding"])
    summary[["推奨順位", "研究テーマ候補", "研究優先度スコア", "因子", "カテゴリ", "方向",
             "歯牙障害件数", "歯牙障害以外件数", "割合差（pt）", "オッズ比", "95%CI下限",
             "95%CI上限", "BH補正p値", "解釈上の注意"]].to_csv(
        settings["summary_dir"] / "Step7-49_研究テーマ候補ランキング.csv", index=False,
        encoding=settings["text_encoding"]
    )
    logger.info("[%s] Sub49 / 全候補=%d / 推奨候補=%d", dataset_name, len(result), len(summary))
