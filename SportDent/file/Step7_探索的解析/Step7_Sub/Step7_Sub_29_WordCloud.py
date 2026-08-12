"""Step7 Sub29：WordCloudの非採用記録。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    reason="面積表現は定量比較に不向き、Sub23の件数・事例出現率表より研究上の追加価値が乏しい。"
    pd.DataFrame([{"Sub":29,"状態":"非採用","理由":reason}]).to_csv(settings["summary_dir"]/"Step7-29_WordCloud_非採用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub29非採用：%s",settings["dataset_name"],reason); return "skipped"
