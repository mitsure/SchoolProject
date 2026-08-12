"""SportDent Step11：通学中事例の臨床レビュー支援資料を生成する。"""
from __future__ import annotations

import argparse
import logging
import secrets
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
STEP7_CODE = PROJECT / "file" / "Step7_探索的解析"
sys.path.insert(0, str(STEP7_CODE))
import Step7_Main as step7  # noqa: E402

OUTPUT = PROJECT / "CreateData" / "Step11_通学中臨床レビュー"
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(FONT)).get_name()
plt.rcParams["axes.unicode_minus"] = False

RULES = {
    "転倒・つまずき": ["転倒", "転ん", "ころん", "つまず", "滑り", "滑っ", "バランスを崩"],
    "衝突・接触": ["衝突", "接触", "ぶつか", "ぶつけ", "追突", "衝突し", "はねら"],
    "転落・落下": ["転落", "落ち", "投げ出", "飛び出"],
    "車両関与": ["自動車", "乗用車", "トラック", "バス", "バイク", "車両", "車に", "車と"],
    "路面と接触": ["アスファルト", "路面", "地面", "道路に", "歩道に", "舗装", "側溝"],
    "構造物と接触": ["ポール", "電柱", "ガードレール", "フェンス", "看板", "壁", "縁石", "段差"],
    "人と接触": ["友人", "児童", "生徒", "歩行者", "相手", "妹", "兄", "弟"],
    "前歯部の記載": ["前歯", "門歯"],
    "歯牙の記載": ["歯"],
    "口腔・口唇の記載": ["口腔", "口唇", "口を", "唇"],
    "顔面・顎の記載": ["顔面", "顔を", "顎", "あご"],
    "ヘルメットの記載": ["ヘルメット"],
    "マウスガードの記載": ["マウスガード", "マウスピース"],
    "速度関与": ["スピード", "速度", "加速", "下り坂"],
    "雨・湿潤路面": ["雨", "濡れ", "湿っ", "水たまり"],
    "ブレーキ・操作": ["ブレーキ", "ハンドル", "操作を誤", "脇見", "前方不注意"],
}


def flag(text: str, words: list[str]) -> str:
    hits = [word for word in words if word in text]
    return "あり：" + " / ".join(hits) if hits else "なし"


def yes(value: str) -> int:
    return int(str(value).startswith("あり："))


