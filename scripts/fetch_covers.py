#!/usr/bin/env python3
"""把 Steam 封面缓存到本地，保证断网/直连 CDN 失败时仍有真实游戏图。

优先使用 cdn.akamai.steamstatic.com 的 header.jpg；新游/新 appid 常常没有
旧版 header 路径，因此退回 Steam 商店页的 og:image（capsule_616x353）。
"""
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "covers"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OG_RE = re.compile(r'<meta property="og:image" content="([^"]+)"')


def load_json(path, default):
    p = ROOT / path
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def target_path(appid):
    return OUT / f"{appid}.jpg"


def save_bytes(appid, data):
    if not data or len(data) < 800:
        return False
    if not (data[:2] == b"\xff\xd8" or data[:8] == b"\x89PNG\r\n\x1a\n"):
        return False
    target_path(appid).write_bytes(data)
    return True


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def direct_header(appid):
    url = f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
    try:
        return save_bytes(appid, get(url))
    except Exception:
        return False


def edge_og(appid):
    """没有 header.jpg 的新游戏，从 Steam 商店页读 og:image。"""
    with tempfile.TemporaryDirectory(prefix="edge-cover-") as profile:
        try:
            proc = subprocess.run(
                [
                    EDGE,
                    "--headless",
                    "--disable-gpu",
                    "--no-first-run",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=25000",
                    "--dump-dom",
                    f"https://store.steampowered.com/app/{appid}/?l=english",
                ],
                capture_output=True,
                timeout=45,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception as exc:
            print(f"[edge] {appid} FAIL {type(exc).__name__}")
            return False
    match = OG_RE.search(proc.stdout or "")
    if not match:
        print(f"[edge] {appid} no og:image")
        return False
    try:
        return save_bytes(appid, get(match.group(1)))
    except Exception as exc:
        print(f"[edge] {appid} image FAIL {type(exc).__name__}")
        return False


def main():
    online = load_json("data/online.json", {}).get("top", [])
    new = load_json("data/new_releases.json", {}).get("items", [])
    top500 = load_json("data/market/top500.json", [])
    priority = []
    for row in online + new:
        appid = int(row["appid"])
        if appid not in priority:
            priority.append(appid)
    archive = []
    for row in top500:
        appid = int(row["appid"])
        if appid not in archive:
            archive.append(appid)

    ok = []
    need_edge = []
    # 先把旧游戏/常见 header 直接抓下来；失败的留给 Edge 查 og:image。
    for appid in priority:
        if direct_header(appid):
            ok.append(appid)
            print(f"[header] {appid} ok")
        else:
            need_edge.append(appid)
    for appid in need_edge:
        if edge_og(appid):
            ok.append(appid)
            print(f"[og] {appid} ok")
        time.sleep(0.3)

    # TOP500 档案库封面，失败不阻塞；页面仍会回退到远程 header / 本地标识。
    missing_archive = [a for a in archive if not target_path(a).exists()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(direct_header, a): a for a in missing_archive}
        for future in as_completed(futures):
            appid = futures[future]
            try:
                if future.result():
                    ok.append(appid)
            except Exception:
                pass

    # 去重并排序，写一份清单方便排查。
    ok = sorted(set(ok))
    (ROOT / "data" / "covers.json").write_text(
        json.dumps({"count": len(ok), "appids": ok}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"done: {len(ok)} covers -> {OUT}")


if __name__ == "__main__":
    main()
