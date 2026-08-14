#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${ROOT}/skills"

usage() {
  cat <<'EOF'
用法:
  ./install.sh                         交互：装全部 skill 到 Cursor / Claude / 两者
  ./install.sh cursor                  全部 skill → ~/.cursor/skills/<name>
  ./install.sh claude                  全部 skill → ~/.claude/skills/<name>
  ./install.sh both                    两处都装全部 skill
  ./install.sh cursor <skill-name>     只装一个
  ./install.sh uninstall               卸掉已安装的本仓库 skill（不删仓库）

skill 源码在 skills/<name>/，互相隔离。Python 一律 uv venv --python 3.11。
也可用: sh install.sh cursor
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "找不到 $1。$2" >&2
    exit 1
  fi
}

copy_one() {
  name="$1"
  dest="$2"
  src="${SKILLS_DIR}/${name}"
  if [ ! -f "${src}/SKILL.md" ]; then
    echo "没有这个 skill: ${name}（应在 skills/${name}/SKILL.md）" >&2
    echo "现有：" >&2
    for d in "${SKILLS_DIR}"/*/SKILL.md; do
      [ -f "$d" ] || continue
      echo "  $(basename "$(dirname "$d")")" >&2
    done
    exit 1
  fi
  mkdir -p "$dest"
  rsync -a --delete \
    --exclude '.venv/' \
    --exclude 'output/' \
    --exclude 'tiles/' \
    --exclude 'cards/' \
    --exclude '__pycache__/' \
    "${src}/" "${dest}/"
  chmod +x "${dest}/scripts/"*.sh "${dest}/scripts/"*.py 2>/dev/null || true
  echo "已安装 ${name} -> ${dest}"
  if [ "${SKIP_VENV:-}" != "1" ] && [ -x "${dest}/scripts/setup_venv.sh" ]; then
    bash "${dest}/scripts/setup_venv.sh"
  fi
}

install_to() {
  dest_root="$1"
  filter="${2:-}"
  found=0
  for d in "${SKILLS_DIR}"/*/SKILL.md; do
    [ -f "$d" ] || continue
    name="$(basename "$(dirname "$d")")"
    if [ -n "$filter" ] && [ "$name" != "$filter" ]; then
      continue
    fi
    copy_one "$name" "${dest_root}/${name}"
    found=1
  done
  if [ "$found" -eq 0 ]; then
    echo "skills/ 下没有可安装的 SKILL.md${filter:+（过滤: $filter）}" >&2
    exit 1
  fi
}

uninstall() {
  for d in "${SKILLS_DIR}"/*/SKILL.md; do
    [ -f "$d" ] || continue
    name="$(basename "$(dirname "$d")")"
    rm -rf "${HOME}/.cursor/skills/${name}" "${HOME}/.claude/skills/${name}"
    echo "已删除 ~/.cursor/skills/${name}  ~/.claude/skills/${name}"
  done
}

list_names() {
  for d in "${SKILLS_DIR}"/*/SKILL.md; do
    [ -f "$d" ] || continue
    printf '%s ' "$(basename "$(dirname "$d")")"
  done
  printf '\n'
}

target="${1:-}"
skill_filter="${2:-}"

if [ "$target" = "-h" ] || [ "$target" = "--help" ]; then
  usage
  exit 0
fi
if [ "$target" = "uninstall" ]; then
  uninstall
  exit 0
fi

if [ -z "$target" ]; then
  echo "安装这些 skill: $(list_names)"
  echo "装到哪里？"
  echo "  1) Cursor  (~/.cursor/skills/<name>)"
  echo "  2) Claude  (~/.claude/skills/<name>)"
  echo "  3) 两者都装"
  printf "选 1/2/3: "
  read -r choice
  case "$choice" in
    1) target="cursor" ;;
    2) target="claude" ;;
    3) target="both" ;;
    *) echo "无效选择"; exit 1 ;;
  esac
fi

need_cmd uv "先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
need_cmd rsync "需要 rsync。"

case "$target" in
  cursor) install_to "${HOME}/.cursor/skills" "$skill_filter" ;;
  claude) install_to "${HOME}/.claude/skills" "$skill_filter" ;;
  both)
    install_to "${HOME}/.cursor/skills" "$skill_filter"
    install_to "${HOME}/.claude/skills" "$skill_filter"
    ;;
  *)
    usage
    exit 1
    ;;
esac

echo
echo "仓库里跑脚本请从仓库根目录："
echo "  sh skills/<name>/scripts/uv_run.sh skills/<name>/scripts/check_deps.py"
echo "用法见各 skill 的 SKILL.md"
