"""Step7 Sub32：既存Step4類似事例成果の再利用判定。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    root=settings["project_dir"]/"CreateData"/"Step4_Jaccard解析"
    files=sorted([x for x in root.glob("*.csv") if "類似事例" in x.name]) if root.exists() else []
    pd.DataFrame([{"Sub":32,"状態":"既存成果を利用","成果数":len(files),
                   "理由":"Step4でAll・歯牙障害の事例間Jaccard上位類似事例が作成済み。",
                   "成果物":" | ".join(x.name for x in files)}]).to_csv(settings["summary_dir"]/"Step7-32_類似文章検索_既存成果利用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub32非採用：Step4類似事例成果%d件を利用",settings["dataset_name"],len(files)); return "skipped"