def write_private_csv(frame: pd.DataFrame, path: Path) -> None:
    """原文・内部ID・人手回答を含むCSVを所有者だけが読める権限で保存する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    path.chmod(0o600)


def secure_private_tree(path: Path) -> None:
    """バックアップを含む非公開ツリーを所有者だけが読める権限にする。"""
    path.chmod(0o700)
    for child in path.rglob("*"):
        child.chmod(0o700 if child.is_dir() else 0o600)


def suppress_count(value: int) -> str | int:
    """公開集計の1〜4件セルを抑制する。"""
    numeric = int(value)
    return "<5" if 0 < numeric < 5 else numeric


def suppress_public_outcome_table(frame: pd.DataFrame, category_column: str) -> pd.DataFrame:
    """結果セル1〜4件と補完計算を防ぐ二次セルを公開表で伏せる。"""
    public = frame.copy()
    dental = pd.to_numeric(public["歯牙障害件数"])
    non_dental = pd.to_numeric(public["全体件数"]) - dental
    hidden = dental.between(1, 4) | non_dental.between(1, 4)
    if int(hidden.sum()) == 1 and len(public) > 1:
        candidates = list(public.index[~hidden])
        preferred = [index for index in candidates if "その他" in str(public.loc[index, category_column])]
        if not preferred:
            preferred = [index for index in candidates if int(dental.loc[index]) == 0]
        secondary = preferred[0] if preferred else max(
            candidates, key=lambda index: int(public.loc[index, "全体件数"])
        )
        hidden.loc[secondary] = True
    public["歯牙障害件数"] = public["歯牙障害件数"].astype(object)
    public.loc[hidden, "歯牙障害件数"] = "非表示（小集計保護）"
    public["歯牙障害割合（％）"] = public["歯牙障害割合（％）"].astype(object)
    public.loc[hidden, "歯牙障害割合（％）"] = "非表示（小集計保護）"
    public["公開上の注記"] = np.where(hidden, "一次または二次セル抑制", "")
    return public


def proportional_blind_sample(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    """歯牙障害の構成を母集団に近づけつつ、表示時には区分を伏せて抽出する。"""
    sample_size = min(size, len(frame))
    dental_size = round(sample_size * frame["歯牙障害"].eq("歯牙障害").mean())
    parts = []
    for group, part in frame.groupby("歯牙障害", sort=True):
        requested = dental_size if group == "歯牙障害" else sample_size - dental_size
        parts.append(part.sample(n=min(requested, len(part)), random_state=seed))
    return pd.concat(parts).sort_values("レビューID")


def hits(text: str, words: list[str]) -> list[str]:
    return [word for word in words if word in text]


def automatic_review(text: str) -> dict[str, str]:
    """原文から臨床レビューの暫定値と根拠を作る。人の確定判定は上書きしない。"""
    found = {name: hits(text, words) for name, words in RULES.items()}
    fall, collision, drop = (bool(found[name]) for name in ["転倒・つまずき", "衝突・接触", "転落・落下"])
    if collision and fall:
        mechanism = "衝突・接触"
    elif fall:
        mechanism = "転倒・つまずき"
    elif collision:
        mechanism = "衝突・接触"
    elif drop:
        mechanism = "転落・落下"
    else:
        mechanism = "判定不能"

    if found["車両関与"] and collision:
        target = "車両"
    elif found["人と接触"] and collision:
        target = "人"
    elif found["構造物と接触"]:
        target = "構造物"
    elif found["路面と接触"] or (fall and any(word in text for word in ["道路", "歩道", "地面", "アスファルト"])):
        target = "路面"
    elif mechanism == "判定不能":
        target = "判定不能"
    else:
        target = "その他・不明"

    dental = bool(found["前歯部の記載"] or found["歯牙の記載"])
    oral = bool(found["口腔・口唇の記載"] or found["顔面・顎の記載"])
    impact_words = hits(text, ["打っ", "打ち", "強打", "衝突", "接触", "ぶつけ", "ぶつか", "脱落", "破折", "折れ"])
    if (dental or oral) and impact_words:
        direct_force = "あり"
    elif dental or oral:
        direct_force = "不明"
    else:
        direct_force = "なし（記載上）"

    sites = []
    if found["前歯部の記載"]: sites.append("前歯部")
    elif found["歯牙の記載"]: sites.append("歯牙・部位不明")
    if found["口腔・口唇の記載"]: sites.append("口腔・口唇")
    if found["顔面・顎の記載"]: sites.append("顔面・顎")
    injury_site = " / ".join(sites) if sites else "判定不能"

    protection_notes = []
    if found["ヘルメットの記載"]: protection_notes.append("ヘルメット記載あり（使用状況要確認）")
    if found["マウスガードの記載"]: protection_notes.append("マウスガード記載あり（使用状況要確認）")
    protection = " / ".join(protection_notes) if protection_notes else "記載なし"

    modifiable = found["速度関与"] + found["雨・湿潤路面"] + found["ブレーキ・操作"] + found["構造物と接触"]
    preventability = "可能性あり" if modifiable else "判定困難"
    core_evidence = found["転倒・つまずき"] + found["衝突・接触"] + found["転落・落下"] + impact_words
    evidence = list(dict.fromkeys(core_evidence + found["路面と接触"] + found["前歯部の記載"] + modifiable))
    if mechanism != "判定不能" and target not in ["判定不能", "その他・不明"] and len(evidence) >= 3:
        confidence = "高"
    elif mechanism != "判定不能" or dental or oral:
        confidence = "中"
    else:
        confidence = "低"
    review_needed = "要確認" if confidence == "低" or "判定不能" in [mechanism, target, injury_site] else "通常確認"
    return {
        "自動暫定：主受傷機転": mechanism, "自動暫定：衝突対象": target,
        "自動暫定：口腔・顔面への直接外力": direct_force, "自動暫定：受傷部位": injury_site,
        "自動暫定：保護具": protection, "自動暫定：予防可能性": preventability,
        "自動判定の根拠語": " / ".join(evidence) if evidence else "根拠語なし",
        "自動判定の確信度": confidence, "人による確認優先度": review_needed,
    }


def make_plot(
    table: pd.DataFrame,
    category: str,
    output_name: str,
    warning: str | None = None,
    directory: Path | None = None,
) -> None:
    plotted = table.loc[table["全体件数"] >= 10].sort_values("歯牙障害割合（％）")
    fig, axis = plt.subplots(figsize=(11, max(5, .55 * len(plotted))))
    bars = axis.barh(plotted[category], plotted["歯牙障害割合（％）"], color="#176B87")
    axis.set_xlabel("通学中の登録事例に占める歯牙障害の割合（％）")
    axis.set_ylabel(category); axis.set_xlim(0, 100); axis.grid(axis="x", color="#D0D5DD", linewidth=.6)
    for bar, value, count in zip(bars, plotted["歯牙障害割合（％）"], plotted["全体件数"]):
        axis.text(min(value + 1, 94), bar.get_y() + bar.get_height()/2, f"{value:.1f}% (n={count})", va="center", fontsize=9)
    axis.set_title(f"通学中事例の{category}別にみた歯牙障害割合")
    if warning:
        axis.text(
            .5, .5, warning, transform=axis.transAxes, ha="center", va="center",
            fontsize=28, color="#B42318", alpha=.22, weight="bold", rotation=12,
        )
        fig.text(.5, .965, warning, ha="center", va="top", fontsize=11, color="#B42318", weight="bold")
    fig.text(
        .01, .01,
        "注：登録された障害事例内の割合である。1〜4件セルと二次抑制カテゴリは図示せず、通学者全体の発生リスクを示さない。",
        fontsize=8, color="#475467",
    )
    fig.tight_layout(rect=[0, .04, 1, .95 if warning else 1])
    destination = directory or (OUTPUT / "Figure")
    destination.mkdir(parents=True, exist_ok=True)
    png_path = destination / f"{output_name}.png"
    svg_path = destination / f"{output_name}.svg"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    if directory is not None:
        destination.chmod(0o700)
        png_path.chmod(0o600)
        svg_path.chmod(0o600)
    plt.close(fig)


def _contains_manual_entries() -> bool:
    """既存の人手入力を自動再生成で消さないための確認。"""
    internal = OUTPUT / "InternalReview"
    if not internal.exists():
        return False
    # Excel入力票は人手レビューの原本である。回答欄が空でも、配布後に
    # Step11を再生成するとレビューIDや原文との対応が変わり得るため停止する。
    if (internal / "REVIEW_WORKFLOW_INITIALIZED.lock").exists():
        return True
    if any(internal.rglob("*.xlsx")):
        return True
    for path in internal.rglob("*.csv"):
        frame = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
        manual_columns = [
            column for column in frame.columns
            if column.startswith("最終：")
            or column.startswith("歯科医師の修正：")
            or column.startswith("評価者A：")
            or column.startswith("評価者B：")
            or column in {"歯科医師コメント", "レビュー者", "レビュー日"}
        ]
        if manual_columns and frame[manual_columns].apply(lambda col: col.str.strip().ne("").any()).any():
            return True
    return False


def main(force: bool = False) -> None:
    logger = logging.getLogger("Step11"); logger.setLevel(logging.INFO); logger.handlers.clear(); logger.addHandler(logging.StreamHandler(sys.stdout))
    # 人手レビュー原本が存在する場合は、入力CSVの読込より前に即時停止する。
    if OUTPUT.exists() and _contains_manual_entries():
        raise RuntimeError("既存の歯科医師入力またはExcelレビュー原本を検出したため、Step11の再生成を停止しました。")
    datasets, _ = step7.load_step2_category_datasets(step7.resolve_unicode_path(step7.STEP2_CATEGORY_DIR), logger)
    raw = datasets["全体"]
    commute = raw.loc[raw["場合別1"].astype("string").str.strip().eq("通学中")].copy()
    commute = commute.sample(frac=1, random_state=20260811).reset_index(drop=True)
    if OUTPUT.exists():
        if not force:
            raise FileExistsError(
                f"{OUTPUT} は既に存在します。再生成する場合は内容を確認して --force を指定してください。"
            )
        backup_root = PROJECT / "CreateData" / "RegenerationBackups"
        backup_root.mkdir(exist_ok=True)
        backup_root.chmod(0o700)
        backup_readme = backup_root / "README.md"
        backup_readme.write_text(
            "# 再生成前バックアップ\n\n自動上書きの直前に保存した復旧用コピーです。現行結果・投稿資料として使用しないでください。\n",
            encoding="utf-8",
        )
        backup_readme.chmod(0o600)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_root / f"Step11_通学中臨床レビュー_{timestamp}"
        shutil.copytree(OUTPUT, backup_path)
        secure_private_tree(backup_path)
        shutil.rmtree(OUTPUT)
    (OUTPUT / "InternalReview" / "AfterReview_DoNotOpen").mkdir(parents=True)
    (OUTPUT / "InternalReview").chmod(0o700)
    (OUTPUT / "InternalReview" / "AfterReview_DoNotOpen").chmod(0o700)
    legacy_internal = OUTPUT / "Internal_DoNotPublish"
    legacy_internal.mkdir()
    legacy_internal.chmod(0o700)
    (OUTPUT / "Figure").mkdir()

    review_ids: list[str] = []
    while len(review_ids) < len(commute):
        candidate = "R-" + secrets.token_hex(5).upper()
        if candidate not in review_ids:
            review_ids.append(candidate)
    review = pd.DataFrame({
        "レビューID": review_ids, "内部ID": commute["記号"].astype("string"),
        "歯牙障害": commute["Step7_歯牙障害フラグ"].map({1: "歯牙障害", 0: "歯牙障害以外"}),
        "学校種": commute["被災学校種"], "学年": commute["被災学年"], "性別": commute["性別"],
        "登下校": commute["場合別2"], "通学方法": commute["通学方法"], "発生場所": commute["発生場所2"],
        "原文（内部確認用）": commute["災害発生時の状況"].astype("string"),
    })
    for name, words in RULES.items(): review[f"自動：{name}"] = review["原文（内部確認用）"].map(lambda text: flag(str(text), words))
    for column in ["最終：主受傷機転", "最終：衝突対象", "最終：口腔・顔面への直接外力", "最終：受傷部位", "最終：保護具", "最終：予防可能性", "最終：判定不能", "歯科医師コメント", "レビュー者", "レビュー日"]:
        review[column] = ""
    blind_columns = [
        "レビューID", "原文（内部確認用）", "最終：主受傷機転", "最終：衝突対象",
        "最終：口腔・顔面への直接外力", "最終：受傷部位", "最終：保護具",
        "最終：予防可能性", "最終：判定不能", "歯科医師コメント", "レビュー者", "レビュー日",
    ]
    write_private_csv(
        review[blind_columns],
        OUTPUT / "InternalReview" / "Step11-01_通学中590件_盲検レビューシート_内部用.csv",
    )
    write_private_csv(
        review,
        OUTPUT / "InternalReview" / "AfterReview_DoNotOpen" / "Step11-01B_レビューID対応・自動検索補助_評価完了まで非表示.csv",
    )

    # 人の最終判定とは別ファイルに、全項目を自動入力した暫定版を作る。
    automatic = pd.DataFrame([automatic_review(str(text)) for text in review["原文（内部確認用）"]])
    automatic_full = pd.concat([
        review[["レビューID", "内部ID", "歯牙障害", "学校種", "学年", "性別", "登下校", "通学方法", "発生場所", "原文（内部確認用）"]],
        automatic,
    ], axis=1)
    automatic_full["歯科医師の修正：主受傷機転"] = ""
    automatic_full["歯科医師の修正：衝突対象"] = ""
    automatic_full["歯科医師の修正：直接外力"] = ""
    automatic_full["歯科医師の修正：受傷部位"] = ""
    automatic_full["歯科医師の修正：保護具"] = ""
    automatic_full["歯科医師の修正：予防可能性"] = ""
    automatic_full["歯科医師コメント"] = ""
    write_private_csv(
        automatic_full,
        OUTPUT / "InternalReview" / "AfterReview_DoNotOpen" / "Step11-10_通学中590件_自動レビュー入力済み_暫定版.csv",
    )
    auto_summary = automatic.assign(歯牙障害=review["歯牙障害"]).groupby(
        ["自動判定の確信度", "人による確認優先度", "自動暫定：主受傷機転", "歯牙障害"], dropna=False
    ).size().rename("件数").reset_index()
    auto_summary.insert(0, "利用状態", "使用停止：人手未確認")
    auto_summary_public = auto_summary.copy()
    auto_summary_public["件数"] = auto_summary_public["件数"].map(suppress_count)
    write_private_csv(auto_summary_public, legacy_internal / "Step11-11_自動レビュー結果集計_使用停止.csv")

    provisional_rows = []
    for field in ["自動暫定：主受傷機転", "自動暫定：衝突対象", "自動暫定：口腔・顔面への直接外力", "自動暫定：受傷部位", "自動暫定：保護具", "自動暫定：予防可能性"]:
        for category, part in automatic_full.groupby(field, dropna=False):
            dental_count = int(part["歯牙障害"].eq("歯牙障害").sum())
            provisional_rows.append({"自動分類項目": field.removeprefix("自動暫定："), "自動分類": category,
                                     "全体件数": len(part), "歯牙障害件数": dental_count,
                                     "歯牙障害以外件数": len(part) - dental_count,
                                     "歯牙障害割合（％）": dental_count / len(part) * 100})
    provisional_table = pd.DataFrame(provisional_rows)
    provisional_table.insert(0, "利用状態", "使用停止：人手未確認")
    provisional_public = provisional_table.copy()
    small_mask = (
        provisional_public["歯牙障害件数"].between(1, 4)
        | provisional_public["歯牙障害以外件数"].between(1, 4)
        | provisional_public["全体件数"].between(1, 4)
    )
    for column in ["全体件数", "歯牙障害件数", "歯牙障害以外件数"]:
        provisional_public[column] = provisional_public[column].astype(object)
        provisional_public.loc[small_mask, column] = "<5"
    provisional_public["歯牙障害割合（％）"] = provisional_public["歯牙障害割合（％）"].astype(object)
    provisional_public.loc[small_mask, "歯牙障害割合（％）"] = "非表示（小集計）"
    write_private_csv(provisional_public, legacy_internal / "Step11-12_自動暫定分類別集計_使用停止.csv")

    mechanism_table = provisional_table.loc[provisional_table["自動分類項目"].eq("主受傷機転")].copy()
    mechanism_table = mechanism_table.rename(columns={"自動分類": "主受傷機転"})
    make_plot(
        mechanism_table, "主受傷機転", "Step11-13_自動暫定_主受傷機転別_歯牙障害割合",
        warning="使用停止・人手未確認",
        directory=legacy_internal,
    )

    mechanism_cross = pd.crosstab(automatic_full["自動暫定：主受傷機転"], automatic_full["歯牙障害"])
    mechanism_p = chi2_contingency(mechanism_cross)[1]

    auto_rows = []
    for name in RULES:
        column = f"自動：{name}"; detected = review[column].map(yes).astype(bool)
        for group, mask in [("全体", pd.Series(True, index=review.index)), ("歯牙障害", review["歯牙障害"].eq("歯牙障害")), ("歯牙障害以外", review["歯牙障害"].eq("歯牙障害以外"))]:
            auto_rows.append({"複数ラベル語彙検出": name, "群": group, "対象件数": int(mask.sum()), "検出件数": int((detected & mask).sum()), "検出割合（％）": (detected & mask).sum()/mask.sum()*100})
    auto_public = pd.DataFrame(auto_rows)
    row_small = auto_public["検出件数"].between(1, 4) | (auto_public["対象件数"] - auto_public["検出件数"]).between(1, 4)
    # 全体＝歯牙障害＋歯牙障害以外なので、1行だけ伏せても差し引きで復元できる。
    # 同じ検索項目の3群をまとめて伏せ、補完推定を防ぐ。
    sensitive_rules = set(auto_public.loc[row_small, "複数ラベル語彙検出"])
    auto_small = auto_public["複数ラベル語彙検出"].isin(sensitive_rules)
    auto_public["検出件数"] = auto_public["検出件数"].astype(object)
    auto_public.loc[auto_small, "検出件数"] = "非表示（補完防止）"
    auto_public["検出割合（％）"] = auto_public["検出割合（％）"].astype(object)
    auto_public.loc[auto_small, "検出割合（％）"] = "非表示（補完防止）"
    auto_public.to_csv(OUTPUT / "Step11-03_複数ラベル語彙検出集計_非識別.csv", index=False, encoding="utf-8-sig")
    dental_only = pd.DataFrame(auto_rows).loc[lambda frame: frame["群"].eq("歯牙障害")].copy()
    dental_small = dental_only["検出件数"].between(1, 4)
    dental_only["検出件数"] = dental_only["検出件数"].astype(object)
    dental_only.loc[dental_small, "検出件数"] = "<5"
    dental_only["検出割合（％）"] = dental_only["検出割合（％）"].astype(object)
    dental_only.loc[dental_small, "検出割合（％）"] = "非表示（小集計）"
    dental_only.to_csv(
        OUTPUT / "Step11-03A_歯牙障害群内_複数ラベル語彙検出集計.csv", index=False, encoding="utf-8-sig"
    )

    tables = {}
    for field, filename in [("通学方法", "Step11-04_通学方法別集計.csv"), ("登下校", "Step11-05_登下校別集計.csv")]:
        values = review[field].astype("string").str.strip().replace("", pd.NA).fillna("不明・記載なし")
        counts = values.value_counts(dropna=False)
        values = values.where(~values.isin(counts[counts < 5].index), "その他（5件未満を統合）")
        table = review.assign(_公開カテゴリ=values).groupby("_公開カテゴリ", dropna=False)["歯牙障害"].agg(
            全体件数="size", 歯牙障害件数=lambda x: x.eq("歯牙障害").sum()
        ).reset_index().rename(columns={"_公開カテゴリ": field})
        table["歯牙障害割合（％）"] = table["歯牙障害件数"] / table["全体件数"] * 100
        public_table = suppress_public_outcome_table(table, field)
        public_table.to_csv(
            OUTPUT / filename, index=False, encoding="utf-8-sig"
        )
        visible = pd.to_numeric(public_table["歯牙障害件数"], errors="coerce").notna()
        tables[field] = table.loc[visible].copy()
    make_plot(tables["通学方法"], "通学方法", "Step11-06_通学方法別_歯牙障害割合")
    make_plot(tables["登下校"], "登下校", "Step11-07_登下校別_歯牙障害割合")

    write = lambda name, text: (OUTPUT / name).write_text(text.strip() + "\n", encoding="utf-8")
    shutil.copy2(
        HERE / "Step11_ReviewCodebook_candidate.md",
        OUTPUT / "Step11-02_歯科医師レビュー判定基準.md",
    )

    development = proportional_blind_sample(review, size=100, seed=20260811)
    remaining = review.loc[~review.index.isin(development.index)]
    validation = proportional_blind_sample(remaining, size=100, seed=20260812)
    answer_items = ["主受傷機転", "衝突対象", "直接外力", "受傷部位", "保護具", "予防可能性", "判定不能", "コメント"]
    for phase, phase_number, sampled in [
        ("開発用", "08", development),
        ("最終評価用", "16", validation),
    ]:
        sample_base = sampled[["レビューID", "原文（内部確認用）"]]
        for reviewer in ["A", "B"]:
            reviewer_sheet = sample_base.copy()
            for column in answer_items:
                reviewer_sheet[f"評価者{reviewer}：{column}"] = ""
            write_private_csv(
                reviewer_sheet,
                OUTPUT / "InternalReview" / f"Step11-{phase_number}{reviewer}_{phase}_評価者{reviewer}_盲検100件.csv",
            )
        automatic_sample = automatic_full.loc[
            automatic_full["レビューID"].isin(sampled["レビューID"])
        ].sort_values("レビューID")
        reference_number = "14" if phase == "開発用" else "17"
        write_private_csv(
            automatic_sample,
            OUTPUT / "InternalReview" / "AfterReview_DoNotOpen" / f"Step11-{reference_number}_{phase}100件_自動回答_評価完了まで非表示.csv",
        )

    auto = pd.DataFrame(auto_rows)
    def detected(name: str, group: str) -> tuple[int, float]:
        row = auto[(auto["複数ラベル語彙検出"] == name) & (auto["群"] == group)].iloc[0]
        return int(row["検出件数"]), float(row["検出割合（％）"])
    fall_d, fall_p = detected("転倒・つまずき", "歯牙障害")
    road_d, road_p = detected("路面と接触", "歯牙障害")
    front_d, front_p = detected("前歯部の記載", "歯牙障害")
    write("Step11-09_原文検索補助レポート_自動未検証.md", f"""
