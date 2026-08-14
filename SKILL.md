---
name: youtube-fishing-remake
description: 用 Playwright CDP 连接已登录的 gemini.google.com 理解 YouTube 短视频，生成中文口播与剪辑点，再经 yt-dlp / edge-tts / ffmpeg 做成抖音二创片。在用户给出 YouTube 链接、要做钓鱼二创、抖音二创、或提到 Gemini CDP / yt-dlp 剪辑时使用。
---

# YouTube 钓鱼短视频二创

用户给一条 YouTube 短视频链接。用**用户自己的 Gemini 网页**理解视频（不走 Gemini API），再下载、配音、剪辑。

不要用 Playwright MCP 另开浏览器，必须 CDP 连用户已登录的 Chrome。不要调用 Gemini API。
**不要直接跑系统 `python` / `python3`。** 一律：

```bash
bash scripts/uv_run.sh scripts/<脚本>.py ...
```

`uv_run.sh` 内部会 `uv venv --python 3.11`，再用 `.venv/bin/python` 执行。

## 前置

1. Chrome 已开远程调试（没有就先跑启动脚本）：

```bash
bash scripts/start-chrome-cdp.sh
```

默认 `http://127.0.0.1:9222`，独立用户目录 `~/.youtube-remaker/chrome-profile`，可与日常 Chrome 并存。第一次要在这个窗口里登录 Google，并确认能打开 https://gemini.google.com/app 。

2. 先建 3.11 环境并检查依赖，缺了就停，不要继续跑：

```bash
bash scripts/setup_venv.sh
bash scripts/uv_run.sh scripts/check_deps.py
```

必须有 `ffmpeg`（含 `ffprobe`）、`yt-dlp`，以及 venv 里的 `edge-tts`。缺少时：

```bash
brew install ffmpeg yt-dlp
bash scripts/setup_venv.sh
```

没有 `uv` 时：`curl -LsSf https://astral.sh/uv/install.sh | sh`

## 工作流

工作目录：`output/<youtube_id>/`。脚本都相对 **skill 根目录**（本仓库根，或安装后的 `~/.cursor/skills/youtube-fishing-remake` / `~/.claude/skills/youtube-fishing-remake`）。

```
Task Progress:
- [ ] bash scripts/uv_run.sh scripts/check_deps.py 通过
- [ ] Chrome CDP 可用
- [ ] Gemini 产出 edit.json
- [ ] yt-dlp 下好源视频
- [ ] 女声 TTS + ffmpeg 对齐合成
- [ ] 把 final.mp4 路径交给用户，不自动发布
```

### 1. 分析（Gemini 网页，省 token）

```bash
bash scripts/uv_run.sh scripts/gemini_cdp.py --url "YOUTUBE_URL" --out "output/<id>/edit.json"
bash scripts/uv_run.sh scripts/gemini_cdp.py --url "YOUTUBE_URL" --out "output/<id>/edit.json" --target-duration 30
```

脚本会：CDP 连接 → 复用或打开 Gemini 标签 → 新对话 → 把链接和提示词贴进去 → 等生成结束 → 抽出 JSON。

失败时：
- 连不上 9222：先跑 `start-chrome-cdp.sh`，让用户登录后再重试
- 停在登录页：让用户在调试 Chrome 里登录 Google
- 抽不到 JSON：把 `output/<id>/gemini_raw.txt` 给用户看，必要时在同一对话补一句「只输出 JSON」再跑 `--reuse-tab`

禁止改用 API，禁止自己编时间轴。

### 2. 下载 + 配音 + 剪辑

```bash
bash scripts/uv_run.sh scripts/remake.py --url "YOUTUBE_URL" --plan "output/<id>/edit.json" --workdir "output/<id>"
```

或一条龙（先分析再成片）：

```bash
bash scripts/uv_run.sh scripts/remake.py --url "YOUTUBE_URL" --all
bash scripts/uv_run.sh scripts/remake.py --url "YOUTUBE_URL" --all --target-duration 30
```

规则（已写进脚本，不要改策略）：
- yt-dlp：`--retries 15`，指数退避；已存在的源视频跳过
- edge-tts：固定 `zh-CN-XiaoxiaoNeural`，不要换男声、不要纠结术语
- 源片是短视频，**不要**做横竖屏转换、不要 blur 铺满、不要分屏
- 每个片段口播对不齐：画面最多慢放到 1.35x，音频最多加速到 1.30x；还不够就末帧定格。口播更短则裁掉画面尾部
- 原声丢掉，只留 TTS
- **默认开二创滤镜**（减轻判重）：按视频 id 播种，每段不同。画面先改再烧字幕/版权图，避免字被扭。手段包括：头尾各切几十毫秒、微旋转、非对称裁切再拉回、对比/饱和/色相/白平衡、轻锐化、时域颗粒、暗角、口播轻微变调。不要左右翻转（钓鱼空间会反），不要横竖屏转换、不要分屏、不要 blur 铺满。不要片尾淡出到黑屏。参数写到 `output/<id>/remix.json`。调试可加 `--no-remix`
- 每段 `script` 烧成底部硬字幕：黑体、字号约 66、橙红字、浅粉描边、外圈红晕；底部留白约 220px，避开播放条。不要白字黑边
- 画面顶部居中叠 `assets/copyright.png`（鱼公移山版权图）；没有该文件才跳过
- 合成到 `output/<id>/final.mp4` 后停，等用户验收

### 3. 验收

告诉用户：`edit.json` 里的时间轴、口播、成片路径。用户没要求就不要发抖音、不要改 JSON 里的选段。

## 账号口播

抖音号「鱼公移山」。提示词在 `prompts/analyze.txt`（`{url}` / `{duration_section}` 会被替换）。Gemini 必须吐这种 JSON：`douyin_title`、`douyin_tags`、`youtube_url`、`clips[].start/end`（秒，数字）、`clips[].script`。选段不要人脸、不要水印/Logo、不要原字幕。口播按约 3 字/秒写。若格式不对，在同一标签让它按 schema 重写。

## 路径

| 脚本 | 作用 |
|------|------|
| `scripts/setup_venv.sh` | `uv venv --python 3.11` + 安装 requirements |
| `scripts/uv_run.sh` | 用该 venv 执行 Python 脚本 |
| `scripts/check_deps.py` | 运行前检查 ffmpeg / yt-dlp / edge-tts / 3.11 venv |
| `scripts/gemini_cdp.py` | CDP 驱动 Gemini 网页，写出 `edit.json` |
| `scripts/remake.py` | yt-dlp + TTS + 二创滤镜 + ffmpeg |
| `scripts/remix.py` | 按视频 id 生成可复现的裁切/调色/颗粒等滤镜 |
| `prompts/analyze.txt` | Gemini 提示词，`{url}`、`{duration_section}` 会被替换 |

选择器在 `scripts/gemini_selectors.py`。Gemini 改版导致点不到输入框时，只改这个文件。更完整的本机操作说明见 `usage.md`（仓库里是 `md/usage.md`）。
