# -*- coding: utf-8 -*-
"""
第 9 周首页数据生成脚本
=======================
把 pratice(python)/games_clean.csv 与 online_top10.json 转成前端可直接引用的
js/data.js（全局变量 games / online），避免把数据硬编码进 main.js。

用法（项目根目录）：
    python scripts/gen_week9_data.py            # 直接写入 js/data.js
    python scripts/gen_week9_data.py --stdout   # 仅打印到终端（受限环境备用）

说明：
- games 保留字段：appid / name / price / rating / total_reviews / type / genres / year / discount
- price 为当前售价（元），免费游戏为 0
- rating 为好评率（0~100），total_reviews 为评价总数
- online 原样复制 online_top10.json（含 fetchedAt 抓取时间）
- appNameFallback 用于 TOP10 中不在 games 数据集里的 appid 名称映射
"""

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "pratice(python)" / "games_clean.csv"
ONLINE_PATH = ROOT / "pratice(python)" / "online_top10.json"
OUT_PATH = ROOT / "js" / "data.js"

# TOP10 中部分 appid 不在本地 123 款游戏里，补一份真实名称映射
APP_NAME_FALLBACK = {
    "271590": "Grand Theft Auto V",
    "322170": "Geometry Dash",
    "3393110": "AION 2",
    "1422450": "Deadlock",
}


def to_int(value, default=0):
    """把 '123.0' 这类字符串安全转成 int。"""
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    """把字符串安全转成 float。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_games():
    """读取清洗后的 CSV，转成前端需要的 games 数组。"""
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    games = []
    for row in rows:
        games.append(
            {
                "appid": to_int(row.get("appid")),
                "name": (row.get("name") or "").strip(),
                "price": to_int(row.get("price")),
                "rating": round(to_float(row.get("rating")), 1),
                "total_reviews": to_int(row.get("total_reviews")),
                "type": (row.get("type") or "其他").strip(),
                "genres": (row.get("genres") or "").strip(),
                "year": to_int(row.get("year")),
                "discount": to_int(row.get("discount_percent")),
            }
        )
    return games


def num(value):
    """整数原样输出，小数保留一位（避免 97.0 这种冗余零）。"""
    if isinstance(value, float):
        text = "%.1f" % value
        return text[:-2] if text.endswith(".0") else text
    return str(value)


def game_line(game):
    """输出单款游戏的紧凑对象字面量，便于人工核对。"""
    return (
        "{appid:%d,name:%s,price:%d,rating:%s,total_reviews:%d,"
        "type:%s,genres:%s,year:%d,discount:%d}"
        % (
            game["appid"],
            json.dumps(game["name"], ensure_ascii=False),
            game["price"],
            num(game["rating"]),
            game["total_reviews"],
            json.dumps(game["type"], ensure_ascii=False),
            json.dumps(game["genres"], ensure_ascii=False),
            game["year"],
            game["discount"],
        )
    )


def build_js(games, online):
    """拼出完整的 data.js 文本。"""
    lines = [
        "/*",
        " * Steam 游戏市场洞察平台 · 首页数据",
        " * 由 scripts/gen_week9_data.py 从以下真实数据生成，请勿手工修改：",
        " *   - pratice(python)/games_clean.csv   （清洗后数据集，%d 款）" % len(games),
        " *   - pratice(python)/online_top10.json （Steam GetMostPlayedGames 官方接口快照）",
        " */",
        "",
        "const games = [",
    ]
    lines += ["  " + game_line(game) + "," for game in games]
    lines += ["];", "", "const online = {", '  fetchedAt: %s,' % json.dumps(online["fetchedAt"])]
    lines.append("  source: %s," % json.dumps(online.get("source", ""), ensure_ascii=False))
    lines.append("  top: [")
    for item in online["top"]:
        lines.append(
            "    {rank:%d,appid:%d,peak_in_game:%d,last_week_rank:%d},"
            % (
                item["rank"],
                item["appid"],
                item["peak_in_game"],
                item["last_week_rank"],
            )
        )
    lines += ["  ]", "};", ""]
    lines.append("/* TOP10 中不在 games 数据集内的 appid → 真实游戏名（补充映射） */")
    lines.append("const appNameFallback = {")
    for appid, name in APP_NAME_FALLBACK.items():
        lines.append("  %s: %s," % (json.dumps(appid), json.dumps(name, ensure_ascii=False)))
    lines += ["};", ""]
    return "\n".join(lines)


def main():
    games = load_games()
    with ONLINE_PATH.open("r", encoding="utf-8") as f:
        online = json.load(f)

    text = build_js(games, online)
    if "--stdout" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
        return

    OUT_PATH.write_text(text, encoding="utf-8", newline="\n")
    years = sorted({g["year"] for g in games})
    print(f"已生成 {OUT_PATH}")
    print(f"games: {len(games)} 款 | online: {len(online['top'])} 条 | 年份: {years[0]}~{years[-1]}")


if __name__ == "__main__":
    main()
