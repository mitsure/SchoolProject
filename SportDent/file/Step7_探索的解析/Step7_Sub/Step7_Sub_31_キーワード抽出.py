"""Step7 Sub31：事例出現率に基づく歯牙障害関連キーワード抽出。"""
from collections import Counter
from typing import Any
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact
from Step7_Utils.statistics import comparable, FLAG, effect, bh_adjust
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None | str:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub31解析不能：2群なし",settings["dataset_name"]); return "skipped"
    cases,stopwords=tokenize_cases_cached(settings); flags=df[FLAG].tolist(); tooth=Counter(); other=Counter()
    for tokens,flag in zip(cases,flags):
        unique=set(analysis_words(tokens,stopwords)); (tooth if flag==1 else other).update(unique)
    tooth_total=sum(x==1 for x in flags); other_total=sum(x==0 for x in flags); rows=[]
    for word in sorted(set(tooth)|set(other)):
        a=tooth[word]; b=other[word]
        if a+b < 5: continue
        c=tooth_total-a; d=other_total-b; _,p=fisher_exact([[a,b],[c,d]]); e=effect(a,b,c,d)
        p_value=max(float(p),float(np.nextafter(0,1)))
        rows.append({"単語":word,"歯牙出現事例数":a,"歯牙事例出現率（％）":round(a/tooth_total*100,4),
                     "非歯牙出現事例数":b,"非歯牙事例出現率（％）":round(b/other_total*100,4),
                     "出現率差（pt）":round((a/tooth_total-b/other_total)*100,4),"オッズ比":e["OR"],
                     "OR_95%CI下限":e["OR_CI_LOW"],"OR_95%CI上限":e["OR_CI_HIGH"],"p値":p_value,
                     "p値下限丸め":bool(p == 0),"0.5補正":e["corrected"]})
    adjusted=bh_adjust([x["p値"] for x in rows])
    for row,q in zip(rows,adjusted): row["BH補正p値"]=q; row["BH有意（5%）"]=q<settings["significance_level"]
    result=pd.DataFrame(rows).sort_values(["BH補正p値","出現率差（pt）"],ascending=[True,False])
    result.to_csv(settings["table_dir"]/"Step7-31_歯牙障害関連キーワード_OR_BH.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub31 / 候補=%d / BH有意=%d",settings["dataset_name"],len(result),int(result["BH有意（5%）"].sum()))
