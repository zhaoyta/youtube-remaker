#!/usr/bin/env python3
"""spoof.json + panels → 竖版恶搞口播短片。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageEnhance

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import media  # noqa: E402
import validate  # noqa: E402

W, H = 1080, 1920
FPS = 30
HISTORY = ROOT / "history.json"


def still_clip(image: Path, audio: Path, subtitle: str, dest: Path, sub_txt: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tts_dur = media.ffprobe_duration(audio)
    frames = max(int(round(tts_dur * FPS)), FPS)
    media.write_sub_txt(subtitle, sub_txt)
    ass_path = sub_txt.with_suffix(".ass")
    media.write_ass(subtitle, tts_dur, ass_path)
    vf = (
        f"scale=1200:2133:force_original_aspect_ratio=increase,"
        f"crop=1200:2133,"
        f"zoompan=z='min(1.0+0.0007*on,1.08)':x='iw/2-(iw/zoom/2)':"
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


def fit_panel(src: Path, dest: Path) -> None:
    """Cover 到 1080x1920，略提对比，底部微暗方便字幕。"""
    im = Image.open(src).convert("RGB")
    scale = max(W / im.width, H / im.height)
    nw, nh = max(int(im.width * scale), 1), max(int(im.height * scale), 1)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max((nw - W) // 2, 0)
    top = max((nh - H) // 2, 0)
    im = im.crop((left, top, left + W, top + H))
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(1.04)
    # 底部渐暗条（方便粉字幕）
    band = 220
    grad = Image.new("L", (1, band))
    for y in range(band):
        grad.putpixel((0, y), int(140 * y / band))
    grad = grad.resize((W, band))
    mask = Image.new("L", (W, H), 0)
    mask.paste(grad, (0, H - band))
    overlay = Image.new("RGB", (W, H), (8, 10, 14))
    im = Image.composite(overlay, im, mask)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "PNG")


def append_history(plan: dict) -> None:
    hist = validate.load_history()
    used = list(hist.get("used") or [])
    entry = {
        "slug": plan["slug"],
        "angle_key": plan["angle_key"],
        "pov": plan["pov"],
        "style": plan["style"],
        "hook_one_liner": plan.get("hook_one_liner"),
        "trend_source": plan.get("trend_source"),
        "cross_trend": plan.get("cross_trend"),
        "created": date.today().isoformat(),
    }
    if any(x.get("angle_key") == entry["angle_key"] for x in used):
        media.log(f"history 已有 {entry['angle_key']}，跳过追加")
        return
    used.append(entry)
    hist["used"] = used
    hist.setdefault("version", 1)
    hist.setdefault("account", "鱼公移山")
    hist.setdefault("series", "钓鱼恶搞")
    HISTORY.write_text(json.dumps(hist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    media.log(f"已写入 history.json: {entry['angle_key']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="恶搞 spoof.json → 竖版短片")
    parser.add_argument("--spoof", required=True)
    parser.add_argument("--workdir", help="输出目录，默认 spoof 所在目录")
    parser.add_argument("--bgm", help="背景音乐；默认 assets/bgm/default.mp3")
    parser.add_argument("--no-bgm", action="store_true")
    parser.add_argument("--bgm-volume", type=float, default=None)
    parser.add_argument("--no-history", action="store_true", help="成片后不写 history")
    parser.add_argument(
        "--force-tts",
        action="store_true",
        help="强制重生成口播（换音色后必加）",
    )
    args = parser.parse_args()

    spoof_path = Path(args.spoof).resolve()
    plan = validate.load_json(spoof_path)
    errs = validate.check(
        plan,
        spoof_path=spoof_path,
        rebuild=bool(args.force_tts or args.no_history),
    )
    if errs:
        for e in errs:
            media.log("校验失败: " + e)
        raise SystemExit(1)

    # 恶搞音色：JSON 可覆盖；鱼开麦默认 yunxia，翻车默认 xiaobei（见 SKILL §3）
    voice = plan.get("voice")
    rate = plan.get("rate")
    pitch = plan.get("pitch")
    if not voice:
        voice = "yunxia" if plan.get("pov") == "fish" else "xiaobei"
    if not rate:
        rate = "+22%"
    if not pitch:
        pitch = "+12Hz" if plan.get("pov") == "fish" else "+6Hz"
    media.log(f"口播音色: {media.resolve_voice(str(voice))}  rate={rate}  pitch={pitch}")

    workdir = Path(args.workdir).resolve() if args.workdir else spoof_path.parent
    workdir.mkdir(parents=True, exist_ok=True)
    cards = workdir / "cards"
    tts_dir = workdir / "tts"
    subs = workdir / "subs"
    parts_dir = workdir / "parts"
    for d in (cards, tts_dir, subs, parts_dir):
        d.mkdir(parents=True, exist_ok=True)

    if spoof_path != workdir / "spoof.json":
        (workdir / "spoof.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    parts: list[Path] = []
    plan_clips = []
    t_cursor = 0.0
    for i, panel in enumerate(plan["panels"]):
        rel = Path(str(panel["file"]))
        src = rel if rel.is_absolute() else (spoof_path.parent / rel)
        if not src.exists():
            # 也允许相对 workdir
            alt = workdir / rel
            if alt.exists():
                src = alt
            else:
                raise SystemExit(f"找不到分镜图: {src}")
        media.log(f"分镜 {i:02d} {src.name}")
        card = cards / f"{i:02d}.png"
        fit_panel(src, card)
        audio = tts_dir / f"{i:02d}.mp3"
        if args.force_tts or not audio.exists() or audio.stat().st_size == 0:
            if audio.exists():
                audio.unlink()
            media.tts(
                str(panel["script"]),
                audio,
                voice=str(voice),
                rate=str(rate),
                pitch=str(pitch),
            )
        else:
            media.log(f"复用口播 {audio.name}")
        part = parts_dir / f"{i:02d}.mp4"
        still_clip(card, audio, str(panel["script"]), part, subs / f"{i:02d}.txt")
        dur = media.ffprobe_duration(part)
        plan_clips.append(
            {
                "start": round(t_cursor, 3),
                "end": round(t_cursor + dur, 3),
                "script": panel["script"],
            }
        )
        t_cursor += dur
        parts.append(part)

    final = workdir / "final.mp4"
    media.concat_parts(parts, final)

    if not args.no_bgm:
        bgm = media.resolve_bgm(args.bgm or plan.get("bgm"))
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
        "angle_key": plan["angle_key"],
        "pov": plan["pov"],
        "style": plan["style"],
    }
    media.report_caption(caption_plan, workdir / "caption.txt")
    (workdir / "edit.json").write_text(
        json.dumps(caption_plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    media.log(f"成片: {final}  时长约 {t_cursor:.1f}s")
    if t_cursor < 18 or t_cursor > 50:
        media.log(f"注意：目标 20～45 秒，当前 {t_cursor:.1f}s，可改口播字数")

    if not args.no_history:
        append_history(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
