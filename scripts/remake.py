#!/usr/bin/env python3
"""yt-dlp 下载 + edge-tts 女声 + ffmpeg 按口播对齐剪辑。"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE = "zh-CN-XiaoxiaoNeural"
MAX_VIDEO_SLOW = 1.35
MAX_AUDIO_FAST = 1.30
FONT = "/System/Library/Fonts/PingFang.ttc"
SUB_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
WATERMARK = ROOT / "assets" / "copyright.png"
SUB_FILL = "0xFF2A12"
SUB_OUTLINE = "0xFFEDE6"
SUB_SIZE = 54
YT_ID_RE = re.compile(
    r"(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=|embed/|live/))([A-Za-z0-9_-]{11})"
)


def log(msg: str) -> None:
    print(f"[remake] {msg}", flush=True)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    log("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, **kwargs)


def youtube_id(url: str) -> str:
    m = YT_ID_RE.search(url)
    if m:
        return m.group(1)
    raise SystemExit(f"无法从 URL 解析视频 id: {url}")


def parse_ts(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    parts = text.split(":")
    if len(parts) == 2:
        mm, ss = parts
        return int(mm) * 60 + float(ss)
    if len(parts) == 3:
        hh, mm, ss = parts
        return int(hh) * 3600 + int(mm) * 60 + float(ss)
    raise ValueError(f"无法解析时间: {value}")


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


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"源视频已存在，跳过下载: {dest}")
        return dest
    last_err = None
    for attempt in range(1, 4):
        cmd = [
            "yt-dlp",
            "--retries",
            "15",
            "--fragment-retries",
            "15",
            "--retry-sleep",
            "exp=1:8:2",
            "--force-overwrites",
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "-o",
            str(dest),
            url,
        ]
        try:
            log(f"yt-dlp 第 {attempt}/3 次")
            run(cmd)
            if dest.exists() and dest.stat().st_size > 0:
                return dest
            merged = dest.with_suffix(".mp4")
            if merged.exists():
                return merged
        except subprocess.CalledProcessError as exc:
            last_err = exc
            wait = 2 ** attempt
            log(f"下载失败，{wait}s 后整任务重试")
            time.sleep(wait)
    raise SystemExit(f"yt-dlp 失败: {last_err}")


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


def atempo_filter(speed: float) -> str:
    """atempo 只接受 0.5–2.0，超出就串起来。"""
    parts = []
    remain = speed
    while remain > 2.0 + 1e-6:
        parts.append("atempo=2.0")
        remain /= 2.0
    while remain < 0.5 - 1e-6:
        parts.append("atempo=0.5")
        remain /= 0.5
    parts.append(f"atempo={remain:.5f}")
    return ",".join(parts)


def sync_plan(video_dur: float, tts_dur: float) -> tuple[float, float, float]:
    """返回 (画面倍速因子>1更慢, 音频倍速因子>1更快, 定格秒数)。"""
    if video_dur <= 0.05:
        video_dur = 0.05
    if tts_dur <= video_dur:
        return 1.0, 1.0, 0.0
    # 口播更长：先慢放画面，再加速音频，最后定格
    slow = min(tts_dur / video_dur, MAX_VIDEO_SLOW)
    stretched = video_dur * slow
    if tts_dur <= stretched + 0.05:
        return slow, 1.0, 0.0
    fast = min(tts_dur / stretched, MAX_AUDIO_FAST)
    audio_out = tts_dur / fast
    freeze = max(0.0, audio_out - stretched)
    return slow, fast, freeze


def subtitle_drawtexts(*, textfile: str | None = None, text: str | None = None) -> list[str]:
    """橙红字 + 浅粉描边 + 外圈红晕，对齐参考字幕风格。"""
    font = SUB_FONT if Path(SUB_FONT).exists() else FONT
    if textfile:
        src = f"textfile='{textfile}'"
    else:
        src = f"text='{text}'"
    common = (
        f"fontfile={font}:{src}:fontsize={SUB_SIZE}:"
        "x=(w-text_w)/2:y=h-text_h-110:line_spacing=10:expansion=none"
    )
    return [
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=6:bordercolor={SUB_FILL}",
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=2:bordercolor={SUB_OUTLINE}",
    ]


def wrap_cn(text: str, width: int = 11) -> list[str]:
    text = "".join(text.split())
    lines: list[str] = []
    buf = ""
    punct = set("，。！？、,!?;；")
    for ch in text:
        buf += ch
        if len(buf) >= width or (len(buf) >= 6 and ch in punct):
            lines.append(buf)
            buf = ""
    if buf:
        lines.append(buf)
    return lines or [text]


def escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def write_sub_txt(text: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(wrap_cn(text)), encoding="utf-8")
    return dest


def cut_clip(
    source: Path,
    start: float,
    end: float,
    audio: Path,
    overlay: str,
    subtitle: str,
    dest: Path,
    sub_txt: Path | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    clip_dur = max(0.2, end - start)
    tts_dur = ffprobe_duration(audio)
    slow, fast, freeze = sync_plan(clip_dur, tts_dur)
    log(
        f"片段 {start:.2f}-{end:.2f}s 画面 {clip_dur:.2f}s / 口播 {tts_dur:.2f}s "
        f"→ 慢放 {slow:.3f} 音频加速 {fast:.3f} 定格 {freeze:.2f}s"
    )

    vf = [f"setpts=PTS*{slow:.5f}"]
    if freeze > 0.05:
        vf.append(f"tpad=stop_mode=clone:stop_duration={freeze:.3f}")
    if overlay.strip() and Path(FONT).exists():
        vf.append(
            "drawtext=fontfile={font}:text='{text}':fontsize=56:fontcolor=yellow:"
            "borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.08:expansion=none".format(
                font=FONT,
                text=escape_drawtext(overlay.strip().replace("\n", " ")),
            )
        )
    if subtitle.strip() and Path(FONT).exists() and sub_txt is not None:
        write_sub_txt(subtitle, sub_txt)
        vf.extend(subtitle_drawtexts(textfile=escape_filter_path(sub_txt)))
    elif subtitle.strip() and Path(FONT).exists():
        vf.extend(
            subtitle_drawtexts(text=escape_drawtext("\n".join(wrap_cn(subtitle))))
        )
    vfilter = ",".join(vf)
    afilter = atempo_filter(fast)

    inputs = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
        "-i",
        str(source),
        "-i",
        str(audio),
    ]
    mark = WATERMARK if WATERMARK.exists() else None
    if mark:
        inputs.extend(["-i", str(mark)])
        # 去黑底，顶部居中叠「鱼公移山」版权图
        graph = (
            f"[0:v]{vfilter}[vbase];"
            f"[2:v]format=rgba,colorkey=0x000000:0.12:0.08,scale=440:-1[wm];"
            f"[vbase][wm]overlay=(W-w)/2:18[v];"
            f"[1:a]{afilter}[a]"
        )
        log(f"叠加版权图 {mark.name}")
    else:
        graph = f"[0:v]{vfilter}[v];[1:a]{afilter}[a]"
        log("未找到 assets/copyright.png，跳过版权图")

    cmd = inputs + [
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-shortest",
        "-r",
        "30",
        "-c:v",
        "libx264",
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
    run(cmd)


def concat_parts(parts: list[Path], dest: Path) -> None:
    list_file = dest.parent / "concat.txt"
    lines = [f"file '{p.resolve()}'" for p in parts]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(dest),
        ]
    )


def load_plan(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("clips"):
        raise SystemExit(f"{path} 没有 clips")
    return data


def edit(plan: dict, workdir: Path, source: Path) -> Path:
    parts_dir = workdir / "parts"
    tts_dir = workdir / "tts"
    subs_dir = workdir / "subs"
    parts: list[Path] = []
    for i, clip in enumerate(plan["clips"]):
        start, end = parse_ts(clip["start"]), parse_ts(clip["end"])
        if end <= start:
            raise SystemExit(f"clips[{i}] 结束时间不大于开始时间")
        script = str(clip.get("script") or clip.get("narration") or "").strip()
        if not script:
            raise SystemExit(f"clips[{i}] 口播为空")
        suggested = max(1, round((end - start) * 3))
        log(f"clips[{i}] 口播 {len(script)} 字 / 按时长建议约 {suggested} 字")
        audio = tts(script, tts_dir / f"{i:02d}.mp3")
        part = parts_dir / f"{i:02d}.mp4"
        cut_clip(
            source,
            start,
            end,
            audio,
            str(clip.get("overlay") or ""),
            script,
            part,
            subs_dir / f"{i:02d}.txt",
        )
        parts.append(part)
    final = workdir / "final.mp4"
    concat_parts(parts, final)
    log(f"成片: {final}")
    return final


def require_deps() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import check_deps

    missing = check_deps.check()
    check_deps.report(missing)
    if missing:
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并对齐剪辑钓鱼二创短视频")
    parser.add_argument("--url", required=True)
    parser.add_argument("--plan", help="gemini_cdp.py 产出的 edit.json")
    parser.add_argument("--workdir")
    parser.add_argument("--all", action="store_true", help="先调 Gemini CDP 再成片")
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--target-duration", type=float, help="期望成片总时长（秒），传给 Gemini")
    args = parser.parse_args()

    require_deps()

    vid = youtube_id(args.url)
    workdir = Path(args.workdir) if args.workdir else ROOT / "output" / vid
    workdir.mkdir(parents=True, exist_ok=True)
    plan_path = Path(args.plan) if args.plan else workdir / "edit.json"

    if args.all or not plan_path.exists():
        gemini = ROOT / "scripts" / "gemini_cdp.py"
        cmd = [
            sys.executable,
            str(gemini),
            "--url",
            args.url,
            "--out",
            str(plan_path),
            "--cdp",
            args.cdp,
        ]
        if args.target_duration:
            cmd.extend(["--target-duration", f"{args.target_duration:g}"])
        run(cmd)

    plan = load_plan(plan_path)
    source = download(args.url, workdir / "source.mp4")
    edit(plan, workdir, source)
    return 0


if __name__ == "__main__":
    sys.exit(main())
