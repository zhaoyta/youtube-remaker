# youtube-remaker

把 YouTube 短视频做成带中文口播、硬字幕和版权图的抖音成片。

理解视频走 **已登录的 Gemini 网页**（Playwright CDP，不调用 Gemini API）。下载用 yt-dlp，配音用 edge-tts，剪辑用 ffmpeg。Python 固定 **uv + 3.11**。

本仓库可安装为 Cursor / Claude skill。

## 依赖

- [uv](https://github.com/astral-sh/uv)
- Google Chrome（开远程调试）
- `ffmpeg`、`yt-dlp`（可用 Homebrew 安装）

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install ffmpeg yt-dlp
```

## 安装 skill

```bash
chmod +x install.sh
./install.sh          # 交互选择 Cursor / Claude / 两者
# 或
./install.sh cursor
./install.sh claude
./install.sh both
```

`install.sh` 会执行 `uv venv --python 3.11` 并安装 `requirements.txt`。不要直接用系统 `python3`。

## 做片

```bash
bash scripts/setup_venv.sh
bash scripts/uv_run.sh scripts/check_deps.py
bash scripts/start-chrome-cdp.sh   # 第一次在这个窗口登录 Google / Gemini

bash scripts/uv_run.sh scripts/remake.py --all --url "https://www.youtube.com/shorts/xxxx"
```

成片：`output/<视频id>/final.mp4`  
时间轴：`output/<id>/edit.json`

可选 `--target-duration 30` 指定期望总秒数。

更细的排错见 [`md/usage.md`](md/usage.md)。

## 成片效果

- 女声口播：`zh-CN-XiaoxiaoNeural`
- 底部硬字幕：黑体、橙红字、浅粉描边
- 顶部版权图：`assets/copyright.png`
- 口播比画面长则慢放 / 加速音频 / 末帧定格
- 默认二创滤镜：裁切、微旋转、调色、颗粒、暗角（不翻转）

## 目录

| 路径 | 作用 |
|------|------|
| `scripts/uv_run.sh` | 用 3.11 venv 跑脚本 |
| `scripts/gemini_cdp.py` | CDP 驱动 Gemini，写出剪辑 JSON |
| `scripts/remake.py` | 下载 + TTS + 二创滤镜 + 字幕 + 版权图 + 合成 |
| `scripts/remix.py` | 按视频 id 生成二创滤镜参数 |
| `prompts/analyze.txt` | Gemini 提示词 |
| `assets/copyright.png` | 「鱼公移山」版权图 |
| `SKILL.md` | Agent skill 说明 |

## License

[Apache License 2.0](LICENSE)

Copyright 2026 zhaoyta
