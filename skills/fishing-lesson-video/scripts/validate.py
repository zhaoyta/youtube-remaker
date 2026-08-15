#!/usr/bin/env python3
"""检查 lesson.json：口播时长、钩型/鱼种必须能对上真实目录。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import catalog as cat  # noqa: E402

LAYOUTS = {"title", "hero", "compare", "hook", "steps", "outro"}
KINDS = {"fish", "hook", "gear", "rig", "line", "bait", "wikimedia"}


def _chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def load_lesson(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("slides"):
        raise SystemExit(f"{path} 没有 slides")
    return data


def check_visual(vis: dict, idx: int) -> list[str]:
    errs: list[str] = []
    kind = vis.get("kind")
    if kind not in KINDS:
        errs.append(f"slides[{idx}] 未知 kind={kind}")
        return errs
    if kind == "fish":
        name = vis.get("name") or vis.get("model")
        if not name:
            errs.append(f"slides[{idx}] fish 缺 name")
        else:
            try:
                cat.resolve_fish(str(name))
            except SystemExit as exc:
                errs.append(str(exc))
    elif kind == "hook":
        model = vis.get("model") or vis.get("name")
        if not model:
            errs.append(f"slides[{idx}] hook 缺 model")
        else:
            try:
                cat.resolve_hook(str(model))
            except SystemExit as exc:
                errs.append(str(exc))
    elif kind in ("gear", "rig"):
        model = vis.get("model") or vis.get("name")
        if not model:
            errs.append(f"slides[{idx}] {kind} 缺 model")
        else:
            try:
                cat.resolve_gear(str(model))
            except SystemExit as exc:
                errs.append(str(exc))
    elif kind == "line":
        model = vis.get("model") or vis.get("name")
        if not model:
            errs.append(f"slides[{idx}] line 缺 model")
        else:
            try:
                key, spec = cat.resolve_line(str(model))
                hao = vis.get("size") or vis.get("hao")
                if hao is not None:
                    want = str(hao).rstrip("号")
                    haos = [str(r["hao"]) for r in spec.get("sizes") or []]
                    if haos and want not in haos:
                        errs.append(f"slides[{idx}] {spec['name']} 没有 {want} 号，可选 {haos}")
            except SystemExit as exc:
                errs.append(str(exc))
    elif kind == "bait":
        name = vis.get("name") or vis.get("model")
        if not name:
            errs.append(f"slides[{idx}] bait 缺 name")
        else:
            try:
                cat.resolve_bait(str(name))
            except SystemExit as exc:
                errs.append(str(exc))
    elif kind == "wikimedia":
        if not vis.get("file") and not vis.get("scientific"):
            errs.append(f"slides[{idx}] wikimedia 要 file 或 scientific")
    return errs


def check(data: dict) -> list[str]:
    errs: list[str] = []
    for key in ("topic", "slug", "title", "douyin_title", "douyin_intro", "douyin_tags", "slides"):
        if not data.get(key):
            errs.append(f"缺字段 {key}")
    slides = data.get("slides") or []
    if len(slides) < 6:
        errs.append(f"教学课至少 6 页，现在 {len(slides)}")
    if len(slides) > 12:
        errs.append(f"页太多（{len(slides)}），3 分钟课控制在 6～10 页")
    total = 0
    layouts = []
    for i, slide in enumerate(slides):
        layout = slide.get("layout")
        layouts.append(layout)
        if layout not in LAYOUTS:
            errs.append(f"slides[{i}] 未知 layout={layout}")
        script = str(slide.get("script") or "")
        n = _chars(script)
        total += n
        if n < 20:
            errs.append(f"slides[{i}] 口播太短（{n} 字）")
        if n > 100:
            errs.append(f"slides[{i}] 口播太长（{n} 字），拆页或删字")
        if not slide.get("title"):
            errs.append(f"slides[{i}] 缺 title")
        visuals = slide.get("visuals") or []
        if layout in ("hero", "hook") and not visuals:
            errs.append(f"slides[{i}] {layout} 必须有 visuals")
        if layout == "compare" and len(visuals) < 2:
            errs.append(f"slides[{i}] compare 要两张 visuals")
        for vis in visuals:
            errs.extend(check_visual(vis, i))
    if layouts and layouts[0] != "title":
        errs.append("第一页必须是 title 冷开场")
    if layouts and layouts[-1] != "outro":
        errs.append("最后一页必须是 outro 互动")
    if total < 620:
        errs.append(f"全文 {total} 字，3 分钟课要 650～780 字（按约 4 字/秒）")
    if total > 820:
        errs.append(f"全文 {total} 字太多，会超过 3.5 分钟，删到 650～780")
    tags = data.get("douyin_tags") or []
    if not any("鱼公移山" in str(t) for t in tags):
        errs.append("标签必须含 #鱼公移山")
    banned = ["能派上大用场", "结构独特", "直接拉满", "太绝了", "家人们", "大家好"]
    blob = json.dumps(data, ensure_ascii=False)
    for word in banned:
        if word in blob:
            errs.append(f"口播/文案禁止空话：{word}")
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description="校验钓鱼教学课 JSON")
    parser.add_argument("--lesson", required=True)
    args = parser.parse_args()
    data = load_lesson(Path(args.lesson))
    errs = check(data)
    if errs:
        print("[validate] 未通过：", flush=True)
        for e in errs:
            print(f"  - {e}", flush=True)
        return 1
    n = sum(_chars(str(s.get("script") or "")) for s in data["slides"])
    print(f"[validate] OK  {len(data['slides'])} 页  约 {n} 字  预估 {n/4:.0f} 秒", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
