#!/usr/bin/env python3
"""复用已有卡片/口播，只重渲硬字幕层并拼接。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import media  # noqa: E402
from build import load_plan, still_clip  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="只重渲字幕并拼接成片")
    parser.add_argument("--workdir", required=True, help="成片工作目录")
    args = parser.parse_args()
    workdir = Path(args.workdir).resolve()
    plan = load_plan(workdir / "spots.json")
    cards = workdir / "cards"
    tts_dir = workdir / "tts"
    subs = workdir / "subs"
    parts_dir = workdir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for p in parts_dir.glob("*.mp4"):
        p.unlink()

    clips = [
        {
            "image": cards / "00_overview.png",
            "overlay": plan["title"],
            "script": plan["intro_script"],
        },
    ]
    for s in plan["spots"]:
        n = int(s["n"])
        clips.append(
            {
                "image": cards / f"{n:02d}.png",
                "overlay": s["name"],
                "script": s["script"],
            }
        )
    clips.append(
        {
            "image": cards / "outro.png",
            "overlay": plan["outro_title"],
            "script": plan["outro_script"],
        }
    )

    parts: list[Path] = []
    plan_clips = []
    t_cursor = 0.0
    for i, clip in enumerate(clips):
        audio = tts_dir / f"{i:02d}.mp3"
        if not audio.exists():
            media.log(f"补口播 {i:02d}")
            media.tts(clip["script"], audio)
        media.log(f"重渲字幕 {i:02d} {clip['overlay']}")
        part = parts_dir / f"{i:02d}.mp4"
        still_clip(clip["image"], audio, clip["script"], part, subs / f"{i:02d}.txt")
        dur = media.ffprobe_duration(part)
        plan_clips.append(
            {
                "start": round(t_cursor, 3),
                "end": round(t_cursor + dur, 3),
                "script": clip["script"],
                "overlay": clip["overlay"],
            }
        )
        t_cursor += dur
        parts.append(part)

    final = workdir / "final.mp4"
    media.concat_parts(parts, final)
    caption_plan = {
        "douyin_title": plan["douyin_title"],
        "douyin_intro": plan["douyin_intro"],
        "douyin_tags": plan["douyin_tags"],
        "clips": plan_clips,
    }
    media.report_caption(caption_plan, workdir / "caption.txt")
    (workdir / "edit.json").write_text(
        json.dumps(caption_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    media.log(f"成片: {final}  时长约 {t_cursor:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
