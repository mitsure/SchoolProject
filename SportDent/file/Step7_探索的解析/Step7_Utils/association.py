"""Step7のカテゴリトランザクションとApriori共通計算。"""
from __future__ import annotations
from collections import Counter
from itertools import combinations
import math
import pandas as pd

EXCLUDED = {"記号", "災害発生時の状況", "種別", "Step7_入力元ファイル",
            "Step7_入力元カテゴリ", "Step7_歯牙障害フラグ"}


def transactions(settings: dict) -> list[frozenset[str]]:
    """欠損は関連パターンを支配しやすいため除外し、非欠損値だけを列名付き項目にする。"""
    cache=settings.setdefault("cache",{}); key="categorical_transactions_v1"
    if key in cache: return cache[key]
    df: pd.DataFrame=settings["df"]; columns=[c for c in df.columns if c not in EXCLUDED]
    result=[]
    for _,row in df[columns].iterrows():
        items=[]
        for column,value in row.items():
            if pd.isna(value) or not str(value).strip(): continue
            items.append(f"{column}={str(value).strip()}")
        result.append(frozenset(items))
    cache[key]=result
    return result


def apriori(settings: dict, min_support: float = .01, max_size: int = 3) -> tuple[list[frozenset[str]], dict[frozenset[str], int]]:
    """Aprioriの下方閉包性で候補を絞り、頻出1〜3項目集合と事例数を返す。"""
    cache=settings.setdefault("cache",{}); key=f"apriori_{min_support}_{max_size}"
    if key in cache: return cache[key]
    tx=transactions(settings); threshold=max(1,math.ceil(len(tx)*min_support)); counts: dict[frozenset[str],int]={}; all_sets=[]
    # 1事例の項目数は高々12程度であるため、実際に出現した組合せだけを
    # Counterで数える。存在しない候補を全事例に照合する方式より高速で、
    # 支持度閾値でサイズごとに剪定するAprioriの結果と一致する。
    for size in range(1,max_size+1):
        observed=Counter(frozenset(combo) for case in tx for combo in combinations(sorted(case),size))
        frequent={itemset:count for itemset,count in observed.items() if count>=threshold}
        counts.update(frequent); all_sets.extend(frequent)
        if not frequent: break
    cache[key]=(all_sets,counts)
    return all_sets,counts
