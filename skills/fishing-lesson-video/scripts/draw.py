#!/usr/bin/env python3
"""按真实钩型几何画钩、漂、线组。禁止拿错钩图贴标签。"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import catalog as cat

PINGFANG = "/System/Library/Fonts/PingFang.ttc"
HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"
HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"
STEEL = (198, 204, 212)
STEEL_DARK = (92, 98, 108)
STEEL_HI = (236, 239, 244)
GOLD = (212, 168, 72)
NAVY = (8, 11, 16)
CREAM = (242, 238, 230)
MUTED = (140, 148, 162)
WHITE = (248, 246, 242)
ORANGE = (232, 156, 64)
CARD = (16, 22, 32)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    # 冬青黑体作标题更利落；正文回落 PingFang
    path = HIRAGINO if bold and Path(HIRAGINO).exists() else (
        PINGFANG if Path(PINGFANG).exists() else HEITI
    )
    idx = 1 if bold and path == PINGFANG else (1 if bold and path == HIRAGINO else 0)
    try:
        return ImageFont.truetype(path, size, index=idx)
    except OSError:
        return ImageFont.truetype(path if Path(path).exists() else HEITI, size)


def _lin(a, b, n: int) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return pts


def _arc(cx, cy, r, a0, sweep, n: int) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        a = math.radians(a0 + sweep * t)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def hook_centerline(spec: dict, origin: tuple[float, float], scale: float) -> list[tuple[float, float]]:
    ox, oy = origin
    shank = spec["shank"] * scale
    gape = spec["gape"] * scale
    br = spec["bend_radius"] * scale
    sweep = float(spec.get("bend_sweep") or 250)
    offset = float(spec.get("offset") or 0) * scale
    cx = ox + br
    cy = oy + shank
    pts = _lin((ox, oy + scale * 0.06), (ox, oy + shank), 18)
    pts += _arc(cx, cy, br, 180, sweep, 42)
    last = pts[-1]
    tip_x = ox + gape * (1 - float(spec["point_in"])) + offset
    tip_y = last[1] - spec["point_len"] * scale
    pts += _lin(last, (tip_x, tip_y), 16)
    return pts


def _stroke(draw: ImageDraw.ImageDraw, pts, radius: float, fill, taper_end: bool = True) -> None:
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        r = radius
        if taper_end and i > n * 0.78:
            t = (i - n * 0.78) / max(n * 0.22, 1)
            r = max(radius * (1 - t * 0.85), 1.2)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def _barb(draw: ImageDraw.ImageDraw, pts, radius: float, fill) -> None:
    if len(pts) < 8:
        return
    a = pts[int(len(pts) * 0.9)]
    b = pts[int(len(pts) * 0.84)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    dx, dy = dx / L, dy / L
    px, py = -dy, dx
    p1 = (a[0] + dx * radius * 0.4, a[1] + dy * radius * 0.4)
    p2 = (a[0] - dx * radius * 3.2 + px * radius * 3.4, a[1] - dy * radius * 3.2 + py * radius * 3.4)
    p3 = (a[0] - dx * radius * 1.1, a[1] - dy * radius * 1.1)
    draw.polygon([p1, p2, p3], fill=fill)


def draw_hook_raw(
    spec: dict, w: int = 720, h: int = 900, *, gold: bool = False, scale_mul: float = 1.0
) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    scale = min(w, h) * 0.42 * scale_mul
    origin = (w * 0.34, h * 0.18)
    pts = hook_centerline(spec, origin, scale)
    radius = spec["wire"] * scale
    body = GOLD if gold else STEEL
    dark = (140, 108, 40) if gold else STEEL_DARK
    hi = (255, 228, 160) if gold else STEEL_HI
    _stroke(draw, pts, radius + 2.2, dark)
    _stroke(draw, pts, radius, body)
    _stroke(draw, pts, max(radius * 0.35, 1.5), hi, taper_end=True)
    if spec.get("barb", True):
        _barb(draw, pts, radius, dark)
        _barb(draw, [ (p[0] - 0.6, p[1] - 0.6) for p in pts ], radius * 0.85, body)
    eye_r = radius * 1.55
    ex, ey = pts[0][0], pts[0][1] - eye_r * 0.2
    draw.ellipse((ex - eye_r - 3, ey - eye_r - 3, ex + eye_r + 3, ey + eye_r + 3), outline=dark, width=int(radius * 0.9) + 2)
    draw.ellipse((ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r), outline=body, width=int(radius * 0.75) + 1)
    return img


def render_hook_card(model: str, w: int = 1000, h: int = 1100) -> Image.Image:
    key, spec = cat.resolve_hook(model)
    img = Image.new("RGB", (w, h), NAVY)
    canvas = ImageDraw.Draw(img)
    hook = draw_hook_raw(spec, int(w * 0.58), int(h * 0.82), gold=key == "sode")
    img.paste(hook, (int(w * 0.02), int(h * 0.06)), hook)
    x = int(w * 0.58)
    canvas.text((x, 48), spec["name"], font=font(52, bold=True), fill=CREAM)
    y = 130
    for line in (spec["tell"], spec["use"]):
        canvas.text((x, y), line, font=font(26), fill=MUTED)
        y += 44
    y += 24
    barb = "无倒刺" if not spec.get("barb", True) else "有倒刺"
    shank_txt = "明显加长" if spec["shank"] >= 1.4 else ("偏短" if spec["shank"] <= 0.9 else "中长")
    gape_txt = "宽，饵团吃得进" if spec["gape"] >= 0.85 else ("窄，适合小口鱼" if spec["gape"] <= 0.55 else "中等")
    point_txt = "明显内弯" if float(spec["point_in"]) >= 0.25 else "较直，刺鱼正"
    bend_txt = "接近正圆" if float(spec["bend_radius"]) >= 0.42 else "偏U形"
    for label, name in (
        ("钩眼", "线从这里绑"),
        ("钩柄", shank_txt),
        ("钩门", gape_txt),
        ("钩底", bend_txt),
        ("钩尖", point_txt),
        (barb, "摘鱼看这个"),
    ):
        canvas.ellipse((x, y + 10, x + 16, y + 26), fill=ORANGE)
        canvas.text((x + 28, y), f"{label}  {name}", font=font(26), fill=CREAM)
        y += 48
    canvas.text((40, h - 56), "按市面真实钩型几何绘制，不是照片贴标签", font=font(22), fill=MUTED)
    return img


def _hook_scale(spec: dict, hao: float | None) -> float:
    base = float(spec.get("size_scale") or 1.0)
    if hao is None:
        return base
    return base * (float(hao) / 3.0)


def render_hook_plain(model: str, w: int = 640, h: int = 800, *, hao: float | None = None) -> Image.Image:
    key, spec = cat.resolve_hook(model)
    bg = Image.new("RGB", (w, h), CARD)
    hook = draw_hook_raw(spec, w, h, gold=key == "sode", scale_mul=_hook_scale(spec, hao))
    bg.paste(hook, (0, 0), hook)
    d = ImageDraw.Draw(bg)
    label = spec["name"] if hao is None else f"{spec['name']} {hao:g}号"
    d.text((24, h - 64), label, font=font(36, bold=True), fill=CREAM)
    return bg


def render_hook_size_row(model: str, sizes: list, w: int = 1000, h: int = 700) -> Image.Image:
    key, spec = cat.resolve_hook(model)
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    d.text((32, 24), f"{spec['name']} 号数对照（同号不同钩型不一样大）", font=font(28, bold=True), fill=CREAM)
    n = max(len(sizes), 1)
    slot = w // n
    for i, hao in enumerate(sizes):
        hao_f = float(hao)
        cell = draw_hook_raw(
            spec, slot, h - 80, gold=key == "sode", scale_mul=_hook_scale(spec, hao_f)
        )
        img.paste(cell, (i * slot, 50), cell)
        d.text((i * slot + 24, h - 48), f"{hao_f:g}号", font=font(28, bold=True), fill=ORANGE)
    return img


def _float_body(draw, cx, y0, body_h, body_w, foot_h, tip_h) -> None:
    # tip
    draw.rectangle((cx - 3, y0, cx + 3, y0 + tip_h), fill=(230, 70, 60))
    draw.rectangle((cx - 3, y0, cx + 3, y0 + tip_h * 0.45), fill=(245, 245, 245))
    y1 = y0 + tip_h
    # body
    draw.ellipse((cx - body_w, y1, cx + body_w, y1 + body_h), fill=(40, 160, 150))
    draw.ellipse((cx - body_w * 0.45, y1 + 8, cx + body_w * 0.2, y1 + body_h * 0.45), fill=(90, 200, 190))
    y2 = y1 + body_h
    draw.rectangle((cx - 4, y2, cx + 4, y2 + foot_h), fill=(90, 70, 40))


def _line_size(spec: dict, hao: str | float | None) -> dict:
    sizes = spec.get("sizes") or []
    if hao is None:
        return sizes[3] if len(sizes) > 3 else (sizes[0] if sizes else {"hao": "1.0", "mm": 0.165, "use": ""})
    want = str(hao).rstrip("号")
    for row in sizes:
        if str(row["hao"]) == want:
            return row
    raise SystemExit(f"{spec.get('name')} 没有 {want} 号。目录号数：{[r['hao'] for r in sizes]}")


def _mono_line(draw, x0, y, x1, mm: float, color, glow=None) -> None:
    r = max(mm * 38, 1.6)
    if glow:
        draw.line([(x0, y), (x1, y)], fill=glow, width=int(r * 2 + 4))
    draw.line([(x0, y), (x1, y)], fill=color, width=int(r * 2))


def _braid_line(draw, x0, y, x1, mm: float) -> None:
    r = max(mm * 38, 2.0)
    colors = [(70, 170, 70), (230, 200, 50), (60, 140, 210), (70, 170, 70)]
    for i, c in enumerate(colors):
        yy = y + (i - 1.5) * max(r * 0.35, 1.2)
        draw.line([(x0, yy), (x1, yy)], fill=c, width=max(int(r * 0.7), 2))
    step = 18
    x = x0
    while x < x1:
        draw.line([(x, y - r), (x + 10, y + r)], fill=(40, 80, 40), width=1)
        x += step


def render_line_card(model: str, hao: str | float | None = None, w: int = 1000, h: int = 1100) -> Image.Image:
    key, spec = cat.resolve_line(model)
    row = _line_size(spec, hao)
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((80, 80, w - 80, 420), 28, fill=(32, 40, 62))
    d.ellipse((120, 120, 380, 380), fill=(48, 56, 78), outline=STEEL_DARK, width=10)
    d.ellipse((175, 175, 325, 325), fill=NAVY)
    color = {"nylon": (220, 210, 150), "fluorocarbon": (170, 210, 220), "braid": (80, 180, 70)}[spec["material"]]
    for i in range(10):
        rr = 118 - i * 7
        d.ellipse((250 - rr, 250 - rr, 250 + rr, 250 + rr), outline=color, width=3)
    d.text((430, 150), spec["name"], font=font(52, bold=True), fill=CREAM)
    d.text((430, 220), f"{row['hao']}号  ·  直径 {row['mm']} mm", font=font(36, bold=True), fill=ORANGE)
    d.text((430, 280), row["use"], font=font(28), fill=MUTED)

    d.text((80, 470), "放大看线体（按真实结构）", font=font(28, bold=True), fill=CREAM)
    y = 560
    if spec["material"] == "braid":
        _braid_line(d, 80, y, w - 80, row["mm"])
        d.text((80, y + 36), "多股编织，不透明。台钓主线/子线不用这个", font=font(26), fill=MUTED)
    else:
        glow = (120, 160, 180) if spec["material"] == "fluorocarbon" else (90, 80, 50)
        _mono_line(d, 80, y, w - 80, row["mm"], color, glow=glow)
        kind = "更透、更硬，多当子线或路亚前导" if spec["material"] == "fluorocarbon" else "单丝半透明，台钓主线子线用这个"
        d.text((80, y + 36), kind, font=font(26), fill=MUTED)

    d.text((80, 680), spec["look"], font=font(28), fill=WHITE)
    for i, line in enumerate((spec["use"], spec["forbid"])):
        d.text((80, 760 + i * 48), line, font=font(26), fill=MUTED if i else CREAM)
    d.text((80, h - 48), "号数按常见国产/日系对照，直径会因品牌略有出入", font=font(22), fill=MUTED)
    return img


def render_nylon_sizes(w: int = 1000, h: int = 1100) -> Image.Image:
    _, spec = cat.resolve_line("nylon")
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    d.text((48, 36), "尼龙线号越大线越粗", font=font(40, bold=True), fill=CREAM)
    d.text((48, 96), "直径按常见对照，不是 PE 号", font=font(26), fill=MUTED)
    rows = [s for s in spec["sizes"] if s["hao"] in {"0.4", "0.6", "0.8", "1.0", "1.5", "2.0", "3.0"}]
    y = 180
    for row in rows:
        _mono_line(d, 280, y + 20, w - 80, row["mm"], (220, 210, 150), glow=(90, 80, 50))
        d.text((48, y), f"{row['hao']}号", font=font(32, bold=True), fill=ORANGE)
        d.text((48, y + 40), f"{row['mm']}mm  {row['use']}", font=font(24), fill=MUTED)
        y += 120
    return img


def _seeded(name: str, n: int) -> list[float]:
    import hashlib

    raw = hashlib.md5(name.encode()).digest()
    out = []
    i = 0
    while len(out) < n:
        out.append(raw[i % len(raw)] / 255.0)
        i += 1
        if i % 16 == 0:
            raw = hashlib.md5(raw).digest()
    return out


def render_bait_draw(model: str, w: int = 720, h: int = 900) -> Image.Image:
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 - 40
    hook = draw_hook_raw(cat.hook_db()["sode"], 260, 320, gold=True)
    if model == "pull_bait":
        rnd = _seeded("pull_bait", 40)
        for i in range(18):
            ang = i / 18 * 6.28
            length = 70 + rnd[i] * 50
            x2 = cx + math.cos(ang) * length
            y2 = cy + math.sin(ang) * length * 0.7
            d.line([(cx, cy), (x2, y2)], fill=(210, 180, 120), width=3)
        d.ellipse((cx - 70, cy - 55, cx + 80, cy + 70), fill=(186, 150, 92))
        d.ellipse((cx - 40, cy - 35, cx + 20, cy + 10), fill=(210, 180, 130))
        img.paste(hook, (cx - 90, cy - 40), hook)
        title, tell = "拉饵", "有拉丝，蓬松，能拉出纤维。不是光滑圆球"
    elif model == "pinch_bait":
        d.ellipse((cx - 90, cy - 80, cx + 90, cy + 95), fill=(150, 108, 60))
        d.ellipse((cx - 50, cy - 50, cx + 10, cy + 10), fill=(176, 128, 78))
        img.paste(hook, (cx - 90, cy - 30), hook)
        title, tell = "搓饵", "手指搓成实心椭圆，包住钩弯，没有拉丝"
    elif model == "loose_cannon":
        rnd = _seeded("loose_cannon", 60)
        for i in range(28):
            x = 80 + rnd[i] * (w - 160)
            y = 180 + rnd[i + 20] * 420
            rw = 12 + rnd[i + 10] * 28
            d.ellipse((x, y, x + rw, y + rw * 0.7), fill=(210, 190, 140) if i % 2 == 0 else (186, 160, 110))
        d.ellipse((cx - 50, cy - 20, cx + 70, cy + 50), fill=(200, 178, 120))
        img.paste(hook, (cx - 80, cy - 10), hook)
        title, tell = "散炮", "干散、颗粒分明，入水就散。不是湿拉饵"
    else:
        d.ellipse((cx - 55, cy - 45, cx + 55, cy + 55), fill=(160, 112, 64))
        rnd = _seeded("dip_bait", 24)
        for i in range(16):
            x = cx - 70 + rnd[i] * 140
            y = cy - 70 + rnd[i + 8] * 130
            d.ellipse((x, y, x + 10, y + 10), fill=(230, 210, 160))
        img.paste(hook, (cx - 90, cy - 20), hook)
        title, tell = "蘸饵", "内层湿、外层干粉壳"
    d.text((32, h - 90), title, font=font(40, bold=True), fill=CREAM)
    d.text((32, h - 42), tell, font=font(22), fill=MUTED)
    return img


def render_line(model: str, hao=None, w: int = 1000, h: int = 1100) -> Image.Image:
    if model in ("nylon_sizes", "线号", "线径"):
        return render_nylon_sizes(w, h)
    return render_line_card(model, hao, w, h)


def render_spinning_reel(draw, cx, cy) -> None:
    """侧视：轮脚在上、线杯在下、抛线环绕转子，和实物纺车一致。"""
    # foot / stem
    draw.rounded_rectangle((cx - 22, cy - 230, cx + 22, cy - 168), 7, fill=STEEL_HI)
    draw.rounded_rectangle((cx - 14, cy - 178, cx + 14, cy - 98), 5, fill=STEEL)
    draw.rectangle((cx - 6, cy - 170, cx + 6, cy - 100), fill=STEEL_DARK)
    # body shell + highlight
    draw.rounded_rectangle((cx - 88, cy - 112, cx + 68, cy + 52), 34, fill=(38, 44, 56))
    draw.rounded_rectangle((cx - 74, cy - 100, cx + 28, cy + 28), 26, fill=(58, 66, 82))
    draw.rounded_rectangle((cx - 66, cy - 92, cx - 8, cy - 20), 14, fill=(92, 102, 118))
    # rotor skirt
    draw.ellipse((cx - 112, cy - 48, cx + 42, cy + 108), fill=(78, 86, 102), outline=STEEL, width=4)
    draw.arc((cx - 100, cy - 36, cx + 30, cy + 96), 210, 30, fill=STEEL_HI, width=3)
    # spool
    draw.rounded_rectangle((cx - 72, cy + 62, cx + 14, cy + 178), 16, fill=(210, 216, 224))
    draw.rounded_rectangle((cx - 62, cy + 88, cx + 4, cy + 152), 10, fill=(34, 40, 54))
    draw.line([(cx - 58, cy + 108), (cx, cy + 108)], fill=(90, 100, 118), width=2)
    draw.line([(cx - 58, cy + 128), (cx, cy + 128)], fill=(90, 100, 118), width=2)
    # drag knob
    draw.ellipse((cx - 56, cy + 42, cx - 4, cy + 90), fill=STEEL_DARK, outline=STEEL_HI, width=4)
    draw.ellipse((cx - 44, cy + 54, cx - 16, cy + 78), fill=(120, 128, 140))
    # bail arm
    draw.arc((cx - 128, cy - 58, cx + 56, cy + 128), 195, 50, fill=STEEL_HI, width=8)
    draw.ellipse((cx - 118, cy + 40, cx - 98, cy + 60), fill=STEEL)
    draw.ellipse((cx + 28, cy - 20, cx + 48, cy), fill=STEEL)
    # handle
    draw.line([(cx + 56, cy - 12), (cx + 148, cy + 42)], fill=STEEL, width=12)
    draw.ellipse((cx + 128, cy + 26, cx + 192, cy + 90), fill=(22, 24, 30), outline=STEEL_HI, width=4)
    draw.ellipse((cx + 144, cy + 42, cx + 176, cy + 74), fill=(48, 52, 62))


def render_baitcaster(draw, cx, cy) -> None:
    """低剖面水滴：线杯横置、星形卸力在摇把内侧，装在竿上。"""
    draw.rounded_rectangle((cx - 168, cy - 78, cx + 148, cy + 96), 40, fill=(34, 38, 50))
    draw.rounded_rectangle((cx - 154, cy - 64, cx + 78, cy + 82), 34, fill=(52, 58, 72))
    draw.rounded_rectangle((cx - 140, cy - 48, cx + 40, cy + 20), 18, fill=(72, 80, 96))
    # horizontal spool
    draw.ellipse((cx - 78, cy - 58, cx + 62, cy + 78), fill=(22, 26, 36), outline=STEEL, width=5)
    draw.ellipse((cx - 48, cy - 26, cx + 34, cy + 46), fill=(168, 176, 188))
    draw.ellipse((cx - 22, cy - 2, cx + 10, cy + 24), fill=(90, 98, 112))
    # palm plate
    draw.rounded_rectangle((cx - 168, cy - 44, cx - 100, cy + 56), 18, fill=(30, 34, 44))
    draw.line([(cx - 160, cy - 20), (cx - 110, cy - 20)], fill=(60, 66, 80), width=2)
    # star drag
    draw.regular_polygon((cx + 98, cy - 6, 26), 5, fill=STEEL_HI)
    draw.ellipse((cx + 90, cy - 14, cx + 106, cy + 2), fill=STEEL_DARK)
    # handle
    draw.line([(cx + 112, cy + 10), (cx + 196, cy + 56)], fill=STEEL, width=11)
    draw.ellipse((cx + 172, cy + 34, cx + 228, cy + 90), fill=(22, 24, 30), outline=STEEL_HI, width=4)
    # thumb bar
    draw.rounded_rectangle((cx - 36, cy - 88, cx + 48, cy - 64), 8, fill=STEEL_DARK)
    draw.rounded_rectangle((cx - 20, cy - 84, cx + 32, cy - 70), 4, fill=STEEL)


def render_round_reel(draw, cx, cy) -> None:
    """圆鼓轮：侧板是大圆，线杯厚，不是扁平水滴。"""
    draw.ellipse((cx - 132, cy - 132, cx + 100, cy + 100), fill=(58, 66, 80), outline=STEEL, width=10)
    draw.ellipse((cx - 118, cy - 118, cx + 86, cy + 86), fill=(42, 48, 60))
    draw.ellipse((cx - 96, cy - 96, cx + 64, cy + 64), fill=(28, 32, 44), outline=STEEL_DARK, width=3)
    draw.ellipse((cx - 54, cy - 54, cx + 26, cy + 26), fill=(178, 184, 194))
    draw.ellipse((cx - 24, cy - 24, cx - 4, cy - 4), fill=STEEL_HI)
    draw.line([(cx + 78, cy - 8), (cx + 172, cy + 48)], fill=STEEL, width=12)
    draw.ellipse((cx + 150, cy + 28, cx + 208, cy + 86), fill=(22, 24, 30), outline=STEEL_HI, width=4)
    draw.regular_polygon((cx + 86, cy - 40, 22), 5, fill=STEEL_HI)


def render_gear(model: str, w: int = 720, h: int = 900) -> Image.Image:
    key, spec = cat.resolve_gear(model)
    if key == "taiwan":
        return render_taiwan_rig(w, h)
    if key == "nylon_sizes":
        return render_nylon_sizes(w, h)
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    cx, cy = w // 2, h // 2 - 20
    if key == "float_olive":
        _float_body(d, cx, 80, 280, 70, 220, 260)
    elif key == "float_long":
        _float_body(d, cx, 60, 380, 42, 180, 240)
    elif key == "float_stubby":
        _float_body(d, cx, 70, 300, 78, 90, 280)
    elif key == "swivel_8":
        for dx in (-40, 40):
            d.ellipse((cx + dx - 48, cy - 48, cx + dx + 48, cy + 48), outline=STEEL, width=14)
        d.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=STEEL_DARK)
    elif key == "space_bean":
        d.ellipse((cx - 40, cy - 90, cx + 40, cy + 90), fill=(40, 40, 48))
        d.ellipse((cx - 22, cy - 70, cx + 18, cy - 10), fill=(70, 70, 80))
        d.rectangle((cx - 6, cy - 100, cx + 6, cy + 100), fill=NAVY)
    elif key == "lead_seat":
        d.rounded_rectangle((cx - 28, cy - 110, cx + 28, cy + 110), 10, fill=(70, 90, 120))
        d.rectangle((cx - 10, cy - 120, cx + 10, cy + 120), fill=NAVY)
        d.rounded_rectangle((cx - 46, cy - 50, cx + 46, cy + 50), 8, fill=(150, 150, 158))
    elif key == "lead_skin":
        d.rounded_rectangle((cx - 160, cy - 28, cx + 160, cy + 28), 6, fill=(168, 172, 180))
        d.rounded_rectangle((cx - 150, cy - 18, cx + 40, cy + 10), 4, fill=(200, 204, 210))
    elif key == "snap":
        d.arc((cx - 70, cy - 80, cx + 70, cy + 80), 200, 160, fill=STEEL, width=10)
        d.line([(cx + 50, cy - 20), (cx + 90, cy - 70)], fill=STEEL, width=8)
        d.ellipse((cx - 16, cy + 70, cx + 16, cy + 102), outline=STEEL, width=8)
    elif key == "float_seat":
        d.rounded_rectangle((cx - 36, cy - 70, cx + 36, cy + 70), 12, fill=(70, 40, 40))
        d.rectangle((cx - 8, cy - 90, cx + 8, cy + 90), fill=NAVY)
        d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=(90, 50, 50))
    elif key == "drop_sinker":
        d.polygon([(cx, cy - 110), (cx + 55, cy + 40), (cx, cy + 120), (cx - 55, cy + 40)], fill=(160, 164, 172))
        d.ellipse((cx - 8, cy - 128, cx + 8, cy - 96), outline=STEEL, width=5)
    elif key == "inline_sinker":
        d.ellipse((cx - 40, cy - 100, cx + 40, cy + 100), fill=(160, 164, 172))
        d.rectangle((cx - 10, cy - 120, cx + 10, cy + 120), fill=NAVY)
    elif key == "olive_sinker":
        d.ellipse((cx - 38, cy - 120, cx + 38, cy + 120), fill=(160, 164, 172))
        d.ellipse((cx - 16, cy - 40, cx + 8, cy + 10), fill=(190, 194, 200))
    elif key == "bomb_rig":
        d.ellipse((cx - 70, cy - 40, cx + 70, cy + 40), outline=STEEL, width=6)
        for i in range(6):
            ang = i / 6 * 6.28
            hx = cx + math.cos(ang) * 110
            hy = cy + math.sin(ang) * 80
            d.line([(cx, cy), (hx, hy)], fill=(210, 180, 80), width=3)
            tiny = draw_hook_raw(cat.hook_db()["iseama"], 90, 110)
            img.paste(tiny, (int(hx - 45), int(hy - 40)), tiny)
    elif key == "string_hooks":
        d.line([(cx, 80), (cx, h - 120)], fill=(210, 180, 80), width=4)
        for i, yy in enumerate((180, 380, 580)):
            tiny = draw_hook_raw(cat.hook_db()["maruseigo"], 160, 200)
            img.paste(tiny, (cx - 20, yy), tiny)
            d.line([(cx, yy + 30), (cx + 90, yy + 30)], fill=MUTED, width=2)
            d.text((cx + 100, yy + 16), f"第{i+1}钩 丸世", font=font(24), fill=CREAM)
    elif key == "spinning_reel":
        render_spinning_reel(d, cx, cy - 40)
    elif key == "baitcaster":
        render_baitcaster(d, cx, cy - 10)
    elif key == "round_reel":
        render_round_reel(d, cx, cy - 10)
    else:
        d.text((40, cy), spec["name"], font=font(40, bold=True), fill=CREAM)
    # 底部信息条，不占主视觉
    d.rectangle((0, h - 96, w, h), fill=(10, 14, 20))
    d.text((32, h - 82), spec["name"], font=font(34, bold=True), fill=CREAM)
    d.text((32, h - 42), spec["tell"], font=font(22), fill=MUTED)
    return img


def render_taiwan_rig(w: int = 720, h: int = 1100) -> Image.Image:
    img = Image.new("RGB", (w, h), CARD)
    d = ImageDraw.Draw(img)
    x = 280
    d.line([(x, 40), (x, h - 80)], fill=(210, 180, 80), width=4)
    items = [
        (70, "主线"),
        (170, "漂"),
        (280, "上太空豆"),
        (360, "铅皮座+铅皮"),
        (440, "下太空豆"),
        (540, "八字环"),
        (700, "子线"),
        (900, "钩"),
    ]
    d.ellipse((x - 22, 150, x + 22, 250), fill=(40, 160, 150))
    d.rectangle((x - 3, 90, x + 3, 150), fill=(230, 70, 60))
    d.ellipse((x - 10, 268, x + 10, 300), fill=(40, 40, 48))
    d.rounded_rectangle((x - 20, 330, x + 20, 410), 6, fill=(150, 150, 158))
    d.ellipse((x - 10, 428, x + 10, 460), fill=(40, 40, 48))
    d.ellipse((x - 18, 520, x + 18, 556), outline=STEEL, width=5)
    d.ellipse((x - 18, 548, x + 18, 584), outline=STEEL, width=5)
    hook = draw_hook_raw(cat.hook_db()["sode"], 180, 220)
    img.paste(hook, (x - 40, 820), hook)
    for y, label in items:
        d.line([(x + 28, y + 20), (x + 90, y + 20)], fill=MUTED, width=2)
        d.text((x + 100, y + 4), label, font=font(28), fill=CREAM)
    d.text((32, 24), "台钓线组（真实顺序）", font=font(36, bold=True), fill=CREAM)
    d.text((32, h - 40), "主线到子线在八字环分家，钩在子线末端", font=font(22), fill=MUTED)
    return img


def render_visual(visual: dict, photo: Image.Image | None = None) -> Image.Image:
    kind = visual.get("kind")
    if kind == "hook":
        sizes = visual.get("sizes")
        if sizes:
            return render_hook_size_row(visual.get("model") or visual.get("name") or "", sizes)
        hao = visual.get("size") or visual.get("hao")
        if visual.get("detail"):
            return render_hook_card(visual["model"])
        return render_hook_plain(
            visual.get("model") or visual.get("name") or "",
            hao=None if hao is None else float(hao),
        )
    if kind == "line":
        return render_line(visual.get("model") or visual.get("name") or "", visual.get("size") or visual.get("hao"))
    if kind == "bait":
        name = visual.get("name") or visual.get("model") or ""
        _, entry = cat.resolve_bait(str(name))
        if entry.get("kind") == "draw":
            return render_bait_draw(entry["model"])
        if photo is not None:
            return photo
        raise SystemExit(f"饵料「{name}」需要真照片，先拉 Wikimedia")
    if kind in ("gear", "rig"):
        return render_gear(visual.get("model") or visual.get("name") or kind)
    if photo is not None:
        return photo
    raise SystemExit(f"视觉素材缺少图片: {visual}")
