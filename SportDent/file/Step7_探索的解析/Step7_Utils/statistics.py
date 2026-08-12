"""探索的カテゴリ比較の共通計算。Subの出力や実行順には依存しない。"""
from __future__ import annotations
import math
import pandas as pd

FLAG = "Step7_歯牙障害フラグ"
EXCLUDED = {"記号", "災害発生時の状況", "種別", FLAG,
            "Step7_入力元ファイル", "Step7_入力元カテゴリ"}


def comparable(df: pd.DataFrame) -> bool:
    """歯牙障害と非歯牙障害の2群が実在するかを返す。"""
    return FLAG in df.columns and set(df[FLAG].dropna().unique()) == {0, 1}


def columns(df: pd.DataFrame) -> list[str]:
    """ID・テキスト・アウトカム・追跡列を除いた候補列を返す。"""
    return [c for c in df.columns if c not in EXCLUDED]


def clean(series: pd.Series) -> pd.Series:
    """欠損と空文字を明示カテゴリにし、分母から黙って除外しない。"""
    return series.astype("string").str.strip().fillna("（欠損）").replace("", "（欠損）")


def table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """行=カテゴリ、列=歯牙障害フラグの分割表を必ず0/1列付きで返す。"""
    return pd.crosstab(clean(df[column]), df[FLAG]).reindex(columns=[0, 1], fill_value=0)


def two_by_two(df: pd.DataFrame, column: str, category: str) -> tuple[int, int, int, int]:
    """a=当該・歯牙、b=当該・非歯牙、c=非当該・歯牙、d=非当該・非歯牙。"""
    values = clean(df[column]); flag = df[FLAG]
    hit = values.eq(category)
    return (int((hit & flag.eq(1)).sum()), int((hit & flag.eq(0)).sum()),
            int((~hit & flag.eq(1)).sum()), int((~hit & flag.eq(0)).sum()))


def effect(a: int, b: int, c: int, d: int) -> dict[str, float | bool]:
    """2×2表のOR、RRと95%CI。0セル時は0.5補正を適用した事実も返す。"""
    corrected = min(a, b, c, d) == 0
    aa, bb, cc, dd = (a + .5, b + .5, c + .5, d + .5) if corrected else (a, b, c, d)
    odds = aa * dd / (bb * cc)
    se_log_or = math.sqrt(1 / aa + 1 / bb + 1 / cc + 1 / dd)
    risk1 = aa / (aa + bb); risk0 = cc / (cc + dd); rr = risk1 / risk0
    se_log_rr = math.sqrt(1 / aa - 1 / (aa + bb) + 1 / cc - 1 / (cc + dd))
    return {"OR": odds, "OR_CI_LOW": math.exp(math.log(odds) - 1.96 * se_log_or),
            "OR_CI_HIGH": math.exp(math.log(odds) + 1.96 * se_log_or), "RR": rr,
            "RR_CI_LOW": math.exp(math.log(rr) - 1.96 * se_log_rr),
            "RR_CI_HIGH": math.exp(math.log(rr) + 1.96 * se_log_rr), "corrected": corrected}


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg法。順位逆順で累積最小を取り、単調性を保証する。"""
    count = len(p_values)
    order = sorted(range(count), key=lambda i: p_values[i])
    adjusted = [1.0] * count; running = 1.0
    for rank_index in range(count - 1, -1, -1):
        original_index = order[rank_index]; rank = rank_index + 1
        running = min(running, p_values[original_index] * count / rank)
        adjusted[original_index] = min(running, 1.0)
    return adjusted


def comparison(df: pd.DataFrame, target_columns: list[str]) -> pd.DataFrame:
    """指定列のカテゴリ別に両群の件数、群内割合、割合差を返す。"""
    rows=[]; tooth_total=int(df[FLAG].eq(1).sum()); other_total=int(df[FLAG].eq(0).sum())
    for column in target_columns:
        if column not in df.columns: continue
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category))
            tooth_pct=a/tooth_total*100 if tooth_total else float("nan")
            other_pct=b/other_total*100 if other_total else float("nan")
            rows.append({"列名":column,"カテゴリ":category,"歯牙障害件数":a,
                         "歯牙障害群内割合（％）":round(tooth_pct,4),
                         "歯牙障害以外件数":b,"歯牙障害以外群内割合（％）":round(other_pct,4),
                         "割合差_歯牙-以外（pt）":round(tooth_pct-other_pct,4),"合計":a+b})
    return pd.DataFrame(rows)
