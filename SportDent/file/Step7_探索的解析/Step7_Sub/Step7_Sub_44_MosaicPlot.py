"""Step7 Sub44：関連が強い「場合別2」のMosaic plot。"""
from typing import Any
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.patches import Patch
from Step7_Utils.statistics import comparable, clean, FLAG
from Step7_Utils.visualization import configure_japanese_font, save_figure


def run(settings: dict[str, Any]) -> None | str:
    df=settings["df"]; column="場合別2"
    if not comparable(df) or column not in df: settings["logger"].info("[%s] Sub44解析不能：必要群または列なし",settings["dataset_name"]); return "skipped"
    configure_japanese_font(); values=clean(df[column]); top=values.value_counts().head(8).index; values=values.where(values.isin(top),"その他")
    categories=list(values.value_counts().index); colors=plt.cm.tab10.colors; color_map={category:colors[i%len(colors)] for i,category in enumerate(categories)}
    fig,ax=plt.subplots(figsize=(12,7)); x=0
    for group,label in [(0,"歯牙障害以外"),(1,"歯牙障害")]:
        group_values=values[df[FLAG].eq(group)]; width=len(group_values)/len(df); y=0
        for category,count in group_values.value_counts().items():
            height=count/len(group_values); ax.add_patch(Rectangle((x,y),width,height,facecolor=color_map[category],edgecolor="white"))
            y+=height
        ax.text(x+width/2,-.04,label,ha="center",va="top"); x+=width
    ax.set(xlim=(0,1),ylim=(-.08,1),ylabel="群内構成割合",title="場合別2と歯牙障害のMosaic plot（上位8+その他）"); ax.set_xticks([])
    ax.legend(handles=[Patch(facecolor=color_map[c],label=c) for c in categories],title="場合別2",bbox_to_anchor=(1.01,1),loc="upper left",fontsize=8)
    save_figure(fig,settings["figure_dir"],"Step7-44_場合別2_MosaicPlot"); settings["logger"].info("[%s] Sub44 / 場合別2上位8+その他",settings["dataset_name"])
