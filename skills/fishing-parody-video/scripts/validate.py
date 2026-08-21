#!/usr/bin/env python3
"""校验 spoof.json：字数、分镜、history 去重。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "history.json"
ALLOWED_POV = {"fish", "angler"}
ALLOWED_STYLE = {"comic-teal", "fisheye-underwater", "paper-gag"}
BANNED = ("大家好", "家人们", "干货满满", "首先", "其次", "再次")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def script_len(plan: dict) -> int:
    parts = [str(p.get("script") or "") for p in plan.get("panels") or []]
    return len("".join("".join(s.split()) for s in parts))


def load_history() -> dict:
    if not HISTORY.exists():
        return {"used": []}
    return load_json(HISTORY)


def check(plan: dict, *, spoof_path: Path | None = None, rebuild: bool = False) -> list[str]:
    errs: list[str] = []
    for key in (
        "slug",
        "angle_key",
        "pov",
        "style",
        "trend_source",
        "cross_trend",
        "title",
        "hook_one_liner",
        "douyin_title",
        "douyin_intro",
        "douyin_tags",
        "panels",
    ):
        if not plan.get(key):
            errs.append(f"缺少字段: {key}")

    pov = str(plan.get("pov") or "")
    if pov and pov not in ALLOWED_POV:
        errs.append(f"pov 只能是 {sorted(ALLOWED_POV)}，当前: {pov}")

    style = str(plan.get("style") or "")
    if style and style not in ALLOWED_STYLE:
        errs.append(f"style 只能是 {sorted(ALLOWED_STYLE)}，当前: {style}")

    panels = plan.get("panels") or []
    if not (3 <= len(panels) <= 6):
        errs.append(f"panels 需要 3～6 页，当前 {len(panels)}")

    for i, panel in enumerate(panels):
        if not panel.get("file"):
            errs.append(f"panels[{i}] 缺少 file")
        if not panel.get("script"):
            errs.append(f"panels[{i}] 缺少 script")
        if not panel.get("image_prompt"):
            errs.append(f"panels[{i}] 缺少 image_prompt")

    n = script_len(plan)
    if n and not (80 <= n <= 180):
        errs.append(f"口播全文去空白后应 80～180 字，当前 {n}")

    full = "".join(str(p.get("script") or "") for p in panels)
    for bad in BANNED:
        if bad in full:
            errs.append(f"口播含禁止词: {bad}")

    tags = plan.get("douyin_tags") or []
    if isinstance(tags, str):
        tags = [tags]
    tag_set = {str(t).strip() for t in tags}
    if "#鱼公移山" not in tag_set:
        errs.append("douyin_tags 必须含 #鱼公移山")
    if "#钓鱼恶搞" not in tag_set:
        errs.append("douyin_tags 必须含 #钓鱼恶搞")

    title = str(plan.get("douyin_title") or "")
    if title and len(title) > 36:
        errs.append(f"douyin_title 过长（{len(title)}），建议 ≤30 字")

    voice_raw = str(plan.get("voice") or "").strip().lower()
    if voice_raw in ("xiaoxiao", "zh-cn-xiaoxiaoneural"):
        errs.append("voice 禁止用教学课晓晓(xiaoxiao)，鱼开麦用 yunxia，翻车用 xiaobei")

    hist = load_history()
    used = hist.get("used") or []
    angle = str(plan.get("angle_key") or "").strip()
    slug = str(plan.get("slug") or "").strip()
    for item in used:
        if item.get("angle_key") == angle:
            # 重渲同一集允许
            if rebuild and item.get("slug") == slug:
                continue
            errs.append(f"angle_key 已在 history.json 用过: {angle}")
            break
    # 连续两集 style 不要相同（重渲本集时跳过）
    if used and style and not rebuild:
        last_style = str((used[-1] or {}).get("style") or "")
        if last_style and last_style == style:
            errs.append(f"连续两集 style 不能相同（上一集 {last_style}）")

    # 分镜图存在性（相对 spoof 所在目录或 workdir）
    if spoof_path:
        base = spoof_path.parent
        for i, panel in enumerate(panels):
            rel = Path(str(panel.get("file") or ""))
            path = rel if rel.is_absolute() else (base / rel)
            if not path.exists() or path.stat().st_size == 0:
                errs.append(f"panels[{i}] 图片不存在或为空: {path}")

    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description="校验恶搞 spoof.json")
    parser.add_argument("--spoof", required=True)
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="写稿阶段先不检查 panels 图片是否已生成",
    )
    args = parser.parse_args()
    path = Path(args.spoof).resolve()
    plan = load_json(path)
    errs = check(plan, spoof_path=None if args.skip_images else path)
    if errs:
        for e in errs:
            print(f"[fail] {e}", file=sys.stderr)
        return 1
    print(f"[ok] {path.name}  字数={script_len(plan)}  panels={len(plan.get('panels') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
