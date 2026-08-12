"""Step7 Sub36：One-hotカテゴリ特徴のMiniBatch K-meansクラスタリング。"""
from typing import Any
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score
from Step7_Utils.multivariate import encoded


def run(settings: dict[str, Any]) -> None:
    matrix,names,_,_,_=encoded(settings); metrics=[]; models={}; sample=min(2000,len(matrix))
    for k in range(2,min(8,len(matrix)-1)+1):
        model=MiniBatchKMeans(n_clusters=k,random_state=settings["random_seed"],n_init=20,batch_size=512)
        labels=model.fit_predict(matrix); score=silhouette_score(matrix,labels,sample_size=sample,random_state=settings["random_seed"])
        metrics.append({"クラスタ数":k,"silhouette_score":score,"慣性":model.inertia_}); models[k]=(model,labels)
    metric_df=pd.DataFrame(metrics).sort_values("silhouette_score",ascending=False); best=int(metric_df.iloc[0]["クラスタ数"]); model,labels=models[best]
    assignments=pd.DataFrame({"記号":settings["df"]["記号"].values,"クラスタ":labels})
    sizes=assignments["クラスタ"].value_counts().sort_index().rename_axis("クラスタ").reset_index(name="件数"); sizes["割合（％）"]=(sizes["件数"]/len(assignments)*100).round(4)
    centers=pd.DataFrame(model.cluster_centers_,columns=names); profile=[]
    for cluster,row in centers.iterrows():
        for rank,(feature,value) in enumerate(row.sort_values(ascending=False).head(15).items(),1): profile.append({"クラスタ":cluster,"順位":rank,"代表特徴":feature,"中心値":value})
    metric_df.to_csv(settings["summary_dir"]/"Step7-36_クラスタ数評価.csv",index=False,encoding=settings["text_encoding"])
    assignments.to_csv(settings["csv_dir"]/"Step7-36_事例別クラスタ.csv",index=False,encoding=settings["text_encoding"])
    sizes.to_csv(settings["table_dir"]/"Step7-36_クラスタ構成.csv",index=False,encoding=settings["text_encoding"])
    pd.DataFrame(profile).to_csv(settings["table_dir"]/"Step7-36_クラスタ代表特徴.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub36 / 採用k=%d / silhouette=%.4f",settings["dataset_name"],best,float(metric_df.iloc[0]["silhouette_score"]))
