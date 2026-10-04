# -*- coding: utf-8 -*-
"""M3 校验：条数/字段/抽样价格/一致性"""
import json
import pandas as pd

out = r"F:\steam-market-insight\data\cleaned"
js = json.load(open(out + r"\games_cleaned.json", encoding="utf-8"))
df = pd.read_csv(out + r"\games_cleaned.csv", encoding="utf-8-sig")

print("JSON 条数:", len(js), "| CSV 行数:", len(df), "| 列数:", len(df.columns))
print("CSV 列:", list(df.columns))
print("appid 唯一:", df["appid"].nunique(), "| 重复:", df["appid"].duplicated().sum())

proj_fields = ["appid", "name", "price", "original_price", "final_price",
               "discount_percent", "currency", "rating", "positive",
               "total_reviews", "type", "genres", "year", "release_date", "url"]
print("CSV 列序与项目一致:", list(df.columns) == proj_fields)
print("JSON key 与项目一致:", list(js[0].keys()) == proj_fields)

# 抽样价格复算
print("--- 抽样 ---")
for aid in [252490, 570, 730, 230410]:
    r = next(x for x in js if x["appid"] == aid)
    print(aid, r["name"], "| price=", r["price"], "| orig=", r["original_price"],
          "| cur=", r["currency"], "| type=", r["type"], "| genres=", r["genres"],
          "| year=", r["year"], "| date=", r["release_date"])

# 校验 Rust 换算: 3999分 USD -> 39.99*6.705 = 268.13 -> 268
rust = next(x for x in js if x["appid"] == 252490)
assert rust["price"] == round(39.99 * 6.705), rust["price"]
assert rust["original_price"] == round(39.99 * 6.705)
print("Rust 复算通过: 3999分 USD ->", rust["price"], "元")

# 再抽 2 个付费 USD 游戏独立复算
paid = [x for x in js if x["currency"] == "USD" and x["price"]][:2]
raw = pd.read_csv(r"F:\2026.9.1\archive\steam_dataset_2025_csv\applications.csv",
                  usecols=["appid", "mat_final_price", "mat_currency"], dtype={"appid": "int64"})
rawmap = dict(zip(raw["appid"], raw["mat_final_price"]))
for p in paid:
    expect = round(float(rawmap[p["appid"]]) / 100 * 6.705)
    assert p["price"] == expect, (p["appid"], p["price"], expect)
    print(f"复算通过: {p['appid']} {p['name']} 价格 {p['price']} 元")

# 免费游戏
dota = next(x for x in js if x["appid"] == 570)
assert dota["price"] == 0 and dota["original_price"] == 0 and dota["currency"] is None
print("Dota 2 免费游戏校验通过: price=0, currency=None")

# 无类型游戏
g = [x for x in js if x["type"] == "未知"]
print("--- 无类型:", [(x["appid"], x["name"]) for x in g])

# CSV/JSON 一致性
csv_sorted = sorted(df.to_dict("records"), key=lambda x: x["appid"])
js_sorted = sorted(js, key=lambda x: x["appid"])
assert [x["appid"] for x in csv_sorted] == [x["appid"] for x in js_sorted]
print("CSV/JSON appid 排序一致: True")

# 缺失统计复核
print("--- 缺失(JSON) ---")
for f in ["release_date", "price", "currency", "year"]:
    n = sum(1 for x in js if x[f] is None or (isinstance(x[f], float) and pd.isna(x[f])))
    print(f, n)
print("rating 全空:", all(x["rating"] is None for x in js))
print("✔ 校验完成")
