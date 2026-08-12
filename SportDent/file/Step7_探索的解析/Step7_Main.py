# ============================================================
# Step7_Main.py
# ============================================================
# 【役割】
# SportDent Step7 全体を一括実行する唯一の実行ファイル。
#
# 【入力方針】
# ・元データは直接使用しない
# ・Step2で抽出し、目視確認済みのカテゴリ別CSV群を使用する
# ・CSV群を統合して「全体」「歯牙障害」「歯牙障害以外」を作成する
#
# 【出力方針】
# ・成果物は CreateData/Step7 に保存する
# ・実行のたびに CreateData/Step7 を削除して再生成する
# ・日時付きの新規フォルダは作成しない
# ============================================================

from __future__ import annotations

import logging
import csv
import io
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path
from typing import Callable

import pandas as pd

from Step7_Sub.Step7_Sub_01_解析対象項目棚卸し import run as run_01
from Step7_Sub.Step7_Sub_02_データ品質診断 import run as run_02
from Step7_Sub.Step7_Sub_03_欠損値解析 import run as run_03
from Step7_Sub.Step7_Sub_04_重複データ確認 import run as run_04
from Step7_Sub.Step7_Sub_05_カテゴリ一覧作成 import run as run_05
from Step7_Sub.Step7_Sub_06_カテゴリ数集計 import run as run_06
from Step7_Sub.Step7_Sub_07_年度別件数推移 import run as run_07
from Step7_Sub.Step7_Sub_08_基本統計量一覧 import run as run_08
from Step7_Sub.Step7_Sub_09_全カテゴリクロス集計 import run as run_09
from Step7_Sub.Step7_Sub_10_カイ二乗検定 import run as run_10
from Step7_Sub.Step7_Sub_11_Fisher正確確率検定 import run as run_11
from Step7_Sub.Step7_Sub_12_CramersV import run as run_12
from Step7_Sub.Step7_Sub_13_標準化残差分析 import run as run_13
from Step7_Sub.Step7_Sub_14_オッズ比解析 import run as run_14
from Step7_Sub.Step7_Sub_15_相対危険度 import run as run_15
from Step7_Sub.Step7_Sub_16_多重比較補正 import run as run_16
from Step7_Sub.Step7_Sub_17_年度比較 import run as run_17
from Step7_Sub.Step7_Sub_18_学校種比較 import run as run_18
from Step7_Sub.Step7_Sub_19_男女比較 import run as run_19
from Step7_Sub.Step7_Sub_20_学年比較 import run as run_20
from Step7_Sub.Step7_Sub_21_発生場所比較 import run as run_21
from Step7_Sub.Step7_Sub_22_発生時間帯比較 import run as run_22
from Step7_Sub.Step7_Sub_23_単語頻度 import run as run_23
from Step7_Sub.Step7_Sub_24_品詞集計 import run as run_24
from Step7_Sub.Step7_Sub_25_TFIDF import run as run_25
from Step7_Sub.Step7_Sub_26_共起ネットワーク import run as run_26
from Step7_Sub.Step7_Sub_27_Ngram解析 import run as run_27
from Step7_Sub.Step7_Sub_28_Jaccard係数 import run as run_28
from Step7_Sub.Step7_Sub_29_WordCloud import run as run_29
from Step7_Sub.Step7_Sub_30_文長解析 import run as run_30
from Step7_Sub.Step7_Sub_31_キーワード抽出 import run as run_31
from Step7_Sub.Step7_Sub_32_類似文章検索 import run as run_32
from Step7_Sub.Step7_Sub_33_Apriori import run as run_33
from Step7_Sub.Step7_Sub_34_FPGrowth import run as run_34
from Step7_Sub.Step7_Sub_35_AssociationRule import run as run_35
from Step7_Sub.Step7_Sub_36_クラスタリング import run as run_36
from Step7_Sub.Step7_Sub_37_PCA import run as run_37
from Step7_Sub.Step7_Sub_38_tSNE import run as run_38
from Step7_Sub.Step7_Sub_39_UMAP import run as run_39
from Step7_Sub.Step7_Sub_40_異常値検出 import run as run_40
from Step7_Sub.Step7_Sub_41_希少事例抽出 import run as run_41
from Step7_Sub.Step7_Sub_42_特徴量ランキング import run as run_42
from Step7_Sub.Step7_Sub_43_ヒートマップ import run as run_43
from Step7_Sub.Step7_Sub_44_MosaicPlot import run as run_44
from Step7_Sub.Step7_Sub_45_SankeyDiagram import run as run_45
from Step7_Sub.Step7_Sub_46_BubbleChart import run as run_46
from Step7_Sub.Step7_Sub_47_NetworkGraph import run as run_47
from Step7_Sub.Step7_Sub_48_重要因子ランキング import run as run_48
from Step7_Sub.Step7_Sub_49_研究テーマ候補ランキング import run as run_49
from Step7_Sub.Step7_Sub_50_総合レポート生成 import run as run_50

