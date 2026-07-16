#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
FILE_ROOT = PROJECT_ROOT / "file"

STEP_DIRECTORIES = [
    "Step5_結果整理",
    "Step6_論文作成支援",
]

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / f"run_from_step3_{datetime.now():%Y%m%d_%H%M%S}.log"


def natural_key(path: Path):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def log(message: str = "") -> None:
    print(message, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


def collect_scripts(directory: Path) -> list[Path]:
    if not directory.exists():
        raise FileNotFoundError(f"フォルダが見つかりません: {directory}")

    return sorted(
        [p for p in directory.glob("Step*.py") if p.is_file()],
        key=natural_key,
    )


def run_script(script: Path) -> float:
    started = time.perf_counter()

    log()
    log("-" * 78)
    log(f"実行開始: {script.relative_to(PROJECT_ROOT)}")
    log(f"Python   : {sys.executable}")
    log("-" * 78)

    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    assert process.stdout is not None

    for line in process.stdout:
        log(line.rstrip("\n"))

    return_code = process.wait()
    elapsed = time.perf_counter() - started

    if return_code != 0:
        raise subprocess.CalledProcessError(
            return_code,
            [sys.executable, str(script)],
        )

    log(f"正常終了: {script.name} ({elapsed:.2f}秒)")
    return elapsed


def main() -> int:
    overall_started = time.perf_counter()
    success_count = 0

    log("=" * 78)
    log("Step3以降の一括実行を開始します")
    log("Step2は手修正データ保護のため実行しません")
    log(f"プロジェクトルート: {PROJECT_ROOT}")
    log(f"ログ保存先        : {LOG_PATH}")
    log("=" * 78)

    try:
        if not FILE_ROOT.exists():
            raise FileNotFoundError(
                "fileフォルダが見つかりません。"
                "このスクリプトをfileフォルダと同じ階層に置いてください。"
            )

        scripts: list[Path] = []

        for directory_name in STEP_DIRECTORIES:
            directory = FILE_ROOT / directory_name
            step_scripts = collect_scripts(directory)

            if not step_scripts:
                log(f"警告: 実行対象なし: {directory.relative_to(PROJECT_ROOT)}")
                continue

            scripts.extend(step_scripts)

        if not scripts:
            raise RuntimeError("Step3以降の実行対象が見つかりません。")

        log()
        log(f"実行予定ファイル数: {len(scripts)}")

        for index, script in enumerate(scripts, start=1):
            log()
            log(f"[{index}/{len(scripts)}] {script.relative_to(PROJECT_ROOT)}")
            run_script(script)
            success_count += 1

    except KeyboardInterrupt:
        log()
        log("ユーザー操作により中断されました。")
        return 130

    except subprocess.CalledProcessError as error:
        failed = Path(error.cmd[-1]).relative_to(PROJECT_ROOT)
        log()
        log("=" * 78)
        log("一括実行を停止しました")
        log(f"終了コード   : {error.returncode}")
        log(f"失敗ファイル : {failed}")
        log(f"正常終了数   : {success_count}")
        log(f"ログ         : {LOG_PATH}")
        log("=" * 78)
        return error.returncode

    except Exception as error:
        log()
        log("=" * 78)
        log("管理処理でエラーが発生しました")
        log(f"{type(error).__name__}: {error}")
        log(f"ログ: {LOG_PATH}")
        log("=" * 78)
        return 1

    elapsed = time.perf_counter() - overall_started

    log()
    log("=" * 78)
    log("Step3以降がすべて正常終了しました")
    log(f"正常終了数   : {success_count}")
    log(f"全体処理時間 : {elapsed:.2f}秒")
    log(f"ログ         : {LOG_PATH}")
    log("=" * 78)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
