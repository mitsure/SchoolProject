"""Step7 Sub16：Fisher検定のBenjamini-Hochberg多重比較補正。"""
from typing import Any
import pandas as pd
from scipy.stats import fisher_exact
from Step7_Utils.statistics import comparable, columns, table, two_by_two, bh_adjust


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; logger=settings["logger"]
    if not comparable(df): logger.info("[%s] Sub16解析不能：2群なし",settings["dataset_name"]); return "skipped"
    rows=[]
    for column in columns(df):
        local=[]
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category)); _,p=fisher_exact([[a,b],[c,d]])
            local.append({"列名":column,"カテゴリ":category,"p値":float(p),"当該カテゴリ合計":a+b})
        adjusted=bh_adjust([x["p値"] for x in local])
        for item,q in zip(local,adjusted): item["BH補正p値"]=q; item["BH有意（5%）"]=q<settings["significance_level"]
        rows.extend(local)
    result=pd.DataFrame(rows).sort_values(["BH補正p値","p値"])
    result.to_csv(settings["table_dir"]/"Step7-16_Fisher_BH多重比較補正.csv",index=False,encoding=settings["text_encoding"])
    logger.info("[%s] Sub16 / %d比較 / BH有意=%d",settings["dataset_name"],len(result),int(result["BH有意（5%）"].sum()))