# ============================================================
# 【システム情報】
# ============================================================
SYSTEM_NAME = "SportDent"
STEP_NAME = "Step7_探索的解析"
VERSION = "v1.1.0"

# ============================================================
# 【プロジェクトパス】
# ------------------------------------------------------------
# 想定：SportDent/file/Step7_探索的解析/Step7_Main.py
# ============================================================
STEP7_DIR = Path(__file__).resolve().parent
PROJECT_DIR = STEP7_DIR.parent.parent
CREATE_DATA_DIR = PROJECT_DIR / "CreateData"
STEP1_CATEGORY_SUMMARY = CREATE_DATA_DIR / "Step1_基本集計" / "Step1-4_基本集計_傷害種別集計.csv"

# ============================================================
# 【Step2カテゴリ別抽出CSVの入力元】
# ------------------------------------------------------------
# 実際のフォルダ名が違う場合は、この1か所だけ変更する。
# ============================================================
STEP2_CATEGORY_DIR = (
    CREATE_DATA_DIR
    / "Step2_傷害カテゴリ別解析"
    / "カテゴリ別抽出データ"
)

# ============================================================
# 【歯牙障害CSVの識別条件】
# ============================================================
TOOTH_DAMAGE_FILE_KEYWORD = "歯牙障害抽出"

# ============================================================
# 【実行対象データセット】
# ============================================================
AVAILABLE_DATASETS = ["全体", "歯牙障害", "歯牙障害以外"]
TARGET_DATASETS = [
    "全体",
    "歯牙障害",
    "歯牙障害以外",
]

# ============================================================
# 【統合時の重複確認設定】
# ------------------------------------------------------------
# 一意ID列が確定したら列名を設定する。
# Noneでは勝手に削除せず、完全一致重複候補だけログへ出す。
# ============================================================
UNIQUE_ID_COLUMN: str | None = None
CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp932"]
SIGNIFICANCE_LEVEL = 0.05
RANDOM_SEED = 42
TEXT_ENCODING = "utf-8-sig"
STOP_ON_ERROR = False
# Sub04以降はSub01〜03の実データ診断後に設計を確定する。
# 未実装の雛形を「成功」と数えないよう、現段階の実行上限を明示する。
ACTIVE_ANALYSIS_MAX = 50
EXPECTED_CATEGORY_FILE_COUNT = 12
EXPECTED_ORIGINAL_COLUMNS = [
    "和暦", "給付年度", "記号", "種別", "被災学校種", "被災学年", "性別",
    "場合別1", "場合別2", "競技種目", "通学方法", "発生場所1", "発生場所2",
    "遊具等", "災害発生時の状況",
]

