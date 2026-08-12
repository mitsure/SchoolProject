"""Step7 Sub26：事例単位の共起ネットワーク用ノード・エッジ表。"""
from collections import Counter
from itertools import combinations
from typing import Any
import pandas as pd
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None:
    """同一事例内の語は1回と数え、最低5事例の共起ペアだけを出力する。"""
    cases,stopwords=tokenize_cases_cached(settings); nodes=Counter(); edges=Counter()
    for tokens in cases:
        words=sorted(set(analysis_words(tokens,stopwords))); nodes.update(words); edges.update(combinations(words,2))
    edge_rows=[]
    for (left,right),count in edges.items():
        if count < 5: continue
        union=nodes[left]+nodes[right]-count
        edge_rows.append({"語1":left,"語2":right,"共起事例数":count,
                          "Jaccard（ネットワーク重み）":count/union if union else 0})
    edge_df=pd.DataFrame(edge_rows).sort_values(["共起事例数","Jaccard（ネットワーク重み）"],ascending=False)
    node_df=pd.DataFrame([{" 単語".strip():word,"出現事例数":count} for word,count in nodes.most_common()])
    edge_df.to_csv(settings["csv_dir"]/"Step7-26_共起ネットワーク_エッジ.csv",index=False,encoding=settings["text_encoding"])
    node_df.to_csv(settings["csv_dir"]/"Step7-26_共起ネットワーク_ノード.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub26 / ノード=%d / エッジ=%d（最小共起5）",settings["dataset_name"],len(node_df),len(edge_df))
