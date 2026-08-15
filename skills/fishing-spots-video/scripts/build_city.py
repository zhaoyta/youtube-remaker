#!/usr/bin/env python3
"""全城 JSON 去重、按区拆开，再逐区成片。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import split_spots  # noqa: E402

BUILD = SCRIPT_DIR / "build.py"


def main() -> int:
    parser = argparse.ArgumentParser(description="一城多区掉点成片")
    parser.add_argument("--spots", required=True, help="全城 all.json / spots.json")
    parser.add_argument("--workdir", required=True, help="output/<city>/")
    parser.add_argument("--dedupe-m", type=float, default=500)
    parser.add_argument("--min-spots", type=int, default=4)
    args = parser.parse_args()

    workdir = Path(args.workdir).resolve()
    manifest = split_spots.run_split(
        Path(args.spots).resolve(),
        workdir,
        dedupe_m=args.dedupe_m,
        min_spots=args.min_spots,
    )
    print(
        f"[city] {manifest['city']} 原始 {manifest['raw']} → 去重 {manifest['after_dedupe']} → {len(manifest['videos'])} 条片子",
        flush=True,
    )
    for item in manifest["videos"]:
        extra = f" 并入 {','.join(item['merged_from'])}" if item["merged_from"] else ""
        print(f"[city] 成片 {item['area']} {item['spots']} 点{extra}", flush=True)
        subprocess.run(
            [
                sys.executable,
                str(BUILD),
                "--spots",
                item["json"],
                "--workdir",
                item["workdir"],
            ],
            check=True,
        )
    print(json.dumps(manifest["videos"], ensure_ascii=False, indent=2), flush=True)
    print(f"[city] manifest: {workdir / 'manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
