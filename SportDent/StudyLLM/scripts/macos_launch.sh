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
    until curl --noproxy '*' --fail --silent --max-time 2 "$endpoint" >/dev/null; do
        attempts=$((attempts + 1))
        [ "$attempts" -lt 30 ] || return 1
        sleep 1
    done
}

log_size() {
    if [ -f "$1" ]; then wc -c < "$1"; else echo 0; fi
}

show_new_log() {
    local path="$1" previous_size="$2" current_size
    current_size="$(log_size "$path")"
    printf '%s（今回の起動操作以降・最大30行）:\n' "$path"
    if [ "$current_size" -gt "$previous_size" ]; then
        tail -c "+$((previous_size + 1))" "$path" | tail -n 30
    elif [ "$current_size" -lt "$previous_size" ]; then
        echo "ログが短くなったため、今回分を特定できません。"
    else
        echo "新しいログはありません。"
    fi
}

show_app_diagnostics() {
    local http_code curl_status=0 service_status
    http_code="$(curl --noproxy '*' --silent --show-error --max-time 2 \
        --output /dev/null --write-out '%{http_code}' http://127.0.0.1:8000)" || curl_status=$?
    if [ "$curl_status" -eq 0 ]; then
        printf 'ローカル接続確認: HTTP %s\n' "$http_code"
    else
        printf 'ローカル接続確認に失敗しました（curl終了コード: %s、HTTP: %s）。\n' "$curl_status" "$http_code"
    fi
    # Do not print the full service record: custom setups may include secrets.
    service_status="$(launchctl print "gui/$user_id/$app_label" 2>/dev/null \
        | sed -n -E '/^[[:space:]]*(state|pid|last exit code|last terminating signal) = /p')"
    echo "StudyLLMサービスの状態:"
    if [ -n "$service_status" ]; then
        printf '%s\n' "$service_status"
    else
        echo "状態を取得できませんでした。"
    fi
    show_new_log logs/studyllm.err.log "$app_err_offset"
    show_new_log logs/studyllm.out.log "$app_out_offset"
}

[ "$(uname -s)" = Darwin ] || fail "このボタンはMac専用です。"
mode="${1:-start}"
case "$mode" in
    update)
        echo "GitHubから更新を取得しています…"
        repo_dir="$(git rev-parse --show-toplevel)"
        [ "$(git branch --show-current)" = main ] || fail "main以外のブランチです。更新を停止します。"
        # Git allows unrelated local files and rejects overlapping changes.
        # Do not auto-stash credentials, local data, or user edits.
        if ! git -C "$repo_dir" pull --ff-only --no-rebase --no-autostash origin main; then
            fail "更新を停止しました。上のGitエラーを確認してください。競合する変更の自動退避・削除は行いません。"
        fi
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
app_err_offset="$(log_size logs/studyllm.err.log)"
app_out_offset="$(log_size logs/studyllm.out.log)"
echo "StudyLLMを起動しています…"
if ! launchctl print "gui/$user_id/$app_label" >/dev/null 2>&1; then
    [ -f "$app_plist" ] || fail "StudyLLMの自動起動設定がありません。手順書の初回設定を行ってください。"
    launchctl bootstrap "gui/$user_id" "$app_plist"
fi
launchctl kickstart -k "gui/$user_id/$app_label"
if ! wait_http http://127.0.0.1:8000; then
    echo "StudyLLMの起動確認に失敗しました。今回の接続状態とログ："
    show_app_diagnostics
    fail "ここまでのエラーを確認してください。"
fi

echo "公開接続を確認しています…"
if ! curl --noproxy '*' --fail --silent --max-time 2 http://127.0.0.1:4040/api/tunnels >/dev/null; then
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
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("http://127.0.0.1:4040/api/tunnels", timeout=2) as response:
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
