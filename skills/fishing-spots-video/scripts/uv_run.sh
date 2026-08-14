#!/usr/bin/env bash
# 在 uv 的 Python 3.11 venv 里执行脚本。用法: bash scripts/uv_run.sh scripts/check_deps.py
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/setup_venv.sh"
export PATH="$ROOT/.venv/bin:$PATH"
exec "$ROOT/.venv/bin/python" "$@"
