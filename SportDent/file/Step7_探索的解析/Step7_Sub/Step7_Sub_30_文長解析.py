"""Step7 Sub30：自由記載の文字数・形態素数・解析対象語数。"""
from typing import Any
import pandas as pd
from Step7_Utils.text_analysis import TEXT_COLUMN, tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; cases,stopwords=tokenize_cases_cached(settings); rows=[]
    for position,(index,text,tokens) in enumerate(zip(df.index,df[TEXT_COLUMN].fillna("").astype(str),cases),1):
        rows.append({"行番号":position,"記号":df.at[index,"記号"] if "記号" in df else pd.NA,
                     "文字数（空白含む）":len(text),"文字数（空白除外）":len("".join(text.split())),
                     "形態素数":len(tokens),"解析対象語数":len(analysis_words(tokens,stopwords))})
    detail=pd.DataFrame(rows); numeric=["文字数（空白含む）","文字数（空白除外）","形態素数","解析対象語数"]
    summary=detail[numeric].describe(percentiles=[.25,.5,.75,.9,.95,.99]).T.reset_index(names="指標")
    detail.to_csv(settings["csv_dir"]/"Step7-30_事例別文長.csv",index=False,encoding=settings["text_encoding"])
    summary.to_csv(settings["summary_dir"]/"Step7-30_文長基本統計.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub30 / %d事例",settings["dataset_name"],len(detail))
