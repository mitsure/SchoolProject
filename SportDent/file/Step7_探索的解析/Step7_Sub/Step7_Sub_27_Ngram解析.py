"""Step7 Sub27：解析対象語の2-gram・3-gram解析。"""
from collections import Counter
from typing import Any
import pandas as pd
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None:
    cases,stopwords=tokenize_cases_cached(settings); rows=[]
    for n in (2,3):
        total=Counter(); documents=Counter()
        for tokens in cases:
            words=analysis_words(tokens,stopwords); grams=[tuple(words[i:i+n]) for i in range(len(words)-n+1)]
            total.update(grams); documents.update(set(grams))
        for rank,(gram,count) in enumerate(total.most_common(),1):
            if documents[gram] < 3: continue
            rows.append({"N":n,"N-gram":" ".join(gram),"総出現回数":count,"出現事例数":documents[gram],
                         "事例出現率（％）":round(documents[gram]/len(cases)*100,4),"N別順位":rank})
    result=pd.DataFrame(rows)
    result.to_csv(settings["table_dir"]/"Step7-27_Ngram_2gram_3gram.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub27 / 出力N-gram=%d（最小3事例）",settings["dataset_name"],len(result))
