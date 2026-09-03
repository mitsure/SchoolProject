from __future__ import annotations

import html
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .auth import AuthManager
from .extractor import RuleBasedExtractor
from .llm_extractor import LLMExtractor
from .metadata import (
    GRADE_RULES,
    INJURY_TYPE_VALUES,
    SCHOOL_LABELS,
    infer_demographics,
    infer_injury_type,
    validate_demographics,
    validate_injury_type,
)
from .ollama_client import OllamaClient
from .storage import ReviewStore
from .validator import ResultValidator, ValidationError


app = FastAPI(
    title="SportDent StudyLLM MVP",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
auth = AuthManager()
validator = ResultValidator()
STATUS_LABELS = {
    "explicit": "原文明記",
    "derived": "規則で補完",
    "not_mentioned": "記載なし",
    "ambiguous": "要確認（曖昧）",
    "conflict": "要確認（矛盾）",
    "unsupported": "候補外",
    "validation_rejected": "検証で除外",
    "not_applicable": "非該当",
}
REVIEW_FIELDS = (
    "種別",
    "被災学校種",
    "被災学年",
    "性別",
    "場合別1",
    "場合別2",
    "競技種目",
    "通学方法",
    "発生場所1",
    "発生場所2",
    "発生場所2（その他詳細）",
    "遊具等",
    "災害発生時の状況",
)
FORM_FIELD_NAMES = {
    "種別": "injury_type",
    "被災学校種": "school_type",
    "被災学年": "grade",
    "性別": "sex",
    "場合別1": "case_level_1",
    "場合別2": "case_level_2",
    "競技種目": "sport",
    "通学方法": "commute_method",
    "発生場所1": "place_level_1",
    "発生場所2": "place_level_2",
    "発生場所2（その他詳細）": "place_other_detail",
    "遊具等": "equipment",
    "災害発生時の状況": "situation",
}


def build_extractor():
    mode = os.environ.get("SPORTDENT_EXTRACTOR", "rules").lower()
    if mode == "rules":
        return RuleBasedExtractor(), "ローカル規則ベース"
    if mode == "ollama":
        model = os.environ.get("SPORTDENT_OLLAMA_MODEL", "qwen3:8b")
        return LLMExtractor(OllamaClient(model=model), validator), f"ローカルLLM ({model})"
    raise RuntimeError("SPORTDENT_EXTRACTORはrulesまたはollamaを指定してください")


extractor, extractor_label = build_extractor()
default_store_path = Path(__file__).resolve().parent.parent / "data" / "reviews.sqlite3"
store = ReviewStore(Path(os.environ.get("SPORTDENT_DB_PATH", default_store_path)))


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def page(body: str, *, authenticated: bool = False) -> str:
    navigation = ""
    if authenticated:
        navigation = """
        <nav>
          <a href='/menu'>メニュー</a>
          <a href='/new'>新規登録</a>
          <a href='/reviews'>DBを見る</a>
          <form class='inline' method='post' action='/logout'><button type='submit'>ログアウト</button></form>
        </nav>
        """
    return f"""<!doctype html>
<html lang='ja'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <title>SportDent</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#202124}}
    textarea{{width:100%;box-sizing:border-box}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #ccc;padding:.55rem;text-align:left;vertical-align:top}}
    input,select,button{{font:inherit}} select,input[type='text'],input[type='password']{{padding:.45rem;max-width:100%;box-sizing:border-box}}
    button,.button{{display:inline-block;padding:.65rem 1rem;border:1px solid #315efb;border-radius:.4rem;background:#315efb;color:white;text-decoration:none;cursor:pointer}}
    .secondary{{background:white;color:#315efb}} .danger{{background:#b42318;border-color:#b42318}} .error{{color:#a00}} .notice{{background:#fff8d8;padding:.8rem;border-radius:.4rem}}
    .login{{max-width:28rem;margin:3rem auto}} .login label{{display:block;margin:1rem 0}} .login input{{display:block;width:100%;margin-top:.35rem}}
    .actions{{display:flex;gap:1rem;flex-wrap:wrap;margin:1.5rem 0}} nav{{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;padding:.7rem 0;border-bottom:1px solid #ddd}}
    nav .inline{{margin-left:auto}} nav button{{padding:.35rem .65rem;background:white;color:#315efb}} .other-location{{display:block;margin-top:.5rem}}
    .record{{margin:1.5rem 0;padding:1rem;border:1px solid #ccc;border-radius:.5rem}} .record h2{{margin-top:0}} .null{{color:#777}} .situation{{white-space:pre-wrap}}
    @media(max-width:700px){{body{{margin:1rem auto}} td,th{{font-size:.9rem}}}}
  </style>
</head>
<body>
  <h1>事故状況の入力支援（ローカルMVP）</h1>
  {navigation}
  {body}
</body>
</html>"""


def is_authenticated(request: Request) -> bool:
    return auth.verify_token(request.cookies.get(auth.COOKIE_NAME))


def login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=303)


