#!/usr/bin/env python3
"""各区 final.mp4 前加居中区名大标题，再拼成一条合集。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import media  # noqa: E402

W, H = 1080, 1920
FPS = 30
PINGFANG = "/System/Library/Fonts/PingFang.ttc"
HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"
NAVY = (11, 16, 32)
CREAM = (255, 244, 214)
MUTED = (168, 178, 196)
ORANGE = (255, 122, 48)
WHITE = (245, 247, 250)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = PINGFANG if Path(PINGFANG).exists() else HEITI
    idx = 1 if bold and path == PINGFANG else 0
    try:
        return ImageFont.truetype(path, size, index=idx)
    except OSError:
        return ImageFont.truetype(path, size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def render_title(city: str, area: str, n: int, extra: str, dest: Path) -> None:
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    city_f = font(44)
    area_f = font(200, bold=True)
    sub_f = font(44)
    extra_f = font(32)
    cw, ch = text_size(draw, city, city_f)
    aw, ah = text_size(draw, area, area_f)
    sub = f"{n} 个免费掉点"
    sw, sh = text_size(draw, sub, sub_f)
    cy = 640
    draw.text(((W - cw) / 2, cy), city, font=city_f, fill=MUTED)
    ay = cy + ch + 36
    draw.text(((W - aw) / 2, ay), area, font=area_f, fill=CREAM)
    bar_y = ay + ah + 28
    draw.rectangle((W / 2 - 80, bar_y, W / 2 + 80, bar_y + 8), fill=ORANGE)
    draw.text(((W - sw) / 2, bar_y + 36), sub, font=sub_f, fill=WHITE)
    if extra:
        ew, _ = text_size(draw, extra, extra_f)
        draw.text(((W - ew) / 2, bar_y + 36 + sh + 24), extra, font=extra_f, fill=MUTED)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG")


def title_clip(image: Path, audio: Path, dest: Path, min_dur: float = 2.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tts_dur = media.ffprobe_duration(audio)
    dur = max(tts_dur, min_dur)
    frames = max(int(round(dur * FPS)), FPS)
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"zoompan=z='min(1.0+0.0004*on,1.04)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
    )
    inputs = ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio)]
    mark = media.WATERMARK if media.WATERMARK.exists() else None
    if mark:
        graph = (
            f"[0:v]{vf}[vbase];"
            f"[2:v]format=rgba,colorkey=0x000000:0.12:0.08,scale=400:-1[wm];"
            f"[vbase][wm]overlay=W-w-{getattr(media, 'WATERMARK_MARGIN', 24)}:{getattr(media, 'WATERMARK_MARGIN', 24)}[v];"
            f"[1:a]apad=whole_dur={dur:.3f},atrim=duration={dur:.3f},"
            f"asetpts=PTS-STARTPTS[a]"
        )
        inputs.extend(["-i", str(mark)])
    else:
        graph = (
            f"[0:v]{vf}[v];"
            f"[1:a]apad=whole_dur={dur:.3f},atrim=duration={dur:.3f},"
            f"asetpts=PTS-STARTPTS[a]"
        )
    media.run(
        inputs
        + [
            "-filter_complex",
            graph,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{dur:.3f}",
            "-r",
            str(FPS),
            "-video_track_timescale",
            "15360",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="按区成片加标题后合并")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--workdir", required=True)
    args = parser.parse_args()
    media.require_deps()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    workdir = Path(args.workdir).resolve()
    titles = workdir / "merge_titles"
    titles.mkdir(parents=True, exist_ok=True)
    city = str(manifest.get("city") or "本市")
    parts: list[Path] = []
    for i, item in enumerate(manifest["videos"]):
        area = str(item["area"])
        n = int(item["spots"])
        src = Path(item["workdir"]) / "final.mp4"
        if not src.exists():
            raise SystemExit(f"缺少成片 {src}")
        extra = ""
        merged = item.get("merged_from") or []
        if merged:
            extra = "含" + "、".join(str(x) for x in merged)
        png = titles / f"{i:02d}_{area}.png"
        mp3 = titles / f"{i:02d}_{area}.mp3"
        clip = titles / f"{i:02d}_{area}.mp4"
        media.log(f"区标题 {area}")
        render_title(city, area, n, extra, png)
        spoken = f"{city}，{area}。" if i == 0 else f"下一段，{area}。"
        media.tts(spoken, mp3)
        title_clip(png, mp3, clip)
        parts.append(clip)
        parts.append(src)
    final = workdir / "final_merged.mp4"
    media.log(f"拼接 {len(parts)} 段")
    media.concat_parts(parts, final)
    media.log(f"合集: {final}  约 {media.ffprobe_duration(final):.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
