"""Step7 Sub24：品詞・品詞細分類集計。"""
from collections import Counter
from typing import Any
import pandas as pd
from Step7_Utils.text_analysis import tokenize_cases_cached


def run(settings: dict[str, Any]) -> None:
    cases,_=tokenize_cases_cached(settings); counts=Counter(); documents=Counter()
    for tokens in cases:
        keys=[(x["品詞"],x["品詞細分類"]) for x in tokens]; counts.update(keys); documents.update(set(keys))
    total=sum(counts.values())
    result=pd.DataFrame([{" 品詞".strip():pos,"品詞細分類":detail,"形態素数":count,
                          "全形態素割合（％）":round(count/total*100,4) if total else 0,
                          "出現事例数":documents[(pos,detail)],"事例出現率（％）":round(documents[(pos,detail)]/len(cases)*100,4)}
                         for (pos,detail),count in counts.most_common()])
    result.to_csv(settings["table_dir"]/"Step7-24_品詞_品詞細分類集計.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub24 / 形態素=%d / 品詞区分=%d",settings["dataset_name"],total,len(result))
