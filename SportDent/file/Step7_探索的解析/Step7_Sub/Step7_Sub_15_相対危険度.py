"""Step7 Sub15：カテゴリ別リスク比（相対危険度）と95%CI。"""
from typing import Any
import pandas as pd
from Step7_Utils.statistics import comparable, columns, table, two_by_two, effect


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub15解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category)); e=effect(a,b,c,d)
            rows.append({"列名":column,"カテゴリ":category,"当該カテゴリの歯牙割合（％）":round(a/(a+b)*100,4) if a+b else pd.NA,
                         "その他の歯牙割合（％）":round(c/(c+d)*100,4) if c+d else pd.NA,
                         "リスク比":e["RR"],"95%CI下限":e["RR_CI_LOW"],"95%CI上限":e["RR_CI_HIGH"],"0.5補正":e["corrected"]})
    pd.DataFrame(rows).to_csv(settings["table_dir"]/"Step7-15_リスク比_95CI.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub15 / %dカテゴリ",settings["dataset_name"],len(rows))
