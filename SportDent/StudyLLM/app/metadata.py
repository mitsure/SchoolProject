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
INJURY_TYPE_VALUES = (
    "外貌・露出部分の醜状障害",
    "視力・眼球運動障害",
    "歯牙障害",
    "精神・神経障害",
    "手指切断・機能障害",
    "胸腹部臓器障害",
    "上肢切断・機能障害",
    "下肢切断・機能障害",
    "せき柱障害",
    "聴力障害",
    "足指切断・機能障害",
    "そしゃく機能障害",
)
INJURY_TYPE_PATTERNS = (
    ("歯牙障害", re.compile(r"前歯|奥歯|永久歯|乳歯|歯牙|歯折|歯の破折|歯(?:を|が)(?:折|欠|脱|損傷|打|ぶつけ)")),
    ("視力・眼球運動障害", re.compile(r"視力・眼球運動障害|視力障害|眼球運動障害|失明")),
    ("聴力障害", re.compile(r"聴力障害|難聴|耳が聞こえ")),
    ("そしゃく機能障害", re.compile(r"そしゃく機能障害|咀嚼機能障害")),
    ("せき柱障害", re.compile(r"せき柱障害|脊柱障害")),
    ("手指切断・機能障害", re.compile(r"手指切断・機能障害|手指(?:を)?切断")),
    ("足指切断・機能障害", re.compile(r"足指切断・機能障害|足指(?:を)?切断")),
    ("上肢切断・機能障害", re.compile(r"上肢切断・機能障害|上肢(?:を)?切断")),
    ("下肢切断・機能障害", re.compile(r"下肢切断・機能障害|下肢(?:を)?切断")),
    ("胸腹部臓器障害", re.compile(r"胸腹部臓器障害")),
    ("精神・神経障害", re.compile(r"精神・神経障害")),
    ("外貌・露出部分の醜状障害", re.compile(r"外貌・露出部分の醜状障害|醜状障害")),
)


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
    full_width = str.maketrans("０１２３４５６", "0123456")
    school = grade = evidence = None
    stage_patterns = (
        (r"(?:小学校|小学|(?<![一-龥ぁ-んァ-ン])小)\s*([1-6１-６一二三四五六])\s*(?:年生|年)?", "小"),
        (r"(?:中学校|中学|(?<![一-龥ぁ-んァ-ン])中)\s*([1-3１-３一二三])\s*(?:年生|年)?", "中"),
        (r"(?:高等学校|高校|(?<![一-龥ぁ-んァ-ン])高)\s*([1-3１-３一二三])\s*(?:年生|年)?", "高"),
    )
    observed_person = re.compile(
        r"^(?:の)?(?:弟|妹|兄|姉|友人|友達|同級生)"
        r"(?:を[^。、]{0,8}(?:見|眺め|観察)|が[^。、]{0,15}(?:のを|ところを)(?:見|眺め|観察))"
    )
    candidates: list[tuple[bool, int, str, str, str]] = []
    for pattern, code in stage_patterns:
        for match in re.finditer(pattern, text):
            raw_grade = match.group(1).translate(full_width)
            candidate = numerals.get(raw_grade, raw_grade)
            if candidate in GRADE_RULES[code]:
                tail = text[match.end():match.end() + 25]
                candidates.append((bool(observed_person.search(tail)), match.start(), code, candidate, match.group(0)))
    if candidates:
        _, _, school, grade, evidence = min(candidates, key=lambda item: (item[0], item[1]))
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


def infer_injury_type(text: str) -> dict[str, str | None]:
    """障害種別を高精度で判断できる明示表現だけから候補化する。"""
    matches: list[tuple[int, str, str]] = []
    for value, pattern in INJURY_TYPE_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append((match.start(), value, match.group(0)))
    if not matches:
        return {"種別": None, "evidence": None}
    _, value, evidence = min(matches)
    return {"種別": value, "evidence": evidence}


def validate_injury_type(value: str | None) -> None:
    if value is not None and value not in INJURY_TYPE_VALUES:
        raise ValueError("種別が許容範囲外です")


def validate_demographics(school: str | None, grade: str | None, sex: str | None) -> None:
    if school is None and grade is not None:
        raise ValueError("学校種が未選択の場合、学年は選択できません")
    if school is not None and school not in GRADE_RULES:
        raise ValueError("学校種が許容範囲外です")
    if grade is not None and grade not in GRADE_RULES[school]:
        raise ValueError("学校種と学年の組合せが不正です")
    if sex not in (None, "男", "女"):
        raise ValueError("性別が許容範囲外です")
