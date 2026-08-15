#!/usr/bin/env python3
"""lesson.json → 真实配图教学卡 + 女声口播竖版片。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import catalog as cat  # noqa: E402
import draw  # noqa: E402
import fetch_images  # noqa: E402
import media  # noqa: E402
import slides  # noqa: E402
import validate  # noqa: E402

W, H = 1080, 1920
FPS = 30


def still_clip(image: Path, audio: Path, subtitle: str, dest: Path, sub_txt: Path) -> None:
    """短句 ASS 字幕按时长轮播，不再整段口播一坨贴底。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tts_dur = media.ffprobe_duration(audio)
    frames = max(int(round(tts_dur * FPS)), FPS)
    media.write_sub_txt(subtitle, sub_txt)
    ass_path = sub_txt.with_suffix(".ass")
    media.write_ass(subtitle, tts_dur, ass_path)
    vf = (
        f"scale=1200:2133:force_original_aspect_ratio=increase,"
        f"crop=1200:2133,"
        f"zoompan=z='min(1.0+0.00055*on,1.06)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        f"{media.ass_filter(ass_path)}"
    )
    inputs = ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio)]
    mark = media.WATERMARK if media.WATERMARK.exists() else None
    if mark:
        graph = (
            f"[0:v]{vf}[vbase];"
            f"[2:v]format=rgba,colorkey=0x000000:0.12:0.08,scale=280:-1[wm];"
            f"[vbase][wm]overlay=W-w-24:16[v];"
            f"[1:a]apad=whole_dur={tts_dur:.3f},atrim=duration={tts_dur:.3f},"
            f"asetpts=PTS-STARTPTS[a]"
        )
        inputs.extend(["-i", str(mark)])
    else:
        graph = (
            f"[0:v]{vf}[v];"
            f"[1:a]apad=whole_dur={tts_dur:.3f},atrim=duration={tts_dur:.3f},"
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
            f"{tts_dur:.3f}",
            "-r",
            str(FPS),
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


def _maybe_cutout(im: Image.Image, cache_path: Path) -> Image.Image:
    """照片抠主体并缓存；结构绘制跳过。"""
    cut = cache_path.with_suffix(cache_path.suffix + ".cutout.png")
    if cut.exists() and cut.stat().st_size > 0:
        return Image.open(cut)
    out = slides.cutout_photo(im)
    try:
        out.save(cut, "PNG")
    except Exception:
        pass
    return out


def resolve_visual(vis: dict, cache: Path) -> tuple[Image.Image, str]:
    kind = vis.get("kind")
    if kind == "fish":
        _, entry = cat.resolve_fish(str(vis.get("name") or vis.get("model")))
        info = fetch_images.resolve_fish_image(entry, cache)
        im = _maybe_cutout(Image.open(info["path"]), Path(info["path"]))
        credit = f"图：Wikimedia · {entry['scientific']} · {info.get('license') or ''}"
        return im, credit.strip()
    if kind == "wikimedia":
        file_name = vis.get("file")
        if file_name:
            info = fetch_images.file_info(str(file_name))
            if not info:
                raise SystemExit(f"Wikimedia 没有这份文件: {file_name}")
            info = fetch_images._save(info, cache)
        else:
            info = fetch_images.search_file(str(vis.get("scientific")))
            if not info:
                raise SystemExit(f"搜不到 Wikimedia: {vis.get('scientific')}")
            info = fetch_images._save(info, cache)
        im = _maybe_cutout(Image.open(info["path"]), Path(info["path"]))
        credit = f"图：Wikimedia · {info.get('title')} · {info.get('license') or ''}"
        return im, credit
    if kind == "hook":
        im = draw.render_visual(vis)
        return im, "按市面真实钩型几何绘制"
    if kind == "line":
        im = draw.render_visual(vis)
        return im, "按常见线号/线径对照绘制，不是品牌包装"
    if kind == "bait":
        _, entry = cat.resolve_bait(str(vis.get("name") or vis.get("model")))
        if entry.get("kind") == "draw":
            im = draw.render_visual(vis)
            return im, "按真实饵料状态绘制，不是商品袋"
        info = fetch_images.resolve_fish_image(entry, cache)
        im = _maybe_cutout(Image.open(info["path"]), Path(info["path"]))
        credit = f"图：Wikimedia · {entry.get('scientific')} · {info.get('license') or ''}"
        return im, credit.strip()
    if kind in ("gear", "rig"):
        im = draw.render_visual(vis)
        return im, "按真实装备结构绘制"
    raise SystemExit(f"未知 visual kind: {kind}")


def render_one(slide: dict, cache: Path, dest: Path) -> list[str]:
    images: list[Image.Image] = []
    credits: list[str] = []
    for vis in slide.get("visuals") or []:
        im, credit = resolve_visual(vis, cache)
        images.append(im)
        credits.append(credit)
    # 不把图源写进画面
    card = slides.render_slide(slide, images)
    dest.parent.mkdir(parents=True, exist_ok=True)
    card.save(dest, "PNG")
    return credits


def main() -> int:
    parser = argparse.ArgumentParser(description="教学课 JSON → 竖版图文口播")
    parser.add_argument("--lesson", required=True, help="lesson.json")
    parser.add_argument("--workdir", help="输出目录，默认 output/<slug>")
    parser.add_argument("--bgm", help="背景音乐路径；默认 assets/bgm/default.mp3")
    parser.add_argument("--no-bgm", action="store_true", help="不要背景音乐")
    parser.add_argument("--bgm-volume", type=float, default=None, help="BGM 音量，默认 0.12")
    args = parser.parse_args()

    media.require_deps()
    lesson_path = Path(args.lesson).resolve()
    plan = validate.load_lesson(lesson_path)
    errs = validate.check(plan)
    if errs:
        for e in errs:
            media.log("校验失败: " + e)
        raise SystemExit(1)

    slug = str(plan["slug"]).strip()
    workdir = Path(args.workdir).resolve() if args.workdir else Path.cwd() / "output" / slug
    workdir.mkdir(parents=True, exist_ok=True)
    cards = workdir / "cards"
    tts_dir = workdir / "tts"
    subs = workdir / "subs"
    parts_dir = workdir / "parts"
    cache = workdir / "images"
    for d in (cards, tts_dir, subs, parts_dir, cache):
        d.mkdir(parents=True, exist_ok=True)

    if lesson_path != workdir / "lesson.json":
        (workdir / "lesson.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    parts: list[Path] = []
    plan_clips = []
    all_credits: list[str] = []
    t_cursor = 0.0
    for i, slide in enumerate(plan["slides"]):
        media.log(f"绘页 {i:02d} {slide.get('layout')} {slide.get('title')}")
        png = cards / f"{i:02d}.png"
        all_credits.extend(render_one(slide, cache, png))
        media.log(f"口播 {i:02d}")
        audio = tts_dir / f"{i:02d}.mp3"
        if not audio.exists() or audio.stat().st_size == 0:
            media.tts(str(slide["script"]), audio)
        else:
            media.log(f"复用口播 {audio.name}")
        part = parts_dir / f"{i:02d}.mp4"
        still_clip(png, audio, str(slide["script"]), part, subs / f"{i:02d}.txt")
        dur = media.ffprobe_duration(part)
        plan_clips.append(
            {
                "start": round(t_cursor, 3),
                "end": round(t_cursor + dur, 3),
                "script": slide["script"],
                "title": slide.get("title"),
            }
        )
        t_cursor += dur
        parts.append(part)

    final = workdir / "final.mp4"
    media.concat_parts(parts, final)

    if not args.no_bgm:
        bgm_key = args.bgm or plan.get("bgm")
        bgm = media.resolve_bgm(bgm_key)
        if bgm:
            vol = args.bgm_volume if args.bgm_volume is not None else media.BGM_VOLUME
            media.mix_bgm(final, final, bgm, volume=vol)
        else:
            media.log("未找到 BGM，成片仅口播")
    else:
        media.log("已跳过 BGM（--no-bgm）")

    caption_plan = {
        "douyin_title": plan["douyin_title"],
        "douyin_intro": plan["douyin_intro"],
        "douyin_tags": plan["douyin_tags"],
        "clips": plan_clips,
        "image_credits": list(dict.fromkeys(all_credits)),
    }
    media.report_caption(caption_plan, workdir / "caption.txt")
    (workdir / "edit.json").write_text(
        json.dumps(caption_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    media.log(f"成片: {final}  时长约 {t_cursor:.1f}s")
    if t_cursor < 150 or t_cursor > 210:
        media.log(f"注意：目标约 3 分钟，当前 {t_cursor/60:.1f} 分钟，下一集改口播字数")
    return 0


if __name__ == "__main__":
    sys.exit(main())
