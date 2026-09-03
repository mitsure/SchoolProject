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
# 種別は事故直後の傷病名ではなく後遺障害の区分であるため、あくまで確認候補。
# 身体部位だけでは決めず、「部位＋受傷」または特徴的な診断・機能障害を必要とする。
INJURY_TYPE_PATTERNS = (
    (
        "歯牙障害",
        re.compile(
            r"前歯|奥歯|永久歯|乳歯|歯牙|歯根|歯冠|歯槽骨|歯折|歯の破折|"
            r"歯[^。、]{0,8}(?:折|欠|脱|損傷|強打|打撲|ぶつけ|抜け|ぐらつ)"
        ),
    ),
    (
        "視力・眼球運動障害",
        re.compile(
            r"視力(?:・眼球運動)?障害|視力(?:低下|喪失)|眼球運動障害|失明|"
            r"(?:右眼|左眼|両眼|眼球|目)[^。、]{0,10}(?:見え|刺さ|負傷|損傷|強打|打撲|当た|ぶつけ|入った)"
        ),
    ),
    ("聴力障害", re.compile(r"聴力障害|聴力低下|難聴|耳鳴り?|耳が聞こえ|音が聞こえ")),
    (
        "そしゃく機能障害",
        re.compile(
            r"そしゃく機能障害|咀嚼機能障害|顎関節(?:症|障害)|"
            r"(?:そしゃく|咀嚼|噛む|かむ|食べる)[^。、]{0,12}(?:困難|不便|できな|機能障害)"
        ),
    ),
    (
        "精神・神経障害",
        re.compile(
            r"精神・神経障害|脳挫傷|脳梗塞|脳血栓|急性脳症|頭蓋内出血|"
            r"くも膜下出血|硬膜(?:外|下)血腫|高次脳機能障害|意識障害|記憶障害|"
            r"神経障害|てんかん|失語|(?:四肢|半身|下半身)麻痺"
        ),
    ),
    (
        "せき柱障害",
        re.compile(
            r"せき柱障害|脊柱障害|"
            r"(?:脊柱|せき柱|脊椎|頸椎|頚椎|胸椎|腰椎|仙椎|背骨)"
            r"[^。、]{0,10}(?:骨折|圧迫|損傷|捻挫|脱臼|障害)"
        ),
    ),
    (
        "足指切断・機能障害",
        re.compile(
            r"足指切断・機能障害|"
            r"(?:足指|足趾|第[1-5１-５一二三四五]趾|足の(?:親指|人差し指|中指|薬指|小指))"
            r"[^。、]{0,10}(?:切断|骨折|損傷|負傷|挟|強打|打撲|欠損|機能障害)"
        ),
    ),
    (
        "手指切断・機能障害",
        re.compile(
            r"手指切断・機能障害|"
            r"(?:手指|手の(?:親指|人差し指|中指|薬指|小指)|[左右](?:親指|人差し指|中指|薬指|小指)|"
            r"[左右]?第[1-5１-５一二三四五]指)"
            r"[^。、]{0,10}(?:切断|骨折|損傷|負傷|挟|強打|打撲|欠損|機能障害)"
        ),
    ),
    (
        "外貌・露出部分の醜状障害",
        re.compile(
            r"外貌・露出部分の醜状障害|醜状障害|瘢痕|傷跡|"
            r"(?:火傷|熱傷|やけど)|"
            r"(?:顔面|顔|前額部|額|頬|鼻|口唇|唇)[^。、]{0,10}(?:切|裂傷|挫創|傷が残|縫合)"
        ),
    ),
    (
        "胸腹部臓器障害",
        re.compile(
            r"胸腹部臓器障害|"
            r"(?:肋骨|あばら骨)[^。、]{0,8}(?:骨折(?:した)?|折(?:った|れた|り)?|おった|おれた|損傷)|"
            r"(?:肺|心臓|肝臓|腎臓|脾臓|膵臓|膀胱|精巣|睾丸|胸腹部臓器)"
            r"[^。、]{0,10}(?:破裂|損傷|摘出|切除|障害)"
        ),
    ),
    (
        "上肢切断・機能障害",
        re.compile(
            r"上肢切断・機能障害|"
            r"(?:上肢|上腕|前腕|腕|肩|肘|ひじ|手首|手関節)"
            r"[^。、]{0,10}(?:切断|骨折|脱臼|損傷|断裂|負傷|機能障害)"
        ),
    ),
    (
        "下肢切断・機能障害",
        re.compile(
            r"下肢切断・機能障害|"
            r"(?:下肢|大腿|太もも|下腿|すね|股関節|膝|ひざ|足首|足関節|踵|かかと|足)"
            r"[^。、]{0,10}(?:切断|骨折|脱臼|損傷|断裂|負傷|機能障害)"
        ),
    ),
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
    matches: list[tuple[int, int, str, str]] = []
    for priority, (value, pattern) in enumerate(INJURY_TYPE_PATTERNS):
        match = pattern.search(text)
        if match:
            matches.append((match.start(), priority, value, match.group(0)))
    if not matches:
        return {"種別": None, "evidence": None}
    _, _, value, evidence = min(matches)
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
