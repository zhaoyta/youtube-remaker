#!/usr/bin/env python3
"""读取 catalog，按中文名/别名解析钩型、鱼种、装备。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def _load(name: str) -> dict:
    path = CATALOG / name
    return json.loads(path.read_text(encoding="utf-8"))


def fish_db() -> dict:
    return _load("fish.json")


def hook_db() -> dict:
    return _load("hooks.json")


def gear_db() -> dict:
    return _load("gear.json")


def line_db() -> dict:
    return _load("lines.json")


def bait_db() -> dict:
    return _load("baits.json")


def _index(db: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, item in db.items():
        out[key.lower()] = key
        out[str(item.get("name", "")).lower()] = key
        for alias in item.get("aliases") or []:
            out[str(alias).lower()] = key
    return out


def resolve_hook(name: str) -> tuple[str, dict]:
    db = hook_db()
    key = _index(db).get(name.strip().lower())
    if not key:
        known = "、".join(item["name"] for item in db.values())
        raise SystemExit(f"未知钩型「{name}」。目录里只有：{known}。不要发明钩名，也不要用错图。")
    return key, db[key]


def resolve_fish(name: str) -> tuple[str, dict]:
    db = fish_db()
    key = _index(db).get(name.strip().lower())
    if not key:
        known = "、".join(db.keys())
        raise SystemExit(
            f"未知鱼种「{name}」。先查学名再写入 catalog/fish.json。"
            f"现有：{known}。禁止用其它鱼的照片顶替。"
        )
    return key, db[key]


def resolve_gear(name: str) -> tuple[str, dict]:
    db = gear_db()
    key = _index(db).get(name.strip().lower())
    if not key:
        known = "、".join(item["name"] for item in db.values())
        raise SystemExit(f"未知装备「{name}」。目录里只有：{known}。")
    return key, db[key]


def resolve_line(name: str) -> tuple[str, dict]:
    db = line_db()
    key = _index(db).get(name.strip().lower())
    if not key:
        known = "、".join(item["name"] for item in db.values())
        raise SystemExit(
            f"未知鱼线「{name}」。只有尼龙线、碳线、PE线。"
            f"现有：{known}。禁止把 PE 画成透明单丝，也禁止尼龙画成编织纹。"
        )
    return key, db[key]


def resolve_bait(name: str) -> tuple[str, dict]:
    db = bait_db()
    key = _index(db).get(name.strip().lower())
    if not key:
        known = "、".join(db.keys())
        raise SystemExit(
            f"未知饵料「{name}」。现有：{known}。"
            "红虫是摇蚊幼虫不是蚯蚓；拉饵有丝、搓饵是实心球。不要画品牌袋。"
        )
    return key, db[key]