def request_uses_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip()
    return forwarded == "https" or request.url.scheme == "https"


def select(name: str, values, selected=None, *, element_id=None, null_label="ー") -> str:
    options = [f"<option value=''>{html.escape(null_label)}</option>"]
    for value in values:
        escaped = html.escape(value)
        mark = " selected" if value == selected else ""
        options.append(f"<option value='{escaped}'{mark}>{escaped}</option>")
    id_attribute = f" id='{html.escape(element_id)}'" if element_id else ""
    return f"<select{id_attribute} name='{html.escape(name)}'>{''.join(options)}</select>"


def display_review_value(name: str, value) -> str:
    if value is None or value == "":
        return "<span class='null'>ー</span>"
    if name == "被災学校種":
        value = SCHOOL_LABELS.get(str(value), value)
    elif name == "被災学年":
        value = f"{value}年"
    css_class = " class='situation'" if name == "災害発生時の状況" else ""
    return f"<span{css_class}>{html.escape(str(value))}</span>"


def form_value(form, field_name: str) -> str:
    """フォーム内部名は文字コード差を避けるためASCIIに固定する。"""
    value = form.get(FORM_FIELD_NAMES[field_name])
    if value is None:
        value = form.get(field_name, "")
    return str(value)


def school_select(selected: str | None) -> str:
    options = ["<option value=''>ー</option>"] + [
        f"<option value='{code}'{' selected' if selected == code else ''}>{html.escape(label)}</option>"
        for code, label in SCHOOL_LABELS.items()
    ]
    return f"<select id='school' name='{FORM_FIELD_NAMES['被災学校種']}'>{''.join(options)}</select>"


def grade_select(selected: str | None) -> str:
    options = ["<option value=''>ー</option>"] + [
        f"<option value='{number}'{' selected' if selected == str(number) else ''}>{number}年</option>"
        for number in range(7)
    ]
    return f"<select id='grade' name='{FORM_FIELD_NAMES['被災学年']}'>{''.join(options)}</select>"


