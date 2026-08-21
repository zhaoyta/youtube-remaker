#!/usr/bin/env python3
"""检查 ffmpeg / edge-tts / pillow。"""

from __future__ import annotations

import shutil
import sys


def main() -> int:
    ok = True
    for bin_name in ("ffmpeg", "ffprobe"):
        path = shutil.which(bin_name)
        if path:
            print(f"[ok] {bin_name}: {path}")
        else:
            print(f"[missing] {bin_name}", file=sys.stderr)
            ok = False
    try:
        import edge_tts  # noqa: F401

        print("[ok] edge_tts")
    except ImportError:
        print("[missing] edge_tts", file=sys.stderr)
        ok = False
    try:
        from PIL import Image  # noqa: F401

        print("[ok] pillow")
    except ImportError:
        print("[missing] pillow", file=sys.stderr)
        ok = False
    if not ok:
        print("依赖不齐。先: bash skills/fishing-parody-video/scripts/setup_venv.sh", file=sys.stderr)
        return 1
    print("[parody] deps ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
