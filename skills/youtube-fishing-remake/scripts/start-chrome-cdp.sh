#!/usr/bin/env bash
set -euo pipefail

PORT="${CHROME_CDP_PORT:-9222}"
USER_DIR="${CHROME_USER_DATA_DIR:-$HOME/.youtube-remaker/chrome-profile}"
CDP="http://127.0.0.1:${PORT}"
CHROME="${CHROME_BIN:-}"

if [[ -z "$CHROME" ]]; then
  if [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  elif command -v google-chrome >/dev/null 2>&1; then
    CHROME="$(command -v google-chrome)"
  elif command -v chromium >/dev/null 2>&1; then
    CHROME="$(command -v chromium)"
  else
    echo "找不到 Google Chrome。请设置 CHROME_BIN。" >&2
    exit 1
  fi
fi

if curl -sf "${CDP}/json/version" >/dev/null; then
  echo "Chrome CDP 已在 ${CDP} 运行"
  curl -s "${CDP}/json/version"
  exit 0
fi

mkdir -p "$USER_DIR"
echo "启动独立 Chrome（不影响你日常那个浏览器）"
echo "  CDP:  ${CDP}"
echo "  配置: ${USER_DIR}"
echo "第一次请在这个窗口登录 Google，并打开 https://gemini.google.com/app"

nohup "$CHROME" \
  --remote-debugging-port="$PORT" \
  --remote-debugging-address=127.0.0.1 \
  --user-data-dir="$USER_DIR" \
  --no-first-run \
  --no-default-browser-check \
  "https://gemini.google.com/app" >/dev/null 2>&1 &
disown || true

for _ in $(seq 1 25); do
  if curl -sf "${CDP}/json/version" >/dev/null; then
    echo "CDP 就绪: ${CDP}"
    exit 0
  fi
  sleep 0.4
done

echo "Chrome 已启动但 ${CDP} 无响应。检查是否被系统拦截。" >&2
exit 1