# 通学中事例の原文検索補助レポート（自動・未検証）

## 位置付け

通学中590件の原文からキーワードを検索した。これは歯科医師レビューの検索補助であり、仮説の検証でも臨床的な確定分類でもない。複数ラベルが同時に付くため、件数の合計は590件を超え得る。

## 歯牙障害262件の複数ラベル語彙検出結果

- 転倒・つまずきの記載：{fall_d}件（{fall_p:.1f}%）
- 路面との接触を示唆する記載：{road_d}件（{road_p:.1f}%）
- 前歯部の記載：{front_d}件（{front_p:.1f}%）

## 現時点で言えること

転倒、路面接触、前歯部という語がそれぞれ検出された。これらが同じ事例で一続きの受傷連鎖を形成すること、記載順、直接外力を本集計は示さない。歯牙障害群の前歯・歯の記載は分類結果を表す可能性があり、原因の裏付けには使えない。

## 次の作業

1. 作成済みの開発用評価者A・Bファイルへ、2名が独立して入力する。
2. 不一致は第三者が調停し、判定規則を固定する。
3. 開発用と重複しない作成済みの最終評価用ファイルへ、規則を変えず入力する。
4. 最終評価標本で一致率、κ係数、分類性能と95%信頼区間を計算する。
""")
    mechanism_lines = []
    for _, row in mechanism_table.sort_values("全体件数", ascending=False).iterrows():
        mechanism_lines.append(f'- {row["主受傷機転"]}：{int(row["全体件数"]):,}件中{int(row["歯牙障害件数"]):,}件（{row["歯牙障害割合（％）"]:.1f}%）')
    legacy_report = legacy_internal / "Step11-15_自動レビュー暫定解析レポート_使用停止.md"
    legacy_report.write_text(f"""
