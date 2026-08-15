---
name: fishing-spots-video
description: 搜集某地免费野钓掉点，按距离去重后按区拆成多条竖版抖音合集（OSM 地图卡 + 女声口播）。在用户给城市名、要做掉点视频、免费钓点、野钓地图、钓点合集时使用。
---

# 免费掉点合集成片

用户给**一个城市**（如「搜广州免费钓点做视频」）：尽量搜全，**不要人为截成 20 个**。去重后按 `area` 拆片，**每个区一条视频**；某区不足 4 个点则并进地理上最近的区。

只改本目录里的脚本。不要 CDP / Gemini / yt-dlp。

**不要直接跑系统 `python` / `python3`。** 在**仓库根目录**执行：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/<脚本>.py ...
```

## 前置

```bash
bash skills/fishing-spots-video/scripts/setup_venv.sh
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/check_deps.py
```

必须有 `ffmpeg`（含 `ffprobe`），venv 里有 `edge-tts`、`pillow`。缺 ffmpeg：`brew install ffmpeg`。

## 工作流（给城市名时默认走这条）

```
Task Progress:
- [ ] check_deps.py 通过
- [ ] 按区搜全（官方适宜垂钓 / 钓友常用），排除禁钓库区
- [ ] 写出 output/<city>/all.json（city + 全量 spots）
- [ ] build_city.py 去重、按区拆片、逐区成片
- [ ] 把各区 final.mp4 和文案交给用户，不自动发布
```

用户明确说「只要一条合集」时，才直接 `build.py` 出一条，不拆区。

### 1. 搜集

核对渔政通告：北京「禁渔」、珠江春季禁渔，多半禁网具电鱼，钓具一般还让用；现场「禁止垂钓」优先。水源地库区不要写进去。

每个点：可导航地名、鱼种、优点、缺点、注意事项、约 20～40 字口播（约 3 字/秒）、WGS84 `lat`/`lon`、`area`（区名，如 番禺 / 南沙 / 增城）。

坐标是**河段附近**不是编号钓台。片子上保留「大致钓位」。高德可能偏 100～300 米。禁止假装厘米级精准。

### 2. 写全城 JSON

保存 `output/<city>/all.json`，必须有 `"city"`。`area` 用来拆片和分色。样例结构见 `examples/beijing.json`，并加上 `"city": "广州"`。

口播宁短勿长。账号：抖音「鱼公移山」。

### 3. 去重 + 按区成片

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/build_city.py \
  --spots output/<city>/all.json \
  --workdir output/<city>
```

默认：500 米内视为同一点（留信息更全的那条）；某区少于 4 个点并进最近的区。可改 `--dedupe-m`、`--min-spots`。

产出：
- `output/<city>/manifest.json` 去重说明和各区路径
- `output/<city>/<区>/spots.json` + `final.mp4` + `caption.txt`

成片规则（不要改）：OSM 瓦片 zoom 10/14；女声 `zh-CN-XiaoxiaoNeural`；橙红硬字幕；顶部 `assets/copyright.png`；只要 TTS。瓦片缓存到各区 `tiles/`。

只拆 JSON 不成片：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/split_spots.py \
  --spots output/<city>/all.json --workdir output/<city>
```

### 4. 验收

列出**每一区**的成片路径、点数、时长、标题/简介/标签。说明：地图是大致钓位；并入邻区的小区要提一句。不发抖音。

## 路径

| 路径 | 作用 |
|------|------|
| `scripts/build_city.py` | 去重 + 按区拆 + 逐区调用 build.py |
| `scripts/split_spots.py` | 只去重拆 JSON |
| `scripts/build.py` | 单份 JSON 成片 |
| `scripts/media.py` | 口播与字幕 |
| `examples/beijing.json` | 样例 |
| `assets/copyright.png` | 鱼公移山版权图 |
