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

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import remix  # noqa: E402

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
VOICE = DEFAULT_VOICE
MAX_VIDEO_SLOW = 1.35
MAX_AUDIO_FAST = 1.30
FONT = "/System/Library/Fonts/PingFang.ttc"
SUB_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
WATERMARK = ROOT / "assets" / "copyright.png"
SUB_FILL = "0xFF2A12"
SUB_OUTLINE = "0xFFEDE6"
SUB_SIZE = 66
SUB_MARGIN_BOTTOM = 220
SUB_LINE_SPACING = 12
SUB_WRAP = 14  # 单行字数；超过才硬切，避免正常短句被拦腰斩断
SUB_HARD_WRAP = 18  # 无标点长句超过此长度才强制拆行
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


def ffprobe_wh(path: Path) -> tuple[int, int]:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    ).strip()
    w, h = out.split(",")
    return int(w), int(h)


def escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace(":", "\\:")
        .replace("%", "\\%")
    )


def youtube_title(url: str) -> str:
    try:
        out = subprocess.check_output(
            ["yt-dlp", "--no-playlist", "--skip-download", "--print", "%(title)s", url],
            text=True,
            timeout=60,
        ).strip()
        return out.splitlines()[-1].strip() if out else ""
    except Exception:
        return ""


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


