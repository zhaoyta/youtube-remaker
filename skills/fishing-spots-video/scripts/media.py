#!/usr/bin/env python3
"""TTS、硬字幕、拼接。"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE = "zh-CN-XiaoxiaoNeural"
FONT = "/System/Library/Fonts/PingFang.ttc"
SUB_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
WATERMARK = ROOT / "assets" / "copyright.png"
SUB_FILL = "0xFF2A12"
SUB_OUTLINE = "0xFFEDE6"
SUB_SIZE = 66
SUB_MARGIN_BOTTOM = 220
SUB_LINE_SPACING = 12
SUB_WRAP = 10
# 版权图右上角边距（build.py overlay 用）
WATERMARK_MARGIN = 24


def log(msg: str) -> None:
    print(f"[spots] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    log("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("%", "\\%")
    )


def edge_tts_cmd(text: str, dest: Path) -> list[str]:
    if shutil.which("edge-tts"):
        return ["edge-tts", "--voice", VOICE, "--text", text, "--write-media", str(dest)]
    return [
        sys.executable,
        "-m",
        "edge_tts",
        "--voice",
        VOICE,
        "--text",
        text,
        "--write-media",
        str(dest),
    ]


def tts(text: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(edge_tts_cmd(text, dest))
    return dest


def wrap_cn(text: str, width: int = SUB_WRAP) -> list[str]:
    text = "".join(text.split())
    lines: list[str] = []
    buf = ""
    punct = set("，。！？、,!?;；")
    for ch in text:
        if ch in punct:
            buf += ch
            if buf:
                lines.append(buf)
                buf = ""
            continue
        if len(buf) >= width:
            lines.append(buf)
            buf = ""
        buf += ch
    if buf:
        lines.append(buf)
    return lines or [text]


def split_cues(text: str) -> list[str]:
    """按标点切成口播短句，一句一屏，随音频切换。"""
    text = "".join(str(text).split())
    if not text:
        return [""]
    cues: list[str] = []
    buf = ""
    punct = set("，。！？、,!?;；")
    for ch in text:
        buf += ch
        if ch in punct:
            cues.append(buf)
            buf = ""
    if buf:
        cues.append(buf)
    # 过长无标点句再按字数切开，避免单屏一大坨
    out: list[str] = []
    for cue in cues:
        if len(cue) <= SUB_WRAP + 2:
            out.append(cue)
            continue
        out.extend(wrap_cn(cue, SUB_WRAP))
    return out or [text]


def allocate_cue_times(cues: list[str], duration: float) -> list[tuple[str, float, float]]:
    """按字数比例分配每句起止时间（秒）。"""
    weights = [max(len("".join(c.split())), 1) for c in cues]
    total = sum(weights) or 1
    # 前后各留一点空隙，避免首尾闪切
    start = 0.08
    end_pad = 0.05
    usable = max(duration - start - end_pad, 0.2)
    t = start
    timed: list[tuple[str, float, float]] = []
    for i, (cue, w) in enumerate(zip(cues, weights)):
        span = usable * (w / total)
        if i == len(cues) - 1:
            t1 = max(duration - end_pad, t + 0.12)
        else:
            t1 = t + span
        timed.append((cue, t, t1))
        t = t1
    return timed


def subtitle_drawtexts(*, textfile: str | None = None, text: str | None = None) -> list[str]:
    """整段字幕（兼容旧调用）；新成片请用 timed_subtitle_drawtexts。"""
    font = SUB_FONT if Path(SUB_FONT).exists() else FONT
    if textfile:
        src = f"textfile='{textfile}'"
    else:
        src = f"text='{escape_drawtext(text or '')}'"
    common = (
        f"fontfile={font}:{src}:fontsize={SUB_SIZE}:"
        f"x=(w-text_w)/2:y=h-text_h-{SUB_MARGIN_BOTTOM}:"
        f"line_spacing={SUB_LINE_SPACING}:expansion=none"
    )
    return [
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=8:bordercolor={SUB_FILL}",
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=3:bordercolor={SUB_OUTLINE}",
    ]


def timed_subtitle_drawtexts(script: str, duration: float) -> list[str]:
    """底部口播字幕：一句一屏，随音频时间切换。"""
    font = SUB_FONT if Path(SUB_FONT).exists() else FONT
    cues = allocate_cue_times(split_cues(script), duration)
    filters: list[str] = []
    for cue, t0, t1 in cues:
        # 单句若仍偏长，内部换行但同一时间窗
        lines = wrap_cn(cue, SUB_WRAP)
        text = escape_drawtext("\n".join(lines))
        enable = f"between(t\\,{t0:.3f}\\,{t1:.3f})"
        common = (
            f"fontfile={font}:text='{text}':fontsize={SUB_SIZE}:"
            f"x=(w-text_w)/2:y=h-text_h-{SUB_MARGIN_BOTTOM}:"
            f"line_spacing={SUB_LINE_SPACING}:expansion=none:"
            f"enable='{enable}'"
        )
        filters.append(f"drawtext={common}:fontcolor={SUB_FILL}:borderw=8:bordercolor={SUB_FILL}")
        filters.append(f"drawtext={common}:fontcolor={SUB_FILL}:borderw=3:bordercolor={SUB_OUTLINE}")
    return filters


def escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def write_sub_txt(text: str, dest: Path) -> Path:
    """写出切句预览（调试用）；成片不再用整文件一次性叠字。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(split_cues(text)), encoding="utf-8")
    return dest


def concat_parts(parts: list[Path], dest: Path) -> None:
    if not parts:
        raise SystemExit("没有可拼接的片段")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if len(parts) == 1:
        shutil.copy2(parts[0], dest)
        return
    inputs: list[str] = ["ffmpeg", "-y"]
    for part in parts:
        inputs.extend(["-i", str(part)])
    n = len(parts)
    v_inputs = "".join(f"[{i}:v:0]" for i in range(n))
    a_inputs = "".join(f"[{i}:a:0]" for i in range(n))
    graph = (
        f"{v_inputs}concat=n={n}:v=1:a=0[v];"
        f"{a_inputs}concat=n={n}:v=0:a=1[a]"
    )
    run(
        inputs
        + [
            "-filter_complex",
            graph,
            "-map",
            "[v]",
            "-map",
            "[a]",
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


def normalize_tags(tags) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        tags = [t for t in re.split(r"[\s,，]+", tags) if t]
    out: list[str] = []
    for tag in tags:
        text = str(tag).strip()
        if not text:
            continue
        if not text.startswith("#"):
            text = "#" + text.lstrip("#")
        out.append(text)
    return out


def report_caption(plan: dict, dest: Path) -> None:
    title = str(plan.get("douyin_title") or "").strip()
    intro = str(plan.get("douyin_intro") or "").strip()
    tags = normalize_tags(plan.get("douyin_tags"))
    tag_line = " ".join(tags)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"标题：{title}\n\n作品简介：{intro}\n\n标签：{tag_line}\n",
        encoding="utf-8",
    )
    log("---------- 抖音文案 ----------")
    log(f"爆款标题: {title or '（缺失）'}")
    log(f"作品简介: {intro or '（缺失）'}")
    log(f"标签: {tag_line or '（缺失）'}")
    log(f"可复制: {dest}")
    log("------------------------------")


def require_deps() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_deps

    missing = check_deps.check()
    check_deps.report(missing)
    if missing:
        raise SystemExit(1)
