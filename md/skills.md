# 仓库 skill 目录

每个 skill 独占 `skills/<name>/`，安装后对应 `~/.cursor/skills/<name>`。不要把 A 的脚本 import B。

| 目录 | 触发 | 成片 |
|------|------|------|
| `skills/youtube-fishing-remake` | YouTube 链接、钓鱼二创、Gemini CDP | `output/<youtube_id>/final.mp4` |
| `skills/fishing-spots-video` | 城市免费掉点（去重后按区各一条） | `output/<city>/<区>/final.mp4` |
| `skills/fishing-lesson-video` | 钓鱼教学课、图文口播教程（主题每次现给） | `output/<slug>/final.mp4` |

新增：复制一个现有目录当骨架，改 `SKILL.md` 的 `name` / `description` 和 `requirements.txt`，再 `./install.sh cursor <name>`。

样例数据：`skills/fishing-spots-video/examples/beijing.json`  
给城市名：写 `output/<city>/all.json`，再跑 `build_city.py`（500 米去重，不足 4 点的区并进邻区）。  
只要一条合集才直接 `build.py`。  
教学课：用户给主题后写 `output/<slug>/lesson.json`，再跑 `fishing-lesson-video` 的 `build.py`。课题不要写进 skill。
