"""Step7 Sub13：調整済み標準化残差分析。"""
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from Step7_Utils.statistics import comparable, columns, table


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub13解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        tab=table(df,column)
        if tab.shape[0]<2: continue
        _,_,_,expected=chi2_contingency(tab,correction=False); observed=tab.to_numpy(); n=observed.sum()
        row_prop=observed.sum(axis=1)/n; col_prop=observed.sum(axis=0)/n
        denominator=np.sqrt(expected*(1-row_prop[:,None])*(1-col_prop[None,:]))
        residual=np.divide(observed-expected,denominator,out=np.full_like(expected,np.nan,dtype=float),where=denominator>0)
        for i,category in enumerate(tab.index):
            for j,group in enumerate([0,1]):
                z=float(residual[i,j]); rows.append({"列名":column,"カテゴリ":category,
                    "群":"歯牙障害" if group==1 else "歯牙障害以外"," 観測度数".strip():int(observed[i,j]),
                    "期待度数":float(expected[i,j]),"調整済み標準化残差":z,"|z|≥1.96":bool(abs(z)>=1.96)})
    pd.DataFrame(rows).to_csv(settings["table_dir"]/"Step7-13_標準化残差分析.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub13 / %dセル",settings["dataset_name"],len(rows))
