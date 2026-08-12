"""Step7 Sub47：上位共起語の小規模ネットワーク図。"""
from collections import Counter
from itertools import combinations
from typing import Any
import math
import matplotlib.pyplot as plt
from Step7_Utils.text_analysis import tokenize_cases_cached, analysis_words
from Step7_Utils.visualization import configure_japanese_font, save_figure


def run(settings: dict[str, Any]) -> None:
    configure_japanese_font(); cases,stopwords=tokenize_cases_cached(settings); edges=Counter(); frequency=Counter()
    for tokens in cases:
        words=set(analysis_words(tokens,stopwords)); frequency.update(words); edges.update(combinations(sorted(words),2))
    # 総頻度語だけで図が支配されないよう、共起数/幾何平均頻度をエッジ強度とする。
    scored=[]
    for (left,right),count in edges.items():
        if count<10: continue
        score=count/math.sqrt(frequency[left]*frequency[right]); scored.append((left,right,count,score))
    top_edges=sorted(scored,key=lambda x:x[3],reverse=True)[:80]; degree=Counter()
    for left,right,count,score in top_edges: degree[left]+=score; degree[right]+=score
    nodes=[word for word,_ in degree.most_common(18)]; node_set=set(nodes); selected=[x for x in top_edges if x[0] in node_set and x[1] in node_set]
    angles={word:2*math.pi*i/len(nodes) for i,word in enumerate(nodes)}; positions={word:(math.cos(a),math.sin(a)) for word,a in angles.items()}
    fig,ax=plt.subplots(figsize=(11,11))
    for left,right,count,score in selected:
        x1,y1=positions[left]; x2,y2=positions[right]; ax.plot([x1,x2],[y1,y2],color="#78909c",alpha=.35,lw=.5+4*score)
    sizes=[100+900*frequency[word]/max(frequency[n] for n in nodes) for word in nodes]
    ax.scatter([positions[n][0] for n in nodes],[positions[n][1] for n in nodes],s=sizes,c="#4c78a8",alpha=.85,edgecolor="white")
    for word in nodes: x,y=positions[word]; ax.text(x*1.12,y*1.12,word,ha="center",va="center",fontsize=10)
    ax.set(xlim=(-1.3,1.3),ylim=(-1.3,1.3)); ax.set_title("共起ネットワーク（関連強度上位18語）",pad=24); ax.axis("off")
    save_figure(fig,settings["figure_dir"],"Step7-47_共起_NetworkGraph"); settings["logger"].info("[%s] Sub47 / ノード=%d / エッジ=%d",settings["dataset_name"],len(nodes),len(selected))
