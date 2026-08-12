"""Step7 Sub25：歯牙障害対非歯牙障害の比較TF-IDF。"""
from typing import Any
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from Step7_Utils.statistics import comparable, FLAG
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub25解析不能：2群なし",settings["dataset_name"]); return "skipped"
    cases,stopwords=tokenize_cases_cached(settings); documents=[" ".join(analysis_words(x,stopwords)) for x in cases]
    vectorizer=TfidfVectorizer(tokenizer=str.split,preprocessor=None,token_pattern=None,lowercase=False,min_df=5)
    matrix=vectorizer.fit_transform(documents); names=vectorizer.get_feature_names_out(); flags=df[FLAG].to_numpy()
    tooth=np.asarray(matrix[flags==1].mean(axis=0)).ravel(); other=np.asarray(matrix[flags==0].mean(axis=0)).ravel()
    result=pd.DataFrame({"単語":names,"歯牙障害_平均TFIDF":tooth,"歯牙障害以外_平均TFIDF":other})
    result["TFIDF差_歯牙-以外"]=result["歯牙障害_平均TFIDF"]-result["歯牙障害以外_平均TFIDF"]
    result["絶対差"]=result["TFIDF差_歯牙-以外"].abs(); result=result.sort_values("絶対差",ascending=False)
    result.to_csv(settings["table_dir"]/"Step7-25_歯牙_vs_非歯牙_TFIDF比較.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub25 / 語彙=%d / min_df=5",settings["dataset_name"],len(result))
