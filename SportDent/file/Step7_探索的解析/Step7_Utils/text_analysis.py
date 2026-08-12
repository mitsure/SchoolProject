"""Step7テキスト解析の共通形態素処理。解析Subの成果物には依存しない。"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from janome.tokenizer import Tokenizer

TEXT_COLUMN = "災害発生時の状況"
TARGET_POS = {"名詞", "動詞", "形容詞"}


def load_stopwords(project_dir: Path) -> set[str]:
    """SportDent共通設定のストップワードを読み、空行とコメントを除外する。"""
    path = project_dir / "file" / "Common" / "Config" / "設定_ストップワード.txt"
    if not path.exists():
        raise FileNotFoundError(f"ストップワード設定がありません: {path}")
    return {line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")}


def tokenize_cases(df: pd.DataFrame, project_dir: Path) -> tuple[list[list[dict[str, str]]], set[str]]:
    """
    1事例ごとにJanome形態素を返す。

    基本形が`*`の場合だけ表層形を使う。語を任意に結合しないため、
    「前歯」と「歯」はJanomeが返す別トークンのまま保持される。
    """
    if TEXT_COLUMN not in df.columns:
        raise KeyError(f"必要列がありません: {TEXT_COLUMN}")
    tokenizer = Tokenizer(); stopwords = load_stopwords(project_dir); cases=[]
    for value in df[TEXT_COLUMN].fillna("").astype(str):
        tokens=[]
        for token in tokenizer.tokenize(value):
            parts=token.part_of_speech.split(","); pos=parts[0]; detail=parts[1]
            base=token.base_form if token.base_form != "*" else token.surface
            tokens.append({"表層形":token.surface,"基本形":base,"品詞":pos,"品詞細分類":detail})
        cases.append(tokens)
    return cases, stopwords


def tokenize_cases_cached(settings: dict) -> tuple[list[list[dict[str, str]]], set[str]]:
    """
    settings内の実行中キャッシュを使い、同一DataFrameのJanome処理を1回に限定する。

    キャッシュが空でも必ず元DataFrameから再計算できるため、
    各SubはほかのSubの実行有無に依存しない。
    """
    cache = settings.setdefault("cache", {})
    key = "janome_case_tokens_v1"
    if key not in cache:
        cache[key] = tokenize_cases(settings["df"], settings["project_dir"])
    return cache[key]


def analysis_words(tokens: list[dict[str, str]], stopwords: set[str]) -> list[str]:
    """名詞・動詞・形容詞の基本形から記号、1文字数字、停止語を除く。"""
    words=[]
    for token in tokens:
        word=token["基本形"].strip()
        if token["品詞"] not in TARGET_POS or not word or word in stopwords: continue
        if token["品詞"] == "名詞" and token["品詞細分類"] in {"非自立", "代名詞", "数"}: continue
        if word.isdigit(): continue
        words.append(word)
    return words
