#!/usr/bin/env python3
"""OSM 地图标注卡 + 女声口播 → 竖版掉点合集。"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import media  # noqa: E402

W, H = 1080, 1920
FPS = 30
UA = "fishing-spots-video/1.0 (personal; osm-tiles)"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
PINGFANG = "/System/Library/Fonts/PingFang.ttc"
HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"

NAVY = (11, 16, 32)
CARD = (18, 24, 44)
CREAM = (255, 244, 214)
WHITE = (245, 247, 250)
MUTED = (168, 178, 196)
ORANGE = (255, 122, 48)
AREA_COLOR = {
    "城区": (255, 122, 48),
    "清河": (61, 155, 233),
    "温榆河": (43, 182, 115),
    "东线": (244, 196, 48),
    "西南": (176, 132, 252),
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = PINGFANG if Path(PINGFANG).exists() else HEITI
    idx = 1 if bold and path == PINGFANG else 0
    try:
        return ImageFont.truetype(path, size, index=idx)
    except OSError:
        return ImageFont.truetype(path, size)


def area_color(name: str) -> tuple[int, int, int]:
    if name in AREA_COLOR:
        return AREA_COLOR[name]
    h = hashlib.md5(name.encode()).hexdigest()
    return (80 + int(h[0:2], 16) // 2, 80 + int(h[2:4], 16) // 2, 80 + int(h[4:6], 16) // 2)


def load_plan(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"spots": data}
    spots = data.get("spots") or []
    if not spots:
        raise SystemExit(f"{path} 没有 spots")
    for i, s in enumerate(spots, start=1):
        s.setdefault("n", i)
        for key in ("name", "area", "nav", "fish", "pro", "con", "note", "script", "lat", "lon"):
            if key not in s:
                raise SystemExit(f"spots[{i-1}] 缺字段 {key}")
    n = len(spots)
    data.setdefault("title", "免费掉点")
    data.setdefault("subtitle", "地图标注 · 优缺点 · 注意事项")
    data.setdefault("intro_script", f"{data['title']}，位置优缺点注意事项，地图标好了，先收藏。")
    data.setdefault("outro_title", "别踩这些")
    data.setdefault("outro_lines", ["现场写着禁止垂钓的岸", "电鱼、毒鱼、地笼、粘网", "鱼获谨慎食用，垃圾带走"])
    data.setdefault("outro_script", "现场禁止垂钓就换点。电鱼网具违法，垃圾带走。")
    data.setdefault("overview_tips", ["手竿路亚休闲钓 · 有禁止垂钓牌就换点"])
    data.setdefault("douyin_title", data["title"][:25])
    data.setdefault("douyin_intro", data["subtitle"])
    data.setdefault("douyin_tags", ["#鱼公移山", "#免费钓点", "#野钓"])
    if not data.get("legend"):
        order: list[str] = []
        ranges: dict[str, list[int]] = {}
        for s in spots:
            a = str(s["area"])
            if a not in ranges:
                order.append(a)
                ranges[a] = [int(s["n"]), int(s["n"])]
            else:
                ranges[a][1] = int(s["n"])
        data["legend"] = [
            [a, str(ranges[a][0]) if ranges[a][0] == ranges[a][1] else f"{ranges[a][0]}-{ranges[a][1]}"]
            for a in order
        ]
    data["_count"] = n
    return data


def lonlat_to_px(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2**z
    x = (lon + 180.0) / 360.0 * n * 256
    lat_r = math.radians(lat)
    y = (1 - math.asinh(math.tan(lat_r)) / math.pi) / 2 * n * 256
    return x, y


def fetch_tile(z: int, x: int, y: int, cache: Path) -> Image.Image:
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{z}_{x}_{y}.png"
    if dest.exists() and dest.stat().st_size > 0:
        return Image.open(dest).convert("RGB")
    n = 2**z
    x %= n
    y = min(max(y, 0), n - 1)
    url = TILE_URL.format(z=z, x=x, y=y)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            dest.write_bytes(data)
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise SystemExit(f"OSM 瓦片失败 {url}: {last}")


def stitch_map(
    center_lon: float, center_lat: float, z: int, w: int, h: int, cache: Path
) -> Image.Image:
    cx, cy = lonlat_to_px(center_lon, center_lat, z)
    left = cx - w / 2
    top = cy - h / 2
    x0 = int(math.floor(left / 256))
    y0 = int(math.floor(top / 256))
    x1 = int(math.floor((left + w) / 256))
    y1 = int(math.floor((top + h) / 256))
    canvas = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256), (220, 224, 228))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            tile = fetch_tile(z, tx, ty, cache)
            canvas.paste(tile, ((tx - x0) * 256, (ty - y0) * 256))
    crop_x = int(left - x0 * 256)
    crop_y = int(top - y0 * 256)
    return canvas.crop((crop_x, crop_y, crop_x + w, crop_y + h))


def draw_pin(img: Image.Image, x: int, y: int, label: str, color: tuple[int, int, int], r: int = 22) -> None:
    d = ImageDraw.Draw(img)
    d.ellipse((x - r - 3, y - r - 3, x + r + 3, y + r + 3), fill=(0, 0, 0))
    d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    d.ellipse((x - r, y - r, x + r, y + r), outline=WHITE, width=3)
    f = font(18 if len(label) > 1 else 20, bold=True)
    bbox = d.textbbox((0, 0), label, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((x - tw / 2, y - th / 2 - 2), label, font=f, fill=WHITE)


def map_to_xy(lon, lat, center_lon, center_lat, z, w, h) -> tuple[int, int]:
    px, py = lonlat_to_px(lon, lat, z)
    cx, cy = lonlat_to_px(center_lon, center_lat, z)
    return int(w / 2 + (px - cx)), int(h / 2 + (py - cy))


def render_overview(plan: dict, dest: Path, cache: Path) -> None:
    spots = plan["spots"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    draw.text((64, 56), plan["title"], font=font(56, bold=True), fill=CREAM)
    draw.text((64, 128), plan["subtitle"], font=font(32), fill=MUTED)

    map_box = (0, 190, W, 1320)
    mw, mh = W, map_box[3] - map_box[1]
    lats = [float(s["lat"]) for s in spots]
    lons = [float(s["lon"]) for s in spots]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    osm = stitch_map(center_lon, center_lat, 10, mw, mh, cache)
    osm = Image.eval(osm, lambda p: int(p * 0.92))
    img.paste(osm, (0, map_box[1]))
    for s in spots:
        x, y = map_to_xy(float(s["lon"]), float(s["lat"]), center_lon, center_lat, 10, mw, mh)
        y += map_box[1]
        if 8 < x < W - 8 and map_box[1] + 8 < y < map_box[3] - 8:
            draw_pin(img, x, y, str(s["n"]), area_color(str(s["area"])), r=20)

    draw.rectangle((0, 1288, W, 1320), fill=(0, 0, 0))
    draw.text((28, 1292), "地图 © OpenStreetMap   标点为大致位置，导航以实地为准", font=font(22), fill=MUTED)

    y = 1355
    x = 48
    for name, rng in plan["legend"]:
        c = area_color(str(name))
        draw.ellipse((x, y + 6, x + 22, y + 28), fill=c)
        draw.text((x + 30, y), f"{name} {rng}", font=font(26), fill=WHITE)
        x += 200
        if x > W - 180:
            x = 48
            y += 44
    tips = plan.get("overview_tips") or []
    ty = 1418
    for tip in tips[:2]:
        draw.text((64, ty), str(tip), font=font(30), fill=CREAM if ty == 1418 else ORANGE)
        ty += 54
    draw.text((64, 1760), "鱼公移山", font=font(28), fill=MUTED)
    img.save(dest, "PNG")


def render_card(spot: dict, total: int, dest: Path, cache: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    color = area_color(str(spot["area"]))
    draw.text((48, 36), f"{int(spot['n']):02d} / {total:02d}", font=font(28, bold=True), fill=color)
    draw.text((200, 32), str(spot["name"]), font=font(48, bold=True), fill=CREAM)
    draw.text((48, 96), f"{spot['area']}  ·  {spot['fish']}", font=font(26), fill=MUTED)

    map_top, map_h = 150, 780
    osm = stitch_map(float(spot["lon"]), float(spot["lat"]), 14, W, map_h, cache)
    img.paste(osm, (0, map_top))
    px, py = W // 2, map_top + map_h // 2
    d2 = ImageDraw.Draw(img)
    d2.ellipse((px - 46, py - 46, px + 46, py + 46), outline=color, width=5)
    draw_pin(img, px, py, str(spot["n"]), color, r=24)
    d2.rectangle((0, map_top + map_h - 36, W, map_top + map_h), fill=NAVY)
    d2.text((24, map_top + map_h - 32), "地图 © OpenStreetMap  ·  红点为大致钓位", font=font(20), fill=MUTED)

    panel_y = map_top + map_h + 16
    draw.rounded_rectangle((32, panel_y, W - 32, H - 48), 28, fill=CARD)
    rows = [
        ("导航", str(spot["nav"]), CREAM),
        ("优点", str(spot["pro"]), (120, 220, 160)),
        ("缺点", str(spot["con"]), (255, 170, 120)),
        ("注意", str(spot["note"]), (255, 110, 110)),
    ]
    y = panel_y + 36
    label_font = font(28, bold=True)
    body_font = font(36)
    for label, text, fill in rows:
        draw.rounded_rectangle((56, y, 156, y + 42), 8, fill=(32, 42, 68))
        draw.text((68, y + 6), label, font=label_font, fill=fill)
        line = ""
        max_w = W - 88 - 180
        for ch in text:
            trial = line + ch
            if body_font.getlength(trial) > max_w:
                draw.text((180, y), line, font=body_font, fill=WHITE)
                y += 48
                line = ch
            else:
                line = trial
        draw.text((180, y), line, font=body_font, fill=WHITE)
        y += 78
    img.save(dest, "PNG")


def render_outro(plan: dict, dest: Path) -> None:
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    draw.text((64, 220), plan["outro_title"], font=font(64, bold=True), fill=CREAM)
    y = 360
    for line in plan["outro_lines"]:
        draw.text((64, y), str(line), font=font(42), fill=WHITE)
        y += 70
    draw.text((64, 1600), "鱼公移山", font=font(32), fill=MUTED)
    img.save(dest, "PNG")


def still_clip(image: Path, audio: Path, subtitle: str, dest: Path, sub_txt: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tts_dur = media.ffprobe_duration(audio)
    frames = max(int(round(tts_dur * FPS)), FPS)
    media.write_sub_txt(subtitle, sub_txt)
    sub_path = media.escape_filter_path(sub_txt)
    vf = (
        f"scale=1200:2133:force_original_aspect_ratio=increase,"
        f"crop=1200:2133,"
        f"zoompan=z='min(1.0+0.00055*on,1.06)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
        + ",".join(media.subtitle_drawtexts(textfile=sub_path))
    )
    inputs = ["ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio)]
    mark = media.WATERMARK if media.WATERMARK.exists() else None
    if mark:
        graph = (
            f"[0:v]{vf}[vbase];"
            f"[2:v]format=rgba,colorkey=0x000000:0.12:0.08,scale=400:-1[wm];"
            f"[vbase][wm]overlay=(W-w)/2:18[v];"
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


def main() -> int:
    parser = argparse.ArgumentParser(description="掉点 JSON → OSM 标注竖版视频")
    parser.add_argument("--spots", required=True, help="spots.json")
    parser.add_argument("--workdir", help="输出目录，默认当前目录 output/<json 名>")
    args = parser.parse_args()

    media.require_deps()
    spots_path = Path(args.spots).resolve()
    plan = load_plan(spots_path)
    workdir = Path(args.workdir).resolve() if args.workdir else Path.cwd() / "output" / spots_path.stem
    workdir.mkdir(parents=True, exist_ok=True)
    cards = workdir / "cards"
    tts_dir = workdir / "tts"
    subs = workdir / "subs"
    parts_dir = workdir / "parts"
    tiles = workdir / "tiles"
    for d in (cards, tts_dir, subs, parts_dir, tiles):
        d.mkdir(parents=True, exist_ok=True)

    dump = {k: v for k, v in plan.items() if not str(k).startswith("_")}
    if spots_path != workdir / "spots.json":
        (workdir / "spots.json").write_text(
            json.dumps(dump, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    overview = cards / "00_overview.png"
    outro = cards / "outro.png"
    media.log("绘制总图")
    render_overview(plan, overview, tiles)
    render_outro(plan, outro)
    total = plan["_count"]
    for s in plan["spots"]:
        path = cards / f"{int(s['n']):02d}.png"
        media.log(f"绘制卡片 {s['n']} {s['name']}")
        render_card(s, total, path, tiles)

    clips = [
        {"image": overview, "overlay": plan["title"], "script": plan["intro_script"]},
    ]
    for s in plan["spots"]:
        clips.append(
            {
                "image": cards / f"{int(s['n']):02d}.png",
                "overlay": s["name"],
                "script": s["script"],
            }
        )
    clips.append(
        {"image": outro, "overlay": plan["outro_title"], "script": plan["outro_script"]}
    )

    parts: list[Path] = []
    plan_clips = []
    t_cursor = 0.0
    for i, clip in enumerate(clips):
        media.log(f"口播 {i:02d} {clip['overlay']}")
        audio = media.tts(clip["script"], tts_dir / f"{i:02d}.mp3")
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
