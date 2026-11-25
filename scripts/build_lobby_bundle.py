# -*- coding: utf-8 -*-
"""把页面要用的六个 JSON 打包成可直接被 file:// 读取的 JS。

双击 index.html 时，浏览器不允许 fetch 本地 JSON；但允许加载 JS。
所以把数据写成 window.__LOBBY_DATA__，页面优先读它，再回退到 fetch。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "agg": ROOT / "data/market/market_agg.json",
    "reviews": ROOT / "data/market/reviews_enriched.json",
    "top500": ROOT / "data/market/top500.json",
    "online": ROOT / "data/online.json",
    "newReleases": ROOT / "data/new_releases.json",
    "model": ROOT / "data/ml/model.json",
}


def main() -> None:
    payload = {}
    for key, path in FILES.items():
        with path.open("r", encoding="utf-8") as handle:
            payload[key] = json.load(handle)

    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # 避免数据里偶然出现 </script> 提前结束脚本块。
    text = text.replace("</", "<\\/")

    out = ROOT / "js/lobby-data.js"
    out.write_text(
        "/* 自动生成，勿手改；源：data/market/*.json / data/online.json / data/new_releases.json / data/ml/model.json */\n"
        "window.__LOBBY_DATA__ = " + text + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
