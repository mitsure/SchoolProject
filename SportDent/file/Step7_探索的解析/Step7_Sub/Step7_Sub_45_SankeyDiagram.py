"""Step7 Sub45：Sankey diagram非採用記録。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    reason="学校種・場合別・発生場所は時間的な流れではなく、Sankeyは因果・移行と誤読される可能性がある。クロス集計とMosaic plotを優先する。"
    pd.DataFrame([{"Sub":45,"状態":"非採用","理由":reason}]).to_csv(settings["summary_dir"]/"Step7-45_SankeyDiagram_非採用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub45非採用：%s",settings["dataset_name"],reason); return "skipped"
