"""SportDent Step10：Step7〜9を反映した統合論文原稿を生成する。"""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
CREATE = PROJECT / "CreateData"
OUTPUT = CREATE / "Step10_統合論文原稿"


def secure_private_tree(path: Path) -> None:
    """再生成前バックアップを所有者だけが読める権限にする。"""
    path.chmod(0o700)
    for child in path.rglob("*"):
        child.chmod(0o700 if child.is_dir() else 0o600)


def write(name: str, text: str) -> None:
    (OUTPUT / name).write_text(text.strip() + "\n", encoding="utf-8")


def main(force: bool = False) -> None:
    step8 = CREATE / "Step8_多変量解析"
    step9 = CREATE / "Step9_感度分析"
    required_inputs = [
        step8 / "Step8-03_調整オッズ比.csv",
        step8 / "Step8-04_モデル診断.csv",
        step8 / "Step8-06_モデル設計と基準カテゴリ.csv",
        step9 / "Step9-01_カテゴリ統合基準_感度分析.csv",
        step9 / "Step9-03_通学中と学校種_交互作用.csv",
        step9 / "Step9-05_5分割交差検証.csv",
        step9 / "Step9-07_フォレストプロット.png",
        step9 / "Step9-07_フォレストプロット.svg",
        step9 / "Step9-10_通学方法二群_感度分析.csv",
    ]
    missing = [path for path in required_inputs if not path.exists()]
    if missing:
        raise FileNotFoundError("Step10の必須入力が不足しています：" + " / ".join(str(path) for path in missing))
    if OUTPUT.exists():
        if not force:
            raise FileExistsError(
                f"{OUTPUT} は既に存在します。研究者の追記を消さないため停止しました。"
                "内容を確認して再生成する場合だけ --force を指定してください。"
            )
        backup_root = CREATE / "RegenerationBackups"
        backup_root.mkdir(exist_ok=True)
        backup_root.chmod(0o700)
        backup_readme = backup_root / "README.md"
        backup_readme.write_text(
            "# 再生成前バックアップ\n\n自動上書きの直前に保存した復旧用コピーです。現行結果・投稿資料として使用しないでください。\n",
            encoding="utf-8",
        )
        backup_readme.chmod(0o600)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = backup_root / f"Step10_統合論文原稿_{timestamp}"
        shutil.copytree(OUTPUT, backup_path)
        secure_private_tree(backup_path)
        shutil.rmtree(OUTPUT)
    (OUTPUT / "Figure").mkdir(parents=True)
    (OUTPUT / "Table").mkdir(parents=True)

    coefficients = pd.read_csv(step8 / "Step8-03_調整オッズ比.csv", encoding="utf-8-sig")
    diagnostics = pd.read_csv(step8 / "Step8-04_モデル診断.csv", encoding="utf-8-sig")
    performance = pd.read_csv(step9 / "Step9-05_5分割交差検証.csv", encoding="utf-8-sig")
    sensitivity = pd.read_csv(step9 / "Step9-01_カテゴリ統合基準_感度分析.csv", encoding="utf-8-sig")
    interaction = pd.read_csv(step9 / "Step9-03_通学中と学校種_交互作用.csv", encoding="utf-8-sig")
    commute_sensitivity = pd.read_csv(step9 / "Step9-10_通学方法二群_感度分析.csv", encoding="utf-8-sig")
    model_design = pd.read_csv(step8 / "Step8-06_モデル設計と基準カテゴリ.csv", encoding="utf-8-sig")

    publish = coefficients.loc[
        coefficients["項目（比較対象／基準）"].ne("切片")
        & ~coefficients["項目（比較対象／基準）"].str.contains("不明|少数カテゴリ")
    ].copy()
    publish["調整オッズ比（95%信頼区間）"] = publish.apply(
        lambda row: f'{row["調整オッズ比"]:.2f} ({row["95%CI下限"]:.2f}–{row["95%CI上限"]:.2f})', axis=1)
    publish[["モデル", "項目（比較対象／基準）", "調整オッズ比（95%信頼区間）"]].to_csv(
        OUTPUT / "Table" / "Table10-1_多変量解析主要結果.csv", index=False, encoding="utf-8-sig")
    diagnostics.to_csv(OUTPUT / "Table" / "Table10-2_モデル診断.csv", index=False, encoding="utf-8-sig")
    performance.to_csv(OUTPUT / "Table" / "Table10-3_交差検証.csv", index=False, encoding="utf-8-sig")
    commute_sensitivity.to_csv(OUTPUT / "Table" / "Table10-4_通学方法二群感度分析.csv", index=False, encoding="utf-8-sig")
    shutil.copy2(step9 / "Step9-07_フォレストプロット.png", OUTPUT / "Figure" / "Figure10-1_調整オッズ比.png")
    shutil.copy2(step9 / "Step9-07_フォレストプロット.svg", OUTPUT / "Figure" / "Figure10-1_調整オッズ比.svg")

    cv = performance.iloc[-1]
    models = diagnostics.set_index("モデル")
    walking = coefficients.loc[
        coefficients["モデル"].eq("通学中サブグループ")
        & coefficients["項目（比較対象／基準）"].str.startswith("通学方法：徒歩（")
    ].iloc[0]
    interaction_p = float(interaction["交互作用全体のLR検定p値"].iloc[0])
    interaction_df = int(interaction["LR検定自由度"].iloc[0])
    walking_sensitivity = commute_sensitivity.loc[
        commute_sensitivity["項目（比較対象／基準）"].str.startswith("通学方法：徒歩（")
    ].iloc[0]
    year_standard_deviation = float(model_design["給付年度の1標準偏差（年）"].iloc[0])
    methods = f"""
# Methods

## 研究デザインと対象

学校管理下で発生した長期障害の登録事例を用いた後ろ向き観察研究とした。データベースの傷害分類から抽出・確認した歯牙障害1,583件と歯牙障害以外6,099件の計7,682件を対象とした。記述解析では全事例および歯牙障害事例を集計し、群間比較では歯牙障害と歯牙障害以外を互いに重複しない群として扱った。

## 候補因子の探索

同じ7,682件を用いた先行の探索的解析で、定型項目の件数・割合と群間差を確認し、場合別2、通学方法、被災学校種、場合別1、発生場所2を多変量解析の候補とした。自由記述のテキスト解析とJaccard解析は別の仮説生成研究として扱い、本回帰原稿の結果には含めなかった。

## 多変量解析

歯牙障害の有無を目的変数とし、探索的ロジスティック回帰を行った。同じ7,682件を用いた先行の探索的解析で上位となった場合別2、通学方法、被災学校種、場合別1、発生場所2を候補とした。場合別1と場合別2は階層関係にあるため同時投入せず、主モデル、詳細活動モデル、通学中サブグループの3モデルを構築した。通学方法は通学中以外で構造的に未記載となるため、通学中590件に限定して評価した。通学中モデルの発生場所2は、完全分離を避けるため解析前に「道路／道路以外」の二値へ統合した。

性別、学校種、給付年度（西暦換算）等を同時に考慮した。和暦と給付年度から西暦相当の給付年度を作成し、標準化した。標準化後の1単位は約{year_standard_deviation:.2f}年であり、給付年度を事故発生年とはみなさなかった。欠損カテゴリは「不明・記載なし」として扱い、1カテゴリ30件未満、または歯牙障害・それ以外のいずれかが5件未満のカテゴリは統合した。結果は調整オッズ比（adjusted odds ratio: aOR）と95%信頼区間（confidence interval: CI）で示した。

## 感度分析とモデル診断

カテゴリ統合基準を20、30、50件に変更し、通学中、小学校、中学校の3係数の安定性を確認した。給付年度を連続値と5年区分で比較した。通学方法のその他カテゴリが疎であったため、自転車と徒歩だけに限定した感度分析も行った。通学中と学校種の交互作用は、通学中事例が十分にある高・中・小の7,104件だけに限定して探索的に検討した。多重共線性はVIFで評価した。主モデルの判別力と予測誤差は、説明項目を固定し、カテゴリ統合、標準化、ダミー化を各学習fold内で行う5分割交差検証のAUCとBrierスコアで内部評価した。説明項目の選択自体は交差検証の外で行われた。

## 解析環境

本回帰解析にはPython、pandas、NumPy、SciPy、scikit-learnおよびmatplotlibを使用した。入力読込で参照するStep7環境にはJanomeも含まれるが、本回帰解析の説明変数作成や推定には使用していない。ソフトウェアとライブラリのバージョンは投稿時に追記する。
"""
    write("Step10-01_Methods_最新版.md", methods)

    results = f"""
# Results

## 解析対象

全7,682件のうち、歯牙障害は1,583件、歯牙障害以外は6,099件であった。通学中590件のうち歯牙障害は262件（44.4%）で、登校中は249件中117件（47.0%）、下校中は319件中135件（42.3%）であった。

## 多変量解析

主モデルでは、通学中は課外指導に対し歯牙障害のオッズが高かった（aOR 3.05, 95% CI 2.51–3.71）。小学校と中学校は高校に対しオッズが低かった（小学校：aOR 0.33, 95% CI 0.27–0.40；中学校：aOR 0.50, 95% CI 0.44–0.58）。

詳細活動モデルでは、体育的部活動に対し、登校中（aOR 3.01, 95% CI 2.28–3.95）および下校中（aOR 3.02, 95% CI 2.34–3.89）でオッズが高かった。探索的な通学中サブグループでは、徒歩は自転車に対しオッズが低かった（aOR {walking['調整オッズ比']:.2f}, 95% CI {walking['95%CI下限']:.2f}–{walking['95%CI上限']:.2f}）。その他交通を除いて自転車と徒歩の{int(walking_sensitivity['解析対象件数']):,}件だけに限定しても、徒歩対自転車はaOR {walking_sensitivity['調整オッズ比']:.2f}（95% CI {walking_sensitivity['95%CI下限']:.2f}–{walking_sensitivity['95%CI上限']:.2f}）であった。

## モデル診断と感度分析

3モデルはいずれも数値計算上は収束し、今回採用したカテゴリ設計では極端な係数または標準誤差の警告はなかった。同一データ内AUCは主モデル{models.loc['主モデル（大分類）','AUC（同一データ内）']:.3f}、詳細活動モデル{models.loc['詳細活動モデル','AUC（同一データ内）']:.3f}、通学中サブグループ{models.loc['通学中サブグループ','AUC（同一データ内）']:.3f}であった。主モデルの5分割交差検証の平均AUCは{cv['AUC']:.3f}、Brierスコアは{cv['Brierスコア']:.3f}であった。

カテゴリ統合基準を20、30、50件に変更しても、通学中のaORは3.04–3.06、小学校は0.33、中学校は0.50–0.51であった。高・中・小の7,104件だけに限定した通学中と学校種の探索的交互作用について、交互作用全体のLR検定はp={interaction_p:.4f}（自由度{interaction_df}）であった。
"""
    write("Step10-02_Results_最新版.md", results)

    discussion = """
# Discussion

## 主要所見

登録された長期障害事例の中では、通学中、特に登下校中の事例で歯牙障害の構成割合が高かった。通学中と歯牙障害分類との関連は、性別、学校種、給付年度（西暦換算）を考慮した後も認められ、通学中、小学校、中学校の3係数はカテゴリ統合基準を変更しても大きく変化しなかった。

## 通学時の歯牙障害

通学中、自転車、道路は定型項目上で重なったが、通学方法が通学中にだけ入力されるなどデータベースの項目構造による重なりを含む。したがって、それぞれを独立した原因とも、新しい臨床所見とも解釈できない。自転車転倒後に前歯部や顔面へ直接外力が加わるという説明は仮説であり、受傷姿勢、衝突速度、保護具の使用、出来事の順序を本解析では確認していない。

## 学校種と給付年度

高校と小・中学校との差には、通学方法、体育的部活動、永久歯と乳歯の違い、障害の認定・登録基準が関与した可能性がある。したがって、学校種別の一般的な歯科外傷発生率の差とは解釈できない。給付年度が新しい区分ほどオッズが低かった所見は、事故発生年の変化を直接示さない。登録・給付の運用、認定までの時間差、比較群の構成変化を考慮する必要がある。

## 限界

1. 障害登録事例のみを対象とし、一般児童生徒数や暴露回数を母数としていない。
2. 未報告事例、軽症例、登録基準の変化の影響を受ける可能性がある。
3. 自由記載の語彙と記載量は均一でない。
4. 「歯」「前歯」「歯科」等は診断や治療結果を直接表し、原因因子ではない。
5. 未測定の交絡因子が残る可能性がある。
6. 説明項目は同じデータの探索結果から選択され、信頼区間は選択過程と多数のカテゴリ比較を考慮していない。
7. 欠損を「不明・記載なし」カテゴリとして扱い、学校単位の事例のまとまりは考慮していない。
8. AUCは中程度であり、個人の高精度な予測を目的としたモデルではない。交差検証は内部評価で、因子選択と外部妥当性を評価していない。
9. 給付年度を事故発生年として解釈できず、事故の経年変化や予防効果は評価できない。
10. 通学中サブグループのその他交通は疎であり、自転車・徒歩二群の感度分析を行ったが外部検証ではない。

## 臨床的示唆

本結果は、通学中に登録された歯牙障害の背景を追加検証する根拠となる。具体的には、歯牙障害分類と自動判定を伏せた原文レビューにより、転倒、衝突対象、路面との接触、受傷歯、保護具の記載を標準化し、予防可能な受傷機転を評価する必要がある。
"""
    write("Step10-03_Discussion_最新版.md", discussion)

    abstract = f"""
# 構造化抄録

## 目的

学校管理下の長期障害登録事例を用い、歯牙障害の特徴を探索し、学校種、活動、通学方法等との関連を検討することを目的とした。

## 方法

歯牙障害1,583件と歯牙障害以外6,099件を解析した。同じデータの探索的解析で抽出した上位因子を用い、性別、学校種、給付年度（西暦換算）等を考慮した探索的ロジスティック回帰を行った。カテゴリ統合基準、給付年度の扱い、高・中・小に限定した交互作用を検討し、主モデルの内部判別性能を5分割交差検証で評価した。

## 結果

通学中は590件中262件（44.4%）が歯牙障害であった。通学中は課外指導に対し歯牙障害のオッズが高かった（aOR 3.05, 95% CI 2.51–3.71）。小学校と中学校は高校に対しオッズが低かった（それぞれaOR 0.33, 95% CI 0.27–0.40；aOR 0.50, 95% CI 0.44–0.58）。カテゴリ統合基準を変えてもこの3係数は大きく変化せず、主モデルの5分割交差検証の平均AUCは{cv['AUC']:.3f}であった。

## 結論

登録された長期障害事例の中で、通学中の事例は歯牙障害に分類されるオッズが高かった。本結果は一般集団の発生リスク、事故発生年の推移、因果関係を示さず、盲検化した原文レビューと独立データでの確認が必要である。
"""
    write("Step10-04_構造化抄録_最新版.md", abstract)

    write("Step10-05_図表キャプション.md", """
# 図表キャプション

## Figure 10-1

主モデルにおける歯牙障害の調整オッズ比と95%信頼区間。点は調整オッズ比、横線は95%信頼区間、赤色破線はオッズ比1を示す。性別、学校種、給付年度（西暦換算）および活動大分類を相互に調整した。図示可能な範囲にある主要項目を表示した。全係数はStep8-03に、投稿候補の係数はTable 10-1に示す。

## Table 10-1

多変量ロジスティック回帰による歯牙障害の調整オッズ比。括弧内は各カテゴリの比較基準を示す。不明・記載なし、および「その他（少数カテゴリ）」は投稿候補表から除外したため、全係数はStep8-03を参照する。

## Table 10-2

多変量解析3モデルの対象件数、説明変数数、数値計算上の収束、有限推定の警告および同一データ内AUC。

## Table 10-3

説明項目を固定した主モデルの5分割交差検証結果。カテゴリ統合、標準化、ダミー化は学習fold内で実施し、AUC、BrierスコアおよびLogLossを示す。因子選択と外部妥当性は評価していない。

## Table 10-4

通学中事例のうち自転車と徒歩だけに限定した探索的感度分析。その他交通の疎なセルを除いた場合に、徒歩対自転車の焦点係数が大きく変化しないかを確認した。
""")

    write("Step10-06_投稿前確認リスト.md", """
# 投稿前確認リスト

- [ ] 研究対象期間を記載した
- [ ] 給付年度と事故発生年の関係を確認し、混同していない
- [ ] データベースの取得日を記載した
- [ ] データの入手方法と利用条件を記載した
- [ ] 選択基準と除外基準を記載した
- [ ] 倫理審査の要否と承認番号を確認した
- [ ] 歯牙障害の定義と登録基準を記載した
- [ ] 歯牙障害以外の内訳を記載した
- [ ] ソフトウェアとライブラリのバージョンを追記した
- [ ] 欠損・少数カテゴリの処理を記載した
- [ ] データ駆動型の因子選択と多重比較を限界に記載した
- [ ] STROBEチェックリストと対象選択フローを準備した
- [ ] 本文、表、図の数値が一致した
- [ ] オッズ比を発生リスクと表現していない
- [ ] 関連を因果関係と表現していない
- [ ] 外れ値候補のIDを公開資料から除外した
- [ ] 自由記載の再識別リスクを確認した
- [ ] 先行研究との一致点・相違点を追記した
- [ ] 投稿規定に合わせて抄録と図表を調整した
""")

    write("README.md", """
# Step10 統合論文原稿

Step7の探索的解析、Step8の多変量解析、Step9の感度分析を反映した論文原稿素材です。Step6の旧原稿は保存したままです。

本フォルダの文章はそのまま投稿する完成原稿ではありません。対象期間、倫理審査、データ利用条件、先行研究および投稿先の規定は研究者による確認が必要です。
""")

    print(f"Step10完了 / 出力={OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存のStep10成果物を確認済みとして再生成する")
    main(force=parser.parse_args().force)
