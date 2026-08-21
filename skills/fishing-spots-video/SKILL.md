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
- [ ] 写出 output/<city>/all.json（city + 全量 spots + 带地方文化的抖音文案）
- [ ] build_city.py 去重、按区拆片、逐区成片（或用户只要合集时 build.py）
- [ ] 把成片路径 + 标题/简介/标签交给用户，不自动发布
```

用户明确说「只要一条合集」时，才直接 `build.py` 出一条，不拆区。

### 1. 搜集

核对渔政通告：北京「禁渔」、珠江春季禁渔，多半禁网具电鱼，钓具一般还让用；现场「禁止垂钓」优先。水源地库区不要写进去。

每个点：可导航地名、鱼种、优点、缺点、注意事项、约 20～40 字口播（约 3 字/秒）、WGS84 `lat`/`lon`、`area`（区名，如 番禺 / 南沙 / 增城）。

坐标是**河段附近**不是编号钓台。片子上保留「大致钓位」。高德可能偏 100～300 米。禁止假装厘米级精准。

### 2. 写全城 JSON

保存 `output/<city>/all.json`，必须有 `"city"`。`area` 用来拆片和分色。样例结构见 `examples/beijing.json`，并加上 `"city": "广州"`。

口播宁短勿长。账号：抖音「鱼公移山」。

**写 JSON 时必须同时写好抖音文案字段**（见下一节），不要用干巴巴的「N个免费掉点 地图标清」交差。

### 3. 抖音标题 / 简介 / 标签（必须带地方文化）

成片前后都要交付可直接粘贴的抖音文案。写入 `all.json` 的 `douyin_title`、`douyin_intro`、`douyin_tags`，并建议加 `culture_hook`（一句本地口头禅/地标氛围，供拆区片复用）。

#### 硬性要求

- **标题** ≤ 30 字左右，前 12 字要能抓住本地人；城市名 + 免费掉点/野钓 + **1 个本地文化钩子**。
- **简介** 80～150 字：先一句地方氛围，再列主要水系/片区，再写「导航·优缺点·注意事项」，最后安全/合规（水源库区、禁钓牌、电鱼网具、垃圾带走）。口吻像当地钓友唠嗑，不要公文腔。
- **标签** 5～8 个：`#鱼公移山` + `#<城>钓鱼` + `#免费钓点` + `#野钓` + **至少 2 个本地标签**（河名/别称/区名/习俗）。
- **禁止**：纯堆点数无文化；假方言硬拗到看不懂；夸大「官方认证」「必爆护」；引导进水源地/禁钓区。

#### 怎么找「地方文化钩子」

每个城至少用 1～2 类（优先和**水/河边生活**沾边）：

| 类型 | 例子 |
|------|------|
| 城市别称/气质 | 哏都、魔都、羊城、山城、泉城 |
| 母亲河/著名水系 | 海河、珠江、黄浦江、松花江、钱塘江 |
| 本地口头禅/语气 | 天津「嘛呢/卫嘴子」、东北「整」、粤语适度点到为止 |
| 地标与片区气质 | 五大道、外滩、珠江夜游、外环河、郊野减河 |
| 饮食/市井（点到为止） | 煎饼果子、早茶——用来拉近，别写成美食探店 |

#### 城市文案示例（写 `all.json` 时对齐这个味道）

**天津（合集）**

- 标题：`哏都钓鱼人看过来 天津海河69个免费掉点`
- 简介：`海河边儿唠两句：卫嘴子钓友常出没的海河两岸、外环河、永定新河、独流减河，一直标到滨海蓟州。69个免费掉点，导航优缺点注意事项地图一次说清。于桥尔王庄水源库区别去，现场有禁止垂钓牌就换点，电鱼网具违法，钓完垃圾带走——咱天津人讲究个利索。`
- 标签：`#鱼公移山 #天津钓鱼 #哏都 #海河 #免费钓点 #野钓 #卫嘴子`
- culture_hook：`海河边儿唠两句`

**北京（合集）**

- 标题：`帝都野钓地图 护城河温榆河免费掉点标清`
- 简介：`京爷河边扎堆那味儿你懂：护城河、清河、温榆河、潮白河再到房山大兴。免费掉点带导航优缺点注意事项。密云怀柔官厅库区别去，现场看牌子，电鱼网具违法，垃圾带走。`
- 标签：`#鱼公移山 #北京钓鱼 #帝都 #温榆河 #免费钓点 #野钓`

**广州（合集）**

- 标题：`羊城钓友收藏 珠江番禺南沙免费掉点`
- 简介：`珠江水暖钓友忙：城区河道到番禺南沙增城，免费掉点地图标清，优缺点注意事项都有。春季禁渔听渔政，现场禁钓牌优先，电鱼网具违法，垃圾带走。`
- 标签：`#鱼公移山 #广州钓鱼 #羊城 #珠江 #免费钓点 #野钓`

#### 拆区片文案

`split_spots.py` 生成各区 `douyin_title` / `douyin_intro` 时：

- 标题：`{城}{区}免费掉点` + **本区标志河段名**（从点名里抽），不要只写「N个标清」，也不要全区标题都复用同一句全市钩子。
- 简介：以全市 `culture_hook` 开场，再写「{区}这边：点名…」，结尾「看牌子、垃圾带走」。
- 标签：继承全城标签，追加 `#{区}`，总数 ≤ 8。

合集片（`build.py` 直接吃 `all.json`）**原样使用** JSON 里写好的 `douyin_*`，成片后的 `caption.txt` 必须与此一致。

交付用户时：全市合集给 1 套文案；拆区则**每一区**各给标题/简介/标签。

### 4. 去重 + 按区成片

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/build_city.py \
  --spots output/<city>/all.json \
  --workdir output/<city>
```

默认：500 米内视为同一点（留信息更全的那条）；某区少于 4 个点并进最近的区。可改 `--dedupe-m`、`--min-spots`。

产出：
- `output/<city>/manifest.json` 去重说明和各区路径
- `output/<city>/<区>/spots.json` + `final.mp4` + `caption.txt`

成片规则（不要改）：OSM 瓦片 zoom 10/14；女声 `zh-CN-XiaoxiaoNeural`；橙红硬字幕在**底部**、按标点**一句一屏随音频切换**；版权图 **右上角** `assets/copyright.png`；只要 TTS。瓦片缓存到各区 `tiles/`。

只拆 JSON 不成片：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/split_spots.py \
  --spots output/<city>/all.json --workdir output/<city>
```

用户只要合集时：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/build.py \
  --spots output/<city>/all.json \
  --workdir output/<city>/合集
```

仅重渲字幕（复用卡片/口播）：

```bash
bash skills/fishing-spots-video/scripts/uv_run.sh skills/fishing-spots-video/scripts/rerender_subs.py \
  --workdir output/<city>/合集
```

### 5. 验收

列出成片路径、点数、时长、**带地方文化的标题/简介/标签**。说明：地图是大致钓位；并入邻区的小区要提一句。不发抖音。

## 路径

| 路径 | 作用 |
|------|------|
| `scripts/build_city.py` | 去重 + 按区拆 + 逐区调用 build.py |
| `scripts/split_spots.py` | 只去重拆 JSON（区片文案带 culture_hook） |
| `scripts/build.py` | 单份 JSON 成片 |
| `scripts/rerender_subs.py` | 复用素材只重渲字幕并拼接 |
| `scripts/media.py` | 口播与字幕 |
| `examples/beijing.json` | 样例（含抖音文案） |
| `assets/copyright.png` | 鱼公移山版权图 |
