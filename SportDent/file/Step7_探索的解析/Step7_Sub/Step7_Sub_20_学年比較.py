"""Step7 Sub20：学年別比較。"""
from typing import Any
from Step7_Utils.statistics import comparable, comparison
def run(settings: dict[str, Any]) -> None:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub20解析不能：2群なし",settings["dataset_name"]); return "skipped"
    result=comparison(df,["被災学年"]); result.to_csv(settings["table_dir"]/"Step7-20_学年比較.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub20 / %dカテゴリ",settings["dataset_name"],len(result))
