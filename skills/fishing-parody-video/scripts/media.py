#!/usr/bin/env python3
"""TTS、硬字幕、拼接、BGM。"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 恶搞默认：卡通男声 + 加速抬调（鱼开麦）；禁止用教学课晓晓
VOICE = "zh-CN-YunxiaNeural"
RATE = "+22%"
PITCH = "+12Hz"
# 可选：卡通女 / 辽宁幽默 / 激情男 /（禁止当默认）晓晓
VOICE_ALIASES = {
    "xiaoyi": "zh-CN-XiaoyiNeural",
    "yunxia": "zh-CN-YunxiaNeural",
    "xiaobei": "zh-CN-liaoning-XiaobeiNeural",
    "yunjian": "zh-CN-YunjianNeural",
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",
}
FONT = "/System/Library/Fonts/PingFang.ttc"
WATERMARK = ROOT / "assets" / "copyright.png"
DEFAULT_BGM = ROOT / "assets" / "bgm" / "default.mp3"
BGM_VOLUME = 0.12
BGM_FADE_OUT = 2.0
# 沙雕字幕：大黄字 + 粗黑边 + 轻微弹入（别用教学课小粉字）
SUB_SIZE = 76
SUB_MARGIN_BOTTOM = 120
SUB_WRAP = 8
SUB_MAX_LINES = 2
SUB_OUTLINE_W = 7
SUB_SHADOW = 3
# ASS &HAABBGGRR：亮黄 #FFE14A → &H004AE1FF；描边近黑
SUB_ASS_PRIMARY = "&H004AE1FF"
SUB_ASS_OUTLINE = "&H00140E0A"
SUB_ASS_SHADOW = "&H80000000"


def log(msg: str) -> None:
    print(f"[parody] {msg}", flush=True)


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


def resolve_voice(name: str | None) -> str:
    raw = (name or VOICE).strip()
    key = raw.lower().replace("_", "-")
    if key in VOICE_ALIASES:
        return VOICE_ALIASES[key]
    # 短名：xiaoyi / yunxia
    short = key.split("-")[-1].replace("neural", "")
    if short in VOICE_ALIASES:
        return VOICE_ALIASES[short]
    return raw


def edge_tts_cmd(
    text: str,
    dest: Path,
    *,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
) -> list[str]:
    v = resolve_voice(voice)
    r = rate or RATE
    p = pitch or PITCH
    if shutil.which("edge-tts"):
        return [
            "edge-tts",
            "--voice",
            v,
            "--rate",
            r,
            "--pitch",
            p,
            "--text",
            text,
            "--write-media",
            str(dest),
        ]
    return [
        sys.executable,
        "-m",
        "edge_tts",
        "--voice",
        v,
        "--rate",
        r,
        "--pitch",
        p,
        "--text",
        text,
        "--write-media",
        str(dest),
    ]


def tts(
    text: str,
    dest: Path,
    *,
    voice: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(edge_tts_cmd(text, dest, voice=voice, rate=rate, pitch=pitch))
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
    out: list[str] = []
    for cue in cues:
        if len(cue) <= 18:
            out.append(cue)
            continue
        out.extend(wrap_cn(cue, 12))
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
    dest.parent.mkdir(parents=True, exist_ok=True)
    cues = split_cues(text)
    weights = [max(len(re.sub(r"\s+", "", c)), 1) for c in cues]
    total_w = sum(weights) or 1
    raw = [duration * w / total_w for w in weights]
    min_dur = 0.9
    if sum(max(d, min_dur) for d in raw) <= duration + 0.05:
        durs = [max(d, min_dur) for d in raw]
        scale = duration / sum(durs)
        durs = [d * scale for d in durs]
    else:
        durs = raw

    font_name = "PingFang SC" if Path(FONT).exists() else "Heiti SC"
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{SUB_SIZE},{SUB_ASS_PRIMARY},&H000000FF,{SUB_ASS_OUTLINE},{SUB_ASS_SHADOW},-1,0,0,0,100,100,1,0,1,{SUB_OUTLINE_W},{SUB_SHADOW},2,36,36,{SUB_MARGIN_BOTTOM},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    t = 0.0
    for cue, dur in zip(cues, durs):
        start, end = t, min(duration, t + dur)
        wrapped = wrap_cn(cue, SUB_WRAP)[:SUB_MAX_LINES]
        body = _ass_escape("\n".join(wrapped))
        # 沙雕弹入：先略大再回落，带一点淡入
        pop = r"{\fad(80,60)\t(0,160,\fscx108\fscy108)\t(160,280,\fscx100\fscy100)}"
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{pop}{body}\n"
        )
        t = end
        if t >= duration - 0.01:
            break
    dest.write_text("".join(lines), encoding="utf-8")
    return dest


def escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def write_sub_txt(text: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(split_cues(text)), encoding="utf-8")
    return dest


def ass_filter(ass_path: Path) -> str:
    return f"ass='{escape_filter_path(ass_path)}'"


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
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_absolute():
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
    dest.parent.mkdir(parents=True, exist_ok=True)
    dur = ffprobe_duration(video)
    fade_start = max(0.0, dur - fade_out)
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
