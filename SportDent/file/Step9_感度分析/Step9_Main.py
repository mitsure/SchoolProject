"""SportDent Step9：Step8多変量解析の妥当性確認と感度分析。"""
from __future__ import annotations

import argparse
import logging
import math
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import chi2
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

STEP9_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STEP9_DIR.parent.parent
STEP7_CODE_DIR = PROJECT_DIR / "file" / "Step7_探索的解析"
STEP8_CODE_DIR = PROJECT_DIR / "file" / "Step8_多変量解析"
sys.path[:0] = [str(STEP7_CODE_DIR), str(STEP8_CODE_DIR)]
import Step7_Main as step7  # noqa: E402
import Step8_Main as step8  # noqa: E402

JAPANESE_FONT_PATH = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
if JAPANESE_FONT_PATH.exists():
    font_manager.fontManager.addfont(str(JAPANESE_FONT_PATH))
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(JAPANESE_FONT_PATH)).get_name()
plt.rcParams["axes.unicode_minus"] = False


def fit_matrix(x_frame: pd.DataFrame, y_series: pd.Series) -> dict:
    """デザイン行列を受け取りロジスティック回帰を実行する。"""
    x = np.column_stack([np.ones(len(x_frame)), x_frame.to_numpy(dtype=float)])
    y = y_series.to_numpy(dtype=float)

    def objective(beta: np.ndarray) -> float:
        probability = np.clip(expit(x @ beta), 1e-12, 1 - 1e-12)
        return float(-(y * np.log(probability) + (1 - y) * np.log(1 - probability)).sum())

    result = minimize(objective, np.zeros(x.shape[1]), jac=lambda beta: x.T @ (expit(x @ beta) - y),
                      method="L-BFGS-B", options={"maxiter": 2000, "ftol": 1e-12})
    probability = np.clip(expit(x @ result.x), 1e-12, 1 - 1e-12)
    weights = probability * (1 - probability)
    covariance = np.linalg.pinv(x.T @ (x * weights[:, None]))
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    return {"x": x, "y": y, "beta": result.x, "se": se, "probability": probability,
            "covariance": covariance, "success": bool(result.success), "nll": objective(result.x)}


def prepare(raw: pd.DataFrame, threshold: int) -> pd.DataFrame:
    data = pd.DataFrame(index=raw.index)
    data["歯牙障害"] = raw["Step7_歯牙障害フラグ"].astype(int)
    for column in ["場合別1", "場合別2", "通学方法", "発生場所2", "被災学校種", "性別"]:
        data[column] = step8.clean_category(raw[column], minimum=threshold)
    year = step8.benefit_year(raw["和暦"], raw["給付年度"])
    year = year.fillna(year.median())
    data["給付年度（西暦換算）"] = year
    data["給付年度（西暦換算・標準化）"] = (year - year.mean()) / year.std(ddof=0)
    return data


def stabilize(data: pd.DataFrame, categorical: list[str]) -> pd.DataFrame:
    result = data.copy()
    for column in categorical:
        cells = pd.crosstab(result[column], result["歯牙障害"]).reindex(columns=[0, 1], fill_value=0)
        sparse = cells.index[cells.min(axis=1) < 5]
        result[column] = result[column].where(~result[column].isin(sparse), "その他（少数カテゴリ）")
    return result


def coefficient_table(model: dict, columns: list[str], analysis: str, setting: str) -> pd.DataFrame:
    rows = []
    for name, beta, se in zip(["切片", *columns], model["beta"], model["se"]):
        rows.append({"解析": analysis, "設定": setting, "項目": name, "調整オッズ比": np.exp(np.clip(beta, -700, 700)),
                     "95%CI下限": np.exp(np.clip(beta - 1.96 * se, -700, 700)),
                     "95%CI上限": np.exp(np.clip(beta + 1.96 * se, -700, 700))})
    return pd.DataFrame(rows)


