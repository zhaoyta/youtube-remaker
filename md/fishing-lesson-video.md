# 钓鱼图文口播教学课

给「鱼公移山」做**竖版教学课**：图文卡 + 女声口播，每集约 3 分钟。课题每次现给，不写进 skill。

## 你怎么用

下一句直接丢主题，例如：

- 野钓鲫鱼到底用袖还是伊势尼
- 调四钓二到底在调什么
- 散炮和拉饵什么时候换

然后走 `fishing-lesson-video`：写 `output/<slug>/lesson.json` → 校验 → 成片。

## 成片命令（仓库根目录）

```bash
bash skills/fishing-lesson-video/scripts/uv_run.sh \
  skills/fishing-lesson-video/scripts/validate.py \
  --lesson output/<slug>/lesson.json

bash skills/fishing-lesson-video/scripts/uv_run.sh \
  skills/fishing-lesson-video/scripts/build.py \
  --lesson output/<slug>/lesson.json \
  --workdir output/<slug>
```

产出：`output/<slug>/final.mp4`、`caption.txt`。

## 画面从哪来

- **鱼 / 活饵**：Wikimedia 真照片。金鱼≠野鲫；红虫≠蚯蚓（红虫是摇蚊幼虫）；沙蚕是海钓饵。
- **钩**：按市面钩型几何画。3 号袖和 3 号伊势尼不是一样大。
- **线**：尼龙单丝、碳线单丝、PE 编织，按号数和线径对照。台钓子线不用 PE。
- **商品饵**：只画状态（拉饵有丝、搓饵实心、散炮干散），不画品牌袋。
- **漂 / 线组 / 坠**：按真实结构画，台钓顺序不能错。

## 课怎么写才像短视频

开头 5 秒反常识或避坑；中间对照 + 号数步骤；结尾问评论区。禁止空话和自我介绍。全文大约 650～780 字。
