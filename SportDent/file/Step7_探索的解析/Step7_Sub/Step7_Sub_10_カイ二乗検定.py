"""Step7 Sub10：歯牙障害と各カテゴリ列のχ²検定。"""
from typing import Any
import pandas as pd
from scipy.stats import chi2_contingency
from Step7_Utils.statistics import comparable, columns, table


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub10解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        tab=table(df,column)
        if tab.shape[0] < 2: continue
        chi2,p,dof,expected=chi2_contingency(tab,correction=False)
        low=int((expected < 5).sum()); total=expected.size
        rows.append({"列名":column,"カテゴリ数":tab.shape[0],"カイ二乗値":chi2,"自由度":dof,"p値":p,
                     "期待度5未満セル数":low,"期待度5未満割合（％）":round(low/total*100,4),
                     "前提条件判定":"要注意" if low/total>.2 or expected.min()<1 else "概ね適合"})
    pd.DataFrame(rows).to_csv(settings["table_dir"]/"Step7-10_カイ二乗検定.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub10 / %d列",settings["dataset_name"],len(rows))
