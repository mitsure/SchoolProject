"""Step7 Sub43：調整済み標準化残差のヒートマップ。"""
from typing import Any
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency
from Step7_Utils.statistics import comparable, columns, table
from Step7_Utils.visualization import configure_japanese_font, save_figure


def run(settings: dict[str, Any]) -> None | str:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub43解析不能：2群なし",settings["dataset_name"]); return "skipped"
    configure_japanese_font(); rows=[]
    for column in columns(df):
        tab=table(df,column)
        if tab.shape[0]<2: continue
        _,_,_,expected=chi2_contingency(tab,correction=False); observed=tab.to_numpy(); n=observed.sum()
        denominator=np.sqrt(expected*(1-observed.sum(1)[:,None]/n)*(1-observed.sum(0)[None,:]/n))
        residual=np.divide(observed-expected,denominator,out=np.zeros_like(expected),where=denominator>0)
        for i,category in enumerate(tab.index): rows.append((f"{column}={category}",float(residual[i,1])))
    selected=sorted(rows,key=lambda x:abs(x[1]),reverse=True)[:30]; labels=[x[0] for x in selected][::-1]; values=np.array([x[1] for x in selected][::-1])[:,None]
    fig,ax=plt.subplots(figsize=(8,12)); image=ax.imshow(values,aspect="auto",cmap="coolwarm",vmin=-max(2,abs(values).max()),vmax=max(2,abs(values).max()))
    ax.set_yticks(range(len(labels)),labels); ax.set_xticks([0],["歯牙障害"]); ax.set_title("歯牙障害の調整済み標準化残差 絶対値上位30")
    # 各セルの境界が印刷時にも判別できるよう罫線を描画する。
    ax.set_xticks(np.arange(-.5,values.shape[1],1),minor=True)
    ax.set_yticks(np.arange(-.5,values.shape[0],1),minor=True)
    ax.grid(which="minor",color="black",linestyle="-",linewidth=.6)
    ax.tick_params(which="minor",bottom=False,left=False)
    for i,value in enumerate(values[:,0]): ax.text(0,i,f"{value:.2f}",ha="center",va="center",fontsize=8)
    fig.colorbar(image,ax=ax,label="調整済み標準化残差"); save_figure(fig,settings["figure_dir"],"Step7-43_標準化残差ヒートマップ")
    settings["logger"].info("[%s] Sub43 / 上位%dカテゴリ",settings["dataset_name"],len(selected))
