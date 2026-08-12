"""Step7 Sub21：発生場所階層1・2の比較。"""
from typing import Any
from Step7_Utils.statistics import comparable, comparison
def run(settings: dict[str, Any]) -> None:
    df=settings["df"]
    if not comparable(df): settings["logger"].info("[%s] Sub21解析不能：2群なし",settings["dataset_name"]); return "skipped"
    result=comparison(df,["発生場所1","発生場所2"]); result.to_csv(settings["table_dir"]/"Step7-21_発生場所比較.csv",index=False,encoding=settings["text_encoding"])
    settings["logger"].info("[%s] Sub21 / %dカテゴリ",settings["dataset_name"],len(result))
