# 钓鱼恶搞：画风 / JSON / 去重

## Style Bible（每张 GenerateImage 都要带）

统一标签（复制到每条 `description` 末尾）：

```
Style: vertical 9:16 Chinese internet meme comic (沙雕表情包风), thick black ink outlines,
flat color blocks, teal-green water and cream paper palette with one coral accent,
exaggerated silly dumpling faces, East Asian Chinese facial features only,
short messy black hair or sun hat over Chinese face, no Western/European face,
no blonde hair, no photorealism, no purple neon glow, no UI mockup, no watermark text,
no brand logos, no bloody hook-in-mouth gore.
```

### 形象硬规则（沙雕 + 国人）

- **人**：短黑发/黑框眼镜/防晒帽均可，但脸必须是**东亚国人五官**；表情沙雕（愣、坏笑、挤眼），像表情包不是精致插画男模
- **禁止**：欧美人脸、高鼻深目、金发、络腮胡牛仔风、迪士尼欧美卡通脸
- **鱼**：圆滚、呆萌或委屈大眼，像国内短视频贴纸鱼，不要写实海钓巨物宣传图
- **口播**：`pov:angler` 嘲鱼时必须**第二人称怼着鱼说**（你/你瞅/你这波），禁止旁白腔「中鱼了先别放」对观众汇报

### 三个 style 变体（写进 spoof.json `style`，连续两集勿重复）

| style | 画面 |
|-------|------|
| `comic-teal` | 岸边/半水上，青绿水面 + 米白天空，沙雕国人钓鱼佬清晰 |
| `fisheye-underwater` | 水下仰视略鱼眼，气泡与光斑，饵钩在前景，鱼脸怼镜头 |
| `paper-gag` | 贴纸拼贴感、表情包边框，仍是青绿/珊瑚配色 |

### 角色一致性

- **鱼开麦**：选定一种鱼（鲫/鲤/草/鲶），写清体色与表情习惯；跨页同一条鱼
- **钓鱼佬**：固定国人沙雕外观（防晒帽/绿背心/黑框眼镜其一），不要每页换人换种族
- 禁止把教学课那套「Wikimedia 真鱼」用在恶搞主视觉上（恶搞要漫画，不要假实证）

### 构图

- 主体占画面中上 60%，底部留字幕安全区（约 180px 空或暗一点）
- 每页只讲一个笑点动作；不要九宫格信息墙
- 图内最多 0～4 个汉字（拟声、短称呼）；整段口播不要烧进图

---

## 跨行业热点与合规

恶搞前先挖**外部热点**，再套**钓鱼场景**。更接近大众正在聊的东西，完播和评论会更好；但合规优先于蹭热度。

### 搜什么（每次轮换品类）

| 层 | 查询方向 | 要带走的 |
|----|----------|----------|
| 跨行业 | 热搜/热榜梗、职场、体育赛事、天气节气、开学毕业、数码汽车餐饮出圈话题 | 情绪词、口头禅、可比喻结构 |
| 垂类 | 鱼开麦、空军、戏耍钓鱼佬、打窝翻车、**淘汰回放嘲鱼** | 分镜节奏、反转类型 |

### 迁移公式

`外部热点情绪/句式` × `钓鱼物件` → 全新 hook  

例（示意，勿照抄当本题）：

- 职场 KPI → 空军天数 / 打窝投产比  
- 自助餐刺客 → 窝料免费吃钩别碰  
- 进度条焦虑 → 浮漂半天不动  
- 决赛夜熬夜 → 夜钓蚊子 BGM  
- **电竞淘汰回放 / 菜就多练** → 人拎鱼怼手机强制看「被调上来」的过程  

### 垂类高传播结构：淘汰回放嘲鱼

爆款结构（只借结构，不抄原片分镜/台词/账号）：

1. 人坐岸边，一手拎鱼、一手举手机**怼鱼脸**  
2. 手机里播「中鱼→出水」过程（漫画里画成小屏回放即可）  
3. 口播必须**对着鱼说**（你瞅这波/你贪不贪/菜就多练），像沙雕鞭尸，不是对观众报幕式旁白  
4. 结尾丢评论区问题（你会回「卡了」吗）

