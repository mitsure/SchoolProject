"""SportDent Step8：Step7の上位関連因子について調整後関連を探索する多変量解析。"""
from __future__ import annotations

import argparse
import logging
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import roc_auc_score

STEP8_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STEP8_DIR.parent.parent
STEP7_CODE_DIR = PROJECT_DIR / "file" / "Step7_探索的解析"
sys.path.insert(0, str(STEP7_CODE_DIR))
import Step7_Main as step7  # noqa: E402

MIN_CATEGORY_COUNT = 30


def benefit_year(era: pd.Series, year: pd.Series) -> pd.Series:
    """和暦と給付年度から西暦相当の給付年度を作る。"""
    numeric = pd.to_numeric(year, errors="coerce")
    era_text = era.astype("string").str.strip()
    converted = pd.Series(np.nan, index=year.index, dtype=float)
    converted.loc[era_text.eq("平成")] = numeric.loc[era_text.eq("平成")] + 1988
    converted.loc[era_text.eq("令和")] = numeric.loc[era_text.eq("令和")] + 2018
    return converted


def clean_category(series: pd.Series, minimum: int = MIN_CATEGORY_COUNT) -> pd.Series:
    """空欄・欠損を明示し、少数カテゴリは過度適合防止のためまとめる。"""
    cleaned = series.astype("string").str.strip().replace("", pd.NA).fillna("不明・記載なし")
    counts = cleaned.value_counts(dropna=False)
    rare = counts[counts < minimum].index
    return cleaned.where(~cleaned.isin(rare), "その他（少数カテゴリ）")


