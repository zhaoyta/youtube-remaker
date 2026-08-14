#!/usr/bin/env python3
"""按视频 id 生成可复现的二创画面/音频滤镜，打乱像素指纹，减轻平台判重。"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import asdict, dataclass


ANCHORS = (
    "left-top",
    "right-top",
    "left-bottom",
    "right-bottom",
    "center",
    "left-center",
    "right-center",
)


@dataclass
class RemixParams:
    crop_pct_w: float
    crop_pct_h: float
    anchor: str
    rotate_deg: float
    brightness: float
    contrast: float
    saturation: float
    gamma: float
    hue_deg: float
    cb_rs: float
    cb_gs: float
    cb_bs: float
    unsharp: float
    noise: int
    noise_seed: int
    vignette: float
    pitch: float
    volume: float
    jitter_in: float
    jitter_out: float
    fade_in: float
    fade_out: float
    crf: int

    def to_dict(self) -> dict:
        return asdict(self)


def seeded_rng(*parts: object) -> random.Random:
    raw = "|".join(map(str, parts)).encode("utf-8")
    digest = hashlib.md5(raw).hexdigest()
    return random.Random(int(digest[:16], 16))


def even(n: int) -> int:
    return max(2, int(n) // 2 * 2)


def make_params(seed: str, clip_idx: int, clip_count: int) -> RemixParams:
    rng = seeded_rng(seed, clip_idx, "remix-v1")
    _ = clip_count
    anchor = ANCHORS[clip_idx % len(ANCHORS)]
    if rng.random() < 0.35:
        anchor = rng.choice(ANCHORS)
    return RemixParams(
        crop_pct_w=rng.uniform(0.045, 0.085),
        crop_pct_h=rng.uniform(0.035, 0.070),
        anchor=anchor,
        rotate_deg=rng.choice([-1, 1]) * rng.uniform(0.28, 0.72),
        brightness=rng.uniform(-0.045, 0.050),
        contrast=rng.uniform(0.97, 1.10),
        saturation=rng.uniform(0.94, 1.14),
        gamma=rng.uniform(0.96, 1.06),
        hue_deg=rng.uniform(-9.0, 9.0),
        cb_rs=rng.uniform(-0.04, 0.05),
        cb_gs=rng.uniform(-0.035, 0.03),
        cb_bs=rng.uniform(-0.03, 0.045),
        unsharp=rng.uniform(0.35, 0.85),
        noise=rng.randint(5, 9),
        noise_seed=rng.randint(1, 10_000_000),
        vignette=rng.uniform(0.50, 0.64),
        pitch=rng.uniform(0.988, 1.016),
        volume=rng.uniform(1.00, 1.07),
        jitter_in=rng.uniform(0.04, 0.10),
        jitter_out=rng.uniform(0.04, 0.10),
        fade_in=0.0,
        fade_out=0.0,
        crf=rng.randint(18, 21),
    )


def jitter_span(
    start: float,
    end: float,
    source_dur: float,
    params: RemixParams,
) -> tuple[float, float]:
    """每段头尾各切掉几十毫秒，切断与原片对齐的帧序列。"""
    ns = max(0.0, start + params.jitter_in)
    ne = min(source_dur - 0.02, end - params.jitter_out)
    if ne - ns < 0.35:
        return start, min(end, source_dur)
    return ns, ne


def _crop_xy(width: int, height: int, cw: int, ch: int, anchor: str) -> tuple[int, int]:
    if "left" in anchor:
        x = 0
    elif "right" in anchor:
        x = width - cw
    else:
        x = (width - cw) // 2
    if "top" in anchor:
        y = 0
    elif "bottom" in anchor:
        y = height - ch
    else:
        y = (height - ch) // 2
    return even(max(0, x)), even(max(0, y))


def video_filters(params: RemixParams, width: int, height: int, out_dur: float) -> list[str]:
    w, h = even(width), even(height)
    rad = params.rotate_deg * math.pi / 180.0
    rot_mx = even(int(abs(math.tan(rad)) * h / 2) + 6)
    rot_my = even(int(abs(math.tan(rad)) * w / 2) + 6)
    extra_x = even(int(w * params.crop_pct_w))
    extra_y = even(int(h * params.crop_pct_h))
    cw = even(w - max(rot_mx * 2, extra_x))
    ch = even(h - max(rot_my * 2, extra_y))
    cw = min(cw, w - rot_mx * 2)
    ch = min(ch, h - rot_my * 2)
    x, y = _crop_xy(w, h, cw, ch, params.anchor)
    x = min(max(x, rot_mx), w - cw - rot_mx)
    y = min(max(y, rot_my), h - ch - rot_my)
    x, y = even(x), even(y)

    fade_out_st = max(0.0, out_dur - params.fade_out)
    filters = [
        f"rotate={rad:.6f}:ow=iw:oh=ih:c=black:bilinear=1",
        f"crop={cw}:{ch}:{x}:{y}",
        f"scale={w}:{h}:flags=lanczos",
        (
            f"eq=brightness={params.brightness:.4f}:contrast={params.contrast:.4f}:"
            f"saturation={params.saturation:.4f}:gamma={params.gamma:.4f}"
        ),
        f"hue=h={params.hue_deg:.3f}",
        (
            f"colorbalance=rs={params.cb_rs:.4f}:gs={params.cb_gs:.4f}:"
            f"bs={params.cb_bs:.4f}"
        ),
        f"unsharp=5:5:{params.unsharp:.3f}:5:5:0.0",
        f"noise=alls={params.noise}:allf=t+u:all_seed={params.noise_seed}",
        f"vignette=a={params.vignette:.4f}:dither=1",
    ]
    if params.fade_in > 0.01:
        filters.append(f"fade=t=in:st=0:d={params.fade_in:.3f}")
    if params.fade_out > 0.01:
        filters.append(f"fade=t=out:st={fade_out_st:.3f}:d={params.fade_out:.3f}")
    filters.append("setsar=1")
    return filters


def audio_filters(base_tempo: str, params: RemixParams, out_dur: float) -> str:
    """变调前先统一到 44100，否则 edge-tts 24kHz 会被 asetrate 压短。"""
    inv = 1.0 / params.pitch
    fade_out_st = max(0.0, out_dur - params.fade_out)
    parts = [
        base_tempo,
        "aresample=44100",
        f"asetrate=44100*{params.pitch:.5f}",
        "aresample=44100",
        f"atempo={inv:.5f}",
        "highpass=f=80",
        "treble=g=1.6",
        f"volume={params.volume:.3f}",
    ]
    if params.fade_in > 0.01:
        parts.append(f"afade=t=in:st=0:d={min(params.fade_in, 0.12):.3f}")
    if params.fade_out > 0.01:
        parts.append(f"afade=t=out:st={fade_out_st:.3f}:d={params.fade_out:.3f}")
    parts.extend(
        [
            f"apad=whole_dur={out_dur:.3f}",
            f"atrim=duration={out_dur:.3f}",
            "asetpts=PTS-STARTPTS",
        ]
    )
    return ",".join(parts)