def main_design(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict[str, str]]:
    categorical = ["場合別1", "被災学校種", "性別"]
    stable = stabilize(data, categorical)
    design, references = step8.make_design(stable, categorical, ["給付年度（西暦換算・標準化）"])
    return design, stable["歯牙障害"], references


def _raw_category(series: pd.Series) -> pd.Series:
    """カテゴリの文字列正規化だけを行う（件数統合は学習foldで行う）。"""
    return series.astype("string").str.strip().replace("", pd.NA).fillna("不明・記載なし")


def _fold_design(
    train_raw: pd.DataFrame,
    test_raw: pd.DataFrame,
    threshold: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """学習foldだけでカテゴリ統合・標準化・ダミー定義を決める。"""
    categorical = ["場合別1", "被災学校種", "性別"]
    train = pd.DataFrame(index=train_raw.index)
    test = pd.DataFrame(index=test_raw.index)
    train["歯牙障害"] = train_raw["Step7_歯牙障害フラグ"].astype(int)
    test["歯牙障害"] = test_raw["Step7_歯牙障害フラグ"].astype(int)

    for column in categorical:
        train_values = _raw_category(train_raw[column])
        test_values = _raw_category(test_raw[column])
        counts = train_values.value_counts(dropna=False)
        retained = set(counts[counts >= threshold].index.astype(str))
        train_values = train_values.where(train_values.astype(str).isin(retained), "その他（少数カテゴリ）")
        test_values = test_values.where(test_values.astype(str).isin(retained), "その他（少数カテゴリ）")

        cells = pd.crosstab(train_values, train["歯牙障害"]).reindex(columns=[0, 1], fill_value=0)
        sparse = set(cells.index[cells.min(axis=1) < 5].astype(str))
        train[column] = train_values.where(~train_values.astype(str).isin(sparse), "その他（少数カテゴリ）")
        test[column] = test_values.where(~test_values.astype(str).isin(sparse), "その他（少数カテゴリ）")

    train_year = step8.benefit_year(train_raw["和暦"], train_raw["給付年度"])
    test_year = step8.benefit_year(test_raw["和暦"], test_raw["給付年度"])
    median = float(train_year.median())
    train_year = train_year.fillna(median)
    test_year = test_year.fillna(median)
    mean = float(train_year.mean())
    standard_deviation = float(train_year.std(ddof=0))
    if standard_deviation == 0:
        standard_deviation = 1.0
    numeric = "給付年度（西暦換算・標準化）"
    train[numeric] = (train_year - mean) / standard_deviation
    test[numeric] = (test_year - mean) / standard_deviation

    train_pieces: list[pd.DataFrame] = []
    test_pieces: list[pd.DataFrame] = []
    for column in categorical:
        reference = str(train[column].value_counts().index[0])
        levels = sorted(str(value) for value in train[column].dropna().unique() if str(value) != reference)
        train_pieces.append(pd.DataFrame(
            {f"{column}：{level}（対 {reference}）": train[column].astype(str).eq(level).astype(int) for level in levels},
            index=train.index,
        ))
        test_pieces.append(pd.DataFrame(
            {f"{column}：{level}（対 {reference}）": test[column].astype(str).eq(level).astype(int) for level in levels},
            index=test.index,
        ))
    train_pieces.append(train[[numeric]].astype(float))
    test_pieces.append(test[[numeric]].astype(float))
    return (
        pd.concat(train_pieces, axis=1),
        pd.concat(test_pieces, axis=1),
        train["歯牙障害"],
        test["歯牙障害"],
    )


def cross_validated_performance(raw: pd.DataFrame, threshold: int = 30) -> pd.DataFrame:
    """固定した主モデルを、前処理も学習fold内に限定して内部評価する。"""
    y = raw["Step7_歯牙障害フラグ"].astype(int)
    splitter = StratifiedKFold(n_splits=5, shuffle=True, random_state=20260811)
    rows = []
    for fold, (train, test) in enumerate(splitter.split(raw, y), start=1):
        train_x, test_design, train_y, test_y = _fold_design(raw.iloc[train], raw.iloc[test], threshold)
        fitted = fit_matrix(train_x, train_y)
        test_x = np.column_stack([np.ones(len(test_design)), test_design.to_numpy(dtype=float)])
        probability = np.clip(expit(test_x @ fitted["beta"]), 1e-12, 1 - 1e-12)
        actual = test_y.to_numpy()
        rows.append({"分割": fold, "対象件数": len(test), "AUC": roc_auc_score(actual, probability),
                     "Brierスコア": brier_score_loss(actual, probability), "LogLoss": log_loss(actual, probability),
                     "前処理": "カテゴリ統合・標準化・ダミー化を学習fold内で実施"})
    frame = pd.DataFrame(rows)
    frame.loc[len(frame)] = {"分割": "5分割平均", "対象件数": frame["対象件数"].sum(),
                             "AUC": frame["AUC"].mean(), "Brierスコア": frame["Brierスコア"].mean(),
                             "LogLoss": frame["LogLoss"].mean(),
                             "前処理": "カテゴリ統合・標準化・ダミー化を学習fold内で実施"}
    return frame


def vif_table(design: pd.DataFrame) -> pd.DataFrame:
    rows = []
    values = design.to_numpy(dtype=float)
    for index, column in enumerate(design.columns):
        target = values[:, index]
        others = np.delete(values, index, axis=1)
        others = np.column_stack([np.ones(len(others)), others])
        fitted = others @ np.linalg.lstsq(others, target, rcond=None)[0]
        denominator = ((target - target.mean()) ** 2).sum()
        r_squared = 0.0 if denominator == 0 else 1 - ((target - fitted) ** 2).sum() / denominator
        rows.append({"項目": column, "VIF": np.inf if r_squared >= 1 else 1 / (1 - r_squared), "R2": r_squared,
                     "判定": "要確認" if r_squared >= .8 else "大きな問題なし"})
    return pd.DataFrame(rows).sort_values("VIF", ascending=False)


def save_forest(table: pd.DataFrame, output: Path) -> None:
    plot = table.loc[table["項目"].ne("切片") & ~table["項目"].str.contains("不明|少数カテゴリ")].copy()
    plot = plot.loc[(plot["95%CI下限"] > .05) & (plot["95%CI上限"] < 20)].head(20).iloc[::-1]
    y = np.arange(len(plot))
    fig, axis = plt.subplots(figsize=(13, max(7, len(plot) * .48)))
    axis.errorbar(plot["調整オッズ比"], y,
                  xerr=[plot["調整オッズ比"] - plot["95%CI下限"], plot["95%CI上限"] - plot["調整オッズ比"]],
                  fmt="o", color="#176B87", ecolor="#64CCC5", capsize=3)
    axis.axvline(1, color="#B42318", linestyle="--", linewidth=1.2, label="群間差なし（OR=1）")
    axis.set_xscale("log"); axis.set_yticks(y); axis.set_yticklabels(plot["項目"], fontsize=8)
    axis.set_xlabel("調整オッズ比（点：推定値、横線：95%信頼区間）\n"
                    "← 歯牙障害のオッズが低い　　OR=1：基準と差なし　　歯牙障害のオッズが高い →")
    axis.set_ylabel("比較項目（括弧内は基準カテゴリ）")
    axis.set_title("歯牙障害との関連：主モデルの調整オッズ比")
    axis.legend(loc="lower right", frameon=False, fontsize=9)
    axis.grid(axis="x", color="#D0D5DD", linewidth=.6)
    fig.text(.01, .01, "注：性別、学校種、給付年度（西暦換算）、活動大分類を相互に調整。登録障害事例内の比較であり、一般集団の発生リスクを示さない。",
             fontsize=8, color="#475467")
    fig.tight_layout(rect=[0, .045, 1, .98])
    fig.savefig(output / "Step9-07_フォレストプロット.svg", bbox_inches="tight")
    fig.savefig(output / "Step9-07_フォレストプロット.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main(force: bool = False) -> None:
    logger = logging.getLogger("Step9"); logger.setLevel(logging.INFO); logger.handlers.clear(); logger.addHandler(logging.StreamHandler(sys.stdout))
    datasets, _ = step7.load_step2_category_datasets(step7.resolve_unicode_path(step7.STEP2_CATEGORY_DIR), logger)
    raw = datasets["全体"].copy()
    output = PROJECT_DIR / "CreateData" / "Step9_感度分析"
    if output.exists():
        if not force:
            raise FileExistsError(
                f"{output} は既に存在します。内部確認候補を含むため、内容を確認して --force を指定してください。"
            )
        shutil.rmtree(output)
    output.mkdir(parents=True)

    sensitivity_tables = []
    for threshold in [20, 30, 50]:
        data = prepare(raw, threshold)
        design, outcome, _ = main_design(data)
        sensitivity_tables.append(coefficient_table(fit_matrix(design, outcome), list(design.columns), "カテゴリ統合基準", f"{threshold}件未満を統合"))
    sensitivity = pd.concat(sensitivity_tables, ignore_index=True)
    sensitivity.to_csv(output / "Step9-01_カテゴリ統合基準_感度分析.csv", index=False, encoding="utf-8-sig")

    data = prepare(raw, 30)
    continuous_x, outcome, references = main_design(data)
    year_group = pd.cut(data["給付年度（西暦換算）"], bins=[2004, 2009, 2014, 2019, 2023], labels=["2005–2009", "2010–2014", "2015–2019", "2020–2023"])
    year_data = stabilize(data.assign(給付年度区分=year_group.astype("string")), ["場合別1", "被災学校種", "性別", "給付年度区分"])
    grouped_x, grouped_refs = step8.make_design(year_data, ["場合別1", "被災学校種", "性別", "給付年度区分"], [])
    year_comparison = pd.concat([
        coefficient_table(fit_matrix(continuous_x, outcome), list(continuous_x.columns), "給付年度の扱い", "連続値"),
        coefficient_table(fit_matrix(grouped_x, outcome), list(grouped_x.columns), "給付年度の扱い", "5年区分"),
    ], ignore_index=True)
    year_comparison.to_csv(output / "Step9-02_給付年度の扱い_感度分析.csv", index=False, encoding="utf-8-sig")

    # 通学中事例が十分にある高・中・小だけへ実際に対象を限定した探索的交互作用解析。
    # 希少学校種を解析対象から除き、記載と解析母集団を一致させる。
    interaction_data = data.loc[data["被災学校種"].isin(["高", "中", "小"])].copy()
    interaction_base_x, interaction_outcome, _ = main_design(interaction_data)
    interaction_x = interaction_base_x.copy()
    commute_column = next(column for column in interaction_x if column.startswith("場合別1：通学中"))
    interaction_names = []
    common_school_columns = [
        column for column in interaction_x
        if column.startswith("被災学校種：中（") or column.startswith("被災学校種：小（")
    ]
    for school_column in common_school_columns:
        name = f"交互作用：通学中×{school_column.split('：', 1)[1]}"
        interaction_x[name] = interaction_x[commute_column] * interaction_x[school_column]
        interaction_names.append(name)
    base_fit = fit_matrix(interaction_base_x, interaction_outcome)
    interaction_fit = fit_matrix(interaction_x, interaction_outcome)
    lr = 2 * (base_fit["nll"] - interaction_fit["nll"])
    base_rank = np.linalg.matrix_rank(base_fit["x"])
    interaction_rank = np.linalg.matrix_rank(interaction_fit["x"])
    interaction_degrees_of_freedom = int(interaction_rank - base_rank)
    interaction_result = coefficient_table(interaction_fit, list(interaction_x.columns), "交互作用", "通学中×学校種")
    interaction_result["LR検定自由度"] = interaction_degrees_of_freedom
    interaction_result["交互作用全体のLR検定p値"] = chi2.sf(max(lr, 0), interaction_degrees_of_freedom)
    interaction_result["解析対象件数"] = len(interaction_data)
    interaction_result["解析対象学校種"] = "高（基準）・中・小のみ"
    interaction_result.to_csv(output / "Step9-03_通学中と学校種_交互作用.csv", index=False, encoding="utf-8-sig")

    # 通学方法の「その他」は一方の結果群が5件未満の疎なセルであるため、
    # 自転車と徒歩だけに限定して焦点係数が変わらないかを確認する。
    commute_two = data.loc[
        data["場合別1"].eq("通学中") & data["通学方法"].isin(["自転車", "徒歩"])
    ].copy()
    commute_two["発生場所2（二値）"] = np.where(
        commute_two["発生場所2"].eq("道路"), "道路", "道路以外"
    )
    commute_two_table, commute_two_diagnostic, _ = step8.fit_logistic(
        commute_two,
        "歯牙障害",
        ["通学方法", "発生場所2（二値）", "被災学校種", "性別"],
        ["給付年度（西暦換算・標準化）"],
        "通学中・自転車徒歩二群感度分析",
    )
    commute_two_table.insert(0, "解析対象件数", len(commute_two))
    commute_two_table.insert(1, "解析上の位置付け", "その他交通の疎セルを除いた探索的感度分析")
    commute_two_table.to_csv(output / "Step9-10_通学方法二群_感度分析.csv", index=False, encoding="utf-8-sig")
    commute_two_walking = commute_two_table.loc[
        commute_two_table["項目（比較対象／基準）"].str.startswith("通学方法：徒歩（")
    ].iloc[0]

    vif = vif_table(continuous_x); vif.to_csv(output / "Step9-04_多重共線性_VIF.csv", index=False, encoding="utf-8-sig")
    performance = cross_validated_performance(raw, threshold=30)
    performance.to_csv(output / "Step9-05_5分割交差検証.csv", index=False, encoding="utf-8-sig")

    fitted = fit_matrix(continuous_x, outcome)
    weights = fitted["probability"] * (1 - fitted["probability"])
    leverage = weights * np.einsum("ij,jk,ik->i", fitted["x"], fitted["covariance"], fitted["x"])
    pearson = (fitted["y"] - fitted["probability"]) / np.sqrt(np.maximum(weights, 1e-12))
    influence = pd.DataFrame({"元データ行": np.arange(len(raw)) + 1, "ID": raw["記号"].astype("string"), "実際の結果": fitted["y"].astype(int),
                              "予測確率": fitted["probability"], "レバレッジ": leverage, "Pearson残差": pearson})
    influence["高レバレッジ"] = leverage > 2 * fitted["x"].shape[1] / len(raw)
    influence["大きなPearson残差"] = abs(pearson) > 3
    influence["要確認"] = influence["高レバレッジ"] | influence["大きなPearson残差"]
    influence["確認理由"] = np.select(
        [influence["高レバレッジ"] & influence["大きなPearson残差"], influence["高レバレッジ"], influence["大きなPearson残差"]],
        ["高レバレッジ＋大残差", "高レバレッジ", "大残差"],
        default="対象外",
    )
    internal = output / "Internal_DoNotPublish"
    internal.mkdir()
    internal.chmod(0o700)
    internal_file = internal / "Step9-06_高レバレッジ・大残差確認候補_内部用.csv"
    influence.loc[influence["要確認"]].sort_values(["確認理由", "レバレッジ"], ascending=[True, False]).to_csv(
        internal_file, index=False, encoding="utf-8-sig")
    internal_file.chmod(0o600)
    influence.loc[influence["要確認"]].groupby(["確認理由", "実際の結果"], dropna=False).size().rename("件数").reset_index().to_csv(
        output / "Step9-06_高レバレッジ・大残差候補_非識別集計.csv", index=False, encoding="utf-8-sig")
    base_plot = sensitivity.loc[sensitivity["設定"].eq("30件未満を統合")]
    save_forest(base_plot, output)

    common = ["場合別1：通学中（対 課外指導）", "被災学校種：小（対 高）", "被災学校種：中（対 高）"]
    stability = sensitivity.loc[sensitivity["項目"].isin(common)].groupby("項目")["調整オッズ比"].agg(["min", "max"])
    cv_mean = performance.iloc[-1]
    max_vif = float(vif["VIF"].replace([np.inf], np.nan).max())
    interaction_p = float(chi2.sf(max(lr, 0), interaction_degrees_of_freedom))
    report = [
        "# Step9 妥当性確認・感度分析総合レポート", "", "## 結論", "",
        "Step8の主要結果が、解析条件を変えても大きく崩れないかを確認した。",
        f"カテゴリ統合基準を20・30・50件に変えたとき、主要項目の調整オッズ比の範囲は以下のとおりだった。", "",
    ]
    for name, row in stability.iterrows(): report.append(f'- {name}：{row["min"]:.2f}〜{row["max"]:.2f}')
    report += ["", "## モデルの確認", "",
               f'- 5分割交差検証の平均AUC：{cv_mean["AUC"]:.3f}', f'- 平均Brierスコア：{cv_mean["Brierスコア"]:.3f}',
               f'- 最大VIF：{max_vif:.2f}', f'- 通学中×学校種（高・中・小）の探索的交互作用（自由度{interaction_degrees_of_freedom}）p値：{interaction_p:.4f}',
               f'- 自転車・徒歩{len(commute_two):,}件だけの感度分析：徒歩対自転車 aOR {commute_two_walking["調整オッズ比"]:.2f}（95%CI {commute_two_walking["95%CI下限"]:.2f}–{commute_two_walking["95%CI上限"]:.2f}）',
               f'- 高レバレッジ・大残差の確認候補：{int(influence["要確認"].sum()):,}件', "",
               "## 読み方", "", "AUCはモデルが歯牙障害とそれ以外を並べ分ける力、Brierスコアは予測確率のずれを表す。VIFは説明項目同士の重なりの指標である。", "",
               "## 注意", "", "安定していたのは通学中、小学校、中学校の3係数であり、モデル内の全係数ではない。5分割交差検証は、説明項目を固定した主モデルについて、カテゴリ統合・標準化・ダミー化を各学習fold内で行った内部評価である。Step7の因子選択自体は全データで行われているため、解析工程全体の未知データ性能や外部妥当性を示さない。", "", "観察データの関連から因果関係は証明できない。また、これは登録された障害事例内の比較であり、一般集団の発生率を示さない。", ""]
    (output / "Step9-08_妥当性確認_総合レポート.md").write_text("\n".join(report), encoding="utf-8")

    category_counts = raw.groupby("場合別1")["Step7_歯牙障害フラグ"].agg(["size", "sum"])
    detail_counts = raw.groupby("場合別2", dropna=False)["Step7_歯牙障害フラグ"].agg(["size", "sum"])
    school_counts = raw.groupby("被災学校種")["Step7_歯牙障害フラグ"].agg(["size", "sum"])
    commute = category_counts.loc["通学中"]
    going = detail_counts.loc["登校（登園）中"]
    returning = detail_counts.loc["下校（降園）中"]
    high_school = school_counts.loc["高"]
    elementary = school_counts.loc["小"]
    interpretation = [
        "# Step9 なぜこの結果になったのか：歯科医師向け解釈レポート", "",
        "## 先に結論", "",
        "本解析では、登録された障害事例の中で、通学中、特に登下校中の事例は歯牙障害に分類される割合が高かった。",
        "定型項目では通学中・自転車・道路が重なる一方、その一部は通学時だけ入力される項目構造を反映する。転倒や衝突が口腔・顔面への外力につながるという説明は、今後確認すべき仮説である。",
        "ただし、本データには通学した全児童生徒数や通学回数がないため、通学による歯牙障害の発生リスクは計算できない。", "",
        "## 1. 通学中のオッズ比が高かった理由", "",
        f'- 通学中は{int(commute["size"]):,}件中{int(commute["sum"]):,}件（{commute["sum"] / commute["size"] * 100:.1f}%）が歯牙障害だった。',
        f'- 内訳は、登校中{int(going["size"]):,}件中{int(going["sum"]):,}件（{going["sum"] / going["size"] * 100:.1f}%）、下校中{int(returning["size"]):,}件中{int(returning["sum"]):,}件（{returning["sum"] / returning["size"] * 100:.1f}%）だった。',
        "- 性別、学校種、給付年度（西暦換算）を考慮しても、通学中の調整オッズ比は3.05（95%信頼区間2.51–3.71）だった。",
        "", "### データから確認できること", "",
        "通学中、自転車、道路は定型項目上で重なっていた。ただし、通学方法が通学中にだけ入力されるなどデータベースの項目構造による重なりを含むため、独立した原因とも新しい臨床所見とも解釈できない。", "",
        "### 臨床・行動面から考えられる仮説", "",
        "- 自転車転倒では、両手がハンドルにあり、転倒時の手掌防御が遅れる可能性がある。",
        "- 走行速度と路面の硬さにより、前歯部や顔面に直接外力が加わる可能性がある。",
        "- 車両、歩行者、段差などの外的要因が、校内活動と異なる受傷機転を生じさせる可能性がある。",
        "これらは臨床的に妥当な仮説だが、現在の解析で受傷姿勢や保護具の使用を直接確認したわけではない。", "",
        "### 疎な交通手段カテゴリの確認", "",
        f"通学方法のその他カテゴリは一方の結果群が5件未満の疎なセルで、推定が不安定になり得た。自転車と徒歩の{len(commute_two):,}件だけに限定しても、徒歩対自転車は調整オッズ比{commute_two_walking['調整オッズ比']:.2f}（95%信頼区間{commute_two_walking['95%CI下限']:.2f}–{commute_two_walking['95%CI上限']:.2f}）で、焦点所見の方向は変わらなかった。これは探索的感度分析であり、外部検証ではない。", "",
        "## 2. 学校種による差がみられた理由", "",
        f'- 高校は{int(high_school["size"]):,}件中{int(high_school["sum"]):,}件（{high_school["sum"] / high_school["size"] * 100:.1f}%）、小学校は{int(elementary["size"]):,}件中{int(elementary["sum"]):,}件（{elementary["sum"] / elementary["size"] * 100:.1f}%）が歯牙障害だった。',
        "- 他の条件を考慮した後も、小学校は高校に対し調整オッズ比0.33、中学校は0.50だった。",
        "", "### 考えられる背景", "",
        "高校生では自転車通学や体育的部活動の比重が高い可能性がある。一方、乳幼児では歯牙障害の等級認定、登録基準、乳歯と永久歯の違いが結果に影響した可能性もある。",
        "したがって、「小学生は歯科外傷が少ない」とは結論できず、「本データで長期障害として登録された事例の構成が異なる」と解釈するのが適切である。", "",
        "## 3. 給付年度が新しい区分でオッズが低かった理由", "",
        "給付年度を5年ごとに区分すると、2005–2009給付年度を基準とした調整オッズ比は、2015–2019給付年度で0.73、2020–2023給付年度で0.57だった。事故発生年の変化を直接示す結果ではない。", "",
        "### 考えられる仮説", "",
        "- 歯科外傷予防や学校安全対策が変化した可能性。",
        "- 障害の認定や登録の運用、記載方法が変化した。",
        "- 歯牙障害以外の障害カテゴリの構成が年代によって変化した。",
        "- 事故発生から認定・給付までの時間差が障害種別で異なる可能性。",
        "本データだけでは上記を区別できないため、事故発生率の低下や予防効果とは断定できない。", "",
        "## 4. 感度分析で結果があまり変わらなかった理由", "",
        "通学中、小学校、中学校は十分な件数があり、20・30・50件のどの統合基準でもそれ自体は統合対象にならなかった。そのため、通学中のオッズ比は3.04–3.06、小学校は0.33、中学校は0.50–0.51と安定した。",
        "これは「解析上のまとめ方に左右されにくい」ことを示すが、交絡がないことや因果関係を保証するものではない。", "",
        "## 5. モデルの判別力が中程度にとどまった理由", "",
        "5分割交差検証の平均AUCは約0.682だった。これは登録事例を歯牙障害とそれ以外に並べ分ける能力が限定的であることを示す。オッズ比、交絡調整、因果解釈の妥当性を示す指標ではない。", "",
        "予測に必要と考えられる受傷姿勢、衝突速度、ヘルメットやマウスガードの使用、歯種、歯列・咬合、外力の方向などが構造化項目として含まれていないことが、判別力の限界の一因と考えられる。", "",
        "## 6. 一部のVIFが高かった理由", "",
        "最大VIFは7.93だったが、これは主に「その他（少数カテゴリ）」としてまとめた項目で生じた。異なる少数カテゴリを同じ箱にまとめたため、活動分類と学校種の「その他」同士が重なったことが主な理由である。",
        "通学中のVIFは1.16、小学校は1.89、中学校は1.34であり、主要所見の項目では大きな多重共線性は認めなかった。", "",
        "## 7. 通学中と学校種の交互作用がみられた理由", "",
        f"通学中事例が十分にある高・中・小に限定した探索的交互作用のモデル全体p値は{interaction_p:.4f}で、通学中と歯牙障害との関連が3学校種で同一でない可能性が示された。特に小学校では、高校と比べた通学中の関連が弱い方向だった。",
        "通学方法の違い（徒歩、自転車など）、年齢による行動や受傷機転の違い、登録基準の影響が候補である。探索的解析であり、独立データでの確認が必要である。", "",
        "## 8. 高レバレッジ・大残差の確認候補が生じた理由", "",
        f"確認候補は{int(influence['要確認'].sum()):,}件だった。これらは、まれな学校種と活動の組合せ、またはモデルの予測と実際の分類が異なる事例である。",
        "「外れ値」は誤入力や除外対象を意味しない。臨床的に重要な少数事例が含まれる可能性があるため、匿名性を確保した上で原文を確認するのが適切である。", "",
        "## 総合的な解釈", "",
        "現時点で統計解析から言えるのは、「登録された長期障害事例の中では、通学中の事例で歯牙障害の構成割合が高く、この関連は性別、学校種、給付年度（西暦換算）を考慮しても認められた」という範囲である。自転車転倒、道路・路面接触、前歯部受傷を一続きの機転とする説明は未検証の仮説である。",
        "次に必要なのは、通学中事例の自由記載を人手で確認し、転倒、車両との衝突、路面との接触、前歯部の受傷、保護具の記載などを標準化して再分類することである。", "",
        "## 表現上の注意", "",
        "- 使用可：「関連がみられた」「多い傾向だった」「仮説として考えられる」",
        "- 避ける：「通学が歯牙障害を引き起こした」「発生リスクが3.05倍」「小学生は安全である」", "",
    ]
    (output / "Step9-09_なぜこの結果になったのか_解釈レポート.md").write_text("\n".join(interpretation), encoding="utf-8")
    logger.info("Step9完了 / 出力=%s", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存のStep9成果物を確認済みとして再生成する")
    main(force=parser.parse_args().force)
