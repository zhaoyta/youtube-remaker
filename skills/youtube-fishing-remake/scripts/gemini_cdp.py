#!/usr/bin/env python3
"""Playwright CDP → 已登录的 gemini.google.com，把 YouTube 短视频理解成 edit.json。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_selectors as sel

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CDP = "http://127.0.0.1:9222"
GEMINI_URL = "https://gemini.google.com/app"


def log(msg: str) -> None:
    print(f"[gemini-cdp] {msg}", flush=True)


def find_visible(page, selectors: list[str], timeout_ms: int = 4000):
    per = max(800, min(timeout_ms, 2500))
    for selector in selectors:
        loc = page.locator(selector).first
        try:
            loc.wait_for(state="visible", timeout=per)
            return loc
        except Exception:
            continue
    return None


def chrome_ready(cdp: str) -> str:
    import urllib.request

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    last_err = None
    candidates = [cdp]
    if "127.0.0.1" in cdp:
        candidates.append(cdp.replace("127.0.0.1", "[::1]"))
    for base in candidates:
        for _ in range(4):
            try:
                with opener.open(f"{base}/json/version", timeout=2) as resp:
                    data = json.loads(resp.read().decode())
                ws = data.get("webSocketDebuggerUrl")
                if ws:
                    log(f"CDP 就绪 {base}")
                    return base
            except Exception as exc:
                last_err = exc
                time.sleep(0.3)
    raise SystemExit(
        f"连不上 Chrome CDP {cdp}（{last_err}）。先运行: bash scripts/start-chrome-cdp.sh"
    )


def inject_prompt(page, text: str) -> None:
    page.evaluate(
        """() => {
          const el =
            document.querySelector("div.ql-editor[contenteditable='true']") ||
            document.querySelector("[contenteditable='true'][role='textbox']") ||
            document.querySelector("[contenteditable='true']");
          if (!el) throw new Error("找不到 Gemini 输入框");
          el.focus();
        }"""
    )
    page.keyboard.press("Meta+A")
    page.keyboard.insert_text(text)


def extract_response(page) -> str:
    return page.evaluate(
        """(selectors) => {
          let best = "";
          for (const sel of selectors) {
            let nodes;
            try { nodes = document.querySelectorAll(sel); } catch { continue; }
            for (const el of nodes) {
              const t = (el.innerText || "").replace(/[\\u200B-\\u200D\\uFEFF]/g, "").trim();
              if (t.length > best.length) best = t;
            }
          }
          return best;
        }""",
        sel.RESPONSE,
    )


def parse_json_blob(raw: str) -> dict:
    stripped = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", stripped, re.S)
    if fenced:
        stripped = fenced.group(1)
    else:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("回复里没有 JSON 对象")
        stripped = stripped[start : end + 1]
    data = json.loads(stripped)
    if not isinstance(data.get("clips"), list) or not data["clips"]:
        raise ValueError("JSON 缺少 clips")
    for i, clip in enumerate(data["clips"]):
        if "start" not in clip or "end" not in clip:
            raise ValueError(f"clips[{i}] 缺少 start/end")
        script = clip.get("script") or clip.get("narration")
        if not str(script or "").strip():
            raise ValueError(f"clips[{i}] 缺少 script")
        clip["script"] = str(script).strip()
    return data


def wait_generation(page, timeout_s: int = 240) -> str:
    log("等待 Gemini 开始生成…")
    started = time.time()
    saw_stop = False
    while time.time() - started < 45:
        if find_visible(page, sel.STOP, timeout_ms=800):
            saw_stop = True
            break
        text = extract_response(page)
        if len(text) > 80:
            break
        time.sleep(0.8)
    if saw_stop:
        log("正在生成，等待结束（视频理解可能要 1～3 分钟）…")
        while time.time() - started < timeout_s:
            if not find_visible(page, sel.STOP, timeout_ms=700):
                break
            time.sleep(1.5)
        else:
            raise TimeoutError("Gemini 生成超时")
    last = ""
    stable = 0
    while time.time() - started < timeout_s:
        text = extract_response(page)
        if text and text == last and len(text) > 40:
            stable += 1
            if stable >= 3:
                return text
        else:
            last = text
            stable = 0
        time.sleep(1.2)
    if last:
        return last
    raise TimeoutError("没有拿到 Gemini 回复")


def ensure_gemini_page(context, reuse_tab: bool):
    pages = context.pages
    gemini = next((p for p in pages if "gemini.google.com" in p.url), None)
    if gemini and reuse_tab:
        log("复用已有 Gemini 标签")
        gemini.bring_to_front()
        return gemini, False
    if gemini and not reuse_tab:
        log("打开新对话")
        gemini.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
        gemini.wait_for_timeout(2500)
        new_btn = find_visible(gemini, sel.NEW_CHAT, timeout_ms=3000)
        if new_btn:
            new_btn.click()
            gemini.wait_for_timeout(2000)
        return gemini, False
    log("打开 https://gemini.google.com/app")
    page = context.new_page()
    page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    return page, True


def main() -> int:
    parser = argparse.ArgumentParser(description="CDP 驱动 Gemini 网页，输出剪辑 JSON")
    parser.add_argument("--url", required=True, help="YouTube 短视频 URL")
    parser.add_argument("--out", required=True, help="edit.json 输出路径")
    parser.add_argument("--cdp", default=DEFAULT_CDP)
    parser.add_argument("--prompt", default=str(ROOT / "prompts" / "analyze.txt"))
    parser.add_argument("--reuse-tab", action="store_true", help="不新开对话，在当前 Gemini 标签继续")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--target-duration", type=float, help="期望成片总时长（秒），写入提示词")
    parser.add_argument("--source-duration", type=float, help="片源真实时长（秒），写入提示词")
    parser.add_argument("--source-title", default="", help="YouTube 原标题，写入提示词防串台")
    args = parser.parse_args()

    prompt_path = Path(args.prompt)
    template = prompt_path.read_text(encoding="utf-8")
    duration_lines = []
    title = (args.source_title or "").strip()
    if title:
        duration_lines.append(f"- 原片标题（仅供参考，以画面为准）：{title}")
        duration_lines.append("- 若标题/画面都不是葫芦钩，禁止写葫芦钩")
    if args.source_duration:
        duration_lines.append(
            f"- 片源真实时长（秒）：{args.source_duration:g}。"
            f"所有 clips 的 end 必须 ≤ {args.source_duration:g}，不要规划更长的片段。"
        )
    else:
        duration_lines.append("- 片源真实时长（秒）：未知，请以视频实际长度为准，不要超出")
    if args.target_duration:
        duration_lines.append(f"- 期望成片总时长（秒）：{args.target_duration:g}（允许 ±10%）")
    else:
        duration_lines.append("- 期望成片总时长：未指定，覆盖片源即可，不要故意拉长")
    duration_section = "\n".join(duration_lines)
    prompt = (
        "【全新任务，禁止复用上一条视频的标题、口播或装备名称】\n\n"
        + template.replace("{url}", args.url.strip()).replace(
            "{duration_section}", duration_section
        )
    )

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("未安装 playwright。请用: bash scripts/setup_venv.sh") from exc

    cdp_url = chrome_ready(args.cdp)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page, _created_tab = ensure_gemini_page(context, args.reuse_tab)
        try:
            if "accounts.google.com" in page.url:
                raise SystemExit("停在 Google 登录页。请在调试 Chrome 里登录后再跑。")

            box = find_visible(page, sel.INPUT, timeout_ms=15000)
            if not box:
                raise SystemExit("找不到 Gemini 输入框。可能未登录，或选择器过期（改 scripts/gemini_selectors.py）。")
            box.click()
            inject_prompt(page, prompt)
            page.wait_for_timeout(600)

            send = find_visible(page, sel.SEND, timeout_ms=5000)
            if send and not send.is_disabled():
                send.click()
            else:
                page.keyboard.press("Enter")
            log("已发送，等待视频理解…")

            raw = wait_generation(page, timeout_s=args.timeout)
            raw_path = out_path.with_name("gemini_raw.txt")
            raw_path.write_text(raw, encoding="utf-8")
            log(f"原始回复已写 {raw_path}（{len(raw)} 字）")
            try:
                data = parse_json_blob(raw)
            except (ValueError, json.JSONDecodeError) as exc:
                raise SystemExit(
                    f"无法从回复解析 JSON: {exc}\n原始文本在 {raw_path}，可加 --reuse-tab 让 Gemini 只输出 JSON。"
                ) from exc
            url = args.url.strip()
            data["youtube_url"] = url
            data["source_url"] = url
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"已写入 {out_path}，{len(data['clips'])} 个片段")
            title = str(data.get("douyin_title") or "").strip() or "（缺失）"
            intro = str(data.get("douyin_intro") or data.get("douyin_desc") or "").strip() or "（缺失）"
            tags = data.get("douyin_tags") or []
            if isinstance(tags, str):
                tag_line = tags.strip()
            else:
                parts = []
                for tag in tags:
                    text = str(tag).strip()
                    if not text:
                        continue
                    if not text.startswith("#"):
                        text = "#" + text.lstrip("#")
                    parts.append(text)
                tag_line = " ".join(parts) or "（缺失）"
            log("---------- 抖音文案 ----------")
            log(f"爆款标题: {title}")
            log(f"作品简介: {intro}")
            log(f"标签: {tag_line}")
            log("------------------------------")
        finally:
            # 绝对不要 browser.close()，那会把用户的 Chrome 一起关停。
            # 分析完关掉 Gemini 标签，避免网页反复跳 App；--reuse-tab 时保留，方便补一句。
            if not args.reuse_tab:
                try:
                    if not page.is_closed():
                        page.close()
                    log("已关闭 Gemini 标签")
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
