# youtube-remaker

钓鱼口播相关 **Cursor / Claude skill** 仓库。每个 skill 单独放在 `skills/<name>/`，脚本和依赖互不引用。

## skill 列表

| 目录 | 做什么 |
|------|------|
| [`skills/youtube-fishing-remake`](skills/youtube-fishing-remake/SKILL.md) | YouTube 短视频 → Gemini 网页理解 → 抖音二创片 |
| [`skills/fishing-spots-video`](skills/fishing-spots-video/SKILL.md) | 某地免费掉点 → 去重后按区各一条 OSM 地图卡合集 |
| [`skills/fishing-lesson-video`](skills/fishing-lesson-video/SKILL.md) | 用户给主题 → 图文卡 + 女声口播的钓鱼教学课（约 3 分钟） |

新增 skill：在 `skills/` 下新建目录，自带 `SKILL.md`、`scripts/`、`requirements.txt`，不要改别的 skill 里的文件。

## 安装

```bash
chmod +x install.sh
./install.sh cursor          # 全部 skill → ~/.cursor/skills/<name>
./install.sh cursor fishing-spots-video
./install.sh both
./install.sh uninstall
```

每个 skill 自己 `uv venv --python 3.11`。不要用系统 `python3`。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install ffmpeg yt-dlp    # 二创还需要 yt-dlp；掉点合集只需 ffmpeg
```

## 从仓库根做片

YouTube 二创：

```bash
bash skills/youtube-fishing-remake/scripts/start-chrome-cdp.sh
bash skills/youtube-fishing-remake/scripts/uv_run.sh \
  skills/youtube-fishing-remake/scripts/remake.py --all --url "https://www.youtube.com/shorts/xxxx"
```

掉点合集（给城市名会按区拆成多条；先写好 `output/<city>/all.json`）：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh \
  skills/fishing-spots-video/scripts/build_city.py \
  --spots output/<city>/all.json \
  --workdir output/<city>
```

教学课（每次给一个主题，先写 `output/<slug>/lesson.json`）：

```bash
bash skills/fishing-lesson-video/scripts/uv_run.sh \
  skills/fishing-lesson-video/scripts/build.py \
  --lesson output/<slug>/lesson.json \
  --workdir output/<slug>
```

成片都在当前工作区 `output/`。排错见 `skills/youtube-fishing-remake/usage.md`。教学课写法见 `md/fishing-lesson-video.md`。

## License

[Apache License 2.0](LICENSE)

Copyright 2026 zhaoyta
