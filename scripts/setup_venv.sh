#!/usr/bin/env bash
# 用 uv 创建 Python 3.11 虚拟环境并安装 requirements.txt。不要用系统 python3。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v uv >/dev/null 2>&1; then
  echo "找不到 uv。先安装: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "[uv] uv venv --python 3.11"
  uv venv --python 3.11 "$ROOT/.venv"
fi

ver="$("$ROOT/.venv/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if [[ "$ver" != "3.11" ]]; then
  echo "[uv] .venv 是 Python ${ver}，需要 3.11，正在重建"
  rm -rf "$ROOT/.venv"
  uv venv --python 3.11 "$ROOT/.venv"
fi

stamp="$ROOT/.venv/.deps-ok"
if [[ ! -f "$stamp" || "$ROOT/requirements.txt" -nt "$stamp" ]]; then
  echo "[uv] uv pip install -r requirements.txt"
  uv pip install -r "$ROOT/requirements.txt" --python "$ROOT/.venv/bin/python"
  touch "$stamp"
fi

echo "[uv] 就绪: $("$ROOT/.venv/bin/python" -V)  ($ROOT/.venv)"
