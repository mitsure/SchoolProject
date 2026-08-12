"""Step7 Sub22：発生時間帯比較の適用可否判定。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> None:
    """実時刻列がないため、場合別から時間帯を推測せず解析不能を出力する。"""
    candidate=[c for c in settings["df"].columns if any(k in c for k in ["時刻","時間帯","発生時間"])]
    status="実行可能" if candidate else "解析不能"
    detail=f"候補列: {candidate}" if candidate else "時刻・時間帯列が存在しない。場合別1/2からの推測変換は行わない。"
    pd.DataFrame([{"Sub":22,"解析名":"発生時間帯比較","状態":status,"理由":detail}]).to_csv(settings["summary_dir"]/"Step7-22_発生時間帯比較_適用可否.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub22 %s：%s",settings["dataset_name"],status,detail)
    return "skipped" if status == "解析不能" else None
