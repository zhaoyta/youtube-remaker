---
name: fishing-spots-video
description: 搜集某地免费野钓掉点，写成带导航/优缺点/注意事项和经纬度的 JSON，再用 OpenStreetMap 底图 + 女声口播做成竖版抖音合集。在用户要做掉点视频、免费钓点、野钓地图、钓点合集，或提到 OSM 标注成片时使用。不要用于 YouTube 二创。
---

# 免费掉点合集成片

把「某地免费钓点」做成竖版口播片：总图 + 每个点一张 OSM 标注卡（导航 / 优点 / 缺点 / 注意）+ 女声。

**不要**走 YouTube 二创 skill，不要 CDP / Gemini / yt-dlp。不要往 `skills/youtube-fishing-remake/` 写代码。

**不要直接跑系统 `python` / `python3`。** 在**仓库根目录**执行：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/<脚本>.py ...
```

安装到 `~/.cursor/skills/fishing-spots-video` 后，把前缀换成该目录。

## 前置

```bash
bash skills/fishing-spots-video/scripts/setup_venv.sh
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/check_deps.py
```

必须有 `ffmpeg`（含 `ffprobe`），venv 里有 `edge-tts`、`pillow`。缺 ffmpeg：`brew install ffmpeg`。没有 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`

不需要 Chrome、yt-dlp、Playwright。

## 工作流

skill 根目录：`skills/fishing-spots-video/`。成片写到当前工作区 `output/<slug>/`。

```
Task Progress:
- [ ] check_deps.py 通过
- [ ] 搜集掉点（官方适宜垂钓 / 钓友常用），排除禁钓库区
- [ ] 写出 spots.json（含 lat/lon、导航、优缺点、注意、口播）
- [ ] build.py 出片
- [ ] 把 final.mp4、标题/简介/标签交给用户，不自动发布
```

### 1. 搜集

核对渔政通告：北京「禁渔」多半禁网具电鱼，钓具一般还让用；现场「禁止垂钓」优先。密云 / 怀柔 / 官厅等库区不要写进去。

每个点要有：可导航的地名、鱼种、优点、缺点、注意事项、约 20～40 字口播（约 3 字/秒）、WGS84 `lat`/`lon`。

坐标来源：Nominatim / 地标，标的是**河段附近**不是某个编号钓台。片子上必须保留「大致钓位」说明。国内高德导航可能偏 100～300 米（火星坐标）。禁止假装厘米级精准。

### 2. 写 JSON

保存到 `output/<slug>/spots.json`。完整对象，不要只丢数组：

```json
{
  "title": "北京 20 个免费掉点",
  "subtitle": "地图标注 · 优缺点 · 注意事项",
  "intro_script": "北京二十个免费掉点，位置优缺点注意事项，地图标好了，先收藏。",
  "outro_title": "别踩这些",
  "outro_lines": ["密云、怀柔、官厅库区", "现场写着禁止垂钓的岸", "电鱼、毒鱼、地笼、粘网"],
  "outro_script": "密云怀柔官厅库区别去。现场禁止垂钓就换点。电鱼网具违法，垃圾带走。",
  "overview_tips": ["手竿路亚休闲钓 · 有禁止垂钓牌就换点", "密云怀柔官厅库区别去 · 电鱼网具违法"],
  "douyin_title": "15～25字标题",
  "douyin_intro": "40～80字简介",
  "douyin_tags": ["#鱼公移山", "#北京钓鱼", "#免费钓点", "#野钓", "#温榆河"],
  "spots": [
    {
      "n": 1,
      "name": "南护城河",
      "area": "城区",
      "nav": "大观园桥→龙潭公园东门",
      "fish": "鲫、白条",
      "pro": "城区最近",
      "con": "人多、鱼小",
      "note": "只手竿，别下河",
      "script": "南护城河，大观园到龙潭。城区最近，人多鱼小，只手竿别下河。",
      "lat": 39.8748,
      "lon": 116.3940
    }
  ]
}
```

`area` 用于分色。参考 `examples/beijing.json`。口播宁短勿长。账号：抖音「鱼公移山」。

### 3. 成片

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/build.py \
  --spots output/<slug>/spots.json \
  --workdir output/<slug>
```

规则（不要改）：
- 底图：OpenStreetMap 瓦片（WGS84 墨卡托），总图 zoom 10，单点 zoom 14
- 针和底图对齐；坐标本身只到河段
- 女声固定 `zh-CN-XiaoxiaoNeural`
- 底部硬字幕：黑体、橙红字、浅粉描边；顶部叠 `assets/copyright.png`
- 原声没有，只有 TTS
- 出 `final.mp4`、`caption.txt`、`edit.json` 后停

底图要联网拉 OSM 瓦片，礼貌缓存到 `output/<slug>/tiles/`。

### 4. 验收

告诉用户成片路径、时长、抖音标题/简介/标签，并一句说明：地图是大致钓位，去现场看牌子、用高德搜导航词。

## 路径

| 路径 | 作用 |
|------|------|
| `scripts/setup_venv.sh` | uv 3.11 venv + requirements |
| `scripts/uv_run.sh` | 用该 venv 跑脚本 |
| `scripts/check_deps.py` | ffmpeg / edge-tts / pillow |
| `scripts/build.py` | OSM 卡片 + TTS + 合成 |
| `scripts/media.py` | 口播与字幕，勿从二创 skill 引用 |
| `examples/beijing.json` | 北京 20 点样例 |
| `assets/copyright.png` | 鱼公移山版权图 |
