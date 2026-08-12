"""Step7 Sub39：UMAP非採用記録。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    reason="UMAPは近傍数・min_distに依存する視覚化で、現段階ではSub36・37に対する研究上の追加価値が明確でない。"
    pd.DataFrame([{"Sub":39,"状態":"非採用","理由":reason}]).to_csv(settings["summary_dir"]/"Step7-39_UMAP_非採用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub39非採用：%s",settings["dataset_name"],reason); return "skipped"
