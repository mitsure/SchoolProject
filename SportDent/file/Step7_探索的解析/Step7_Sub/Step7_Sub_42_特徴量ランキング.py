"""Step7 Sub42：歯牙障害フラグとOne-hotカテゴリ特徴の相互情報量ランキング。"""
from typing import Any
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import mutual_info_score
from Step7_Utils.multivariate import encoded
from Step7_Utils.statistics import comparable, FLAG


def run(settings: dict[str, Any]) -> None | str:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub42解析不能：2群なし",settings["dataset_name"]); return "skipped"
    matrix,names,origins,_,_=encoded(settings); target=df[FLAG].to_numpy()
    values=mutual_info_classif(matrix,target,discrete_features=True,random_state=settings["random_seed"])
    detail=pd.DataFrame({"元列名":origins,"特徴量":names,"相互情報量":values}).sort_values("相互情報量",ascending=False)
    # One-hot指標の単純合計は水準数が多い列を有利にするため、
    # ランキングには元のカテゴリ変数全体とアウトカムのMIを使う。
    summary_rows=[]
    for column in dict.fromkeys(origins):
        clean=df[column].astype("string").str.strip().fillna("（欠損）").replace("","（欠損）")
        subset=detail.loc[detail["元列名"].eq(column),"相互情報量"]
        summary_rows.append({"元列名":column,"カテゴリ変数全体の相互情報量":mutual_info_score(clean,target),
                             "One-hot最大相互情報量":subset.max(),"One-hot特徴量数":len(subset)})
    summary=pd.DataFrame(summary_rows).sort_values("カテゴリ変数全体の相互情報量",ascending=False)
    summary.insert(0,"順位",range(1,len(summary)+1)); detail.to_csv(settings["table_dir"]/"Step7-42_特徴量別相互情報量.csv",index=False,encoding=settings["text_encoding"])
    summary.to_csv(settings["summary_dir"]/"Step7-42_列別特徴量ランキング.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub42 / 元列=%d / One-hot特徴=%d",settings["dataset_name"],len(summary),len(detail))
