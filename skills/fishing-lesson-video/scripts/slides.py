#!/usr/bin/env python3
"""竖版教学卡：真图铺底 + 口语感排版（别做成杂志目录）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance

import draw as D

W, H = 1080, 1920
# 已取消硬字幕，底部只留安全边距
SUB_BAND = 72

INK = (10, 12, 16)
PAPER = (246, 242, 234)
MUTED = (158, 162, 170)
AMBER = (255, 152, 48)
AMBER_SOFT = (255, 186, 110)
GREEN = (120, 186, 150)
SOFT_RED = (210, 130, 120)

PINGFANG = "/System/Library/Fonts/PingFang.ttc"
HIRAGINO = "/System/Library/Fonts/Hiragino Sans GB.ttc"
NOTEWORTHY = "/System/Library/Fonts/Noteworthy.ttc"
MARKER = "/System/Library/Fonts/MarkerFelt.ttc"
HEITI = "/System/Library/Fonts/STHeiti Medium.ttc"


def _truetype(path: str, size: int, index: int = 0) -> ImageFont.FreeTypeFont | None:
    if not Path(path).exists():
        return None
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return None


def font_title(size: int) -> ImageFont.FreeTypeFont:
    """标题：粗黑体口语感，不用宋体那种课本味。"""
    for path, idx in ((PINGFANG, 8), (PINGFANG, 5), (HIRAGINO, 1), (HEITI, 0)):
        f = _truetype(path, size, idx)
        if f:
            return f
    return D.font(size, bold=True)


def font_soft(size: int) -> ImageFont.FreeTypeFont:
    """轻松感：中文仍走苹方，别用 Noteworthy（缺汉字会变方框）。"""
    for path, idx in ((PINGFANG, 3), (PINGFANG, 2), (HIRAGINO, 0), (HEITI, 0)):
        f = _truetype(path, size, idx)
        if f:
            return f
    return D.font(size)


def font_play(size: int) -> ImageFont.FreeTypeFont:
    """仅英文装饰（VS 等）。"""
    for path, idx in ((NOTEWORTHY, 1), (MARKER, 0), (PINGFANG, 2)):
        f = _truetype(path, size, idx)
        if f:
            return f
    return font_soft(size)


def font_body(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path, idx in (
        (PINGFANG, 5 if bold else 2),
        (HIRAGINO, 1 if bold else 0),
        (HEITI, 0),
    ):
        f = _truetype(path, size, idx)
        if f:
            return f
    return D.font(size, bold=bold)


def font_display(size: int) -> ImageFont.FreeTypeFont:
    return font_title(size)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return font_body(size, bold=bold)


def bg_solid() -> Image.Image:
    return Image.new("RGB", (W, H), INK)


def cover(im: Image.Image, w: int, h: int) -> Image.Image:
    im = im.convert("RGB")
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.05)
    scale = max(w / im.width, h / im.height)
    nw, nh = max(int(im.width * scale), 1), max(int(im.height * scale), 1)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max((nw - w) // 2, 0)
    top = max((nh - h) // 2, 0)
    return im.crop((left, top, left + w, top + h))


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines: list[str] = []
    buf = ""
    for ch in text:
        trial = buf + ch
        if fnt.getlength(trial) > max_w and buf:
            lines.append(buf)
            buf = ch
        else:
            buf = trial
    if buf:
        lines.append(buf)
    return lines or [text]


def wrap_title(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    """标题优先在逗号/顿号处断行，第二行往往更短，不死板均分。"""
    breaks = "，、：:；; "
    if fnt.getlength(text) <= max_w:
        return [text]
    best = -1
    for i, ch in enumerate(text):
        if ch in breaks and fnt.getlength(text[: i + 1].rstrip(breaks)) <= max_w:
            best = i
    if best > 0 and best < len(text) - 1:
        a = text[: best + 1].rstrip(breaks + " ")
        b = text[best + 1 :].lstrip(breaks + " ")
        return [a, b] if b else [a]
    return wrap(draw, text, fnt, max_w)


def fade_bottom(im: Image.Image, fade_h: int = 280) -> Image.Image:
    im = im.convert("RGBA")
    fade = Image.new("L", (im.width, fade_h), 0)
    fp = fade.load()
    for y in range(fade_h):
        a = int(255 * (y / max(fade_h - 1, 1)) ** 1.15)
        for x in range(im.width):
            fp[x, y] = a
    dark = Image.new("RGBA", im.size, (*INK, 255))
    mask = Image.new("L", im.size, 0)
    mask.paste(fade, (0, im.height - fade_h))
    return Image.composite(dark, im, mask)


def paste_bleed(base: Image.Image, vis: Image.Image, y0: int, y1: int, *, fade: bool = True) -> None:
    h = max(y1 - y0, 1)
    fitted = cover(vis, W, h)
    if fade:
        fitted = fade_bottom(fitted, fade_h=min(160, h // 5)).convert("RGB")
    else:
        fitted = fitted.convert("RGB")
    base.paste(fitted, (0, y0))


def paste_half(base: Image.Image, left: Image.Image, right: Image.Image, y0: int, y1: int) -> None:
    h = max(y1 - y0, 1)
    mid = W // 2
    gap = 6
    for im, x0, x1 in ((left, 0, mid - gap // 2), (right, mid + gap // 2, W)):
        bw = x1 - x0
        fitted = cover(im, bw, h)
        faded = fade_bottom(fitted, fade_h=min(220, h // 3))
        base.paste(faded.convert("RGB"), (x0, y0))
    draw = ImageDraw.Draw(base)
    draw.rectangle((mid - 2, y0, mid + 2, y1), fill=INK)


def shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt,
    fill,
    *,
    shadow: tuple[int, int, int] = (0, 0, 0),
) -> None:
    x, y = xy
    draw.text((x + 2, y + 3), text, font=fnt, fill=shadow)
    draw.text((x, y), text, font=fnt, fill=fill)


def draw_kicker(draw: ImageDraw.ImageDraw, text: str, x: int, y: int) -> int:
    if not text:
        return y
    # 拆成「数字」+「中文」，数字用活泼字，中文用苹方轻体
    parts = text.split(" ", 1)
    cx = x
    if len(parts) == 2 and parts[0] and parts[0][0].isdigit():
        nf = font_play(34)
        draw.text((cx, y - 2), parts[0], font=nf, fill=AMBER)
        cx += int(nf.getlength(parts[0])) + 14
        text = parts[1]
    f = font_soft(28)
    # 字距略拉开，少一点「贴成一块」的死板
    for ch in text:
        draw.text((cx, y), ch, font=f, fill=AMBER_SOFT)
        cx += int(f.getlength(ch)) + 4
    return y + 44


def draw_title_block(
    draw: ImageDraw.ImageDraw,
    title: str,
    *,
    x: int,
    y: int,
    max_w: int,
    size: int = 54,
    fill=PAPER,
) -> int:
    f = font_title(size)
    lines = wrap_title(draw, title, f, max_w)
    for i, line in enumerate(lines):
        xx = x + (22 if i else 0)
        fs = font_title(size - (6 if i else 0))
        shadow_text(draw, (xx, y), line, fs, fill)
        if i == 0:
            # 短色条点在标题前两三个字下方，像随手划的，不要通栏
            bar_w = min(int(fs.getlength(line[:3]) if len(line) >= 3 else fs.getlength(line)), 160)
            draw.rounded_rectangle(
                (xx + 4, y + size + 4, xx + 4 + bar_w, y + size + 12),
                5,
                fill=AMBER,
            )
            y += size + 30
        else:
            y += int(size * 1.08)
    return y


def key_points(draw: ImageDraw.ImageDraw, items: list, y: int, *, bottom: int | None = None) -> int:
    """口语要点：第一句放大，后面轻松跟，不要 01— 目录感。"""
    bottom = bottom or (H - SUB_BAND - 20)
    for i, item in enumerate(items[:4]):
        text = str(item)
        if i == 0:
            f = font_title(42)
            for line in wrap(draw, text, f, W - 110):
                shadow_text(draw, (56, y), line, f, PAPER)
                y += 56
            y += 18
            continue
        ox = 56 + (i % 2) * 12
        draw.ellipse((ox, y + 14, ox + 14, y + 28), fill=AMBER)
        f = font_body(32, bold=False)
        fill = (210, 210, 214)
        ly = y
        for line in wrap(draw, text, f, W - 140):
            draw.text((ox + 28, ly), line, font=f, fill=fill)
            ly += 44
        y = ly + 22
        if y > bottom - 40:
            break
    return y


def cutout_photo(im: Image.Image) -> Image.Image:
    rgba = im.convert("RGBA")
    small = im.convert("RGB").resize((48, 48))
    colors = small.getcolors(48 * 48) or []
    if len(colors) <= 40:
        return rgba
    try:
        from rembg import remove

        return remove(rgba)
    except Exception:
        return rgba


def credit_line(draw: ImageDraw.ImageDraw, text: str, y: int) -> None:
    return


def prepare_photo(im: Image.Image) -> Image.Image:
    if im.mode == "RGBA":
        canvas = Image.new("RGBA", im.size, (*INK, 255))
        canvas.paste(im, (0, 0), im)
        return canvas.convert("RGB")
    return im.convert("RGB")


def render_slide(slide: dict, visuals: list[Image.Image]) -> Image.Image:
    layout = slide.get("layout") or "hero"
    img = bg_solid()
    draw = ImageDraw.Draw(img)
    title = str(slide.get("title") or "")
    kicker = str(slide.get("kicker") or "")
    caption = str(slide.get("caption") or "")
    credit = str(slide.get("credit") or "")
    items = list(slide.get("bullets") or [])
    content_bottom = H - SUB_BAND
    visuals = [prepare_photo(v) for v in visuals]

    if layout == "title":
        # 上图下文，标题不压主图
        if visuals:
            paste_bleed(img, visuals[0], 0, int(H * 0.58), fade=True)
        draw = ImageDraw.Draw(img)
        y = int(H * 0.60)
        y = draw_kicker(draw, "鱼公移山", 56, y)
        y = draw_title_block(draw, title, x=56, y=y + 4, max_w=W - 120, size=60)
        sub = str(slide.get("subtitle") or "")
        if sub:
            draw.text((56, y + 12), sub, font=font_soft(30), fill=(200, 200, 204))
        return img

    if layout == "outro":
        # 结尾：有趣相关图在上，互动文案在下
        if visuals:
            paste_bleed(img, visuals[0], 0, int(H * 0.55), fade=True)
            draw = ImageDraw.Draw(img)
            y = int(H * 0.57)
        else:
            y = 220
        y = draw_title_block(draw, title or "你怎么选的", x=56, y=y, max_w=W - 120, size=52)
        y += 28
        for item in items:
            f = font_soft(34)
            for line in wrap(draw, str(item), f, W - 120):
                draw.text((56, y), line, font=f, fill=PAPER)
                y += 48
            y += 16
        return img

    if layout == "steps":
        # 上图完整露出 + 下文，禁止标题压示意图字
        if visuals:
            paste_bleed(img, visuals[0], 0, int(H * 0.40), fade=False)
            draw = ImageDraw.Draw(img)
            y = int(H * 0.42)
        else:
            y = 140
        y = draw_kicker(draw, kicker, 56, y)
        y = draw_title_block(draw, title, x=56, y=y, max_w=W - 140, size=48)
        y += 24
        for i, item in enumerate(items[:6]):
            mark = "①②③④⑤⑥"[i] if i < 6 else str(i + 1)
            draw.text((56, y), mark, font=font_soft(34), fill=AMBER)
            ly = y + 2
            for line in wrap(draw, str(item), font_body(32), W - 180):
                draw.text((120, ly), line, font=font_body(32), fill=PAPER)
                ly += 42
            y = ly + 22
            if y > content_bottom - 40:
                break
        return img

    # hero / compare / hook：图在上半完整露出，字全部在图下方
    vis_top = 0
    vis_bottom = int(H * 0.48)

    if layout == "compare":
        if len(visuals) < 2:
            raise SystemExit(f"compare 页需要两张图: {title}")
        paste_half(img, visuals[0], visuals[1], vis_top, vis_bottom)
        draw = ImageDraw.Draw(img)
        cx, cy = W // 2, (vis_top + vis_bottom) // 2
        draw.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), fill=AMBER)
        vf = font_play(28)
        draw.text((cx - vf.getlength("VS") / 2, cy - 16), "VS", font=vf, fill=INK)
        labels = slide.get("labels") or []
        if labels:
            shadow_text(draw, (40, vis_bottom - 56), str(labels[0]), font_soft(28), GREEN)
        if len(labels) > 1:
            lab = str(labels[1])
            lf = font_soft(28)
            shadow_text(draw, (W - 40 - int(lf.getlength(lab)), vis_bottom - 56), lab, lf, SOFT_RED)
    else:
        if not visuals:
            raise SystemExit(f"{layout} 页必须有图: {title}")
        paste_bleed(img, visuals[0], vis_top, vis_bottom, fade=False)
        draw = ImageDraw.Draw(img)

    y = vis_bottom + 28
    y = draw_kicker(draw, kicker, 56, y)
    y = draw_title_block(draw, title, x=56, y=y, max_w=W - 140, size=48)
    credit_line(draw, credit or caption, y + 6)
    key_points(draw, items, y + 28, bottom=content_bottom - 8)
    return img
