#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="youtube-fishing-remake"
CURSOR_DEST="${HOME}/.cursor/skills/${SKILL_NAME}"
CLAUDE_DEST="${HOME}/.claude/skills/${SKILL_NAME}"

usage() {
  cat <<'EOF'
用法:
  ./install.sh              交互选择安装到 Cursor / Claude / 两者
  ./install.sh cursor       装到 ~/.cursor/skills/youtube-fishing-remake
  ./install.sh claude       装到 ~/.claude/skills/youtube-fishing-remake
  ./install.sh both         两处都装
  ./install.sh uninstall    卸掉两处的 skill 副本（不删本仓库）

Python 一律 uv venv --python 3.11，不要用系统 python3。
EOF
}

need_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    echo "找不到 uv。先安装: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
  fi
}

copy_skill() {
  local dest="$1"
  mkdir -p "$dest/scripts" "$dest/prompts"
  cp "${ROOT}/SKILL.md" "${ROOT}/requirements.txt" "$dest/"
  if [[ -f "${ROOT}/.python-version" ]]; then
    cp "${ROOT}/.python-version" "$dest/"
  fi
  if [[ -f "${ROOT}/md/usage.md" ]]; then
    cp "${ROOT}/md/usage.md" "$dest/usage.md"
  fi
  rsync -a --delete "${ROOT}/scripts/" "$dest/scripts/"
  rsync -a --delete "${ROOT}/prompts/" "$dest/prompts/"
  if [[ -d "${ROOT}/assets" ]]; then
    rsync -a --delete "${ROOT}/assets/" "$dest/assets/"
  fi
  chmod +x "$dest/scripts/"*.sh "$dest/scripts/"*.py 2>/dev/null || true
  echo "已安装 -> $dest"
  if [[ "${SKIP_VENV:-}" != "1" ]]; then
    bash "$dest/scripts/setup_venv.sh"
  fi
}

uninstall() {
  rm -rf "$CURSOR_DEST" "$CLAUDE_DEST"
  echo "已删除:"
  echo "  $CURSOR_DEST"
  echo "  $CLAUDE_DEST"
}

need_rsync() {
  if ! command -v rsync >/dev/null 2>&1; then
    echo "需要 rsync。" >&2
    exit 1
  fi
}

setup_repo_venv() {
  if [[ "${SKIP_VENV:-}" == "1" ]]; then
    return
  fi
  bash "${ROOT}/scripts/setup_venv.sh"
}

check_tools() {
  bash "${ROOT}/scripts/uv_run.sh" "${ROOT}/scripts/check_deps.py" \
    || echo "依赖未齐。系统工具用 brew 装，Python 包由 uv venv 安装。"
}

target="${1:-}"
if [[ "$target" == "-h" || "$target" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "$target" == "uninstall" ]]; then
  uninstall
  exit 0
fi

if [[ -z "$target" ]]; then
  echo "把 skill 安装到哪里？"
  echo "  1) Cursor  (~/.cursor/skills/${SKILL_NAME})"
  echo "  2) Claude  (~/.claude/skills/${SKILL_NAME})"
  echo "  3) 两者都装"
  read -r -p "选 1/2/3: " choice
  case "$choice" in
    1) target="cursor" ;;
    2) target="claude" ;;
    3) target="both" ;;
    *) echo "无效选择"; exit 1 ;;
  esac
fi

need_uv
need_rsync
setup_repo_venv
case "$target" in
  cursor) copy_skill "$CURSOR_DEST" ;;
  claude) copy_skill "$CLAUDE_DEST" ;;
  both)
    copy_skill "$CURSOR_DEST"
    copy_skill "$CLAUDE_DEST"
    ;;
  *)
    usage
    exit 1
    ;;
esac

check_tools
echo
echo "运行脚本请用: bash scripts/uv_run.sh scripts/check_deps.py"
echo "下一步: bash scripts/start-chrome-cdp.sh"
echo "然后在调试 Chrome 里登录 Google，打开 Gemini。"
echo "用法见 md/usage.md"
