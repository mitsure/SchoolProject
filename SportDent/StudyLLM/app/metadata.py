from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import METADATA_NAMES


DB_PATH = Path(__file__).resolve().parent.parent.parent / "DB" / "shougai(2025.01.31).csv"

GRADE_RULES = {
    "小": ["1", "2", "3", "4", "5", "6"], "中": ["1", "2", "3"],
    "高": ["1", "2", "3"], "特小": ["1", "2", "3", "4", "5", "6"],
    "特中": ["1", "2", "3"], "特高": ["1", "2", "3"],
    "高専": ["1", "2", "3", "4", "5"], "幼": ["3", "4", "5", "6"],
    "保": ["0", "1", "2", "3", "4", "5", "6"], "幼連": ["1", "2", "3", "4", "5", "6"],
}
SCHOOL_LABELS = {
    "小": "小学校", "中": "中学校", "高": "高等学校", "特小": "特別支援学校小学部",
    "特中": "特別支援学校中学部", "特高": "特別支援学校高等部", "高専": "高等専門学校",
    "幼": "幼稚園", "保": "保育所等", "幼連": "幼保連携型認定こども園",
}


def load_metadata_choices(path: Path = DB_PATH) -> dict[str, list[str]]:
    """既存DBの観測値。公式コード確定までの暫定的な画面選択肢。"""
    choices = {name: set() for name in METADATA_NAMES if name != "記号"}
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            for name in choices:
                value = row.get(name, "").strip()
                if value:
                    choices[name].add(value)
    return {name: sorted(values, key=lambda value: (not value.isdigit(), int(value) if value.isdigit() else value)) for name, values in choices.items()}


def validate_metadata(metadata: dict[str, str | None], choices: dict[str, list[str]]) -> None:
    if set(metadata) != set(METADATA_NAMES):
        raise ValueError("基本情報の項目が不足しています")
    for name, value in metadata.items():
        if value is None:
            continue
        if name == "記号":
            if len(value) > 100:
                raise ValueError("記号が長すぎます")
        elif value not in choices[name]:
            raise ValueError(f"{name}の値が既存DBの選択肢にありません")


def infer_demographics(text: str) -> dict[str, str | None]:
    numerals = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"}
    school = grade = evidence = None
    for phrase, code in (("小学校", "小"), ("小学", "小"), ("中学校", "中"), ("中学", "中"), ("高等学校", "高"), ("高校", "高")):
        match = re.search(re.escape(phrase) + r"([1-6一二三四五六])年生", text)
        if match:
            candidate = numerals.get(match.group(1), match.group(1))
            if candidate in GRADE_RULES[code]:
                school, grade, evidence = code, candidate, match.group(0)
            break
    sex = None
    male = re.search(r"被災(?:した|者は)[^。]{0,8}(男子|男児|男の子)", text)
    female = re.search(r"被災(?:した|者は)[^。]{0,8}(女子|女児|女の子)", text)
    if male and not female:
        sex = "男"
    elif female and not male:
        sex = "女"
    else:
        # 文頭の主語として明示された場合に限り候補化する。
        subject = re.match(r"^[^。、]{0,30}(男子生徒|女子生徒|男児|女児)(?:が|は)", text)
        if subject:
            sex = "男" if subject.group(1) in ("男子生徒", "男児") else "女"
    return {"被災学校種": school, "被災学年": grade, "性別": sex, "evidence": evidence}


def validate_demographics(school: str | None, grade: str | None, sex: str | None) -> None:
    if school is None and grade is not None:
        raise ValueError("学校種が未選択の場合、学年は選択できません")
    if school is not None and school not in GRADE_RULES:
        raise ValueError("学校種が許容範囲外です")
    if grade is not None and grade not in GRADE_RULES[school]:
        raise ValueError("学校種と学年の組合せが不正です")
    if sex not in (None, "男", "女"):
        raise ValueError("性別が許容範囲外です")
