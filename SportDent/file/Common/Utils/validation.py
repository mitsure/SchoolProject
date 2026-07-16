import pandas as pd


def require_columns(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    """
    必要な列が存在するか、データが0件でないかを確認する。
    """
    missing = [
        column
        for column in columns
        if column not in dataframe.columns
    ]

    if missing:
        raise ValueError(f"必要な列がありません：{missing}")

    if dataframe.empty:
        raise ValueError("入力データが0件です。")
