---
name: fishing-lesson-video
description: 按用户给的主题做钓鱼教学竖版片（图文卡 + 女声口播，约 3 分钟）。钩型按真实几何绘制，鱼线按号数/线径对照，活饵用 Wikimedia 真图，商品饵按真实状态画。在用户要做钓鱼教学课、图文口播教程、调漂/钩型/鱼线/饵料/线组讲解时使用。课题每次由用户提供，不要写死在 skill 里。
---

# 钓鱼教学课成片

用户每次给**一个主题**。写成约 3 分钟竖版图文口播课，账号「鱼公移山」。

只改本目录里的脚本。不要 CDP / Gemini / yt-dlp。
**不要**把课题写进本 skill；样例只抄字段。
**不要直接跑系统 `python` / `python3`。** 在**仓库根目录**执行：

```bash
bash skills/fishing-lesson-video/scripts/uv_run.sh skills/fishing-lesson-video/scripts/<脚本>.py ...
```

## 前置

```bash
bash skills/fishing-lesson-video/scripts/setup_venv.sh
bash skills/fishing-lesson-video/scripts/uv_run.sh skills/fishing-lesson-video/scripts/check_deps.py
```

必须有 `ffmpeg`（含 `ffprobe`），venv 里有 `edge-tts`、`pillow`。缺 ffmpeg：`brew install ffmpeg`。

## 工作流（给主题时走这条）

```
Task Progress:
- [ ] check_deps.py 通过
- [ ] 按主题写 output/<slug>/lesson.json（6～10 页，全文 650～780 字）
- [ ] validate.py 通过
- [ ] build.py 成片
- [ ] 把 final.mp4、时长、标题/简介/标签交给用户，不自动发布
```

没有主题就停，问用户要这一集讲什么。不要自己定系列大纲当成本期内容。

### 1. 写教案 JSON

保存 `output/<slug>/lesson.json`。`slug` 用英文短横线（如 `iseama-vs-sode`）。

结构见 [reference.md](reference.md)。硬规则：

- 第一页 `layout: title` 冷开场：先钩子（点名听众 + 避坑威胁 + 反常识），再进干货；禁止第一句就进店里/百科
- 中间必须有对照（`compare`）和可执行步骤（`steps` 或带号数的 `hero`）
- 口播按约 4 字/秒，全文 650～780 字 → 约 3 分钟；每页 35～85 字
- 口语，像跟钓友当面说，有画面、有脾气。禁止：大家好、家人们、能派上大用场、结构独特、直接拉满、太绝了、首先其次、说明书腔
- 钩、鱼、线、饵、装备必须能在 `catalog/` 对上。没有的鱼/活饵：先查学名，把 Wikimedia 文件名补进目录，再写 JSON
- 禁止 AI 生成鱼/钩图（防认错钩型、假鱼种）。装备优先 Wikimedia 真图；没有真图再用结构绘制。禁止画假品牌包装袋。

`visuals.kind`：

| kind | 怎么写 | 画面 |
|------|--------|------|
| `fish` | `"name": "鲫鱼"` | Wikimedia 真鱼 |
| `hook` | `"model": "iseama"`，可加 `"size": 3` 或 `"sizes": [2,3,4]` | 按真实钩型/号数画 |
| `line` | `"model": "nylon"`, `"size": "0.8"` | 尼龙/碳线/PE 线体+号数 |
| `bait` | `"name": "拉饵"` 或 `"红虫"` | 状态图或活饵真图 |
| `gear` / `rig` | `"model": "float_olive"` / `"taiwan"` | 按真实结构画 |
| `wikimedia` | `"file": "Cyprinus carpio.jpeg"` | 指定真图 |

钩型 key：`iseama` 伊势尼、`sode` 袖、`haixi` 海夕、`shinkanto` 新关东、`chinu` 千又、`izu` 伊豆、`maruseigo` 丸世。  
线：`nylon` 尼龙、`fluoro` 碳线、`pe` PE。饵：蚯蚓/红虫/玉米/麦粒/螺蛳用真图；拉饵/搓饵/散炮/蘸饵按状态画。

### 2. 校验 + 成片

```bash
bash skills/fishing-lesson-video/scripts/uv_run.sh \
  skills/fishing-lesson-video/scripts/validate.py \
  --lesson output/<slug>/lesson.json

bash skills/fishing-lesson-video/scripts/uv_run.sh \
  skills/fishing-lesson-video/scripts/build.py \
  --lesson output/<slug>/lesson.json \
  --workdir output/<slug>
```

规则（不要改）：竖版 1080×1920；女声 `zh-CN-XiaoxiaoNeural`；硬字幕按标点**分段轮播**（ASS，粉色粗体加大字，每次一两行，不要整段口播一坨贴底）；默认混入 `assets/bgm/default.mp3`（音量约 0.12，不盖口播；`--no-bgm` / `--bgm` 可关或换曲）；右上角 `assets/copyright.png`；只要 TTS。卡片不要写「钓鱼课」「图文口播」。图文分区：上图下文，标题不要压在主图上。结尾 `outro` 要配有趣相关图（喜获、翻车现场等），不要黑屏空场。鱼图缓存到该集 `images/`。

成片后若时长不在 2.5～3.5 分钟，改口播字数再编，不要靠拉长静帧。

### 3. 验收

给用户：`final.mp4` 路径、时长、`douyin_title` / `douyin_intro` / `douyin_tags`。说明鱼/活饵来自 Wikimedia，钩型、线径、商品饵状态是按实物结构绘制。不发抖音。

## 短视频课怎么写

详情见 [reference.md](reference.md)。每集只做一个决定（用哪只钩、调几目、饵多湿）。开头 5 秒先钩子再干货，结尾留一个能回的问题。

## 路径

| 路径 | 作用 |
|------|------|
| `scripts/build.py` | lesson.json → 成片 |
| `scripts/validate.py` | 校验字数和真图目录 |
| `catalog/fish.json` | 鱼种学名和 Wikimedia 文件 |
| `catalog/hooks.json` | 钩型几何和号数比例 |
| `catalog/lines.json` | 尼龙/碳线/PE 号数与线径 |
| `catalog/baits.json` | 活饵真图 + 商品饵状态 |
| `catalog/gear.json` | 漂、坠、线组、爆炸钩 |
| `assets/copyright.png` | 鱼公移山版权图 |
| `assets/bgm/` | 轻底 BGM（默认 `default.mp3`） |
