from __future__ import annotations
import html, json, os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from .extractor import RuleBasedExtractor
from .metadata import GRADE_RULES, SCHOOL_LABELS, infer_demographics, validate_demographics
from .llm_extractor import LLMExtractor
from .ollama_client import OllamaClient
from .storage import ReviewStore
from .validator import ResultValidator, ValidationError

app = FastAPI(title="SportDent StudyLLM MVP")
validator = ResultValidator()
STATUS_LABELS = {
    "explicit": "原文明記", "derived": "規則で補完", "not_mentioned": "記載なし（NULL）",
    "ambiguous": "要確認（曖昧）", "conflict": "要確認（矛盾）", "unsupported": "候補外（NULL）",
    "validation_rejected": "検証で除外（NULL）", "not_applicable": "非該当（NULL）",
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
store = ReviewStore(Path(__file__).resolve().parent.parent / "data" / "reviews.sqlite3")

def page(body):
    return f"""<!doctype html><html lang='ja'><head><meta charset='utf-8'><title>SportDent</title><style>body{{font-family:sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}}textarea{{width:100%}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.5rem}}.error{{color:#a00}}.notice{{background:#fff8d8;padding:.8rem}}select,input[type='text']{{padding:.3rem}}.other-location{{display:block;margin-top:.5rem}}</style></head><body><h1>事故状況の入力支援（ローカルMVP）</h1>{body}</body></html>"""

def select(name, values, selected=None, *, element_id=None, null_label="未選択（NULL）"):
    options = [f"<option value=''>{html.escape(null_label)}</option>"]
    for value in values:
        escaped, mark = html.escape(value), " selected" if value == selected else ""
        options.append(f"<option value='{escaped}'{mark}>{escaped}</option>")
    id_attribute = f" id='{html.escape(element_id)}'" if element_id else ""
    return f"<select{id_attribute} name='{html.escape(name)}'>{''.join(options)}</select>"

@app.get("/", response_class=HTMLResponse)
def index():
    return page(f"<p class='notice'>架空または適切に匿名化された文章だけを入力してください。現在の抽出器：{html.escape(extractor_label)}</p><form method='post' action='/analyze'><h2>災害発生時の状況</h2><textarea name='text' rows='8' maxlength='5000' required></textarea><p><button>確認</button></p></form>")

@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request):
    form = await request.form(); text = str(form.get("text", "")); result = extractor.extract(text)
    if result["processing_status"] == "error": return page(f"<p class='error'>解析を停止しました: {html.escape(result['error_code'])}</p><p><a href='/'>戻る</a></p>")
    try: validator.validate(text.strip(), result)
    except ValidationError as exc: raise HTTPException(500, str(exc)) from exc
    demo = infer_demographics(text)
    schools = ["<option value=''>未選択</option>"] + [f"<option value='{c}'{' selected' if demo['被災学校種']==c else ''}>{html.escape(label)}</option>" for c,label in SCHOOL_LABELS.items()]
    grades = ["<option value=''>未選択</option>"] + [f"<option value='{n}'{' selected' if demo['被災学年']==str(n) else ''}>{n}年</option>" for n in range(7)]
    sexes = ["<option value=''>未選択</option>"] + [f"<option value='{v}'{' selected' if demo['性別']==v else ''}>{v}</option>" for v in ("男","女")]
    status, evidence = ("原文明記" if demo["被災学校種"] else "人が選択"), html.escape(demo["evidence"] or "")
    rows = [f"<tr><th>被災学校種</th><td><select id='school' name='被災学校種'>{''.join(schools)}</select></td><td>{status}</td><td>{evidence}</td></tr>", f"<tr><th>被災学年</th><td><select id='grade' name='被災学年'>{''.join(grades)}</select></td><td>{status}</td><td>{evidence}</td></tr>", f"<tr><th>性別</th><td><select name='性別'>{''.join(sexes)}</select></td><td>{'原文明記' if demo['性別'] else '人が選択'}</td><td></td></tr>"]
    for name, field in result["fields"].items():
        control = select(name, sorted(validator.allowed[name]), field["value"], element_id="place2" if name == "発生場所2" else None)
        if name == "発生場所2":
            control += "<label id='place-other-wrap' class='other-location' hidden>その他の発生場所 <input id='place-other' type='text' name='発生場所2（その他詳細）' maxlength='100' placeholder='例：校門横の自転車置き場' disabled></label>"
        rows.append(f"<tr><th>{html.escape(name)}</th><td>{control}</td><td>{html.escape(STATUS_LABELS.get(field['status'], field['status']))}</td><td>{html.escape(field['evidence_text'] or '')}</td></tr>")
    rows.append(f"<tr><th>災害発生時の状況</th><td colspan='3'>{html.escape(text)}</td></tr>")
    payload, rules = html.escape(json.dumps(result, ensure_ascii=False)), html.escape(json.dumps(GRADE_RULES, ensure_ascii=False))
    script = f"<script>const rules=JSON.parse('{rules}'),school=document.getElementById('school'),grade=document.getElementById('grade'),place2=document.getElementById('place2'),placeOther=document.getElementById('place-other'),placeOtherWrap=document.getElementById('place-other-wrap');function syncGrade(){{const a=rules[school.value]||[];for(const o of grade.options)o.hidden=o.value!==''&&!a.includes(o.value);if(!a.includes(grade.value))grade.value='';grade.disabled=!school.value}}function syncOtherPlace(){{const active=place2.value==='その他';placeOtherWrap.hidden=!active;placeOther.disabled=!active;placeOther.required=active;if(!active)placeOther.value=''}}school.addEventListener('change',syncGrade);place2.addEventListener('change',syncOtherPlace);syncGrade();syncOtherPlace()</script>"
    return page(f"<form method='post' action='/save'><input type='hidden' name='text' value='{html.escape(text)}'><input type='hidden' name='result_json' value='{payload}'><table><tr><th>項目</th><th>候補（修正可）</th><th>状態</th><th>根拠</th></tr>{''.join(rows)}</table><p><label><input type='checkbox' name='confirmed' value='yes' required> 全項目を確認しました</label></p><p><button type='button' onclick='history.back()'>入力画面へ戻る</button> <button type='submit'>確定保存</button></p></form>{script}")

@app.post("/save", response_class=HTMLResponse)
async def save(request: Request):
    form = await request.form()
    if form.get("confirmed") != "yes": raise HTTPException(400, "全項目の確認が必要です")
    text = str(form.get("text", ""))
    try: result = json.loads(str(form.get("result_json", "")))
    except json.JSONDecodeError as exc: raise HTTPException(400, "解析結果の形式が不正です") from exc
    validator.validate(text.strip(), result)
    school, grade, sex = (str(form.get(n, "")).strip() or None for n in ("被災学校種","被災学年","性別"))
    confirmed = {n: (str(form.get(n, "")).strip() or None) for n in result["fields"]}
    try:
        validate_demographics(school, grade, sex)
        validator.validate_confirmed(confirmed)
        other_location = validator.validate_other_location(confirmed["発生場所2"], str(form.get("発生場所2（その他詳細）", "")))
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    record = {"被災学校種":school,"被災学年":grade,"性別":sex,**confirmed,"発生場所2（その他詳細）":other_location,"災害発生時の状況":text}
    review_id = store.save(text, result, record)
    return page(f"<p>確認結果を保存しました（ID: {review_id}）。</p><p><a href='/'>次を入力</a></p>")
