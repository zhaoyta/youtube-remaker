# 仓库 skill 目录

每个 skill 独占 `skills/<name>/`，安装后对应 `~/.cursor/skills/<name>`。不要把 A 的脚本 import B。

| 目录 | 触发 | 成片 |
|------|------|------|
| `skills/youtube-fishing-remake` | YouTube 链接、钓鱼二创、Gemini CDP | `output/<youtube_id>/final.mp4` |
| `skills/fishing-spots-video` | 免费掉点、野钓地图、钓点合集 | `output/<slug>/final.mp4` |

新增：复制一个现有目录当骨架，改 `SKILL.md` 的 `name` / `description` 和 `requirements.txt`，再 `./install.sh cursor <name>`。

样例数据：`skills/fishing-spots-video/examples/beijing.json`  
北京 20 点成片：`output/beijing-20-spots/final.mp4`
