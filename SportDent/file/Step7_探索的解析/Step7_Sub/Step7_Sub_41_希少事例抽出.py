"""Step7 Sub41：5件以下のカテゴリを含む希少事例。"""
from typing import Any
import pandas as pd
from Step7_Utils.multivariate import COLUMNS


def run(settings: dict[str, Any]) -> None:
    df=settings["df"]; columns=[c for c in COLUMNS if c in df.columns]; rows=[]
    cleaned={c:df[c].astype("string").str.strip() for c in columns}
    count_maps={c:cleaned[c].value_counts(dropna=True).to_dict() for c in columns}
    for index,row in df.iterrows():
        reasons=[]
        for column in columns:
            value=row[column]
            if pd.isna(value) or not str(value).strip(): continue
            count=int(count_maps[column].get(str(value).strip(),0))
            if count<=5: reasons.append(f"{column}={str(value).strip()}（{count}件）")
        if reasons: rows.append({"記号":row["記号"],"希少カテゴリ数":len(reasons),"抽出理由":" | ".join(reasons),
                                 "Step7_入力元カテゴリ":row.get("Step7_入力元カテゴリ","")})
    result=pd.DataFrame(rows)
    result.to_csv(settings["csv_dir"]/"Step7-41_希少事例.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub41 / 希少事例=%d（自由記載は非出力）",settings["dataset_name"],len(result))
