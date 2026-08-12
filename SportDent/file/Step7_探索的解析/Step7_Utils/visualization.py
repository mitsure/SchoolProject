"""Step7 Figure共通処理。日本語フォントがなければ明示的に失敗する。"""
from __future__ import annotations
import os
from pathlib import Path
os.environ.setdefault("MPLCONFIGDIR", "/tmp/sportdent-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONT_PRIORITY=["Noto Sans CJK JP","Noto Serif CJK JP","IPAexGothic","IPAGothic","Yu Gothic","Hiragino Sans"]


def configure_japanese_font():
    """Step5と同様に実在フォントを検索し、名称とFontPropertiesを返す。"""
    available={}
    for path in font_manager.findSystemFonts():
        try: available.setdefault(font_manager.FontProperties(fname=path).get_name(),Path(path))
        except Exception: continue
    for preferred in FONT_PRIORITY:
        for actual,path in available.items():
            if actual==preferred or preferred.lower() in actual.lower():
                font_manager.fontManager.addfont(str(path)); prop=font_manager.FontProperties(fname=str(path))
                plt.rcParams.update({"font.family":prop.get_name(),"axes.unicode_minus":False,"pdf.fonttype":42,"ps.fonttype":42,"svg.fonttype":"none"})
                return actual,prop
    raise FileNotFoundError("日本語対応フォントが見つからないためFigureを生成できません。")


def save_figure(fig, directory: Path, stem: str) -> None:
    """PNG 300dpiとSVGを同名で上書き保存する。"""
    directory.mkdir(parents=True,exist_ok=True)
    fig.savefig(directory/f"{stem}.png",dpi=300,bbox_inches="tight",facecolor="white")
    fig.savefig(directory/f"{stem}.svg",bbox_inches="tight",facecolor="white")
    plt.close(fig)
