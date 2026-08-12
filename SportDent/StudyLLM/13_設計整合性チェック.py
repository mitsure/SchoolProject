"""StudyLLMの設計資料を変更せずに横断検証する。"""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rows(name: str) -> list[dict[str, str]]:
    path = ROOT / name
    require(path.exists(), f"必須ファイルがありません: {name}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_categories() -> None:
    hierarchy = rows("02_上下位カテゴリ対応表.csv")
    require(len(hierarchy) == 74, "上下位カテゴリ表の行数が不一致です")
    pairs = {(row["項目"], row["観測上位値"], row["観測下位値"]) for row in hierarchy}
    require(len(pairs) == len(hierarchy), "上下位カテゴリ表に重複行があります")
    totals: dict[str, int] = {}
    for row in hierarchy:
        totals[row["項目"]] = totals.get(row["項目"], 0) + int(row["全体観測件数"])
        if row["観測下位値"] in {"その他", "null"}:
            require(row["下位から上位を自動補完"] == "不可", "曖昧・構造的nullを自動補完しようとしています")
    require(totals == {"場合別": 7682, "発生場所": 7682}, f"上下位カテゴリの合計が不一致です: {totals}")

    observed = rows("04_観測選択肢辞書.csv")
    observed_pairs = {(row["項目"], row["観測値"]) for row in observed}
    require(len(observed_pairs) == len(observed), "観測選択肢辞書に重複があります")
    observed_totals: dict[str, int] = {}
    for row in observed:
        observed_totals[row["項目"]] = observed_totals.get(row["項目"], 0) + int(row["全体件数"])
        require(row["候補生成方針"] != "通常", "無条件候補に見える旧方針「通常」が残っています")
    require(
        observed_totals == {"競技種目": 3923, "通学方法": 590, "遊具等": 275},
        f"観測選択肢の合計が不一致です: {observed_totals}",
    )

    synonyms = rows("05_同義語候補辞書.csv")
    require(len({row["rule_id"] for row in synonyms}) == len(synonyms), "同義語rule_idが重複しています")
    allowed_from_hierarchy = {
        ("場合別2" if row["項目"] == "場合別" else "発生場所2", row["観測下位値"])
        for row in hierarchy
        if row["観測下位値"] != "null"
    }
    allowed = allowed_from_hierarchy | observed_pairs
    for row in synonyms:
        require((row["項目"], row["DB候補値"]) in allowed, f"辞書外の候補値です: {row}")
        require(row["候補生成区分"] in {"候補のみ", "条件付き候補"}, f"直接置換に見える区分です: {row}")
        require(row["必要条件"] and row["主な除外条件"], f"文脈条件が不足しています: {row['rule_id']}")


def validate_error_contract() -> None:
    schema = json.loads((ROOT / "09_構造化出力JSONSchema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["schema_version"]["const"] == "1.0.1", "JSON Schema版が1.0.1ではありません")
    require(schema["properties"]["processing_status"]["enum"] == ["success", "error"], "処理状態の列挙が不一致です")
    success_branch, error_branch = schema["allOf"]
    success_fields = success_branch["then"]["properties"]["fields"]
    error_fields = error_branch["then"]["properties"]["fields"]
    require(len(success_fields["required"]) == 6, "成功時の必須6項目が定義されていません")
    require(error_fields.get("maxProperties") == 0, "処理障害時に項目値を返せるスキーマです")
    field_definition = schema["$defs"]["fieldResult"]
    require("error" not in field_definition["properties"]["status"]["enum"], "項目statusに処理障害が混在しています")
    require("error" not in field_definition["properties"]["validator_status"]["enum"], "検証障害が項目結果として保存可能です")
    null_statuses = field_definition["allOf"][3]["if"]["properties"]["status"]["enum"]
    require("error" not in null_statuses, "処理障害がnull扱いに残っています")


def validate_evaluation_and_security() -> None:
    evaluation = (ROOT / "03_LLM精度評価計画.md").read_text(encoding="utf-8")
    for phrase in [
        "LLMとDBの一致例",
        "LLMのnull例",
        "2名が独立判定",
        "第三者または合議",
        "片側95%信頼下限98%以上",
        "新規利用者が入力した未使用文",
    ]:
        require(phrase in evaluation, f"精度評価計画に必須要件がありません: {phrase}")

    gate = (ROOT / "06_実装前確認事項.md").read_text(encoding="utf-8")
    for phrase in [
        "匿名化方法",
        "保存期間、学習利用、再委託、保存地域",
        "通信時・保存時の暗号化",
        "利用者認証と閲覧権限",
        "監査ログの保持・削除期限",
        "エラーログへ原文を残さない",
        "実事故文を用いた外部API試験を開始しない",
    ]:
        require(phrase in gate, f"実装開始ゲートに必須要件がありません: {phrase}")

    rules = rows("07_項目依存ルール.csv")
    require(len({row["rule_id"] for row in rules}) == len(rules), "項目依存rule_idが重複しています")
    error_rule = next((row for row in rules if row["rule_id"] == "ERROR_001"), None)
    require(error_rule is not None, "処理障害ルールがありません")
    require("processing_status=error" in error_rule["不成立時の扱い"], "処理障害がトップレベルerrorになっていません")
    require("保存停止" in error_rule["不成立時の扱い"], "処理障害時の保存停止がありません")


def validate_references() -> None:
    all_text = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.iterdir() if path.suffix in {".md", ".csv", ".json"})
    require("10_LLMカテゴリ対応表.csv" not in all_text, "旧ファイル名への参照が残っています")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for name in [
        "01_LLM構造化抽出仕様.md",
        "02_上下位カテゴリ対応表.csv",
        "03_LLM精度評価計画.md",
        "04_観測選択肢辞書.csv",
        "05_同義語候補辞書.csv",
        "06_実装前確認事項.md",
        "07_項目依存ルール.csv",
        "08_カテゴリ定義と出典の監査.md",
        "09_構造化出力JSONSchema.json",
        "10_安全性試験ケース.csv",
        "11_バージョン管理.md",
        "12_再検討・修正記録.md",
        "13_設計整合性チェック.py",
    ]:
        require(name in readme, f"READMEの資料一覧にありません: {name}")
        require((ROOT / name).exists(), f"README参照先がありません: {name}")

    tests = rows("10_安全性試験ケース.csv")
    require(len({row["test_id"] for row in tests}) == len(tests), "安全性試験IDが重複しています")
    require(any("空入力エラー" in row["期待する処理"] for row in tests), "空入力を処理エラーにする試験がありません")


def main() -> None:
    validate_categories()
    validate_error_contract()
    validate_evaluation_and_security()
    validate_references()
    print("VALIDATION_OK: StudyLLM設計・辞書・評価・安全性")


if __name__ == "__main__":
    main()
