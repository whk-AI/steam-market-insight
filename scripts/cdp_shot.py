"""Small Edge CDP screenshot helper used for page acceptance.

Requires Edge started with --remote-debugging-port=9222. It clicks the boot
screen, scrolls to a target selector, and saves a 1280x1000 viewport image.
"""
from __future__ import annotations

import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

from websockets.asyncio.client import connect


def http_json(url: str, method: str = "GET") -> dict:
    req = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


async def main(url: str, selector: str, out: Path, width: int = 1280, height: int = 1000) -> None:
    target = http_json(f"http://127.0.0.1:9222/json/new?{url}", method="PUT")
    ws = target["webSocketDebuggerUrl"]
    seq = 0
    pending = {}

    async with connect(ws, max_size=None) as sock:
        async def send(method: str, params: dict | None = None) -> dict:
            nonlocal seq
            seq += 1
            msg_id = seq
            pending[msg_id] = asyncio.get_running_loop().create_future()
            await sock.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            return await pending[msg_id]

        async def recv_loop() -> None:
            async for raw in sock:
                message = json.loads(raw)
                if "id" in message and message["id"] in pending:
                    fut = pending.pop(message["id"])
                    if not fut.done():
                        fut.set_result(message)

        receiver = asyncio.create_task(recv_loop())
        await send("Page.enable")
        await send("Runtime.enable")
        await send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        await send("Page.navigate", {"url": url})
        await asyncio.sleep(4)
        await send("Runtime.evaluate", {"expression": "document.querySelector('#enter-hall')?.click()"})
        await asyncio.sleep(1)
        await send("Runtime.evaluate", {"expression": f"document.querySelector({json.dumps(selector)})?.scrollIntoView({{block:'start'}})"})
        await asyncio.sleep(1)
        shot = await send("Page.captureScreenshot", {"format": "png", "fromSurface": True})
        out.write_bytes(base64.b64decode(shot["result"]["data"]))
        overflow_expr = """JSON.stringify({
          errors: window.__lastErrors || [],
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          overflow: [...document.querySelectorAll('body *')]
            .map(el => ({tag: el.tagName, cls: el.className && String(el.className).slice(0,40), right: Math.round(el.getBoundingClientRect().right), left: Math.round(el.getBoundingClientRect().left)}))
            .filter(x => x.right > innerWidth + 1 || x.left < -1).slice(0, 12)
        })"""
        errors = await send("Runtime.evaluate", {"expression": overflow_expr})
        print("saved", out, out.stat().st_size, "page", errors.get("result", {}).get("result", {}).get("value"))
        receiver.cancel()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("usage: cdp_shot.py URL SELECTOR OUT.png")
    width = int(sys.argv[4]) if len(sys.argv) > 4 else 1280
    height = int(sys.argv[5]) if len(sys.argv) > 5 else 1000
    asyncio.run(main(sys.argv[1], sys.argv[2], Path(sys.argv[3]), width, height))
