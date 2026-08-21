---
name: fishing-parody-video
description: >-
  做钓鱼恶搞竖版短片（漫画分镜图文 + 恶搞口播，约 20～45 秒）：鱼视角吐槽、空军翻车、戏耍钓鱼佬等。
  每次先搜跨行业社会热点与钓鱼圈爆款结构，能合规蹭热点则优先；对照 history.json 去重。
  用户说恶搞、戏耍钓鱼佬、鱼开麦、空军段子、钓鱼搞笑图文视频时使用。
  配音禁止用教学课新闻腔晓晓，须用卡通/幽默音色并加速抬调。须合规，规避法律与平台风险。
---

# 钓鱼恶搞成片

用户说「恶搞一条」「做个鱼开麦」「空军搞笑图文」时走本 skill。账号「鱼公移山」，系列感用标签 `#钓鱼恶搞`。

只改本目录脚本与 `history.json`。不要 CDP / Gemini / yt-dlp。  
**不要直接跑系统 `python` / `python3`。** 在**仓库根目录**执行：

```bash
bash skills/fishing-parody-video/scripts/uv_run.sh skills/fishing-parody-video/scripts/<脚本>.py ...
```

## 前置

```bash
bash skills/fishing-parody-video/scripts/setup_venv.sh
bash skills/fishing-parody-video/scripts/uv_run.sh skills/fishing-parody-video/scripts/check_deps.py
```

必须有 `ffmpeg`（含 `ffprobe`），venv 里有 `edge-tts`、`pillow`。

## 工作流（每次都走完）

```
Task Progress:
- [ ] 读 history.json，列出已用 angle_key / 钩子
- [ ] WebSearch：**跨行业热点**（至少 2 条）+ **钓鱼恶搞结构**（至少 2 条）
- [ ] 合规筛选：能蹭的热点留下，踩红线的丢掉（见 §1 / reference 合规）
- [ ] 选定「热点梗或情绪 × 钓鱼场景 + 全新钩子」，确认不与 history 重复
- [ ] 写 skills/fishing-parody-video/output/<slug>/spoof.json（含 trend_source、cross_trend、angle_key、style、voice/rate/pitch）
- [ ] 按 style bible 用 GenerateImage 生成每页竖版分镜 → 同目录 panels/
- [ ] validate.py 通过
- [ ] build.py 成片
- [ ] 把本条写入 history.json
- [ ] 交付 final.mp4 + 抖音文案；不自动发布
```

用户没说具体桥段时：**不要问一堆选择题**，先挖热点再开干。用户指定桥段时，仍要搜一轮热点与同质化风险，能轻蹭则蹭，不能则换包装。

### 1. 搜热点（强制：跨行业 + 垂类）

每次开干前用 WebSearch，**两层都要搜**：

**A. 跨行业 / 社会热点**（至少 2 条查询，贴近当天日期），例如：

- `今日热搜` / `抖音热榜 梗` / `短视频 热门挑战`
- `职场 热梗` / `体育 出圈` / `天气 开学 节气` / `数码 汽车 餐饮 出圈话题`（轮换品类，别每次只搜同一行）

目标：找**可迁移的情绪或句式**（加班、摸鱼、自习、涨价、决赛夜、回南天…），不是搬运新闻案情。

**B. 钓鱼垂类恶搞结构**（至少 2 条）：

- `抖音 钓鱼恶搞 爆款` / `鱼视角 吐槽 钓鱼佬`
- `空军 段子 短视频` / `戏耍钓鱼佬 AI` / `钓鱼 淘汰回放 菜就多练`

#### 怎么蹭才算「更接近热点」

优先选能同时满足的：

1. 热点里有大众已懂的情绪/口头禅  
2. 能自然落在钓鱼场景（打窝=自助餐、空军=KPI、浮漂=进度条…）  
3. **合规通过**（见下）

写进 `spoof.json`：

- `cross_trend`：蹭的是哪类外部热点（一句话，勿写未结案新闻标题）  
- `trend_source`：用的垂类结构 + 怎么改包装  

蹭不上合规热点时：仍可做纯钓鱼圈梗，但 `cross_trend` 写 `none` 并说明原因。

#### 合规红线（违反任一条就换题，不要擦边）

| 禁止 | 说明 |
|------|------|
| 真实案件 / 灾难 / 伤亡 | 不拿事故、刑案、灾难梗做笑点 |
| 影射真人真企业真官员 | 不点名网暴对象、不模仿可识别公众人物脸与商标 |
| 政治、宗教、民族、性别仇恨 | 不碰 |
| 违法捕捞示范 | 不鼓吹电鱼、毒鱼、禁渔期偷钓、保护区下杆 |
| 虚假广告 / 假测评 | 不挂「官方认证必爆护」、不演假品牌实测 |
| 血腥虐鱼、虐待动物 | 不上钩穿嘴特写、不虐鱼画面 |
| 抄袭可定位作品 | 只借结构，不抄台词、不盗用原片分镜文案 |
| 未成年人不当内容 | 不涉及 |
| 赌博、违禁品 | 不碰 |

详情与「可蹭 / 不可蹭」对照见 [reference.md](reference.md)「跨行业热点与合规」。

去重：`angle_key` 与 `history.json` 冲突则换题。
### 2. 写 spoof.json

保存 `skills/fishing-parody-video/output/<slug>/spoof.json`。`slug` 英文短横线，如 `fish-eye-strawberry-bait`。

字段与口播规则见 [reference.md](reference.md)。硬规则：

