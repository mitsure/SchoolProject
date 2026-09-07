from __future__ import annotations

import html
from urllib.parse import urlencode

from .research import ERROR_CATEGORIES, EVALUATION_FIELDS, SAMPLING, SPLITS, field_options, record_version


def escape(value) -> str:
    return html.escape(str(value))


def dropdown(name, options, selected="") -> str:
    return f"<select name='{escape(name)}'>" + "".join(
        f"<option value='{escape(value)}'{' selected' if value == selected else ''}>{escape(label)}</option>"
        for value, label in options
    ) + "</select>"


def assessment_page(record, validator, history) -> str:
    assessment = record["assessment"] or {}
    labels, categories = assessment.get("labels", {}), assessment.get("error_categories", {})
    rows = []
    for index, (name, values) in enumerate(field_options(validator).items()):
        label = labels.get(name, {})
        selected = {"indeterminate": "__unknown", "no_value": "__none"}.get(label.get("status"), label.get("value") or "")
        options = [("", "未評価"), ("__unknown", "原文から判定不能")]
        if name != "種別":
            options.append(("__none", "値を入れないのが正しい（記載なし・非該当）"))
        options.extend((value, value) for value in values)
        rows.append(f"<tr><th>{escape(name)}</th><td>{dropdown(f'gold_{index}', options, selected)}</td>"
                    f"<td>{dropdown(f'error_{index}', [(v, v) for v in ERROR_CATEGORIES], categories.get(name, '未分類'))}</td></tr>")
    history_html = "".join(
        f"<details><summary>評価 #{item['id']} / {escape(item['created_at'])} UTC / {escape(item['assessment']['reviewer'])}</summary>"
        f"<p>{escape(item['assessment']['note'])}</p><ul>" + "".join(
            f"<li>{escape(name)}: {escape(label['value'] if label['value'] is not None else label['status'])}</li>"
            for name, label in item["assessment"]["labels"].items()
        ) + "</ul></details>" for item in history
    )
    return (
        f"<h2>ID: {record['id']} 研究用の人手評価</h2>"
        "<p class='notice'>これは一次評価です。この画面には自動判定・通常の確定値を表示していません。"
        "原文を読んで評価してください。過去に候補を見た評価者の盲検性は保証されません。"
        "『種別』は後遺障害のDB区分です。事故文だけで判断できない場合は判定不能にしてください。</p>"
        f"<section class='record'><h3>解析時の原文（後から編集された文章ではありません）</h3><p class='situation'>{escape(record['input_text'])}</p></section>"
        f"<form method='post' action='/reviews/{record['id']}/assess'>"
        f"<input type='hidden' name='expected_id' value='{record['assessment_id'] or ''}'>"
        f"<p><label>評価者ID <input name='reviewer' maxlength='100' required value='{escape(assessment.get('reviewer', ''))}'></label> "
        f"<label>データセットID <input name='dataset' maxlength='100' required placeholder='例：pilot-2026-09' value='{escape(assessment.get('dataset', ''))}'></label></p>"
        f"<p><label>用途 {dropdown('split', SPLITS.items(), assessment.get('split', 'development'))}</label> "
        f"<label>抽出方法 {dropdown('sampling', SAMPLING.items(), assessment.get('sampling', 'unspecified'))}</label></p>"
        "<p>データセットID・用途・抽出方法は研究計画に合わせて記録します。最終評価用の指定だけで独立した評価になるわけではありません。</p>"
        f"<p><label>扱い {dropdown('status', [('active', '評価対象'), ('excluded', '除外')], assessment.get('status', 'active'))}</label> "
        f"<label>除外理由 <input name='exclusion_reason' maxlength='500' value='{escape(assessment.get('exclusion_reason', ''))}'></label></p>"
        "<div class='table-scroll'><table><tr><th>項目</th><th>原文から判断した正解</th><th>誤答原因（後から追記可）</th></tr>"
        f"{''.join(rows)}</table></div>"
        "<p>未評価は未作業、判定不能は判断材料が不足・曖昧な状態です。『値を入れないのが正しい』は空欄が適切だと判断できた場合に使います。</p>"
        f"<label>評価メモ<textarea name='note' rows='3' maxlength='2000'>{escape(assessment.get('note', ''))}</textarea></label>"
        "<p><button type='submit'>評価を保存</button> <a href='/dashboard'>ダッシュボードへ</a></p></form>"
        f"<h3>評価履歴（最新 {len(history)} 件）</h3>{history_html or '<p>まだ評価はありません。</p>'}"
    )