def dependent_select_script() -> str:
    rules = json.dumps(GRADE_RULES, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    return f"""<script>
    const rules={rules},school=document.getElementById('school'),grade=document.getElementById('grade'),place2=document.getElementById('place2'),placeOther=document.getElementById('place-other'),placeOtherWrap=document.getElementById('place-other-wrap');
    function syncGrade(){{const allowed=rules[school.value]||[];for(const option of grade.options)option.hidden=option.value!==''&&!allowed.includes(option.value);if(!allowed.includes(grade.value))grade.value='';grade.disabled=!school.value}}
    function syncOtherPlace(){{const active=place2.value==='その他';placeOtherWrap.hidden=!active;placeOther.disabled=!active;placeOther.required=active;if(!active)placeOther.value=''}}
    school.addEventListener('change',syncGrade);place2.addEventListener('change',syncOtherPlace);syncGrade();syncOtherPlace();
    </script>"""


def editable_review_rows(record: dict) -> str:
    rows = [
        f"<tr><th>種別</th><td>{select(FORM_FIELD_NAMES['種別'], INJURY_TYPE_VALUES, record.get('種別'))}</td></tr>",
        f"<tr><th>被災学校種</th><td>{school_select(record.get('被災学校種'))}</td></tr>",
        f"<tr><th>被災学年</th><td>{grade_select(record.get('被災学年'))}</td></tr>",
        f"<tr><th>性別</th><td>{select(FORM_FIELD_NAMES['性別'], ('男', '女'), record.get('性別'))}</td></tr>",
    ]
    for name in validator.allowed:
        control = select(
            FORM_FIELD_NAMES[name],
            sorted(validator.allowed[name]),
            record.get(name),
            element_id="place2" if name == "発生場所2" else None,
        )
        if name == "発生場所2":
            detail = html.escape(str(record.get("発生場所2（その他詳細）") or ""))
            control += (
                "<label id='place-other-wrap' class='other-location' hidden>その他の発生場所 "
                f"<input id='place-other' type='text' name='{FORM_FIELD_NAMES['発生場所2（その他詳細）']}' maxlength='100' value='{detail}' disabled></label>"
            )
        rows.append(f"<tr><th>{html.escape(name)}</th><td>{control}</td></tr>")
    situation = html.escape(str(record.get("災害発生時の状況") or ""))
    rows.append(
        "<tr><th>災害発生時の状況</th>"
        f"<td><textarea name='{FORM_FIELD_NAMES['災害発生時の状況']}' rows='8' maxlength='5000' required>{situation}</textarea></td></tr>"
    )
    return "".join(rows)


def confirmed_record_from_form(form) -> dict:
    injury_type, school, grade, sex = (
        form_value(form, name).strip() or None
        for name in ("種別", "被災学校種", "被災学年", "性別")
    )
    confirmed = {name: form_value(form, name).strip() or None for name in validator.allowed}
    validate_injury_type(injury_type)
    validate_demographics(school, grade, sex)
    validator.validate_confirmed(confirmed)
    other_location = validator.validate_other_location(
        confirmed["発生場所2"],
        form_value(form, "発生場所2（その他詳細）"),
    )
    situation = form_value(form, "災害発生時の状況").strip()
    if not situation or len(situation) > 5000:
        raise ValueError("災害発生時の状況が不正です")
    return {
        "種別": injury_type,
        "被災学校種": school,
        "被災学年": grade,
        "性別": sex,
        **confirmed,
        "発生場所2（その他詳細）": other_location,
        "災害発生時の状況": situation,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/menu", status_code=303)
    warning = ""
    if auth.uses_default_credentials:
        warning = "<p class='notice'>現在は仮アカウントです。インターネット公開時は起動環境変数で必ず変更してください。</p>"
    return page(
        f"""<section class='login'><h2>ログイン</h2>{warning}
        <form method='post' action='/login'>
          <label>ユーザー名<input name='username' autocomplete='username' required autofocus></label>
          <label>パスワード<input type='password' name='password' autocomplete='current-password' required></label>
          <button type='submit'>ログイン</button>
          <p>この端末ではログイン状態を30日間保持します。</p>
        </form></section>"""
    )


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", ""))
    password = str(form.get("password", ""))
    if not auth.authenticate(username, password):
        return HTMLResponse(
            page("<section class='login'><h2>ログイン失敗</h2><p class='error'>ユーザー名またはパスワードが違います。</p><p><a href='/'>戻る</a></p></section>"),
            status_code=401,
        )
    response = RedirectResponse(url="/menu", status_code=303)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.issue_token(),
        max_age=auth.ttl_seconds,
        httponly=True,
        secure=request_uses_https(request),
        samesite="strict",
        path="/",
    )
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return response


@app.get("/menu", response_class=HTMLResponse)
def menu(request: Request):
    if not is_authenticated(request):
        return login_redirect()
    return page(
        """<h2>メニュー</h2><div class='actions'>
        <a class='button' href='/new'>新規登録</a>
        <a class='button secondary' href='/reviews'>DBを見る</a>
        </div>""",
        authenticated=True,
    )


@app.get("/new", response_class=HTMLResponse)
def new_record(request: Request):
    if not is_authenticated(request):
        return login_redirect()
    return page(
        f"<p class='notice'>架空または適切に匿名化された文章だけを入力してください。現在の抽出器：{html.escape(extractor_label)}</p>"
        "<form method='post' action='/analyze'><h2>災害発生時の状況</h2>"
        "<textarea name='text' rows='8' maxlength='5000' required></textarea><p><button>確認</button></p></form>",
        authenticated=True,
    )


@app.get("/reviews", response_class=HTMLResponse)
def reviews(request: Request):
    if not is_authenticated(request):
        return login_redirect()
    saved_reviews = store.list_confirmed()
    if not saved_reviews:
        return page("<h2>保存済みデータ</h2><p>まだ保存データはありません。</p>", authenticated=True)
    sections = []
    for review in saved_reviews:
        record = review["confirmed"]
        rows = "".join(
            f"<tr><th>{html.escape(name)}</th><td>{display_review_value(name, record.get(name))}</td></tr>"
            for name in REVIEW_FIELDS
        )
        sections.append(
            f"<section class='record'><h2>ID: {review['id']}</h2>"
            f"<p>保存日時（UTC）: {html.escape(str(review['created_at']))}</p><table>{rows}</table>"
            f"<div class='actions'><a class='button secondary' href='/reviews/{review['id']}/edit'>編集</a>"
            f"<a class='button danger' href='/reviews/{review['id']}/delete'>削除</a></div></section>"
        )
    return page(f"<h2>保存済みデータ（{len(saved_reviews)}件）</h2>{''.join(sections)}", authenticated=True)


@app.get("/reviews/{review_id}/edit", response_class=HTMLResponse)
def edit_review(request: Request, review_id: int):
    if not is_authenticated(request):
        return login_redirect()
    review = store.get_confirmed(review_id)
    if review is None:
        raise HTTPException(404, "保存データが見つかりません")
    return page(
        f"<h2>ID: {review_id}を編集</h2><form method='post' action='/reviews/{review_id}/edit'>"
        f"<table><tr><th>項目</th><th>修正値</th></tr>{editable_review_rows(review['confirmed'])}</table>"
        "<p><label><input type='checkbox' name='confirmed' value='yes' required> 変更内容を確認しました</label></p>"
        "<div class='actions'><a class='button secondary' href='/reviews'>キャンセル</a>"
        "<button type='submit'>変更を保存</button></div></form>"
        f"{dependent_select_script()}",
        authenticated=True,
    )


@app.post("/reviews/{review_id}/edit", response_class=HTMLResponse)
async def update_review(request: Request, review_id: int):
    if not is_authenticated(request):
        return login_redirect()
    form = await request.form()
    if form.get("confirmed") != "yes":
        raise HTTPException(400, "変更内容の確認が必要です")
    try:
        record = confirmed_record_from_form(form)
    except (ValidationError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "更新内容が不正です") from exc
    if not store.update_confirmed(review_id, record):
        raise HTTPException(404, "保存データが見つかりません")
    return page(
        f"<p>ID: {review_id}の変更を保存しました。</p><p><a class='button' href='/reviews'>DB一覧へ戻る</a></p>",
        authenticated=True,
    )


@app.get("/reviews/{review_id}/delete", response_class=HTMLResponse)
def confirm_delete_review(request: Request, review_id: int):
    if not is_authenticated(request):
        return login_redirect()
    review = store.get_confirmed(review_id)
    if review is None:
        raise HTTPException(404, "保存データが見つかりません")
    situation = display_review_value("災害発生時の状況", review["confirmed"].get("災害発生時の状況"))
    return page(
        f"<h2>ID: {review_id}を削除</h2><p class='notice'>この操作は取り消せません。</p>"
        f"<p>{situation}</p><form method='post' action='/reviews/{review_id}/delete'>"
        "<p><label><input type='checkbox' name='confirm' value='yes' required> このデータを削除します</label></p>"
        "<div class='actions'><a class='button secondary' href='/reviews'>キャンセル</a>"
        "<button class='danger' type='submit'>完全に削除</button></div></form>",
        authenticated=True,
    )


@app.post("/reviews/{review_id}/delete", response_class=HTMLResponse)
async def delete_review(request: Request, review_id: int):
    if not is_authenticated(request):
        return login_redirect()
    form = await request.form()
    if form.get("confirm") != "yes":
        raise HTTPException(400, "削除確認が必要です")
    if not store.delete(review_id):
        raise HTTPException(404, "保存データが見つかりません")
    return page(
        f"<p>ID: {review_id}を削除しました。</p><p><a class='button' href='/reviews'>DB一覧へ戻る</a></p>",
        authenticated=True,
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request):
    if not is_authenticated(request):
        return login_redirect()
    form = await request.form()
    text = str(form.get("text", ""))
    result = extractor.extract(text)
    if result["processing_status"] == "error":
        return page(
            f"<p class='error'>解析を停止しました: {html.escape(result['error_code'])}</p><p><a href='/new'>戻る</a></p>",
            authenticated=True,
        )
    try:
        validator.validate(text.strip(), result)
    except ValidationError as exc:
        raise HTTPException(500, str(exc)) from exc

    injury = infer_injury_type(text)
    demo = infer_demographics(text)
    schools = ["<option value=''>未選択</option>"] + [
        f"<option value='{code}'{' selected' if demo['被災学校種'] == code else ''}>{html.escape(label)}</option>"
        for code, label in SCHOOL_LABELS.items()
    ]
    grades = ["<option value=''>未選択</option>"] + [
        f"<option value='{number}'{' selected' if demo['被災学年'] == str(number) else ''}>{number}年</option>"
        for number in range(7)
    ]
    sexes = ["<option value=''>未選択</option>"] + [
        f"<option value='{value}'{' selected' if demo['性別'] == value else ''}>{value}</option>"
        for value in ("男", "女")
    ]
    demographic_status = "原文明記" if demo["被災学校種"] else "人が選択"
    evidence = html.escape(demo["evidence"] or "")
    injury_value = injury["種別"]
    injury_evidence = html.escape(injury["evidence"] or "")
    rows = [
        f"<tr><th>種別</th><td>{select(FORM_FIELD_NAMES['種別'], INJURY_TYPE_VALUES, injury_value)}</td>"
        f"<td>{'規則で補完' if injury_value else '人が選択'}</td><td>{injury_evidence}</td></tr>",
        f"<tr><th>被災学校種</th><td><select id='school' name='{FORM_FIELD_NAMES['被災学校種']}'>{''.join(schools)}</select></td><td>{demographic_status}</td><td>{evidence}</td></tr>",
        f"<tr><th>被災学年</th><td><select id='grade' name='{FORM_FIELD_NAMES['被災学年']}'>{''.join(grades)}</select></td><td>{demographic_status}</td><td>{evidence}</td></tr>",
        f"<tr><th>性別</th><td><select name='{FORM_FIELD_NAMES['性別']}'>{''.join(sexes)}</select></td><td>{'原文明記' if demo['性別'] else '人が選択'}</td><td></td></tr>",
    ]
    for name, field in result["fields"].items():
        control = select(
            FORM_FIELD_NAMES[name],
            sorted(validator.allowed[name]),
            field["value"],
            element_id="place2" if name == "発生場所2" else None,
        )
        if name == "発生場所2":
            control += f"<label id='place-other-wrap' class='other-location' hidden>その他の発生場所 <input id='place-other' type='text' name='{FORM_FIELD_NAMES['発生場所2（その他詳細）']}' maxlength='100' placeholder='例：校門横の自転車置き場' disabled></label>"
        rows.append(
            f"<tr><th>{html.escape(name)}</th><td>{control}</td>"
            f"<td>{html.escape(STATUS_LABELS.get(field['status'], field['status']))}</td>"
            f"<td>{html.escape(field['evidence_text'] or '')}</td></tr>"
        )
    rows.append(f"<tr><th>災害発生時の状況</th><td colspan='3'>{html.escape(text)}</td></tr>")
    payload = html.escape(json.dumps(result, ensure_ascii=False))
    script = dependent_select_script()
    return page(
        f"<form method='post' action='/save'><input type='hidden' name='text' value='{html.escape(text)}'>"
        f"<input type='hidden' name='result_json' value='{payload}'><table><tr><th>項目</th><th>候補（修正可）</th><th>状態</th><th>根拠</th></tr>{''.join(rows)}</table>"
        "<p><label><input type='checkbox' name='confirmed' value='yes' required> 全項目を確認しました</label></p>"
        "<p><button type='button' class='secondary' onclick='history.back()'>入力画面へ戻る</button> <button type='submit'>確定保存</button></p></form>"
        f"{script}",
        authenticated=True,
    )


@app.post("/save", response_class=HTMLResponse)
async def save(request: Request):
    if not is_authenticated(request):
        return login_redirect()
    form = await request.form()
    if form.get("confirmed") != "yes":
        raise HTTPException(400, "全項目の確認が必要です")
    text = str(form.get("text", ""))
    try:
        result = json.loads(str(form.get("result_json", "")))
        validator.validate(text.strip(), result)
        injury_type, school, grade, sex = (
            form_value(form, name).strip() or None
            for name in ("種別", "被災学校種", "被災学年", "性別")
        )
        confirmed = {name: form_value(form, name).strip() or None for name in result["fields"]}
        validate_injury_type(injury_type)
        validate_demographics(school, grade, sex)
        validator.validate_confirmed(confirmed)
        other_location = validator.validate_other_location(
            confirmed["発生場所2"],
            form_value(form, "発生場所2（その他詳細）"),
        )
    except (json.JSONDecodeError, ValidationError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, "保存内容が不正です") from exc
    record = {
        "種別": injury_type,
        "被災学校種": school,
        "被災学年": grade,
        "性別": sex,
        **confirmed,
        "発生場所2（その他詳細）": other_location,
        "災害発生時の状況": text,
    }
    review_id = store.save(text, result, record)
    return page(
        f"<p>確認結果を保存しました（ID: {review_id}）。</p>"
        "<div class='actions'><a class='button' href='/new'>次を入力</a><a class='button secondary' href='/reviews'>DBを見る</a></div>",
        authenticated=True,
    )