- 时长目标 **20～45 秒**（全文约 80～180 字，约 4 字/秒）
- **3～6 页**分镜；第 1 页 2 秒内必须有钩子
- 视角二选一写进 `pov`：`fish`（鱼开麦）或 `angler`（钓鱼佬翻车）；同一集不要混人设
- 口语、有脾气；`pov:angler` 嘲鱼时**对着鱼第二人称说**（你/你瞅），禁止对观众旁白汇报
- 画面：**沙雕表情包风 + 东亚国人五官**；禁止欧美人脸/金发/精致男模脸（见 reference Style Bible）
- 禁止血腥上钩特写、禁止假品牌包装、禁止伪装「本人真实爆护战报」
- 片尾可留一句评论区问题（空军天数、最惨挂底等）
- **配音必须恶搞腔**（见下一节），禁止照搬教学课 `XiaoxiaoNeural`

### 3. 恶搞配音（硬规则，不要改默认）

口播要像吐槽短剧，不要像念新闻或钓鱼课。成片走 `edge-tts`，参数写进 `spoof.json`（可省略则用下表默认）。

| `pov` | 默认 `voice` | 音色 | 默认 `rate` | 默认 `pitch` |
|-------|--------------|------|-------------|--------------|
| `fish`（鱼开麦） | `yunxia` → `zh-CN-YunxiaNeural` | 卡通男声 | `+22%` | `+12Hz` |
| `angler`（钓鱼佬翻车） | `xiaobei` → `zh-CN-liaoning-XiaobeiNeural` | 辽宁幽默女声 | `+22%` | `+6Hz` |

允许别名：`yunxia` / `xiaoyi`（卡通女） / `xiaobei` / `yunjian`（激情男）。  
**禁止**默认使用 `zh-CN-XiaoxiaoNeural`（教学课新闻暖女声，恶搞听着太普通）。  
换音色或调速后重渲同一集：`--force-tts --no-history`。

写 `spoof.json` 时建议显式带上三字段，避免以后默认被改掉还以为没变：

```json
"voice": "yunxia",
"rate": "+22%",
"pitch": "+12Hz"
```

详情与更多音色说明见 [reference.md](reference.md)「恶搞配音」。

### 4. 画风（强制统一）

生成每页图前先读 [reference.md](reference.md) 的 **Style Bible**。  
用 Cursor `GenerateImage`，`aspect_ratio: "9:16"`，文件落到 `skills/fishing-parody-video/output/<slug>/panels/01.png` …

**必须遵守：**

- 固定漫画吐槽风：**沙雕表情包感**、粗墨线、扁平色块；**禁止**写实摄影、紫霓虹 AI 风、**欧美插画脸**
- 调色锁定：水色青绿 + 纸色米白 + 一点珊瑚红强调；人物/鱼有清晰剪影
- 人设必须是**东亚国人五官**（短黑发/黑框眼镜/防晒帽均可），表情沙雕；鱼要圆滚呆萌
- `pov: fish` 时用水下广角/轻微鱼眼，钩与饵在前景
- 同系列角色外观跨页一致（同一种鱼、同一顶帽子钓鱼佬）
- `pov:angler` 嘲鱼口播必须怼着鱼说，不要旁白腔
- 画面干净：少字或无字；文案靠口播和字幕，不要把整段台词烤进图里
- 每张图的 `description` 末尾复读 Style Bible 短标签（见 reference）

`spoof.json` 的 `style` 字段填本次选用的变体名（`comic-teal` / `fisheye-underwater` / `paper-gag`），且**连续两集不要同变体**（对照 history）。

### 5. 校验 + 成片

```bash
bash skills/fishing-parody-video/scripts/uv_run.sh \
  skills/fishing-parody-video/scripts/validate.py \
  --spoof skills/fishing-parody-video/output/<slug>/spoof.json

bash skills/fishing-parody-video/scripts/uv_run.sh \
  skills/fishing-parody-video/scripts/build.py \
  --spoof skills/fishing-parody-video/output/<slug>/spoof.json \
  --workdir skills/fishing-parody-video/output/<slug>
```

成片规则（不要改）：竖版 1080×1920；口播按 **§3 恶搞配音**；硬字幕要**沙雕活泼**：亮黄粗字 + 粗黑描边 + 短句弹入（ASS），禁止教学课那种小粉字安静贴底；默认混 `assets/bgm/default.mp3`（约 0.12）；右上角 `assets/copyright.png`；只要 TTS。分镜图来自 `panels/`，build 只做轻微暗角与底部安全区，不重绘主体。

换音色重渲：

```bash
bash skills/fishing-parody-video/scripts/uv_run.sh \
  skills/fishing-parody-video/scripts/build.py \
  --spoof skills/fishing-parody-video/output/<slug>/spoof.json \
  --workdir skills/fishing-parody-video/output/<slug> \
  --force-tts --no-history
```

### 6. 写入 history + 验收

成片成功后，把本条追加进 `history.json` 的 `used`（字段：`slug`、`angle_key`、`pov`、`style`、`hook_one_liner`、`trend_source`、`cross_trend`、`created`）。

交付用户：`final.mp4` 路径、时长、文案、`angle_key`、本集蹭了哪类热点（或为何未蹭）。说明恶搞创作、非真实鱼获。不发抖音。

## 路径

| 路径 | 作用 |
|------|------|
| `scripts/build.py` | spoof.json + panels → 成片 |
| `scripts/validate.py` | 字数、分镜、history 去重 |
| `history.json` | 已用角度，防重复 |
| `reference.md` | 画风 + 跨行业热点合规 + JSON + 配音 |
| `examples/sample.json` | 字段样例 |
| `assets/copyright.png` | 版权角标 |
| `assets/bgm/default.mp3` | 轻底 BGM |
