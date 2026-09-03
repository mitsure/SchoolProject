#!/bin/bash
set -eu

service_label="jp.sportdent.ngrok"
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
log_dir="${project_dir}/logs"
agent_dir="${HOME}/Library/LaunchAgents"
agent_path="${agent_dir}/${service_label}.plist"
user_id="$(id -u)"
ngrok_path="$(command -v ngrok || true)"

if [ -z "$ngrok_path" ]; then
    echo "エラー: ngrokが見つかりません。先に brew install ngrok を実行してください。" >&2
    exit 1
fi

mkdir -p "$log_dir" "$agent_dir"

cat > "$agent_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${service_label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${ngrok_path}</string>
    <string>http</string>
    <string>8000</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${log_dir}/ngrok.out.log</string>
  <key>StandardErrorPath</key>
  <string>${log_dir}/ngrok.err.log</string>
</dict>
</plist>
EOF
chmod 600 "$agent_path"

launchctl bootout "gui/${user_id}" "$agent_path" >/dev/null 2>&1 || true
launchctl bootstrap "gui/${user_id}" "$agent_path"
launchctl kickstart -k "gui/${user_id}/${service_label}"

echo "ngrokの自動起動を設定しました。"
echo "公開URLはngrok管理画面、または http://127.0.0.1:4040 で確認できます。"
echo "公開停止: launchctl bootout gui/${user_id} ${agent_path}"
echo "再開: launchctl bootstrap gui/${user_id} ${agent_path}"
