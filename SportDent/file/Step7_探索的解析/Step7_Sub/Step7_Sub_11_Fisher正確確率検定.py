"""Step7 Sub11：各カテゴリの一対その他Fisher正確確率検定。"""
from typing import Any
import pandas as pd
from scipy.stats import fisher_exact
from Step7_Utils.statistics import comparable, columns, table, two_by_two


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub11解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category)); odds,p=fisher_exact([[a,b],[c,d]])
            rows.append({"列名":column,"カテゴリ":category,"歯牙_当該":a,"非歯牙_当該":b,
                         "歯牙_その他":c,"非歯牙_その他":d,"Fisherオッズ比":odds,"p値":p})
    pd.DataFrame(rows).to_csv(settings["table_dir"]/"Step7-11_Fisher正確確率検定.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub11 / %d比較",settings["dataset_name"],len(rows))