形象：沙雕国人钓鱼佬 + 呆萌漫画鱼；禁止欧美插画脸。  

合规注意：

- 用**漫画分镜**，不要伪造成某爆款账号的实拍搬运  
- 鱼表情夸张即可，**禁止**血腥穿嘴、虐鱼特写  
- 不出现可识别真人脸、不碰具体战队/主播名誉  
- `trend_source` 写「模仿淘汰回放嘲鱼结构」，不要写原作者昵称当标题引流  

- 季节天气、节气、开学放假、周末氛围  
- 泛职场情绪（加班、摸鱼、开会）——不点名公司  
- 体育/赛事**赛果气氛**（紧张、加时）——不侮辱运动员、不造谣  
- 短视频通用句式（「至于吗」「老实交代」）——不抄某条爆款全文  

### 不可蹭（直接换题）

- 灾难、刑案、舆情当事人、未结案新闻  
- 可识别的真人、明星脸、企业商标与包装  
- 政治立场、宗教民族对立、性别羞辱  
- 电鱼毒鱼、禁渔偷钓、保护区违法示范  
- 赌博、违禁品、色情、未成年人不当  
- 血腥虐鱼、假冒「本人真实爆护/官方认证」  

拿不准：当作不可蹭，退回纯钓鱼圈梗，`cross_trend` 填 `none`。

### spoof 字段

```json
"cross_trend": "泛职场摸鱼情绪，映射打窝自助餐",
"trend_source": "模仿鱼开麦看穿圈套结构，包装成草鱼董事会否决银钩"
```

`cross_trend` 为 `none` 时写一句原因，例如：`none：当日热搜偏舆情案件，未合规蹭`

---

## 搜垂类结构怎么用

目标是借**结构**，不是搬**台词**：

| 热门结构 | 你该改成 |
|----------|----------|
| 电竞淘汰回放嘲鱼 | 换鱼种 + 换「失误点评」理由（贪吃/探头/抢口） |
| 鱼视角吐槽饵料 | 换鱼种人设 + 换具体饵/场景 |
| 空军收竿名言 | 换翻车物件（鞋/水草/啤酒罐） |
| 戏耍钓鱼佬三连 | 换三连内容，保留节奏 |
| 社畜鱼开会 | 换会议主题（打窝/浮漂） |

`trend_source` 示例：`模仿「鱼开麦吐槽饵料」结构，钩子改为草莓味拉饵嫌夸张`

禁止：照抄某条爆款完整台词；连续两集同一 `angle_key` 前缀（如连续 `air-force-*` 要换 pov 或核心物件）。

---

## angle_key 与去重

`angle_key`：小写英文短横线，概括「谁 + 干了啥」，例如：

- `crucian-roast-strawberry-bait`
- `angler-hooks-old-shoe`
- `carp-boss-rejects-groundbait`

与 `history.json` → `used[].angle_key` **完全相同**则拒收。  
与已有条目的核心名词高度重合（同物件+同 pov）也应主动换题，即使 key 字符串不同。

---

## 恶搞配音（Voice Bible）

恶搞片**禁止**用教学课那套新闻暖女声。口播要像短剧吐槽：偏卡通、偏快、略抬调。

### 默认（build.py 未写字段时自动套）

| `pov` | `voice` 别名 | 实际 edge-tts | `rate` | `pitch` | 听感 |
|-------|--------------|---------------|--------|---------|------|
| `fish` | `yunxia` | `zh-CN-YunxiaNeural` | `+22%` | `+12Hz` | 卡通男，鱼开麦 |
| `angler` | `xiaobei` | `zh-CN-liaoning-XiaobeiNeural` | `+22%` | `+6Hz` | 辽宁幽默，翻车吐槽 |

### 允许别名

