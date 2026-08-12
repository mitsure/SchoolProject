"""Step7 Sub37：One-hot特徴の主成分分析。"""
from typing import Any
import pandas as pd
from sklearn.decomposition import PCA
from Step7_Utils.multivariate import encoded


def run(settings: dict[str, Any]) -> None:
    matrix,names,_,_,_=encoded(settings); components=min(10,matrix.shape[0]-1,matrix.shape[1])
    model=PCA(n_components=components,random_state=settings["random_seed"]); scores=model.fit_transform(matrix)
    variance=pd.DataFrame({"主成分":[f"PC{i+1}" for i in range(components)],"寄与率":model.explained_variance_ratio_,
                           "累積寄与率":model.explained_variance_ratio_.cumsum()})
    score_df=pd.DataFrame(scores,columns=[f"PC{i+1}" for i in range(components)]); score_df.insert(0,"記号",settings["df"]["記号"].values)
    loadings=[]
    for i,vector in enumerate(model.components_):
        series=pd.Series(vector,index=names)
        for rank,(feature,value) in enumerate(series.reindex(series.abs().sort_values(ascending=False).index).head(20).items(),1):
            loadings.append({"主成分":f"PC{i+1}","順位":rank,"特徴":feature,"負荷量":value,"絶対負荷量":abs(value)})
    variance.to_csv(settings["summary_dir"]/"Step7-37_PCA_寄与率.csv",index=False,encoding=settings["text_encoding"])
    score_df.to_csv(settings["csv_dir"]/"Step7-37_PCA_事例スコア.csv",index=False,encoding=settings["text_encoding"])
    pd.DataFrame(loadings).to_csv(settings["table_dir"]/"Step7-37_PCA_主要負荷量.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub37 / PC=%d / 累積寄与率=%.4f",settings["dataset_name"],components,variance.iloc[-1]["累積寄与率"])
