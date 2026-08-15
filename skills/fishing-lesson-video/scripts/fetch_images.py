#!/usr/bin/env python3
"""从 Wikimedia Commons 拉真实鱼种照片。钩型和线组用绘制，不在这里找图。"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "fishing-lesson-video/1.0 (personal; educational; commons-images)"
API = "https://commons.wikimedia.org/w/api.php"


def _get(params: dict) -> dict:
    params = {**params, "format": "json"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise SystemExit(f"Wikimedia API 失败: {last}")


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                dest.write_bytes(resp.read())
            return
        except Exception as exc:
            last = exc
            time.sleep(0.6 * (attempt + 1))
    raise SystemExit(f"下载失败 {url}: {last}")


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def file_info(title: str) -> dict | None:
    if not title.startswith("File:"):
        title = "File:" + title
    data = _get(
        {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata|size",
            "iiurlwidth": "1600",
            "titles": title,
        }
    )
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        if page.get("missing") is not None:
            return None
        infos = page.get("imageinfo") or []
        if not infos:
            return None
        info = infos[0]
        meta = info.get("extmetadata") or {}
        mime = str(info.get("mime") or "")
        if not mime.startswith("image/"):
            return None
        return {
            "title": page.get("title") or title,
            "url": info.get("thumburl") or info.get("url"),
            "artist": _strip_html(str((meta.get("Artist") or {}).get("value") or "")),
            "license": str((meta.get("LicenseShortName") or {}).get("value") or "Wikimedia"),
            "scientific": _strip_html(str((meta.get("ObjectName") or {}).get("value") or "")),
        }
    return None


def _blocked(title: str, extra: list[str] | None = None) -> bool:
    blob = title.lower()
    words = [
        "goldfish",
        "golden fish",
        "nishikigoi",
        "koi carp",
        "map of",
        "logo",
        "icon",
        "flag",
        "skeleton",
        "dissection",
        "aquarium gold",
    ]
    for w in words + [x.lower() for x in (extra or [])]:
        if w and w in blob:
            return True
    return False


def search_file(query: str, avoid: list[str] | None = None) -> dict | None:
    data = _get(
        {
            "action": "query",
            "list": "search",
            "srnamespace": "6",
            "srlimit": "12",
            "srsearch": query,
        }
    )
    hits = ((data.get("query") or {}).get("search")) or []
    for hit in hits:
        title = str(hit.get("title") or "")
        if _blocked(title, avoid):
            continue
        if not re.search(r"\.(jpe?g|png)$", title, re.I):
            continue
        info = file_info(title)
        if info:
            return info
    return None


def resolve_fish_image(entry: dict, cache: Path) -> dict:
    avoid = list(entry.get("avoid") or [])
    tried: list[str] = []
    for fname in entry.get("files") or []:
        tried.append(fname)
        info = file_info(fname)
        if info and not _blocked(info["title"], avoid):
            return _save(info, cache)
    for q in [entry.get("scientific"), *(entry.get("search") or [])]:
        if not q:
            continue
        tried.append(str(q))
        info = search_file(str(q), avoid)
        if info:
            return _save(info, cache)
    raise SystemExit(
        f"找不到「{entry.get('scientific')}」的真实照片。已试：{tried}。"
        "不要换其它鱼的图。把 Wikimedia 文件名写进 catalog/fish.json 后再编。"
    )


def _save(info: dict, cache: Path) -> dict:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", info["title"].replace("File:", ""))
    dest = cache / slug
    if not dest.exists() or dest.stat().st_size == 0:
        _download(info["url"], dest)
    info = {**info, "path": str(dest)}
    (cache / (slug + ".json")).write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return info
