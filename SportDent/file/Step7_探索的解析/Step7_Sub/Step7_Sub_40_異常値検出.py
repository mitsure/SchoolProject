"""Step7 Sub40：低頻度カテゴリと文長による透明な異常値候補検出。"""
from typing import Any
import numpy as np
import pandas as pd
from Step7_Utils.multivariate import COLUMNS
from Step7_Utils.text_analysis import TEXT_COLUMN


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; columns=[c for c in COLUMNS if c in df.columns]; rarity=np.zeros(len(df)); rare_count=np.zeros(len(df),dtype=int)
    for column in columns:
        clean=df[column].astype("string").str.strip().fillna("（欠損）").replace("","（欠損）"); counts=clean.value_counts(); freq=clean.map(counts)/len(df)
        rarity += -np.log(freq.to_numpy(dtype=float)); rare_count += (clean.map(counts).to_numpy()<=5)
    lengths=df[TEXT_COLUMN].fillna("").astype(str).str.len().to_numpy(); median=float(np.median(lengths)); mad=float(np.median(np.abs(lengths-median)))
    robust_z=(lengths-median)/(1.4826*mad) if mad>0 else np.zeros(len(df)); threshold=float(np.quantile(rarity,.99))
    result=pd.DataFrame({"記号":df["記号"].values,"希少性スコア":rarity,"5件以下カテゴリ数":rare_count,
                         "文字数":lengths,"文長頑健zスコア":robust_z})
    result["希少性上位1%"]=result["希少性スコア"]>=threshold; result["|文長z|≥3.5"]=result["文長頑健zスコア"].abs()>=3.5
    result["確認候補"]=result["希少性上位1%"]|result["|文長z|≥3.5"]
    result.sort_values(["確認候補","希少性スコア"],ascending=False).to_csv(settings["csv_dir"]/"Step7-40_異常値確認候補.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub40 / 確認候補=%d（自動除外なし）",settings["dataset_name"],int(result["確認候補"].sum()))
