#!/bin/bash
# Existing credentials and saved records are preserved.
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
trap 'echo "処理を停止しました。上のエラーを確認してください。"' ERR

fail() { echo "$1" >&2; exit 1; }
wait_http() {
    local endpoint="$1" attempts=0
    until curl --fail --silent --max-time 2 "$endpoint" >/dev/null; do
        attempts=$((attempts + 1))
        [ "$attempts" -lt 30 ] || return 1
        sleep 1
    done
}

[ "$(uname -s)" = Darwin ] || fail "このボタンはMac専用です。"
mode="${1:-start}"
case "$mode" in
    update)
        echo "GitHubから更新を取得しています…"
        repo_dir="$(git rev-parse --show-toplevel)"
        [ "$(git branch --show-current)" = main ] || fail "main以外のブランチです。更新を停止します。"
        [ -z "$(git status --porcelain)" ] || fail "未保存のGit変更があります。変更を確認してから更新してください。"
        git -C "$repo_dir" pull --ff-only origin main
        git log -1 --oneline
        # Run the freshly downloaded version of this script.
        exec bash "$project_dir/scripts/macos_launch.sh" updated
        ;;
    start|updated) ;;
    *) fail "不明な操作です。" ;;
esac

[ -x .venv/bin/python ] || fail "Python環境がありません。手順書の初回設定を行ってください。"
[ -f .env ] || fail "公開用ログイン設定がありません。手順書の初回設定を行ってください。"
if [ "$mode" = updated ]; then
    echo "必要なライブラリを更新しています…"
    .venv/bin/python -m pip install -r requirements.txt
fi

echo "Ollamaを起動しています…"
open -a Ollama
wait_http http://127.0.0.1:11434/api/tags || fail "Ollamaが起動しません。Ollamaアプリを確認してください。"

user_id="$(id -u)"
app_label="jp.sportdent.studyllm"
app_plist="$HOME/Library/LaunchAgents/$app_label.plist"
echo "StudyLLMを起動しています…"
if ! launchctl print "gui/$user_id/$app_label" >/dev/null 2>&1; then
    [ -f "$app_plist" ] || fail "StudyLLMの自動起動設定がありません。手順書の初回設定を行ってください。"
    launchctl bootstrap "gui/$user_id" "$app_plist"
fi
launchctl kickstart -k "gui/$user_id/$app_label"
if ! wait_http http://127.0.0.1:8000; then
    echo "StudyLLMの起動に失敗しました。直近のログ："
    tail -n 30 logs/studyllm.err.log || true
    fail "ここまでのエラーを確認してください。"
fi

echo "公開接続を確認しています…"
if ! curl --fail --silent --max-time 2 http://127.0.0.1:4040/api/tunnels >/dev/null; then
    bash scripts/install_ngrok_autostart.sh
fi
wait_http http://127.0.0.1:4040/api/tunnels || fail "ngrokが起動しません。logs/ngrok.err.logを確認してください。"

# The inspector can start before the public tunnel is ready.
public_url=""
for attempt in {1..30}; do
    public_url="$(.venv/bin/python - <<'PY'
import json
import urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as response:
        tunnels = json.load(response).get("tunnels", [])
    for tunnel in tunnels:
        url = tunnel.get("public_url", "")
        upstream = tunnel.get("config", {}).get("addr", "")
        if url.startswith("https://") and upstream in (
            "http://localhost:8000", "http://127.0.0.1:8000", "localhost:8000", "127.0.0.1:8000", "8000"
        ):
            print(url)
            break
except (OSError, ValueError):
    pass
PY
)"
    [ -z "$public_url" ] || break
    sleep 1
done
[ -n "$public_url" ] || fail "8000番への公開URLを取得できません。http://127.0.0.1:4040 を確認してください。"
open "$public_url"
echo "起動確認が完了しました。公開URL：$public_url"
echo "このターミナルを閉じてもアプリは動き続けます。Macのスリープ中は利用できません。"
