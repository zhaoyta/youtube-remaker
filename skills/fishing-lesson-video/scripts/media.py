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
DEFAULT_BGM = ROOT / "assets" / "bgm" / "default.mp3"
# 口播下压：约 10%～14%，别盖女声
BGM_VOLUME = 0.12
BGM_FADE_OUT = 2.5
# 粉色粗体 + 深描边（ASS 色值见 write_ass）
SUB_FILL = "0xFF69B4"
SUB_OUTLINE = "0x0A0E14"
SUB_SIZE = 58
SUB_MARGIN_BOTTOM = 96
SUB_LINE_SPACING = 10
SUB_WRAP = 10
SUB_MAX_LINES = 2
# ASS: &HAABBGGRR，粉 #FF69B4 → &H00B469FF；Bold=-1
SUB_ASS_PRIMARY = "&H00B469FF"
SUB_ASS_OUTLINE = "&H00140E0A"


def log(msg: str) -> None:
    print(f"[lesson] {msg}", flush=True)


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
        buf += ch
        if len(buf) >= width and ch in punct:
            lines.append(buf)
            buf = ""
        elif len(buf) >= width + 2:
            lines.append(buf)
            buf = ""
    if buf:
        lines.append(buf)
    return lines or [text]


def split_cues(text: str) -> list[str]:
    """按标点拆成短句字幕，避免一整段一坨。"""
    text = "".join(str(text or "").split())
    if not text:
        return []
    parts = re.split(r"(?<=[，。！？；、,!?;])", text)
    cues: list[str] = []
    buf = ""
    for part in parts:
        if not part:
            continue
        trial = buf + part
        # 单条控制在约 16 字内，超过就先吐出缓冲
        if buf and len(trial) > 16:
            cues.append(buf)
            buf = part
        else:
            buf = trial
        if len(buf) >= 10 and buf[-1] in "，。！？；、,!?;":
            cues.append(buf)
            buf = ""
    if buf:
        cues.append(buf)
    # 再把过长的句硬切
    out: list[str] = []
    for cue in cues:
        if len(cue) <= 18:
            out.append(cue)
            continue
        for line in wrap_cn(cue, 12):
            out.append(line)
    return out or [text]


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", "\\N")
    )


def write_ass(text: str, duration: float, dest: Path) -> Path:
    """按时长比例轮播短字幕（ASS）。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    cues = split_cues(text)
    weights = [max(len(re.sub(r"\s+", "", c)), 1) for c in cues]
    total_w = sum(weights) or 1
    # 每条至少 1.1s，总长不够就等比压缩
    raw = [duration * w / total_w for w in weights]
    min_dur = 1.1
    if sum(max(d, min_dur) for d in raw) <= duration + 0.05:
        durs = [max(d, min_dur) for d in raw]
        scale = duration / sum(durs)
        durs = [d * scale for d in durs]
    else:
        durs = raw

    font_name = "PingFang SC" if Path(FONT).exists() else "Heiti SC"
    # ASS PrimaryColour / OutlineColour 是 &HAABBGGRR；Bold=-1 粗体
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{SUB_SIZE},{SUB_ASS_PRIMARY},&H000000FF,{SUB_ASS_OUTLINE},&H64000000,-1,0,0,0,100,100,0,0,1,4,0,2,40,40,{SUB_MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    t = 0.0
    for cue, dur in zip(cues, durs):
        start, end = t, min(duration, t + dur)
        # 单条最多两行
        wrapped = wrap_cn(cue, SUB_WRAP)[:SUB_MAX_LINES]
        body = _ass_escape("\n".join(wrapped))
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{body}\n"
        )
        t = end
        if t >= duration - 0.01:
            break
    dest.write_text("".join(lines), encoding="utf-8")
    return dest


def escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def write_sub_txt(text: str, dest: Path) -> Path:
    """备查：按句拆开写文本，不再整段糊成一坨。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(split_cues(text)), encoding="utf-8")
    return dest


def ass_filter(ass_path: Path) -> str:
    return f"ass='{escape_filter_path(ass_path)}'"


# 兼容旧调用名
def subtitle_drawtexts(*, textfile: str | None = None, text: str | None = None) -> list[str]:
    font = SUB_FONT if Path(SUB_FONT).exists() else FONT
    if textfile:
        src = f"textfile='{textfile}'"
    else:
        src = f"text='{text}'"
    common = (
        f"fontfile={font}:{src}:fontsize={SUB_SIZE}:"
        f"x=(w-text_w)/2:y=h-text_h-{SUB_MARGIN_BOTTOM}:"
        f"line_spacing={SUB_LINE_SPACING}:expansion=none"
    )
    return [
        f"drawtext={common}:fontcolor={SUB_OUTLINE}:borderw=6:bordercolor={SUB_OUTLINE}",
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=2:bordercolor={SUB_OUTLINE}",
    ]


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
    graph = f"{v_inputs}concat=n={n}:v=1:a=0[v];{a_inputs}concat=n={n}:v=0:a=1[a]"
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


def resolve_bgm(explicit: str | Path | None = None) -> Path | None:
    """优先用传入路径 / lesson 字段，否则用 assets/bgm/default.mp3。"""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
            # 相对 skill 根 或 仓库常见写法 assets/bgm/xxx.mp3
            for base in (ROOT, ROOT / "assets" / "bgm", Path.cwd()):
                cand = (base / p).resolve()
                if cand.exists():
                    return cand
            p = p.resolve()
        if p.exists() and p.stat().st_size > 0:
            return p
        log(f"BGM 不存在，跳过: {p}")
        return None
    if DEFAULT_BGM.exists() and DEFAULT_BGM.stat().st_size > 0:
        return DEFAULT_BGM
    return None


def mix_bgm(
    video: Path,
    dest: Path,
    bgm: Path,
    *,
    volume: float = BGM_VOLUME,
    fade_out: float = BGM_FADE_OUT,
) -> Path:
    """口播成片下压混入循环 BGM，结尾淡出。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dur = ffprobe_duration(video)
    fade_start = max(0.0, dur - fade_out)
    # 循环 BGM → 压音量 → 淡出；与口播 amix，以视频时长为准
    graph = (
        f"[1:a]volume={volume:.3f},"
        f"afade=t=out:st={fade_start:.3f}:d={fade_out:.3f}[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2,"
        f"alimiter=limit=0.95[a]"
    )
    tmp = dest.with_suffix(".bgm.tmp.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-stream_loop",
            "-1",
            "-i",
            str(bgm),
            "-filter_complex",
            graph,
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    tmp.replace(dest)
    log(f"已混 BGM: {bgm.name}  volume={volume:.2f}")
    return dest


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
    credits = plan.get("image_credits") or []
    credit_block = ""
    if credits:
        credit_block = "\n\n图片署名（仅文案备查，不上屏）：\n" + "\n".join(f"- {c}" for c in credits)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"标题：{title}\n\n作品简介：{intro}\n\n标签：{tag_line}{credit_block}\n",
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