# ============================================================
# 【解析モジュール一覧】
# ============================================================
ANALYSIS_MODULES: list[tuple[int, str, Callable]] = [

    (1, "解析対象項目棚卸し", run_01),
    (2, "データ品質診断", run_02),
    (3, "欠損値解析", run_03),
    (4, "重複データ確認", run_04),
    (5, "カテゴリ一覧作成", run_05),
    (6, "カテゴリ数集計", run_06),
    (7, "年度別件数推移", run_07),
    (8, "基本統計量一覧", run_08),
    (9, "全カテゴリクロス集計", run_09),
    (10, "カイ二乗検定", run_10),
    (11, "Fisher正確確率検定", run_11),
    (12, "CramersV", run_12),
    (13, "標準化残差分析", run_13),
    (14, "オッズ比解析", run_14),
    (15, "相対危険度", run_15),
    (16, "多重比較補正", run_16),
    (17, "年度比較", run_17),
    (18, "学校種比較", run_18),
    (19, "男女比較", run_19),
    (20, "学年比較", run_20),
    (21, "発生場所比較", run_21),
    (22, "発生時間帯比較", run_22),
    (23, "単語頻度", run_23),
    (24, "品詞集計", run_24),
    (25, "TFIDF", run_25),
    (26, "共起ネットワーク", run_26),
    (27, "Ngram解析", run_27),
    (28, "Jaccard係数", run_28),
    (29, "WordCloud", run_29),
    (30, "文長解析", run_30),
    (31, "キーワード抽出", run_31),
    (32, "類似文章検索", run_32),
    (33, "Apriori", run_33),
    (34, "FPGrowth", run_34),
    (35, "AssociationRule", run_35),
    (36, "クラスタリング", run_36),
    (37, "PCA", run_37),
    (38, "tSNE", run_38),
    (39, "UMAP", run_39),
    (40, "異常値検出", run_40),
    (41, "希少事例抽出", run_41),
    (42, "特徴量ランキング", run_42),
    (43, "ヒートマップ", run_43),
    (44, "MosaicPlot", run_44),
    (45, "SankeyDiagram", run_45),
    (46, "BubbleChart", run_46),
    (47, "NetworkGraph", run_47),
    (48, "重要因子ランキング", run_48),
    (49, "研究テーマ候補ランキング", run_49),
    (50, "総合レポート生成", run_50),

]

