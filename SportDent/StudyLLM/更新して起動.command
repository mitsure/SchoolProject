#!/bin/bash
cd "$(dirname "$0")" || exit 1
bash scripts/macos_launch.sh update
result=$?
printf '\nEnterキーで閉じます。'
read -r _
exit "$result"
