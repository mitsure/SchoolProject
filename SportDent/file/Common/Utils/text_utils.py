from pathlib import Path
import json


def load_stopwords(path: Path) -> set[str]:
    """ストップワードを1行1語のテキストファイルから読み込む。"""
    if not path.exists():
        raise FileNotFoundError(
            f"ストップワードファイルがありません：{path}"
        )

    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def load_json(path: Path) -> dict:
    """JSON形式の辞書ファイルを読み込む。"""
    if not path.exists():
        raise FileNotFoundError(
            f"設定ファイルがありません：{path}"
        )

    return json.loads(path.read_text(encoding="utf-8"))


def match_labels(
    text: str,
    labels: dict[str, list[str]],
) -> list[str]:
    """
    文章中にキーワードを含むラベルを返す。
    """
    return [
        label
        for label, keywords in labels.items()
        if any(keyword in text for keyword in keywords)
    ]


def normalize_by_synonym(
    word: str,
    synonym_dictionary: dict[str, list[str]],
) -> str:
    """
    同義語辞書に基づいて語を代表語へ統一する。
    """
    for representative, variants in synonym_dictionary.items():
        if word in variants:
            return representative

    return word