# Step11 自動レビュー暫定解析レポート（使用停止）

## この資料の扱い

通学中590件をルールベースで自動分類した旧暫定結果である。歯科医師による人手判定前で、既知のルール上の問題があるため、以下の件数・割合・p値を研究結果、抄録、発表、論文へ使用しない。現行ルールは複数機転の順序を判定できない。

## 主受傷機転の自動暫定

{chr(10).join(mechanism_lines)}

旧ルールから計算されたカイ二乗検定のp値は{mechanism_p:.4g}であったが、分類誤りとルール設計の問題を考慮できないため解釈しない。

## 現時点の判断

自動回答と歯牙障害分類を伏せた原文を2名が独立判定する。ルール開発用と最終評価用の標本を分け、低確信度例だけでなく全分類と判定不能から無作為に抽出した例も確認する。

## 注意

`Step11-03_複数ラベル語彙検出集計_非識別.csv`だけを内部検索補助として利用できる。臨床的確定分類、時系列、因果関係は示さない。
""".strip() + "\n", encoding="utf-8")
    legacy_report.chmod(0o600)
    shutil.copy2(HERE / "README.md", OUTPUT / "README.md")
    logger.info("Step11完了 / 通学中=%d件 / 出力=%s", len(review), OUTPUT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="人手入力がない既存のStep11出力を再生成する")
    main(force=parser.parse_args().force)
