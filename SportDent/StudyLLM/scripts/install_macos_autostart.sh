#!/bin/bash
set -eu

service_label="jp.sportdent.studyllm"
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
python_path="${project_dir}/.venv/bin/python"
env_path="${project_dir}/.env"
log_dir="${project_dir}/logs"
agent_dir="${HOME}/Library/LaunchAgents"
agent_path="${agent_dir}/${service_label}.plist"
user_id="$(id -u)"

if [ ! -x "$python_path" ]; then
    echo "エラー: ${python_path} がありません。先に仮想環境とrequirementsを準備してください。" >&2
    exit 1
fi

printf "公開用ユーザー名 [admin]: "
IFS= read -r configured_username
configured_username="${configured_username:-admin}"
printf "公開用パスワード（12文字以上・入力は表示されません）: "
IFS= read -r -s configured_password
printf "\n"

if [ "${#configured_password}" -lt 12 ]; then
    echo "エラー: パスワードは12文字以上にしてください。" >&2
    exit 1
fi
case "${configured_username}${configured_password}" in
    *"'"*)
        echo "エラー: ユーザー名とパスワードにはシングルクォートを使用できません。" >&2
        exit 1
        ;;
esac

session_secret="$(openssl rand -hex 32)"
umask 077
mkdir -p "$log_dir" "$agent_dir"

cat > "$env_path" <<EOF
SPORTDENT_USERNAME='${configured_username}'
SPORTDENT_PASSWORD='${configured_password}'
SPORTDENT_SESSION_SECRET='${session_secret}'
SPORTDENT_EXTRACTOR='ollama'
SPORTDENT_OLLAMA_MODEL='qwen3:8b'
SPORTDENT_HOST='127.0.0.1'
SPORTDENT_PORT='8000'
SPORTDENT_RELOAD='0'
EOF
chmod 600 "$env_path"

cat > "$agent_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${service_label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${python_path}</string>
    <string>${project_dir}/run.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${project_dir}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${log_dir}/studyllm.out.log</string>
  <key>StandardErrorPath</key>
  <string>${log_dir}/studyllm.err.log</string>
</dict>
</plist>
EOF
chmod 600 "$agent_path"

launchctl bootout "gui/${user_id}" "$agent_path" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${user_id}" "$agent_path"
launchctl kickstart -k "gui/${user_id}/${service_label}"

echo "StudyLLMの自動起動を設定しました。"
echo "ローカル確認: http://127.0.0.1:8000"
echo "ログ: ${log_dir}/studyllm.err.log"
