"""Step7 Sub46：カテゴリ別割合差・OR・件数のBubble chart。"""
from typing import Any
import math
import matplotlib.pyplot as plt
import pandas as pd
from Step7_Utils.statistics import comparable, columns, table, two_by_two, effect
from Step7_Utils.visualization import configure_japanese_font, save_figure


def run(settings: dict[str, Any]) -> None | str:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub46解析不能：2群なし",settings["dataset_name"]); return "skipped"
    configure_japanese_font(); tooth_total=int(df["Step7_歯牙障害フラグ"].eq(1).sum()); other_total=len(df)-tooth_total; rows=[]
    for column in columns(df):
        for category in table(df,column).index:
            a,b,c,d=two_by_two(df,column,str(category)); total=a+b
            if total<20: continue
            e=effect(a,b,c,d); rows.append({"ラベル":f"{column}={category}","割合差":a/tooth_total*100-b/other_total*100,
                "log2OR":math.log2(e["OR"]),"件数":total,"強度":abs(math.log2(e["OR"]))})
    result=pd.DataFrame(rows).sort_values("強度",ascending=False).head(30); fig,ax=plt.subplots(figsize=(12,9))
    ax.scatter(result["割合差"],result["log2OR"],s=result["件数"].pow(.6)*8,c=result["log2OR"],cmap="coolwarm",alpha=.7,edgecolor="gray")
    # 上位すべてへラベルを付けると読めないため、効果量上位12に限定する。
    for i,(_,row) in enumerate(result.head(12).iterrows()):
        offset=(5,7 if i%2==0 else -10); ax.annotate(row["ラベル"],(row["割合差"],row["log2OR"]),fontsize=7,xytext=offset,textcoords="offset points")
    ax.axhline(0,color="gray",lw=.8); ax.axvline(0,color="gray",lw=.8); ax.set(xlabel="群内割合差：歯牙-非歯牙（pt）",ylabel="log2(オッズ比)",title="歯牙障害関連カテゴリ Bubble chart（最小20件）")
    save_figure(fig,settings["figure_dir"],"Step7-46_カテゴリ効果量_BubbleChart"); settings["logger"].info("[%s] Sub46 / 表示=%d",settings["dataset_name"],len(result))
