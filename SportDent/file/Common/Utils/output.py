from pathlib import Path

import pandas as pd


def save_csv(dataframe: pd.DataFrame, path: Path) -> None:
    """
    出力先フォルダを自動生成し、UTF-8 with BOMでCSVを保存する。

    同名CSVが存在する場合は上書きする。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")
