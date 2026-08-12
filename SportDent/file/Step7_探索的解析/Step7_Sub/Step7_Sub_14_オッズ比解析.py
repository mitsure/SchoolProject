"""Step7 Sub14：カテゴリ別オッズ比と95%CI。"""
from typing import Any
import pandas as pd
from Step7_Utils.statistics import comparable, columns, table, two_by_two, effect


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub14解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category)); e=effect(a,b,c,d)
            rows.append({"列名":column,"カテゴリ":category,"a_当該歯牙":a,"b_当該非歯牙":b,"c_非当該歯牙":c,"d_非当該非歯牙":d,
                         "オッズ比":e["OR"],"95%CI下限":e["OR_CI_LOW"],"95%CI上限":e["OR_CI_HIGH"],"0.5補正":e["corrected"]})
    pd.DataFrame(rows).to_csv(settings["table_dir"]/"Step7-14_オッズ比_95CI.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub14 / %dカテゴリ",settings["dataset_name"],len(rows))