# ============================================================
# 【ログ設定】
# ============================================================
def setup_logger(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("Step7")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_dir / "Step7_RunLog.txt", encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

# ============================================================
# 【CreateData/Step7の上書き再生成】
# ============================================================
def recreate_step7_output(output_root: Path, logger: logging.Logger) -> None:
    if output_root.exists():
        logger.info("旧Step7成果物を削除します: %s", output_root)
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    logger.info("Step7成果物フォルダを再生成しました: %s", output_root)

# ============================================================
# 【CSV安全読込】
# ============================================================
def resolve_unicode_path(path: Path) -> Path:
    """各階層のUnicode正規化形式が異なっても、一意に一致する実パスを返す。"""
    current = path.anchor and Path(path.anchor) or Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        direct = current / part
        if direct.exists():
            current = direct
            continue
        if not current.exists():
            raise FileNotFoundError(f"親フォルダがありません: {current}")
        target = unicodedata.normalize("NFC", part)
        matches = [p for p in current.iterdir() if unicodedata.normalize("NFC", p.name) == target]
        if len(matches) != 1:
            raise FileNotFoundError(
                f"Unicode正規化後にパスを一意に特定できません: {direct} / 候補={matches}"
            )
        current = matches[0]
    return current


def read_csv_safely(csv_file: Path, logger: logging.Logger) -> tuple[pd.DataFrame, str]:
    """通常読込を優先し、構文異常時のみ事例開始行を根拠に復元する。"""
    errors=[]
    for enc in CSV_ENCODINGS:
        try:
            dataframe = pd.read_csv(csv_file, encoding=enc)
            # pandasが例外を出さず、自由記載の継続行を
            # ID欠損の別レコードとして読む場合も構文異常と判定する。
            ids = dataframe["記号"].astype("string") if "記号" in dataframe else pd.Series(dtype="string")
            categories = dataframe["種別"].astype("string") if "種別" in dataframe else pd.Series(dtype="string")
            structurally_valid = (
                list(dataframe.columns) == EXPECTED_ORIGINAL_COLUMNS
                and not ids.isna().any()
                and not ids.str.strip().eq("").any()
                and not categories.isna().any()
                and categories.dropna().str.strip().nunique() == 1
            )
            if structurally_valid:
                return dataframe, "通常読込"
            errors.append(f"{enc}: 読込後構造検証失敗")
            break
        except Exception as e:
            errors.append(f"{enc}: {type(e).__name__}: {e}")

    # Step2成果物には自由記載内の改行と引用符の不整合がある。
    # 先頭3列の形式が「和暦,給付年度,記号」で安定しているため、
    # 年号で始まる行だけを新規事例とし、途中行を直前の自由記載へ連結する。
    try:
        text = csv_file.read_text(encoding="utf-8-sig")
        lines = text.splitlines(keepends=True)
        header = next(csv.reader([lines[0].rstrip("\r\n")]))
        start_pattern = re.compile(r"^(?:明治|大正|昭和|平成|令和),")
        records: list[str] = []
        current = ""
        for line in lines[1:]:
            if start_pattern.match(line) and current:
                records.append(current)
                current = line
            else:
                current += line
        if current:
            records.append(current)
        rows = [next(csv.reader(io.StringIO(record))) for record in records]
        invalid = [(i + 2, len(row)) for i, row in enumerate(rows) if len(row) != len(header)]
        if header != EXPECTED_ORIGINAL_COLUMNS or invalid:
            raise ValueError(f"復元後も列構成が不正: header={header}, invalid={invalid[:20]}")
        logger.warning("CSV構文異常を事例開始行により復元: %s / %d件", csv_file.name, len(rows))
        return pd.DataFrame(rows, columns=header), "構文復元読込"
    except Exception as recovery_error:
        raise RuntimeError(
            f"CSVを読み込めませんでした: {csv_file}\n"
            f"通常読込エラー={errors}\n復元エラー={recovery_error}"
        ) from recovery_error

# ============================================================
# 【Step2カテゴリ別CSV群の統合】
# ------------------------------------------------------------
# 全体          ：すべてのCSVを結合
# 歯牙障害      ：ファイル名に「歯牙障害抽出」を含むCSV
# 歯牙障害以外  ：上記以外のCSV
#
# 入力元追跡用に次の列を追加する。
# ・Step7_入力元ファイル
# ・Step7_入力元カテゴリ
# ============================================================
def load_step2_category_datasets(category_dir: Path, logger: logging.Logger) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    if not category_dir.exists():
        raise FileNotFoundError(f"Step2カテゴリ別抽出データフォルダがありません: {category_dir}")
    csv_files = sorted(category_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"CSVが1件もありません: {category_dir}")

    if len(csv_files) != EXPECTED_CATEGORY_FILE_COUNT:
        raise RuntimeError(f"Step2カテゴリCSVは{EXPECTED_CATEGORY_FILE_COUNT}件必要です: 検出={len(csv_files)}")
    expected_counts: dict[str, int] = {}
    if STEP1_CATEGORY_SUMMARY.exists():
        step1_summary = pd.read_csv(STEP1_CATEGORY_SUMMARY, encoding="utf-8-sig")
        if {"種別", "件数"}.issubset(step1_summary.columns):
            expected_counts = dict(zip(step1_summary["種別"].astype(str), step1_summary["件数"].astype(int)))
    all_frames=[]; tooth_frames=[]; other_frames=[]; diagnostics=[]
    reference_columns=None; mismatch=[]
    logger.info("Step2カテゴリ別CSV検出数: %d", len(csv_files))

    for f in csv_files:
        df, read_method=read_csv_safely(f, logger)
        cols=list(df.columns)
        if cols != EXPECTED_ORIGINAL_COLUMNS:
            raise ValueError(f"想定外の列構成です: {f.name} / {cols}")
        categories=sorted(df["種別"].dropna().astype(str).str.strip().unique().tolist())
        if len(categories) != 1:
            raise ValueError(f"種別が1種類ではありません: {f.name} / {categories}")
        if reference_columns is None:
            reference_columns=cols
        elif cols != reference_columns:
            mismatch.append(f.name)
        df=df.copy()
        df["Step7_入力元ファイル"]=f.name
        df["Step7_入力元カテゴリ"]=categories[0]
        df["Step7_歯牙障害フラグ"]=(df["種別"].astype(str).str.strip() == "歯牙障害").astype(int)
        all_frames.append(df)
        if TOOTH_DAMAGE_FILE_KEYWORD in f.name:
            tooth_frames.append(df); group="歯牙障害"
        else:
            other_frames.append(df); group="歯牙障害以外"
        logger.info("読込完了 | %s | %s | %d件", group, f.name, len(df))
        expected = expected_counts.get(categories[0])
        difference = len(df) - expected if expected is not None else pd.NA
        status = "一致" if difference == 0 else ("不一致" if expected is not None else "比較不能")
        if status == "不一致":
            logger.warning("Step1件数と不一致: %s / Step2=%d / Step1=%d", categories[0], len(df), expected)
        diagnostics.append({
            "入力ファイル": f.name, "カテゴリ": categories[0], "Step2件数": len(df),
            "Step1集計件数": expected, "差（Step2-Step1）": difference, "件数照合": status,
            "列数": len(cols), "読込方法": read_method,
        })

    if not tooth_frames:
        raise RuntimeError(f"歯牙障害CSVを識別できません。キーワード={TOOTH_DAMAGE_FILE_KEYWORD!r}")
    if mismatch:
        raise ValueError(f"列構成が一致しないCSV: {mismatch}")

    df_all=pd.concat(all_frames, ignore_index=True, sort=False)
    df_tooth=pd.concat(tooth_frames, ignore_index=True, sort=False)
    df_other=(pd.concat(other_frames, ignore_index=True, sort=False)
              if other_frames else pd.DataFrame(columns=df_all.columns))

    logger.info("全体統合件数: %d", len(df_all))
    logger.info("歯牙障害統合件数: %d", len(df_tooth))
    logger.info("歯牙障害以外統合件数: %d", len(df_other))

    tech={"Step7_入力元ファイル", "Step7_入力元カテゴリ"}
    check_cols=[c for c in df_all.columns if c not in tech]
    dup=int(df_all.duplicated(subset=check_cols, keep=False).sum()) if check_cols else 0
    logger.info("全体の完全一致重複候補行数: %d", dup)

    id_column = UNIQUE_ID_COLUMN or ("記号" if "記号" in df_all.columns else None)
    if id_column:
        id_text=df_all[id_column].astype("string")
        missing_id=int(id_text.isna().sum() + (id_text.notna() & id_text.str.strip().eq("")).sum())
        id_dup=int(df_all.duplicated(subset=[id_column], keep=False).sum())
        logger.info("ID診断（%s）: 欠損=%d / 重複候補行=%d", id_column, missing_id, id_dup)
        if missing_id or id_dup:
            logger.warning("一意ID候補の条件を満たしません: %s", id_column)

    return {"全体": df_all, "歯牙障害": df_tooth, "歯牙障害以外": df_other}, pd.DataFrame(diagnostics)

# ============================================================
# 【settings作成】
# ------------------------------------------------------------
# Sub側では保存先を組み立てず、各dirを直接使う。
# ============================================================
def create_settings(dataset_name: str, df: pd.DataFrame, output_root: Path, log_dir: Path, logger: logging.Logger) -> dict:
    base=output_root/dataset_name
    dirs={name: base/name for name in ["CSV", "Figure", "Table", "Report", "Summary"]}
    for d in dirs.values(): d.mkdir(parents=True, exist_ok=True)
    return {
        "system_name": SYSTEM_NAME, "step_name": STEP_NAME, "version": VERSION,
        "dataset_name": dataset_name, "df": df,
        "project_dir": PROJECT_DIR, "step7_dir": STEP7_DIR,
        "step2_category_dir": STEP2_CATEGORY_DIR,
        "output_root": output_root, "output_dir": base,
        "csv_dir": dirs["CSV"], "figure_dir": dirs["Figure"],
        "table_dir": dirs["Table"], "report_dir": dirs["Report"],
        "summary_dir": dirs["Summary"], "log_dir": log_dir,
        "logger": logger, "significance_level": SIGNIFICANCE_LEVEL,
        "random_seed": RANDOM_SEED, "text_encoding": TEXT_ENCODING,
        # 同一データセット内の高コスト中間計算だけを保持する。
        # Subの成果物や実行順に依存する値は格納しない。
        "cache": {},
    }

# ============================================================
# 【データ0件時の共通スキップ判定】
# ============================================================
def should_skip_dataset(settings: dict) -> bool:
    if settings["df"].empty:
        settings["logger"].info("[%s] 対象データ0件のためスキップ", settings["dataset_name"])
        return True
    return False

# ============================================================
# 【解析1件の実行】
# ============================================================
def execute_analysis(number: int, name: str, func: Callable, settings: dict) -> str:
    logger=settings["logger"]; dataset=settings["dataset_name"]
    if should_skip_dataset(settings): return "skipped"
    start=time.perf_counter()
    logger.info("[%s] Sub%02d %s：開始", dataset, number, name)
    try:
        result = func(settings)
    except Exception:
        logger.exception("[%s] Sub%02d %s：失敗", dataset, number, name)
        return "failure"
    if result == "skipped":
        logger.info("[%s] Sub%02d %s：解析不能・スキップ（%.2f秒）", dataset, number, name, time.perf_counter()-start)
        return "skipped"
    logger.info("[%s] Sub%02d %s：完了（%.2f秒）", dataset, number, name, time.perf_counter()-start)
    return "success"

# ============================================================
# 【Main処理】
# ============================================================
def main() -> None:
    log_dir=STEP7_DIR/"Log"
    output_root=CREATE_DATA_DIR/"Step7"
    logger=setup_logger(log_dir)
    start=time.perf_counter()
    logger.info("============================================================")
    logger.info("%s / %s / %s", SYSTEM_NAME, STEP_NAME, VERSION)
    category_dir=resolve_unicode_path(STEP2_CATEGORY_DIR)
    logger.info("Step2入力元: %s", category_dir)
    logger.info("Step7出力先: %s", output_root)
    logger.info("実行対象: %s", TARGET_DATASETS)
    logger.info("============================================================")

    unknown=set(TARGET_DATASETS)-set(AVAILABLE_DATASETS)
    if unknown: raise ValueError(f"未定義データセット: {sorted(unknown)}")

    # 入力検証失敗時に旧成果物を消さないよう、読込を先に完了させる。
    datasets, input_diagnostics=load_step2_category_datasets(category_dir, logger)
    recreate_step7_output(output_root, logger)
    input_diagnostics.to_csv(output_root / "Step7_入力ファイル診断.csv", index=False, encoding=TEXT_ENCODING)
    success=failure=skipped=0

    for dataset_name in TARGET_DATASETS:
        df=datasets[dataset_name]
        logger.info("------------------------------------------------------------")
        logger.info("解析対象: %s / %d件", dataset_name, len(df))
        logger.info("------------------------------------------------------------")
        settings=create_settings(dataset_name, df, output_root, log_dir, logger)
        active_modules = [item for item in ANALYSIS_MODULES if item[0] <= ACTIVE_ANALYSIS_MAX]
        logger.info("現段階の実行Sub: 01〜%02d", ACTIVE_ANALYSIS_MAX)
        for number, name, func in active_modules:
            status=execute_analysis(number, name, func, settings)
            if status == "success": success+=1
            elif status == "skipped": skipped+=1
            else:
                failure+=1
                if STOP_ON_ERROR: raise RuntimeError(f"Sub{number:02d} {name}で停止")

    logger.info("============================================================")
    logger.info("終了 / 成功:%d / 解析不能・スキップ:%d / 失敗:%d / 総時間:%.2f秒", success, skipped, failure, time.perf_counter()-start)
    logger.info("============================================================")

if __name__ == "__main__":
    main()
