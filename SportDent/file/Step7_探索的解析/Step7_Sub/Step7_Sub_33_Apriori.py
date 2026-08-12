"""Step7 Sub33：カテゴリ項目のApriori頻出項目集合。"""
from typing import Any
import pandas as pd
from Step7_Utils.association import transactions, apriori


def run(settings: dict[str, Any]) -> None:
    tx=transactions(settings); itemsets,counts=apriori(settings,min_support=.01,max_size=3)
    rows=[]
    for itemset in itemsets:
        count=counts[itemset]
        rows.append({"項目数":len(itemset),"項目集合":" | ".join(sorted(itemset)),"事例数":count,
                     "支持度":count/len(tx),"支持度（％）":round(count/len(tx)*100,4)})
    result=pd.DataFrame(rows).sort_values(["項目数","事例数"],ascending=[True,False])
    result.to_csv(settings["table_dir"]/"Step7-33_Apriori_頻出項目集合.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub33 / トランザクション=%d / 頻出集合=%d / min_support=1%%",settings["dataset_name"],len(tx),len(result))