def split_script_cues(text: str) -> list[str]:
    """把口播拆成短字幕句：按标点切，过长再按字数切。禁止整段糊成一坨。"""
    text = "".join(str(text or "").split())
    if not text:
        return []
    raw: list[str] = []
    buf = ""
    punct = set("，。！？、,!?;；…—～~")
    for ch in text:
        buf += ch
        if ch in punct:
            piece = buf.strip()
            if piece:
                raw.append(piece)
            buf = ""
    if buf.strip():
        raw.append(buf.strip())
    cues: list[str] = []
    for piece in raw or [text]:
        body = piece
        while len(body) > SUB_HARD_WRAP:
            # 尽量在靠后位置找可断点，找不到再按 SUB_WRAP 切
            cut = SUB_WRAP
            for i in range(min(len(body) - 1, SUB_HARD_WRAP), max(4, SUB_WRAP // 2), -1):
                if body[i - 1] in "的了吗呢吧啊呀":
                    cut = i
                    break
            cues.append(body[:cut])
            body = body[cut:]
        if body:
            cues.append(body)
    return cues or [text]


def cue_timeline(cues: list[str], duration: float) -> list[tuple[float, float, str]]:
    """按字数比例分配时间，与口播节奏大致对齐。"""
    if not cues:
        return []
    duration = max(0.2, duration)
    weights = [max(1, len("".join(ch for ch in c if ch.strip()))) for c in cues]
    total = sum(weights)
    timeline: list[tuple[float, float, str]] = []
    t = 0.0
    for i, (cue, w) in enumerate(zip(cues, weights)):
        if i == len(cues) - 1:
            end = duration
        else:
            end = min(duration, t + duration * (w / total))
            # 过短会闪，至少给 0.35s；不够就挤后面
            end = max(end, t + 0.35)
            end = min(end, duration - 0.05 * (len(cues) - i - 1))
        if end <= t:
            end = min(duration, t + 0.2)
        timeline.append((t, end, cue))
        t = end
    if timeline:
        s, _, c = timeline[-1]
        timeline[-1] = (s, duration, c)
    return timeline


def subtitle_drawtexts_for_cue(text: str, *, enable: str | None = None) -> list[str]:
    """单句字幕：橙红字 + 浅粉描边 + 外圈红晕。可带 enable 做逐句切换。"""
    font = SUB_FONT if Path(SUB_FONT).exists() else FONT
    # 单句优先一行；超长才折行，仍只显示当前句
    display = "\n".join(wrap_cn(text)) if len(text) > SUB_WRAP else text
    src = f"text='{escape_drawtext(display)}'"
    common = (
        f"fontfile={font}:{src}:fontsize={SUB_SIZE}:"
        f"x=(w-text_w)/2:y=h-text_h-{SUB_MARGIN_BOTTOM}:"
        f"line_spacing={SUB_LINE_SPACING}:expansion=none"
    )
    if enable:
        common = f"{common}:enable='{enable}'"
    return [
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=8:bordercolor={SUB_FILL}",
        f"drawtext={common}:fontcolor={SUB_FILL}:borderw=3:bordercolor={SUB_OUTLINE}",
    ]


def build_subtitle_filters(script: str, out_dur: float) -> list[str]:
    """硬字幕必须与 TTS 文案一致，并按句切换，不要整段一直堆在底部。"""
    cues = split_script_cues(script)
    timed = cue_timeline(cues, out_dur)
    filters: list[str] = []
    for start, end, cue in timed:
        # filter graph 里逗号要转义
        enable = f"between(t\\,{start:.3f}\\,{end:.3f})"
        filters.extend(subtitle_drawtexts_for_cue(cue, enable=enable))
    return filters


def write_sub_cues(script: str, out_dur: float, dest: Path) -> Path:
    """调试用：写出逐句字幕时间轴，便于核对文案=语音。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (start, end, cue) in enumerate(cue_timeline(split_script_cues(script), out_dur), 1):
        lines.append(f"{i:02d}\t{start:.3f}-{end:.3f}\t{cue}")
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
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
    *,
    remix_params: remix.RemixParams | None = None,
    frame_size: tuple[int, int] | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    clip_dur = max(0.2, end - start)
    tts_dur = ffprobe_duration(audio)
    slow, fast, freeze = sync_plan(clip_dur, tts_dur)
    out_dur = tts_dur / max(fast, 1e-6)
    log(
        f"片段 {start:.2f}-{end:.2f}s 画面 {clip_dur:.2f}s / 口播 {tts_dur:.2f}s "
        f"→ 慢放 {slow:.3f} 音频加速 {fast:.3f} 定格 {freeze:.2f}s"
    )

    vf = [f"setpts=PTS*{slow:.5f}"]
    if freeze > 0.05:
        vf.append(f"tpad=stop_mode=clone:stop_duration={freeze:.3f}")
    if remix_params is not None:
        width, height = frame_size or ffprobe_wh(source)
        vf.extend(remix.video_filters(remix_params, width, height, out_dur))
        log(
            f"二创 {remix_params.anchor} 裁 {remix_params.crop_pct_w*100:.1f}%/"
            f"{remix_params.crop_pct_h*100:.1f}% 转 {remix_params.rotate_deg:.2f}° "
            f"色相 {remix_params.hue_deg:.1f} 颗粒 {remix_params.noise}"
        )
    if overlay.strip() and Path(FONT).exists():
        vf.append(
            "drawtext=fontfile={font}:text='{text}':fontsize=56:fontcolor=yellow:"
            "borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.08:expansion=none".format(
                font=FONT,
                text=escape_drawtext(overlay.strip().replace("\n", " ")),
            )
        )
    spoken = subtitle.strip()
    if spoken and Path(FONT).exists():
        if sub_txt is not None:
            write_sub_cues(spoken, out_dur, sub_txt)
        cues = split_script_cues(spoken)
        log(f"字幕 {len(cues)} 句切换（与口播同文）")
        vf.extend(build_subtitle_filters(spoken, out_dur))
    vf.append(f"trim=duration={out_dur:.3f},setpts=PTS-STARTPTS")
    vfilter = ",".join(vf)
    afilter = atempo_filter(fast)
    if remix_params is not None:
        afilter = remix.audio_filters(afilter, remix_params, out_dur)
    else:
        afilter = (
            f"{afilter},apad=whole_dur={out_dur:.3f},"
            f"atrim=duration={out_dur:.3f},asetpts=PTS-STARTPTS"
        )

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

    crf = str(remix_params.crf if remix_params is not None else 20)
    cmd = inputs + [
        "-filter_complex",
        graph,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        f"{out_dur:.3f}",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-crf",
        crf,
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
    if not parts:
        raise SystemExit("没有可拼接的片段")
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


def load_plan(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("clips"):
        raise SystemExit(f"{path} 没有 clips")
    return data


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


def fallback_intro(plan: dict) -> str:
    scripts = []
    for clip in plan.get("clips") or []:
        text = str(clip.get("script") or clip.get("narration") or "").strip()
        if text:
            scripts.append(text.rstrip("！!。"))
    if not scripts:
        return str(plan.get("douyin_title") or "").strip()
    joined = "，".join(scripts[:2])
    if not joined.endswith(("！", "!", "。")):
        joined += "！"
    return joined


def report_caption(plan: dict, dest: Path) -> None:
    title = str(plan.get("douyin_title") or "").strip()
    intro = str(plan.get("douyin_intro") or plan.get("douyin_desc") or "").strip()
    if not intro:
        intro = fallback_intro(plan)
        plan["douyin_intro"] = intro
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


def edit(
    plan: dict,
    workdir: Path,
    source: Path,
    *,
    seed: str,
    enable_remix: bool = True,
) -> Path:
    parts_dir = workdir / "parts"
    tts_dir = workdir / "tts"
    subs_dir = workdir / "subs"
    parts: list[Path] = []
    source_dur = ffprobe_duration(source)
    frame_size = ffprobe_wh(source)
    clip_count = len(plan["clips"])
    remix_dump: list[dict] = []
    for i, clip in enumerate(plan["clips"]):
        start, end = parse_ts(clip["start"]), parse_ts(clip["end"])
        start = max(0.0, start)
        end = min(end, source_dur)
        if end - start < 0.2:
            log(f"clips[{i}] 超出片源 {source_dur:.2f}s，跳过")
            continue
        params = remix.make_params(seed, i, clip_count) if enable_remix else None
        if params is not None:
            start, end = remix.jitter_span(start, end, source_dur, params)
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
            remix_params=params,
            frame_size=frame_size,
        )
        parts.append(part)
        if params is not None:
            remix_dump.append(
                {
                    "clip": i,
                    "start": round(start, 3),
                    "end": round(end, 3),
                    **params.to_dict(),
                }
            )
    if remix_dump:
        dump_path = workdir / "remix.json"
        dump_path.write_text(
            json.dumps(remix_dump, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        log(f"二创参数: {dump_path}")
    final = workdir / "final.mp4"
    concat_parts(parts, final)
    log(f"成片: {final}")
    report_caption(plan, workdir / "caption.txt")
    plan_dump = workdir / "edit.json"
    plan_dump.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
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
    parser.add_argument("--no-remix", action="store_true", help="关闭二创滤镜（调试用）")
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"edge-tts 音色（默认 {DEFAULT_VOICE}）",
    )
    parser.add_argument(
        "--prompt",
        help="传给 gemini_cdp.py 的提示词文件（仅 --all / 缺 plan 时生效）",
    )
    args = parser.parse_args()

    require_deps()

    global VOICE
    VOICE = args.voice
    log(f"TTS 音色: {VOICE}")

    vid = youtube_id(args.url)
    workdir = Path(args.workdir) if args.workdir else Path.cwd() / "output" / vid
    workdir.mkdir(parents=True, exist_ok=True)
    plan_path = Path(args.plan) if args.plan else workdir / "edit.json"
    source = download(args.url, workdir / "source.mp4")

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
            "--source-duration",
            f"{ffprobe_duration(source):.3f}",
        ]
        if args.prompt:
            cmd.extend(["--prompt", args.prompt])
        title = youtube_title(args.url)
        if title:
            cmd.extend(["--source-title", title])
            log(f"原片标题: {title}")
        if args.target_duration:
            cmd.extend(["--target-duration", f"{args.target_duration:g}"])
        run(cmd)

    plan = load_plan(plan_path)
    edit(plan, workdir, source, seed=vid, enable_remix=not args.no_remix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
