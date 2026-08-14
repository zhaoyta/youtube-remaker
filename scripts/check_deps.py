#!/usr/bin/env python3
"""运行前检查 ffmpeg / yt-dlp / edge-tts。缺任何一个就退出。"""

from __future__ import annotations

import shutil
import subprocess
import sys

INSTALL_HINT = {
    "ffmpeg": "brew install ffmpeg",
    "ffprobe": "brew install ffmpeg",
    "yt-dlp": "brew install yt-dlp",
    "edge-tts": "bash scripts/setup_venv.sh",
    "python3.11-venv": "bash scripts/uv_run.sh <脚本>   # 内部会 uv venv --python 3.11",
}


def have_bin(name: str) -> bool:
    return shutil.which(name) is not None


def have_edge_tts() -> bool:
    if have_bin("edge-tts"):
        return True
    try:
        subprocess.run(
            [sys.executable, "-c", "import edge_tts"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def probe_ffmpeg() -> bool:
    if not have_bin("ffmpeg"):
        return False
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def python_ok() -> bool:
    return sys.version_info[:2] == (3, 11)


def in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def check() -> list[str]:
    missing: list[str] = []
    if not python_ok() or not in_venv():
        missing.append("python3.11-venv")
    if not probe_ffmpeg():
        missing.append("ffmpeg")
    if not have_bin("ffprobe"):
        missing.append("ffprobe")
    if not have_bin("yt-dlp"):
        missing.append("yt-dlp")
    if not have_edge_tts():
        missing.append("edge-tts")
    return missing


def report(missing: list[str]) -> None:
    print("[deps] 检查本机依赖：", flush=True)
    status = {
        "python3.11-venv": "python3.11-venv" not in missing,
        "ffmpeg": "ffmpeg" not in missing,
        "yt-dlp": "yt-dlp" not in missing,
        "edge-tts": "edge-tts" not in missing,
        "ffprobe": "ffprobe" not in missing,
    }
    print(
        f"[deps] Python {sys.version.split()[0]}  prefix={sys.prefix}",
        flush=True,
    )
    for name, ok in status.items():
        print(f"  {'ok ' if ok else '缺 '} {name}", flush=True)
    if not missing:
        print("[deps] 全部就绪", flush=True)
        return
    print("[deps] 缺少依赖，先安装再运行：", flush=True)
    seen = set()
    for name in missing:
        hint = INSTALL_HINT.get(name, name)
        if hint in seen:
            continue
        seen.add(hint)
        print(f"  {hint}", flush=True)


def main() -> int:
    missing = check()
    report(missing)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
