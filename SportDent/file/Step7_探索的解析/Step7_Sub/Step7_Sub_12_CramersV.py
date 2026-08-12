"""Step7 Sub12：バイアス補正Cramér's V。"""
from typing import Any
import math
import pandas as pd
from scipy.stats import chi2_contingency
from Step7_Utils.statistics import comparable, columns, table


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub12解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        tab=table(df,column); n=tab.to_numpy().sum(); r,k=tab.shape
        if r<2 or n<=1: continue
        chi2,p,_,_=chi2_contingency(tab,correction=False); phi2=chi2/n
        phi2c=max(0,phi2-((k-1)*(r-1))/(n-1)); rc=r-((r-1)**2)/(n-1); kc=k-((k-1)**2)/(n-1)
        denominator=min(kc-1,rc-1); value=math.sqrt(phi2c/denominator) if denominator>0 else float('nan')
        rows.append({"列名":column,"カテゴリ数":r,"CramersV（バイアス補正）":value,"p値（カイ二乗）":p})
    pd.DataFrame(rows).sort_values("CramersV（バイアス補正）",ascending=False).to_csv(settings["table_dir"]/"Step7-12_CramersV.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub12 / %d列",settings["dataset_name"],len(rows))
