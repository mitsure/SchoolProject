from pathlib import Path

import pandas as pd


def load_csv(path: Path) -> pd.DataFrame:
    """
    日本語CSVを複数の文字コード候補で読み込む。

    Parameters
    ----------
    path:
        読み込むCSVのパス。

    Returns
    -------
    pandas.DataFrame
        読み込んだデータ。
    """
    last_error: Exception | None = None

    for encoding in ("utf-8-sig", "cp932", "shift_jis", "utf-8"):
        try:
            dataframe = pd.read_csv(path, encoding=encoding)
            print(f"入力ファイル：{path}")
            print(f"文字コード　：{encoding}")
            return dataframe
        except Exception as error:
            last_error = error

    raise RuntimeError(
        f"CSVを読み込めませんでした。\n"
        f"対象ファイル：{path}\n"
        f"最終エラー　：{last_error}"
    )