| 别名 | 音色 | 何时用 |
|------|------|--------|
| `yunxia` | 卡通男 | 鱼开麦默认 |
| `xiaoyi` | 卡通女活泼 | 想换女鱼人设时 |
| `xiaobei` | 辽宁幽默女 | 钓鱼佬翻车默认 |
| `yunjian` | 激情男 | 夸张播报感翻车 |

### 禁止

- **`zh-CN-XiaoxiaoNeural` / `xiaoxiao`**：教学课默认声，恶搞听着太普通
- `rate` ≤ `+0%` 且 `pitch` ≤ `+0Hz` 的「平读」组合（除非用户明确要求）

### spoof.json 建议显式写出

```json
"voice": "yunxia",
"rate": "+22%",
"pitch": "+12Hz"
```

换音色重渲同一集：`build.py --force-tts --no-history`。

### 沙雕字幕（成片默认）

- 亮黄粗字 `#FFE14A` + 粗黑描边 + 轻微弹入动画  
- 字号约 76，短句换行（约 8 字），不要教学课小粉字安静贴底  

---

## spoof.json

```json
{
  "slug": "crucian-roast-strawberry-bait",
  "angle_key": "crucian-roast-strawberry-bait",
  "pov": "fish",
  "style": "fisheye-underwater",
  "voice": "yunxia",
  "rate": "+22%",
  "pitch": "+12Hz",
  "cross_trend": "泛职场摸鱼/开会情绪，映射水下董事会",
  "trend_source": "模仿鱼开麦吐槽饵料结构，钩子改为草莓味拉饵",
  "title": "草莓味？至于吗",
  "hook_one_liner": "水下第一条鱼开麦：这饵香得假",
  "douyin_title": "鱼开麦了 草莓味饵至于这么夸张吗",
  "douyin_intro": "恶搞短片，非真实鱼获。钓友评论区说说你被哪种饵戏耍过。",
  "douyin_tags": ["#鱼公移山", "#钓鱼恶搞", "#鱼视角", "#空军", "#野钓"],
  "cast": {
    "fish": "圆滚鲫鱼，浅金体色，眉毛似的眼上纹，爱翻白眼",
    "angler": "戴宽边防晒帽的瘦高男，绿背心"
  },
  "panels": [
    {
      "file": "panels/01.png",
      "script": "喂，上面那位，草莓味粉团甩下来的时候，",
      "image_prompt": "……完整英文画面描述 + Style Bible 短标签"
    }
  ]
}
```

### 字段约束

| 字段 | 规则 |
|------|------|
| `pov` | 仅 `fish` 或 `angler` |
| `style` | 仅三个变体之一 |
| `cross_trend` | 必填。蹭的外部热点一句话，或 `none：原因` |
| `trend_source` | 必填。垂类结构 + 怎么改包装 |
| `voice` / `rate` / `pitch` | 建议显式写。默认见「恶搞配音」；禁止 `xiaoxiao` |
| `panels` | 3～6；每个有 `file`、`script`、`image_prompt` |
| 全文 `script` 拼接 | 80～180 字（校验按去空白计） |
| `douyin_title` | ≤ 30 字，前 12 字有钩子 |
| `douyin_tags` | 5～8 个，必须含 `#鱼公移山` `#钓鱼恶搞` |

### 口播结构（20～45 秒）

1. **钩子**（1 句）：点名冲突（饵太香 / 自称必爆护）
2. **过程**（2～4 句）：一个完整小翻车或吐槽
3. **收束**（1 句）：扎心金句或评论区提问

禁止教学说教结尾（「所以调漂要注意」）。

---

## history.json 追加格式

```json
{
  "slug": "crucian-roast-strawberry-bait",
  "angle_key": "crucian-roast-strawberry-bait",
  "pov": "fish",
  "style": "fisheye-underwater",
  "hook_one_liner": "水下第一条鱼开麦：这饵香得假",
  "trend_source": "模仿鱼开麦吐槽饵料结构，钩子改为草莓味拉饵",
  "cross_trend": "泛职场摸鱼/开会情绪，映射水下董事会",
  "created": "2026-08-21"
}
```
