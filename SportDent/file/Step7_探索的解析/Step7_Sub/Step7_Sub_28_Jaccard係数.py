"""Step7 Sub28：既存Step4 Jaccard成果の再利用判定。"""
from typing import Any
import pandas as pd
def run(settings: dict[str, Any]) -> str:
    root=settings["project_dir"]/"CreateData"/"Step4_Jaccard解析"; files=sorted(root.glob("*.csv")) if root.exists() else []
    pd.DataFrame([{"Sub":28,"状態":"既存成果を利用","Step4成果数":len(files),
                   "理由":"Step4で特徴間・事例間・All対歯牙障害のJaccard解析が実施済みのため再計算しない。",
                   "成果物":" | ".join(x.name for x in files)}]).to_csv(settings["summary_dir"]/"Step7-28_Jaccard_既存成果利用.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub28非採用：Step4成果%d件を利用",settings["dataset_name"],len(files)); return "skipped"
