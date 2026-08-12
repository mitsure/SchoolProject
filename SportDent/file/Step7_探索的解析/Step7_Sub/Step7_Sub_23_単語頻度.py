"""Step7 Sub23：トークン頻度と事例出現率。"""
from collections import Counter
from typing import Any
import pandas as pd
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None:
    cases,stopwords=tokenize_cases_cached(settings)
    total=Counter(); documents=Counter()
    for tokens in cases:
        words=analysis_words(tokens,stopwords); total.update(words); documents.update(set(words))
    rows=[{"単語":word,"総出現回数":count,"出現事例数":documents[word],
           "事例出現率（％）":round(documents[word]/len(cases)*100,4),"頻度順位":rank}
          for rank,(word,count) in enumerate(total.most_common(),1)]
    result=pd.DataFrame(rows)
    result.to_csv(settings["table_dir"]/"Step7-23_単語頻度_事例出現率.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub23 / 事例=%d / 異なり語=%d",settings["dataset_name"],len(cases),len(result))
