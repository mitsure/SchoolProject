"""承認済みコードブックで通学中590件をAI暫定分類し、歯牙障害別に集計する。

先に盲検原文だけから分類を固定し、そのハッシュを記録してから歯牙障害区分を結合する。
結果は人手確認前の探索的内部資料であり、予測性能や因果関係を示さない。
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import Step11_ReviewWorkflow as workflow
import Step11_SoloAssistedReview as solo


OUTPUT = solo.OUTPUT / "Full590"
SOURCE = workflow.INTERNAL / "Step11-01_通学中590件_盲検レビューシート_内部用.csv"
MAPPING = workflow.INTERNAL / "AfterReview_DoNotOpen" / "Step11-01B_レビューID対応・自動検索補助_評価完了まで非表示.csv"
FULL_CSV = OUTPUT / "Step11-41_通学中590件_Codex二次検査済み_AI暫定版.csv"
AGGREGATE_CSV = OUTPUT / "Step11-42_通学中590件_AI暫定項目別集計.csv"
COMPARISON_CSV = OUTPUT / "Step11-43_歯牙障害別_AI暫定比較.csv"
REPORT = OUTPUT / "Step11-44_通学中590件_AI暫定解析レポート.md"
MANIFEST = OUTPUT / "Step11-45_通学中590件_AI解析マニフェスト.json"

SCHEMA_VERSION = "Step11-FullAIAnalysis-1.0"
EXPECTED_ROWS = 590
ANALYSIS_FIELDS = [
    "起点機転", "出来事の順序", "最終接触対象", "口腔・顔面への直接外力",
    *workflow.SITE_COLUMNS, "ヘルメット", "マウスガード", "予防可能性",
    "予防可能性の根拠区分", "判定不能理由", "AI確認優先度", "AI確信度",
]


class FullAnalysisError(RuntimeError):
    """個票を変更せず処理を停止すべき問題。"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_blind_source() -> pd.DataFrame:
    if not SOURCE.exists():
        raise FullAnalysisError(f"590件盲検CSVがありません: {SOURCE}")
    frame = pd.read_csv(SOURCE, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    needed = [workflow.ID_COLUMN, workflow.TEXT_COLUMN]
    if not set(needed).issubset(frame.columns) or len(frame) != EXPECTED_ROWS:
        raise FullAnalysisError("590件盲検CSVの列または件数が不正です")
    frame = frame[needed].copy()
    if frame[workflow.ID_COLUMN].duplicated().any() or frame[workflow.TEXT_COLUMN].str.strip().eq("").any():
        raise FullAnalysisError("590件盲検CSVにID重複または原文空欄があります")
    return frame


def classify_blind() -> pd.DataFrame:
    source = read_blind_source()
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for index, row in source.iterrows():
        values = solo.classify(row[workflow.TEXT_COLUMN])
        missing = [field for field in workflow.CHOICES if field != workflow.CONFIRM_COLUMN and not values.get(field)]
        problems = workflow.row_problems(values)
        if missing:
            problems.append("AI必須分類が空: " + "/".join(missing))
        if problems:
            errors.append(f"事例{index + 1}: " + " / ".join(problems))
        rows.append({workflow.ID_COLUMN: row[workflow.ID_COLUMN], workflow.TEXT_COLUMN: row[workflow.TEXT_COLUMN], **values})
    if errors:
        raise FullAnalysisError("590件AI分類の整合性検査に失敗:\n" + "\n".join(errors[:30]))
    return pd.DataFrame(rows)


def verify_development_subset(full: pd.DataFrame) -> None:
    """既に二次検査済みの開発用100件が、590件処理でも同じ値になることを確認する。"""
    if not solo.AI_REVIEWED_CSV.exists():
        raise FullAnalysisError("開発用100件のAI二次検査済みCSVがありません")
    development = pd.read_csv(solo.AI_REVIEWED_CSV, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    fields = [workflow.ID_COLUMN, workflow.TEXT_COLUMN, *solo.AI_META_COLUMNS]
    fields += [field for field in workflow.CHOICES if field != workflow.CONFIRM_COLUMN]
    left = development[fields].sort_values(workflow.ID_COLUMN).reset_index(drop=True)
    right = full.loc[full[workflow.ID_COLUMN].isin(left[workflow.ID_COLUMN]), fields].sort_values(workflow.ID_COLUMN).reset_index(drop=True)
    if len(right) != workflow.EXPECTED_ROWS or not left.equals(right):
        raise FullAnalysisError("開発用100件と590件処理の分類値が一致しません")


def aggregate_table(full: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for field in ANALYSIS_FIELDS:
        for value, count in full[field].value_counts(dropna=False).items():
            rows.append({"項目": field, "値": str(value), "件数": int(count), "割合（%）": round(int(count) / len(full) * 100, 1)})
    return pd.DataFrame(rows)


def read_outcome_mapping() -> pd.DataFrame:
    if not MAPPING.exists():
        raise FullAnalysisError(f"歯牙障害区分の対応表がありません: {MAPPING}")
    mapping = pd.read_csv(MAPPING, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    needed = [workflow.ID_COLUMN, "歯牙障害"]
    if not set(needed).issubset(mapping.columns) or len(mapping) != EXPECTED_ROWS:
        raise FullAnalysisError("対応表の列または件数が不正です")
    mapping = mapping[needed].copy()
    if mapping[workflow.ID_COLUMN].duplicated().any() or not set(mapping["歯牙障害"]).issubset({"歯牙障害", "歯牙障害以外"}):
        raise FullAnalysisError("対応表のIDまたは歯牙障害区分が不正です")
    return mapping


def comparison_table(full: pd.DataFrame, mapping: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = full.merge(mapping, on=workflow.ID_COLUMN, how="left", validate="one_to_one")
    if merged["歯牙障害"].eq("").any() or merged["歯牙障害"].isna().any():
        raise FullAnalysisError("AI分類と歯牙障害区分を全件結合できません")
    rows: list[dict[str, object]] = []
    for field in ANALYSIS_FIELDS:
        grouped = merged.groupby(field, dropna=False)["歯牙障害"]
        for value, outcomes in grouped:
            total = int(len(outcomes))
            dental = int((outcomes == "歯牙障害").sum())
            rows.append({
                "項目": field, "値": str(value), "全体件数": total,
                "歯牙障害件数": dental, "歯牙障害以外件数": total - dental,
                "歯牙障害割合（%）": round(dental / total * 100, 1) if total else None,
                "結果区分": "AI暫定分類・人手未確認",
            })
    return pd.DataFrame(rows), merged


def report_text(full: pd.DataFrame, merged: pd.DataFrame) -> str:
    n_dental = int((merged["歯牙障害"] == "歯牙障害").sum())

    def overall(field: str, value: str) -> int:
        return int((full[field] == value).sum())

    def group_line(value: str) -> str:
        part = merged[merged["起点機転"] == value]
        dental = int((part["歯牙障害"] == "歯牙障害").sum())
        percentage = dental / len(part) * 100 if len(part) else 0
        return f"- {value}：{len(part)}件中、歯牙障害{dental}件（{percentage:.1f}%）"

    return f"""# Step11 通学中590件 AI暫定解析レポート

## 解析の位置付け

通学中590件の盲検原文だけを用いてAI暫定分類を固定し、分類CSVのハッシュを記録した後に歯牙障害区分を結合した。コードブックは`{workflow.CODEBOOK_VERSION}`である。

この結果はAI分類を歯科医師が全件確認したものではなく、探索的な内部資料である。予測性能、因果関係、2名独立評価またはGold Standardを示さない。

## 全体

- 対象：590件
- 歯牙障害：{n_dental}件（{n_dental / len(merged) * 100:.1f}%）
- 歯牙障害以外：{len(merged) - n_dental}件
- 転倒・つまずき：{overall('起点機転', '転倒・つまずき')}件
- 衝突・接触：{overall('起点機転', '衝突・接触')}件
- 転落・落下：{overall('起点機転', '転落・落下')}件
- 起点機転判定不能：{overall('起点機転', '判定不能')}件
- 口腔・顔面への直接外力あり（明記）：{overall('口腔・顔面への直接外力', 'あり（明記）')}件
- 修正可能要因の明記あり：{overall('予防可能性', '修正可能要因の明記あり')}件

## 起点機転別の歯牙障害割合

{group_line('転倒・つまずき')}
{group_line('衝突・接触')}
{group_line('転落・落下')}
{group_line('判定不能')}

## この結果から暫定的に言えること

起点機転、口腔・顔面への直接外力、受傷部位の記載および修正可能要因を、同一の固定ルールで590件に付与したため、通学中事例の記述パターンを歯牙障害の有無で比較できる。ただし、歯や前歯などの語は歯牙障害区分そのものに近いため、機械学習の予測特徴として使うと情報漏洩になる可能性が高い。

## 次に確認する部分

発表や論文で確定値として用いる場合は、少なくともAI確認優先度が「最優先」の事例、判定不能事例および無作為抽出した通常事例を歯科医師が原文照合する。確定前の割合は小数点以下の違いまで強く解釈しない。
"""


def run() -> None:
    outputs = [FULL_CSV, AGGREGATE_CSV, COMPARISON_CSV, REPORT, MANIFEST]
    existing = [path for path in outputs if path.exists()]
    if existing:
        raise FullAnalysisError("既存の590件AI解析成果物を上書きしません: " + ", ".join(path.name for path in existing))
    if not workflow.APPROVAL.exists():
        raise FullAnalysisError("コードブック承認記録がありません")

    full = classify_blind()
    verify_development_subset(full)
    aggregate = aggregate_table(full)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix="step11-full-ai-", dir=OUTPUT.parent) as temp_name:
        temp = Path(temp_name)
        blind_frozen = temp / FULL_CSV.name
        full.to_csv(blind_frozen, index=False, encoding="utf-8-sig")
        blind_hash = sha256(blind_frozen)

        # 盲検分類の固定後にだけ歯牙障害区分を読む。
        mapping = read_outcome_mapping()
        comparison, merged = comparison_table(full, mapping)
        aggregate.to_csv(temp / AGGREGATE_CSV.name, index=False, encoding="utf-8-sig")
        comparison.to_csv(temp / COMPARISON_CSV.name, index=False, encoding="utf-8-sig")
        (temp / REPORT.name).write_text(report_text(full, merged), encoding="utf-8")

        record = {
            "schema_version": SCHEMA_VERSION, "status": "AI_FULL590_COMPLETE_HUMAN_NOT_CONFIRMED",
            "created_at_utc": utc_now(), "rows": len(full), "codebook_version": workflow.CODEBOOK_VERSION,
            "blind_source_sha256": sha256(SOURCE), "blind_classification_sha256_before_unblinding": blind_hash,
            "outcome_mapping_sha256": sha256(MAPPING), "classifier_sha256": sha256(Path(solo.__file__).resolve()),
            "analysis_script_sha256": sha256(Path(__file__).resolve()), "codebook_sha256": sha256(workflow.CODEBOOK_SOURCE),
            "approval_sha256": sha256(workflow.APPROVAL),
            "warning": "歯科医師の全件確認前。探索的内部利用のみ。予測性能・因果・Gold Standardを主張しない。",
        }
        (temp / MANIFEST.name).write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        OUTPUT.mkdir(parents=True, exist_ok=False)
        OUTPUT.chmod(0o700)
        for path in temp.iterdir():
            path.chmod(0o600)
            os.replace(path, OUTPUT / path.name)
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(f"FULL_AI_ANALYSIS_OK: {len(full)}件 / レポート={REPORT}")


if __name__ == "__main__":
    try:
        run()
    except FullAnalysisError as error:
        raise SystemExit(f"STOP: {error}") from error