def suppress_public_outcome_cells(frame: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """1〜4件セルと、差し引きで復元できる単独抑制を公開表で伏せる。"""
    public = frame.copy()
    dental = pd.to_numeric(public["歯牙障害件数"])
    non_dental = pd.to_numeric(public["全体件数"]) - dental
    hidden = dental.between(1, 4) | non_dental.between(1, 4)
    for _, indices in public.groupby(group_column, sort=False).groups.items():
        group_indices = list(indices)
        primary = [index for index in group_indices if bool(hidden.loc[index])]
        if len(primary) != 1 or len(group_indices) < 2:
            continue
        candidates = [index for index in group_indices if index not in primary]
        preferred = [index for index in candidates if "不明" in str(public.loc[index, "カテゴリ"])]
        if not preferred:
            preferred = [index for index in candidates if "その他（少数カテゴリ）" in str(public.loc[index, "カテゴリ"])]
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


def make_design(
    data: pd.DataFrame,
    categorical: list[str],
    numeric: list[str],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """最頻値を基準とするダミー変数を作る。"""
    pieces: list[pd.DataFrame] = []
    references: dict[str, str] = {}
    for column in categorical:
        values = data[column].astype("string")
        reference = str(values.value_counts().index[0])
        references[column] = reference
        levels = sorted(str(value) for value in values.dropna().unique() if str(value) != reference)
        pieces.append(pd.DataFrame(
            {f"{column}：{level}（対 {reference}）": values.eq(level).astype(int) for level in levels},
            index=data.index,
        ))
    if numeric:
        pieces.append(data[numeric].astype(float))
    return pd.concat(pieces, axis=1), references


def fit_logistic(
    data: pd.DataFrame,
    outcome: str,
    categorical: list[str],
    numeric: list[str],
    model_name: str,
) -> tuple[pd.DataFrame, dict, dict[str, str]]:
    """最尤法によるロジスティック回帰とWald型95%信頼区間を計算する。"""
    model_data = data.copy()
    # 片方の結果が極端に少ないカテゴリは完全分離を起こすため、
    # モデルごとに「その他（少数カテゴリ）」へ統合する。
    for column in categorical:
        cells = pd.crosstab(model_data[column], model_data[outcome]).reindex(columns=[0, 1], fill_value=0)
        sparse_levels = cells.index[cells.min(axis=1) < 5]
        model_data[column] = model_data[column].where(
            ~model_data[column].isin(sparse_levels), "その他（少数カテゴリ）"
        )
    design, references = make_design(model_data, categorical, numeric)
    x = np.column_stack([np.ones(len(data)), design.to_numpy(dtype=float)])
    y = model_data[outcome].to_numpy(dtype=float)

    def objective(beta: np.ndarray) -> float:
        probability = np.clip(expit(x @ beta), 1e-12, 1 - 1e-12)
        return float(-(y * np.log(probability) + (1 - y) * np.log(1 - probability)).sum())

    def gradient(beta: np.ndarray) -> np.ndarray:
        return x.T @ (expit(x @ beta) - y)

    result = minimize(objective, np.zeros(x.shape[1]), jac=gradient, method="L-BFGS-B",
                      options={"gtol": 1e-7, "ftol": 1e-12, "maxiter": 2000})
    beta = result.x
    probability = expit(x @ beta)
    weights = probability * (1 - probability)
    covariance = np.linalg.pinv(x.T @ (x * weights[:, None]))
    standard_error = np.sqrt(np.maximum(np.diag(covariance), 0))
    unstable = bool(
        (not np.isfinite(beta).all())
        or (not np.isfinite(standard_error).all())
        or (np.abs(beta).max() > 10)
        or (standard_error.max() > 10)
    )
    rows = []
    for name, coefficient, se in zip(["切片", *design.columns], beta, standard_error):
        rows.append({
            "モデル": model_name, "項目（比較対象／基準）": name, "回帰係数": coefficient,
            "調整オッズ比": float(np.exp(np.clip(coefficient, -700, 700))),
            "95%CI下限": float(np.exp(np.clip(coefficient - 1.96 * se, -700, 700))),
            "95%CI上限": float(np.exp(np.clip(coefficient + 1.96 * se, -700, 700))), "標準誤差": se,
        })
    diagnostics = {
        "モデル": model_name, "対象件数": len(data), "歯牙障害件数": int(y.sum()),
        "説明変数数（ダミー化後）": design.shape[1], "収束": bool(result.success),
        "有限推定の警告": "要確認" if unstable else "なし",
        "最適化メッセージ": str(result.message), "AUC（同一データ内）": roc_auc_score(y, probability),
    }
    return pd.DataFrame(rows), diagnostics, references


def main(force: bool = False) -> None:
    logger = logging.getLogger("Step8")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler(sys.stdout))

    source = step7.resolve_unicode_path(step7.STEP2_CATEGORY_DIR)
    datasets, _ = step7.load_step2_category_datasets(source, logger)
    raw = datasets["全体"].copy()
    output = PROJECT_DIR / "CreateData" / "Step8_多変量解析"
    if output.exists():
        if not force:
            raise FileExistsError(
                f"{output} は既に存在します。内容を確認して再生成する場合だけ --force を指定してください。"
            )
        shutil.rmtree(output)
    output.mkdir(parents=True)

    data = pd.DataFrame(index=raw.index)
    data["歯牙障害"] = raw["Step7_歯牙障害フラグ"].astype(int)
    for column in ["場合別2", "通学方法", "被災学校種", "場合別1", "発生場所2", "性別"]:
        data[column] = clean_category(raw[column])
    year = benefit_year(raw["和暦"], raw["給付年度"])
    year_missing = int(year.isna().sum())
    year = year.fillna(year.median())
    year_standard_deviation = float(year.std(ddof=0))
    data["給付年度（西暦換算・標準化）"] = (year - year.mean()) / year_standard_deviation

    ranking_path = PROJECT_DIR / "CreateData" / "Step7" / "全体" / "Summary" / "Step7-48_重要因子ランキング.csv"
    ranking = pd.read_csv(ranking_path, encoding="utf-8-sig")
    selected = ranking.head(5)[["順位", "因子", "総合重要度スコア", "解釈上の注意"]].copy()
    selected["Step8での扱い"] = selected["因子"].map({
        "場合別2": "詳細活動モデル", "通学方法": "通学中サブグループモデル",
        "被災学校種": "主・詳細活動・通学中モデル", "場合別1": "主モデル",
        "発生場所2": "通学中サブグループモデル",
    })
    selected.to_csv(output / "Step8-00_Step7上位因子と解析対応.csv", index=False, encoding="utf-8-sig")

    distributions = []
    for column in selected["因子"]:
        table = data.groupby(column, dropna=False)["歯牙障害"].agg(全体件数="size", 歯牙障害件数="sum").reset_index()
        table.insert(0, "因子", column)
        table = table.rename(columns={column: "カテゴリ"})
        table["歯牙障害割合（％）"] = table["歯牙障害件数"] / table["全体件数"] * 100
        distributions.append(table)
    distribution_table = pd.concat(distributions, ignore_index=True)
    suppress_public_outcome_cells(distribution_table, "因子").to_csv(
        output / "Step8-01_上位5因子カテゴリ別集計.csv", index=False, encoding="utf-8-sig")

    # カテゴリ間の強い重なりを検知するため、ワンホット指標間の最大相関を出力する。
    encoded = pd.get_dummies(data[selected["因子"].tolist()], prefix_sep="：", dtype=int)
    correlations = encoded.corr()
    pairs = []
    columns = list(encoded.columns)
    for i, left in enumerate(columns):
        for right in columns[i + 1:]:
            left_factor, right_factor = left.split("：", 1)[0], right.split("：", 1)[0]
            if left_factor != right_factor:
                pairs.append({"指標1": left, "指標2": right, "相関係数": correlations.loc[left, right], "絶対値": abs(correlations.loc[left, right])})
    pd.DataFrame(pairs).sort_values("絶対値", ascending=False).head(100).to_csv(
        output / "Step8-02_上位因子の重なり.csv", index=False, encoding="utf-8-sig")

    # 通学中の発生場所2には、細分類のままでは歯牙障害が0件の水準があり、
    # 通常の最尤ロジスティック回帰で完全分離を起こす。通学中モデルでは
    # 解析前に臨床的に解釈できる「道路／道路以外」の二値へ固定する。
    commute_data = data.loc[data["場合別1"].eq("通学中")].copy()
    commute_data["発生場所2（二値）"] = np.where(
        commute_data["発生場所2"].eq("道路"), "道路", "道路以外"
    )

    specs = [
        ("主モデル（大分類）", data, ["場合別1", "被災学校種", "性別"]),
        ("詳細活動モデル", data, ["場合別2", "被災学校種", "性別"]),
        ("通学中サブグループ", commute_data, ["通学方法", "発生場所2（二値）", "被災学校種", "性別"]),
    ]
    tables, diagnostics, model_notes = [], [], []
    numeric = ["給付年度（西暦換算・標準化）"]
    for name, subset, categorical in specs:
        table, diagnostic, references = fit_logistic(subset, "歯牙障害", categorical, numeric, name)
        tables.append(table)
        diagnostics.append(diagnostic)
        model_notes.append({
            "モデル": name, "対象": "通学中の事例のみ" if "通学中" in name else "全事例",
            "同時に考慮した項目": " / ".join([*categorical, "給付年度（西暦換算）"]),
            "基準カテゴリ": " / ".join(f"{key}={value}" for key, value in references.items()),
            "給付年度の1標準偏差（年）": year_standard_deviation,
        })
    coefficients = pd.concat(tables, ignore_index=True)
    coefficients.to_csv(output / "Step8-03_調整オッズ比.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(diagnostics).to_csv(output / "Step8-04_モデル診断.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(model_notes).to_csv(output / "Step8-06_モデル設計と基準カテゴリ.csv", index=False, encoding="utf-8-sig")

    notable = coefficients.loc[
        coefficients["項目（比較対象／基準）"].ne("切片")
        & ~coefficients["項目（比較対象／基準）"].str.contains("不明・記載なし|その他（少数カテゴリ）", regex=True)
        & ((coefficients["95%CI下限"] > 1) | (coefficients["95%CI上限"] < 1))
    ].assign(基準からの差=lambda frame: abs(np.log(frame["調整オッズ比"]))).sort_values("基準からの差", ascending=False)
    lines = [
        "# Step8 多変量解析 歯科医師向け結果要約", "", f"対象：全{len(data):,}件（歯牙障害{int(data['歯牙障害'].sum()):,}件）",
        f"給付年度を西暦換算できず中央値で補った件数：{year_missing}件", "",
        "## 何を調べたか", "",
        "Step7で上位となった「場合別2」「通学方法」「被災学校種」「場合別1」「発生場所2」について、同じデータ内で調整後の関連を探索しました。",
        "項目同士の重なりを考慮し、大まかな活動、詳細な活動、通学中の3つのモデルに分けました。",
        "性別、学校種、給付年度（西暦換算）など、各モデル内の他の条件を同時に考慮しています。", "",
        "## 結果を読むときの要点", "",
        "調整オッズ比は、性別、学校種、給付年度（西暦換算）などを考慮した上で、各カテゴリを基準カテゴリと比較した値です。1より大きいと歯牙障害のオッズが高く、1より小さいと低い傾向を示します。",
        "主な数値は以下のとおりです（推定幅が1をまたがない結果から、基準との差が大きい順）。", "",
    ]
    for _, row in notable.head(12).iterrows():
        lines.append(f'- {row["モデル"]}：{row["項目（比較対象／基準）"]} — 調整オッズ比{row["調整オッズ比"]:.2f}（推定幅{row["95%CI下限"]:.2f}–{row["95%CI上限"]:.2f}）')
    lines.extend([
        "", "## 注意", "",
        "これは歯牙障害とそれ以外の登録事例を比べた結果です。一般の児童生徒に歯牙障害が発生する確率や、原因を示すものではありません。",
        "「場合別1」と「場合別2」は大分類と詳細分類の関係にあるため、同じモデルへ重複投入していません。",
        "通学方法は通学中以外で記載されないことが多いため、通学中の事例に限って比較しています。",
        "通学中モデルの発生場所は、完全分離を避けるため解析前に「道路／道路以外」の二値へまとめています。",
        "ここで用いた年は事故発生年ではなく、データベースの給付年度を西暦換算した値です。",
        f"給付年度（標準化）のオッズ比は1標準偏差、すなわち約{year_standard_deviation:.2f}年の差に対する値です。1年当たりの値ではありません。",
        "Step7の因子選択と同じ事例を用いているため、独立データによる再現確認ではありません。",
        f"少数カテゴリは1カテゴリ{MIN_CATEGORY_COUNT}件未満、または歯牙障害・それ以外のどちらかが5件未満の場合に統合しました。",
    ])
    (output / "Step8-05_一般向け結果要約.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Step8完了 / 出力=%s", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存のStep8成果物を確認済みとして再生成する")
    main(force=parser.parse_args().force)
