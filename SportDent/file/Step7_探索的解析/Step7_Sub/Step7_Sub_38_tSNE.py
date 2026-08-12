"""Step7 Sub38：t-SNE非採用記録。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    reason="t-SNEの2次元配置はperplexity・初期値に強く依存し、軸やクラスタ間距離を定量解釈できない。Sub36・37を優先する。"
    pd.DataFrame([{"Sub":38,"状態":"非採用","理由":reason}]).to_csv(settings["summary_dir"]/"Step7-38_tSNE_非採用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub38非採用：%s",settings["dataset_name"],reason); return "skipped"