def format_rate(metric) -> str:
    if metric["value"] is None:
        return "算出不可（分母0）"
    low, high = metric["ci95_wilson"]
    return (f"<strong>{metric['value']:.1%}</strong> <small>({metric['numerator']}/{metric['denominator']})"
            f"<br>95% CI {low:.1%}–{high:.1%}</small>")


def dashboard_page(records, all_records, summary, filters) -> str:
    versions = {}
    for row in all_records:
        version, metadata = record_version(row), row["metadata"] or {}
        versions[version] = "旧データ（版不明）" if version == "legacy" else f"{metadata.get('model') or '規則'} / {version}"
    if filters["version"] not in versions:
        versions[filters["version"]] = "対象データなし"
    model_warning = ""
    if any((r["metadata"] or {}).get("extractor") == "ollama" and not r["metadata"].get("model_revision") for r in records):
        model_warning = "<p class='notice'>モデルの重みの版が未記録のデータを含みます。同名モデルの入れ替えは識別できません。実験時はモデルを固定して版を記録してください。</p>"
    filter_html = dropdown("version", versions.items(), filters["version"])
    for key, title, choices in (
        ("dataset", "データセット", [(v, v) for v in sorted({r['assessment']['dataset'] for r in all_records if r['assessment']})]),
        ("split", "用途", list(SPLITS.items())), ("sampling", "抽出方法", list(SAMPLING.items())),
    ):
        filter_html += f" <label>{title} {dropdown(key, [('', 'すべて')] + choices, filters[key])}</label>"
    stats = [("登録件数", summary["total"]), ("評価なし", summary["pending"]), ("評価対象（重複除外後）", summary["evaluated"]),
             ("除外", summary["excluded"]), ("同一文・同一版の重複", summary["duplicates"])]
    cards = "".join(f"<div class='metric-card'>{label}<strong>{value}</strong></div>" for label, value in stats)
    screening = summary["screening"]
    metrics = "".join(f"<div class='metric-card'>{label}{format_rate(screening[key])}</div>" for key, label in (
        ("accuracy", "スクリーニング正答率"), ("sensitivity", "感度：陽性例を拾えた割合"),
        ("specificity", "特異度：陰性例を正しく除外"), ("positive_predictive_value", "陽性的中率：検出の的中割合"),
    ))
    cm = screening["confusion_matrix"]
    field_rows = []
    for name in EVALUATION_FIELDS:
        field = summary["fields"][name]
        value = field["accuracy"]["value"]
        bar = f"<meter min='0' max='1' value='{value}' aria-label='{escape(name)}の正答率'></meter>" if value is not None else ""
        field_rows.append(f"<tr><th>{escape(name)}</th><td>{format_rate(field['accuracy'])}{bar}</td>"
                          f"<td>{format_rate(field['precision'])}</td><td>{format_rate(field['coverage'])}</td>"
                          f"<td>{field['correct_empty']}/{field['no_value']}</td>"
                          f"<td>{field['indeterminate']} / {field['unreviewed']} / {field['missing']}</td></tr>")
    error_rows = "".join(
        f"<tr><td><a href='/reviews/{r['review_id']}/assess'>{r['review_id']}</a></td><td>{escape(r['field'])}</td>"
        f"<td>{escape(r['predicted'] or '候補なし')}</td><td>{escape(r['gold'] or '空欄が正解')}</td>"
        f"<td>{escape(r['category'])}</td><td class='situation'>{escape(r['text'])}</td></tr>" for r in summary["errors"][:100]
    )
    categories = "".join(f"<li>{escape(name)}：{count}項目</li>" for name, count in summary["error_categories"].items())
    queue = "".join(f"<tr><td>{r['id']}</td><td>{escape(r['input_text'][:100])}</td>"
                    f"<td>{escape('評価なし' if not r['assessment'] else '除外' if r['assessment']['status'] == 'excluded' else '評価あり（一部未評価の場合あり）')}</td>"
                    f"<td><a href='/reviews/{r['id']}/assess'>人手評価</a></td></tr>" for r in records[:200])
    query = escape(urlencode(filters))
    return (
        "<h2>研究評価ダッシュボード</h2>"
        f"<form method='get' class='actions'>{filter_html}<button>集計を更新</button></form>"
        "<p class='notice'>人手の一次評価との比較です。通常の確定保存は正解扱いしません。"
        "表示対象の版・データセット・用途・抽出方法を確認してください。任意登録や誤答を集めた標本の数値を母集団の性能とはみなせません。"
        "処理に失敗した入力や未保存の入力は集計に含まれず、処理失敗率は算出していません。</p>"
        f"{model_warning}"
        f"<div class='metric-grid'>{cards}</div>"
        "<h3>歯牙障害スクリーニング（歯牙外傷の診断ではありません）</h3>"
        "<p>陽性＝人手で『歯牙障害』、陰性＝他の11種別。種別はLLMではなく規則による候補です。"
        "人手の判定不能・未評価と、保存当時の種別候補がない旧データは除外します。"
        "システムの候補なしは『検出なし』に数えるため、陽性例なら見逃しになります。</p>"
        f"<div class='metric-grid'>{metrics}</div>"
        f"<p>評価 {cm['total']}件 ／ うちシステムの種別候補なし {summary['screening_abstained']}件</p>"
        "<table class='confusion'><caption>混同行列（件）</caption><tr><th></th><th>システム：検出</th><th>システム：検出なし</th></tr>"
        f"<tr><th>人手：歯牙障害</th><td class='correct'>TP（検出成功） {cm['tp']}</td><td class='incorrect'>FN（見逃し） {cm['fn']}</td></tr>"
        f"<tr><th>人手：他の種別</th><td class='incorrect'>FP（過剰検出） {cm['fp']}</td><td class='correct'>TN（除外成功） {cm['tn']}</td></tr></table>"
        "<h3>項目ごとの性能</h3>"
        "<p>正答率の分母は人手で値を決められた件数（候補なしも含む）。空欄が正解の例は別欄です。"
        "適合率は評価可能な例の非空欄出力、カバー率は値あり正解＋空欄正解が分母です。CIはWilson法。"
        "同一原文・同一版は最新の有効な評価1件を採用します。近似重複・別表記の同一事故は別途確認が必要です。</p>"
        f"<div class='table-scroll'><table><tr><th>項目</th><th>正答率</th><th>適合率</th><th>カバー率</th><th>空欄正解の一致件数</th><th>判定不能 / 未評価 / 予測未保存</th></tr>{''.join(field_rows)}</table></div>"
        f"<p>全11項目完全一致率（全項目評価済み・予測保存済み例、空欄正解を含む）：{format_rate(summary['complete_accuracy'])}</p>"
        f"<h3>誤答一覧（{len(summary['errors'])}項目、画面は先頭100項目）</h3>"
        f"<p><a href='/dashboard/errors.csv?{query}'>誤答CSVをダウンロード</a> ／ <a href='/dashboard/export.json?{query}'>評価データ・指標JSONをダウンロード</a></p>"
        f"<ul>{categories}</ul><div class='table-scroll'><table><tr><th>ID</th><th>項目</th><th>自動判定</th><th>人手評価</th><th>原因</th><th>原文</th></tr>{error_rows}</table></div>"
        f"<h3>評価する記録（絞り込み内 {len(records)}件、先頭200件）</h3><table><tr><th>ID</th><th>原文の先頭</th><th>状態</th><th>操作</th></tr>{queue}</table>"
    )
