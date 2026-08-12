"""SportDent Step12：汎用の投稿準備パッケージを生成する。"""
from __future__ import annotations

import argparse
import hashlib
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy
import openpyxl
import pandas
import scipy
import sklearn

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
CREATE = PROJECT / "CreateData"
STEP10 = CREATE / "Step10_統合論文原稿"
STEP11 = CREATE / "Step11_通学中臨床レビュー"
OUTPUT = CREATE / "Step12_投稿準備"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def write(name: str, text: str) -> None:
    (OUTPUT / name).write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def secure_private_tree(path: Path) -> None:
    """再生成前バックアップを所有者だけが読める権限にする。"""
    path.chmod(0o700)
    for child in path.rglob("*"):
        child.chmod(0o700 if child.is_dir() else 0o600)


def git_metadata() -> tuple[str, str]:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT.parent, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = "あり" if subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=PROJECT.parent, text=True, stderr=subprocess.DEVNULL
        ).strip() else "なし"
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "取得不能", "取得不能"


def main(force: bool = False) -> None:
    step2_root = CREATE / "Step2_傷害カテゴリ別解析"
    source_files = sorted(step2_root.rglob("Step2-*_傷害カテゴリ別解析_*抽出.csv"))
    source_files.append(CREATE / "Step7" / "全体" / "Summary" / "Step7-48_重要因子ランキング.csv")
    code_files = [
        PROJECT / "file" / "Step7_探索的解析" / "Step7_Main.py",
        PROJECT / "file" / "Step8_多変量解析" / "Step8_Main.py",
        PROJECT / "file" / "Step9_感度分析" / "Step9_Main.py",
        PROJECT / "file" / "Step10_統合論文原稿" / "Step10_Main.py",
        PROJECT / "file" / "Step11_通学中臨床レビュー" / "Step11_Main.py",
        PROJECT / "file" / "Step11_通学中臨床レビュー" / "Step11_ReviewWorkflow.py",
        PROJECT / "file" / "Step11_通学中臨床レビュー" / "Step11_PostReviewWorkflow.py",
        PROJECT / "file" / "Step11_通学中臨床レビュー" / "Step11_ReviewAnalysis.py",
        PROJECT / "file" / "Step11_通学中臨床レビュー" / "Step11_ReviewCodebook_candidate.md",
        PROJECT / "file" / "Step12_投稿準備" / "Step12_Main.py",
        PROJECT / "file" / "Step12_投稿準備" / "Validate_Step8_12.py",
    ]
    required_inputs = [
        STEP10 / "Step10-01_Methods_最新版.md",
        STEP10 / "Step10-02_Results_最新版.md",
        STEP10 / "Step10-03_Discussion_最新版.md",
        STEP10 / "Step10-04_構造化抄録_最新版.md",
        STEP10 / "Figure" / "Figure10-1_調整オッズ比.png",
        STEP10 / "Figure" / "Figure10-1_調整オッズ比.svg",
        *sorted((STEP10 / "Table").glob("*.csv")),
        *source_files,
        *code_files,
        HERE / "requirements-lock.txt",
    ]
    missing = [path for path in required_inputs if not path.exists()]
    if missing or len(required_inputs) < 8:
        raise FileNotFoundError("Step12の必須入力が不足しています：" + " / ".join(str(path) for path in missing))
    if OUTPUT.exists():
        if not force:
            raise FileExistsError(
                f"{OUTPUT} は既に存在します。研究者の追記を消さないため停止しました。"
                "内容を確認した上で再生成する場合だけ --force を指定してください。"
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
        backup_path = backup_root / f"Step12_投稿準備_{timestamp}"
        shutil.copytree(OUTPUT, backup_path)
        secure_private_tree(backup_path)
        shutil.rmtree(OUTPUT)
    (OUTPUT / "Figure").mkdir(parents=True); (OUTPUT / "Table").mkdir(); (OUTPUT / "Internal_DoNotPublish").mkdir()
    (OUTPUT / "Internal_DoNotPublish").chmod(0o700)

    methods = read(STEP10 / "Step10-01_Methods_最新版.md")
    results = read(STEP10 / "Step10-02_Results_最新版.md")
    discussion = read(STEP10 / "Step10-03_Discussion_最新版.md")
    abstract = read(STEP10 / "Step10-04_構造化抄録_最新版.md")
    coefficient_table = pandas.read_csv(STEP10 / "Table" / "Table10-1_多変量解析主要結果.csv", encoding="utf-8-sig")
    walking = coefficient_table.loc[
        coefficient_table["モデル"].eq("通学中サブグループ")
        & coefficient_table["項目（比較対象／基準）"].str.startswith("通学方法：徒歩（")
    ].iloc[0]["調整オッズ比（95%信頼区間）"]
    manuscript = f"""
# 学校管理下の長期障害登録事例における歯牙障害の特徴：探索的解析と多変量解析

> 仮題。投稿先と研究者の意図に合わせて修正する。

> 投稿前素材。緒言、参考文献、倫理・利益相反等の必須事項が未確定であり、このまま投稿しない。

{abstract}

# 緒言

> 未完成：学校歯科外傷の疾病負担、通学中の事故予防、既存研究の限界、本研究の新規性を引用文献付きで追記する。

{methods}

{results}

{discussion}

# 結論

登録された長期障害事例の中で、通学中の事例は課外指導中の事例と比較して歯牙障害に分類されるオッズが高かった。自転車転倒、道路・路面接触、前歯部受傷を一続きの機転とする説明は、盲検化した歯科医師レビューで検証すべき仮説である。本結果は一般集団の発生リスク、事故発生年の推移、因果関係を示さない。

# 倫理的配慮

> 研究者入力必須：倫理審査の要否、承認番号、オプトアウト、公開データ利用条件を記載する。

# 利益相反

> 研究者入力必須。

# 資金提供

> 研究者入力必須。

# データ利用可能性

> 研究者入力必須。原文と内部IDを含むStep11/InternalReviewは非公開とする。

# 参考文献

> 未作成。投稿先の形式に合わせて追記する。

"""
    write("Step12-01_統合原稿_投稿準備版.md", manuscript)

    write("Step12-02_歯科医師向け要約.md", f"""
# 歯科医師向け研究要約

## 何を調べたか

学校管理下で長期障害として登録された7,682件を対象に、歯牙障害1,583件とそれ以外6,099件の特徴を比較した。

## 主な結果

- 通学中590件のうち、歯牙障害は262件（44.4%）だった。
- 性別、学校種、給付年度（西暦換算）を考慮しても、通学中は課外指導に対し調整オッズ比3.05（95% CI 2.51–3.71）だった。
- 探索的な通学中サブグループでは、徒歩対自転車の調整オッズ比は{walking}だった。
- カテゴリのまとめ方を変えても、通学中、小学校、中学校の3係数は大きく変化しなかった。

## 歯科臨床上の仮説

自転車転倒後に前歯部や顔面が路面へ直接接触する受傷連鎖は、今後検証すべき仮説である。Step11の単一機転・直接外力の自動分類には既知のルール上の問題があり、歯科医師による盲検評価が完了するまで結果として使用しない。

## 言えないこと

本データには通学者全体の人数や通学回数がない。したがって、通学中の歯牙障害発生率、自転車通学による絶対リスク、因果関係は判断できない。また、年の変数は給付年度であり、事故発生年の推移は判断できない。
""")

    write("Step12-03_未確定事項_研究者入力シート.md", """
# 研究者入力が必要な未確定事項

| 項目 | 入力欄 |
|---|---|
| 正式な論文タイトル | |
| 著者名・所属 | |
| 責任著者 | |
| 対象期間 | |
| 給付年度と事故発生年の関係 | |
| データベース取得日 | |
| データ提供元の正式名称 | |
| データ利用条件 | |
| 倫理審査の要否 | |
| 倫理審査承認番号 | |
| インフォームドコンセントの扱い | |
| 利益相反 | |
| 研究費 | |
| 著者の貢献 | |
| 謝辞 | |
| 投稿候補誌 | |
| 字数・図表数の制限 | |
| 参考文献形式 | |
""")

    inventory = []
    for source, target in [
        (STEP10 / "Figure" / "Figure10-1_調整オッズ比.png", OUTPUT / "Figure" / "Figure1_調整オッズ比.png"),
        (STEP10 / "Figure" / "Figure10-1_調整オッズ比.svg", OUTPUT / "Figure" / "Figure1_調整オッズ比.svg"),
    ]:
        shutil.copy2(source, target); inventory.append((target.name, "投稿候補" if "Figure1" in target.name else "内部用・未確定"))
    for source in sorted((STEP10 / "Table").glob("*.csv")):
        target = OUTPUT / "Table" / source.name; shutil.copy2(source, target); inventory.append((target.name, "投稿候補"))

    workbook = OUTPUT / "Table" / "Step12_論文用表統合.xlsx"
    with pandas.ExcelWriter(workbook, engine="openpyxl") as writer:
        for index, source in enumerate(sorted((STEP10 / "Table").glob("*.csv")), start=1):
            pandas.read_csv(source, encoding="utf-8-sig").to_excel(writer, sheet_name=f"Table{index}", index=False)
    inventory.append((workbook.name, "投稿用変換元・投稿先規定を確認"))
    pandas.DataFrame(inventory, columns=["ファイル", "扱い"]).to_csv(OUTPUT / "Step12-04_図表・公開可否一覧.csv", index=False, encoding="utf-8-sig")

    internal_readme = OUTPUT / "Internal_DoNotPublish" / "README.md"
    internal_readme.write_text(
        "# 非公開領域\n\nStep11の自動単一分類は人手検証前かつ既知のルール問題があるため、投稿本文・図表をここへも複製していません。\n",
        encoding="utf-8",
    )
    internal_readme.chmod(0o600)

    commit, dirty = git_metadata()
    manifest_rows = []
    for kind, paths in [("解析入力", source_files), ("生成コード", code_files)]:
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"再現用マニフェストの対象が不足しています：{path}")
            manifest_rows.append({
                "区分": kind,
                "ファイル": str(path.relative_to(PROJECT)),
                "SHA-256": sha256_file(path),
                "バイト数": path.stat().st_size,
            })
    pandas.DataFrame(manifest_rows).to_csv(
        OUTPUT / "Step12-06_入力・コードハッシュ.csv", index=False, encoding="utf-8-sig"
    )

    lock_source = HERE / "requirements-lock.txt"
    lock_target = OUTPUT / "Step12-07_requirements-lock.txt"
    shutil.copy2(lock_source, lock_target)

    write("Step12-05_再現環境.md", f"""
# 解析の再現環境

- Python: {platform.python_version()}
- pandas: {pandas.__version__}
- NumPy: {numpy.__version__}
- SciPy: {scipy.__version__}
- scikit-learn: {sklearn.__version__}
- matplotlib: {matplotlib.__version__}
- openpyxl: {openpyxl.__version__}
- Janome: 0.5.0
- Git commit: {commit}
- Git未反映変更: {dirty}
- 5分割交差検証の乱数seed: 20260811
- Step11開発用標本seed: 20260811
- Step11最終評価用標本seed: 20260812
- Step11標本: 事例集合は上記seedで再現し、レビューIDは暗号学的乱数で生成する。元データとの対応は非公開表だけに保存し、ID文字列自体は意図的に再現対象外とする

入力CSVと生成コードのSHA-256は`Step12-06_入力・コードハッシュ.csv`、直接依存の固定版は`Step12-07_requirements-lock.txt`に記録した。Git未反映変更が「あり」の場合、commit hashだけでは同じコードを再現できないため、ハッシュ表を併用する。

## 前提成果物

- Step2の確認済み傷害カテゴリ別抽出CSV
- Step7-48の重要因子ランキング

## 再生成順

1. `.venv/bin/python SportDent/file/Step8_多変量解析/Step8_Main.py --force`
2. `.venv/bin/python SportDent/file/Step9_感度分析/Step9_Main.py --force`
3. `.venv/bin/python SportDent/file/Step10_統合論文原稿/Step10_Main.py --force`
4. 新規環境かつ人手レビュー開始前に限り、`.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_Main.py --force`
5. クリーンな新規再生成環境でのみ、`.venv/bin/python SportDent/file/Step11_通学中臨床レビュー/Step11_ReviewWorkflow.py prepare`
6. `.venv/bin/python SportDent/file/Step12_投稿準備/Step12_Main.py --force`
7. `.venv/bin/python SportDent/file/Step12_投稿準備/Validate_Step8_12.py`

Step11のコードブック`Step11-CB-1.0.0-rc1`は2026-08-12に承認済みである。ユーザー指示により個人名は省略し、研究責任者・評価者A/B・調停担当者の役割コードを承認記録へ保存した。開発用A/B Excelは入力可能で、現時点の回答は各0/100件である。入力中は`validate`、提出前は`validate --require-complete`を使う。完了後は必ず`Step11_PostReviewWorkflow.py freeze-submissions --phase 開発用 --confirm-exact "開発用A/B回答原本を凍結する"`を先に実行し、その凍結原本へ`Step11_ReviewAnalysis.py --phase 開発用`を適用する。後半プログラムは、調停票生成、人手合意値固定、最終人手コードブック・入力仕様固定および別100件Excel生成まで実装済みだが、人手回答前のため未実施である。互換する自動分類器、予測封印、unblindおよびAI性能採点は未実装であり、旧自動回答を流用しない。Excel生成後または人手回答開始後はStep11を再生成しない。コードはExcel原本・初期化記録・人手入力を検出して停止し、再生成前の成果物は`CreateData/RegenerationBackups/`へ非公開権限で保存する。

Step11の単一自動分類は人手検証前かつ既知のルール問題があるため、本投稿準備版の本文・図表には含めない。
""")

    write("README.md", """
# Step12 投稿準備パッケージ

投稿先が未指定のため、汎用形式で整理した投稿前素材です。統合原稿には未確定箇所を `>` で明示しています。緒言、参考文献、倫理等が未確定のため、このまま投稿できる完成版ではありません。

`Internal_DoNotPublish/`は投稿・公開対象外です。Step11の原文・内部ID付きCSVはこのパッケージに複製していません。

再現用に入力・コードのハッシュ表と直接依存の固定版を同梱しています。既存成果物を`--force`で再生成する前に、`CreateData/RegenerationBackups/`へ自動バックアップします。
""")
    print(f"Step12完了 / 出力={OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存の投稿準備フォルダを確認済みとして再生成する")
    main(force=parser.parse_args().force)
