"""Step7 Sub34：FP-Growth非採用の記録。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    reason="Aprioriと同一の頻出項目集合を別アルゴリズムで再計算するもので、研究結果の追加にならない。"
    pd.DataFrame([{"Sub":34,"状態":"非採用","理由":reason,"代替":"Sub33 Apriori"}]).to_csv(settings["summary_dir"]/"Step7-34_FPGrowth_非採用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub34非採用：%s",settings["dataset_name"],reason); return "skipped"
