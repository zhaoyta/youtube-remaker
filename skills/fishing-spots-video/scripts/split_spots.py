#!/usr/bin/env python3
"""全城 spots.json：按距离去重，再按 area 拆成多份。点太少的区并进最近的区。"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

EARTH_M = 6371000.0


def haversine_m(a: dict, b: dict) -> float:
    lat1, lon1 = math.radians(float(a["lat"])), math.radians(float(a["lon"]))
    lat2, lon2 = math.radians(float(b["lat"])), math.radians(float(b["lon"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_M * math.asin(min(1.0, math.sqrt(h)))


def centroid(spots: list[dict]) -> dict:
    return {
        "lat": sum(float(s["lat"]) for s in spots) / len(spots),
        "lon": sum(float(s["lon"]) for s in spots) / len(spots),
    }


def richer(a: dict, b: dict) -> dict:
    score = lambda s: len(str(s.get("nav") or "")) + len(str(s.get("note") or "")) + len(str(s.get("script") or ""))
    return a if score(a) >= score(b) else b


def dedupe(spots: list[dict], meters: float) -> tuple[list[dict], list[dict]]:
    kept: list[dict] = []
    dropped: list[dict] = []
    for s in spots:
        hit = None
        for i, k in enumerate(kept):
            if haversine_m(s, k) <= meters:
                hit = i
                break
        if hit is None:
            kept.append(dict(s))
            continue
        kept[hit] = richer(kept[hit], s)
        dropped.append({"name": s.get("name"), "kept": kept[hit].get("name"), "meters": round(haversine_m(s, kept[hit]), 1)})
    return kept, dropped


def slug(text: str) -> str:
    text = str(text).strip() or "area"
    text = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    return text.replace(" ", "")


def split_areas(spots: list[dict], min_spots: int) -> tuple[dict[str, list[dict]], dict[str, list[str]]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in spots:
        groups[str(s.get("area") or "其他")].append(s)
    if len(spots) < min_spots:
        return {"全市": list(spots)}, {"全市": []}
    large = {a: list(pts) for a, pts in groups.items() if len(pts) >= min_spots}
    small = {a: pts for a, pts in groups.items() if len(pts) < min_spots}
    if not large:
        return {"全市": list(spots)}, {"全市": []}
    merged_from: dict[str, list[str]] = {a: [] for a in large}
    for area, pts in small.items():
        c = centroid(pts)
        nearest = min(large, key=lambda a: haversine_m(c, centroid(large[a])))
        large[nearest].extend(pts)
        merged_from[nearest].append(area)
    return large, merged_from


def load_plan(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"spots": data}
    if not data.get("spots"):
        raise SystemExit(f"{path} 没有 spots")
    return data


def city_name(plan: dict) -> str:
    if plan.get("city"):
        return str(plan["city"]).strip()
    title = str(plan.get("title") or "")
    m = re.match(r"^(.{2,8}?)\s*\d*\s*个免费掉点", title)
    if m:
        return m.group(1).strip()
    return title.replace("免费掉点", "").strip() or "本市"


def area_plan(base: dict, city: str, area: str, spots: list[dict]) -> dict:
    n = len(spots)
    numbered = []
    for i, s in enumerate(spots, start=1):
        item = dict(s)
        item["n"] = i
        numbered.append(item)
    names = "、".join(str(s["name"]) for s in numbered[:4])
    out = {k: v for k, v in base.items() if k != "spots"}
    out["city"] = city
    out["area"] = area
    out["title"] = f"{city} {area} {n} 个免费掉点"
    out["subtitle"] = base.get("subtitle") or "地图标注 · 优缺点 · 注意事项"
    out["intro_script"] = f"{city}{area}{n}个免费掉点，位置优缺点注意事项，地图标好了，先收藏。"
    out["douyin_title"] = f"{city}{area}免费掉点 {n}个标清"
    out["douyin_intro"] = f"{names}等。去之前看现场牌子，垃圾带走。"
    tags = list(base.get("douyin_tags") or ["#鱼公移山", "#免费钓点", "#野钓"])
    extra = f"#{city}钓鱼"
    if extra not in tags:
        tags = tags[:1] + [extra] + tags[1:]
    extra_area = f"#{area}"
    if extra_area not in tags:
        tags.append(extra_area)
    out["douyin_tags"] = tags[:6]
    out["spots"] = numbered
    return out


def run_split(
    spots_path: Path,
    workdir: Path,
    *,
    dedupe_m: float,
    min_spots: int,
) -> dict:
    plan = load_plan(spots_path)
    city = city_name(plan)
    raw = list(plan["spots"])
    kept, dropped = dedupe(raw, dedupe_m)
    grouped, merged_from = split_areas(kept, min_spots)
    workdir.mkdir(parents=True, exist_ok=True)
    videos = []
    for area, pts in grouped.items():
        folder = workdir / slug(area)
        folder.mkdir(parents=True, exist_ok=True)
        area_json = folder / "spots.json"
        payload = area_plan(plan, city, area, pts)
        area_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        videos.append(
            {
                "area": area,
                "spots": len(pts),
                "merged_from": merged_from.get(area, []),
                "json": str(area_json),
                "workdir": str(folder),
            }
        )
    videos.sort(key=lambda v: (-v["spots"], v["area"]))
    manifest = {
        "city": city,
        "source": str(spots_path),
        "raw": len(raw),
        "after_dedupe": len(kept),
        "dropped": dropped,
        "dedupe_m": dedupe_m,
        "min_spots": min_spots,
        "videos": videos,
    }
    dest = workdir / "manifest.json"
    dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="掉点去重并按区拆 JSON")
    parser.add_argument("--spots", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--dedupe-m", type=float, default=500)
    parser.add_argument("--min-spots", type=int, default=4)
    args = parser.parse_args()
    manifest = run_split(
        Path(args.spots).resolve(),
        Path(args.workdir).resolve(),
        dedupe_m=args.dedupe_m,
        min_spots=args.min_spots,
    )
    print(json.dumps({k: manifest[k] for k in ("city", "raw", "after_dedupe", "videos")}, ensure_ascii=False, indent=2))
    print(f"manifest: {Path(args.workdir).resolve() / 'manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
