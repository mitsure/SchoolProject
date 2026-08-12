"""Step7多変量解析の共通One-hot特徴量作成。"""
from __future__ import annotations
import pandas as pd
from sklearn.preprocessing import OneHotEncoder

COLUMNS = ["給付年度", "被災学校種", "被災学年", "性別", "場合別1", "場合別2",
           "競技種目", "通学方法", "発生場所1", "発生場所2", "遊具等"]


def encoded(settings: dict):
    """欠損を明示水準とした密One-hot行列、名称、元列名、エンコーダを返す。"""
    cache=settings.setdefault("cache",{}); key="multivariate_onehot_v1"
    if key in cache: return cache[key]
    df: pd.DataFrame=settings["df"]; columns=[c for c in COLUMNS if c in df.columns]
    clean=df[columns].astype("string").apply(lambda s:s.str.strip().fillna("（欠損）").replace("","（欠損）"))
    encoder=OneHotEncoder(handle_unknown="ignore",sparse_output=False,dtype="float32")
    matrix=encoder.fit_transform(clean); names=encoder.get_feature_names_out(columns).tolist()
    origins=[]
    for column,categories in zip(columns,encoder.categories_): origins.extend([column]*len(categories))
    cache[key]=(matrix,names,origins,encoder,columns)
    return cache[key]
