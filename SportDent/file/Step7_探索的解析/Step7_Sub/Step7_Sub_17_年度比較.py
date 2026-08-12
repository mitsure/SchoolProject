"""Step7 Sub17：年度別の歯牙障害対非歯牙障害比較。"""
from typing import Any
from Step7_Utils.statistics import comparable, comparison
def run(settings: dict[str, Any]) -> None:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub17解析不能：2群なし",settings["dataset_name"]); return "skipped"
    result=comparison(df,["給付年度"]); result.to_csv(settings["table_dir"]/"Step7-17_年度比較.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub17 / %d年度",settings["dataset_name"],len(result))
