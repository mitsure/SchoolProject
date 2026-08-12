"""Step7 Sub35：Apriori頻出項目集合からの関連ルール。"""
from itertools import combinations
from typing import Any
import pandas as pd
from Step7_Utils.association import transactions, apriori


def run(settings: dict[str, Any]) -> None:
    tx=transactions(settings); itemsets,counts=apriori(settings,min_support=.01,max_size=3); n=len(tx); rows=[]
    for itemset in itemsets:
        if len(itemset)<2: continue
        for left_size in range(1,len(itemset)):
            for left_tuple in combinations(itemset,left_size):
                left=frozenset(left_tuple); right=itemset-left
                left_count=counts.get(left) or sum(left.issubset(case) for case in tx)
                right_count=counts.get(right) or sum(right.issubset(case) for case in tx)
                joint=counts[itemset]; confidence=joint/left_count; right_support=right_count/n; lift=confidence/right_support
                if confidence < .20 or lift < 1.20: continue
                rows.append({"前件":" | ".join(sorted(left)),"後件":" | ".join(sorted(right)),"項目数":len(itemset),
                             "共起事例数":joint,"支持度":joint/n,"信頼度":confidence,"lift":lift})
    result=pd.DataFrame(rows).sort_values(["lift","共起事例数"],ascending=False)
    result.to_csv(settings["table_dir"]/"Step7-35_AssociationRule.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub35 / ルール=%d / confidence≥0.20 / lift≥1.20",settings["dataset_name"],len(result))
