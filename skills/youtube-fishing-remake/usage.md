# YouTube 钓鱼短视频二创

把一条 YouTube 短视频，经 **已登录的 Gemini 网页**（Playwright CDP，不花 API token）理解成剪辑 JSON，再用 yt-dlp / edge-tts / ffmpeg 合成抖音成片。

## 一次安装

```bash
chmod +x install.sh
./install.sh
```

交互选择装到 Cursor、Claude，或两处都装。也可以：

```bash
./install.sh cursor
./install.sh claude
./install.sh both
```

skill 源码在 `skills/youtube-fishing-remake/`。安装是把整个目录拷到：

- Cursor：`~/.cursor/skills/youtube-fishing-remake`
- Claude：`~/.claude/skills/youtube-fishing-remake`

只装这一个：`./install.sh cursor youtube-fishing-remake`

**不要用系统 python3。** 先有 `uv`，再用 3.11 虚拟环境：

```bash
# 若没有 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

bash skills/youtube-fishing-remake/scripts/setup_venv.sh
brew install yt-dlp ffmpeg
```

不需要 `playwright install`，脚本连的是你本机 Chrome。

运行前检查（必须通过 uv venv）：

```bash
bash skills/youtube-fishing-remake/scripts/uv_run.sh skills/youtube-fishing-remake/scripts/check_deps.py
```

## 每次做片

1. 启动带调试端口的独立 Chrome（可和日常浏览器同时开）：

```bash
bash skills/youtube-fishing-remake/scripts/start-chrome-cdp.sh
```

第一次在这个窗口登录 Google，确认 https://gemini.google.com/app 能用。

2. 一条龙（Gemini 分析 + 下载 + 女声 + 剪辑）：

```bash
bash skills/youtube-fishing-remake/scripts/uv_run.sh skills/youtube-fishing-remake/scripts/remake.py --all --url "https://www.youtube.com/shorts/xxxx"
bash skills/youtube-fishing-remake/scripts/uv_run.sh skills/youtube-fishing-remake/scripts/remake.py --all --url "https://www.youtube.com/shorts/xxxx" --target-duration 30
```

成片在 `output/<视频id>/final.mp4`。同目录 `edit.json` 有时间轴和口播；`caption.txt` 是可直接复制的抖音标题、作品简介和标签。脚本结束时也会把这三项打到终端。

只分析、或已有 JSON 再成片：

```bash
bash skills/youtube-fishing-remake/scripts/uv_run.sh skills/youtube-fishing-remake/scripts/gemini_cdp.py --url "YOUTUBE_URL" --out output/<id>/edit.json
bash skills/youtube-fishing-remake/scripts/uv_run.sh skills/youtube-fishing-remake/scripts/remake.py --url "YOUTUBE_URL" --plan output/<id>/edit.json
```

## 对齐规则

口播比画面长时：画面最多慢放 1.35 倍，音频最多加速 1.30 倍，还不够就末帧定格。  
口播比画面短时：按音频长度裁掉画面尾部。  
音色固定 `zh-CN-XiaoxiaoNeural`。不做横竖屏转换。

成片默认套二创滤镜（裁切、微旋转、调色、颗粒、暗角、口播轻变调），参数在 `output/<id>/remix.json`。字幕和版权图在滤镜之后烧上。不要左右翻转，不要片尾淡出到黑屏。调试可加 `--no-remix`。

## 常见问题

- **连不上 9222**：先跑 `start-chrome-cdp.sh`，不要拿日常那个没开调试的 Chrome 硬连。
- **停在登录页**：在调试 Chrome（用户目录 `~/.youtube-remaker/chrome-profile`）里登录，不是日常窗口。
- **Gemini 没吐 JSON**：看 `output/<id>/gemini_raw.txt`，然后：

```bash
bash scripts/uv_run.sh scripts/gemini_cdp.py --url "YOUTUBE_URL" --out output/<id>/edit.json --reuse-tab
```

- **输入框找不到**：Google 改了网页，改 `scripts/gemini_selectors.py`。
- **绝对不要**在脚本里 `browser.close()`，那会把调试 Chrome 一起关停。分析结束后只关 Gemini 标签，不关 Chrome。`--reuse-tab` 时保留标签。
