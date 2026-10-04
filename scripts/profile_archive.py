# -*- coding: utf-8 -*-
"""快速探查 archive 数据集：命中率 + 数据质量画像（只读）"""
import json
import pandas as pd

BASE = r"F:\2026.9.1\archive\steam_dataset_2025_csv"
PROJ = r"F:\steam-market-insight\data\games.json"

games = json.load(open(PROJ, encoding="utf-8"))
proj_appids = {g["appid"] for g in games}
print("项目 games.json 条数:", len(games), "唯一 appid:", len(proj_appids))

cols = ["appid", "name", "type", "is_free", "release_date", "required_age",
        "metacritic_score", "recommendations_total",
        "mat_supports_windows", "mat_supports_mac", "mat_supports_linux",
        "mat_initial_price", "mat_final_price", "mat_discount_percent",
        "mat_currency", "mat_achievement_count"]
df = pd.read_csv(BASE + r"\applications.csv", usecols=cols, dtype={"appid": "int64"}, low_memory=False)
print("applications.csv 总行数:", len(df))

hit = df[df["appid"].isin(proj_appids)]
print("命中项目 appid 的行数:", len(hit), "命中 appid 数:", hit["appid"].nunique())
miss = proj_appids - set(hit["appid"])
print("未命中 appid:", sorted(miss) if miss else "无")

sub = hit.copy()
print("\n--- 命中子集质量画像 ---")
print("重复 appid 行数:", sub["appid"].duplicated().sum())
print("列缺失率:\n", (sub.isna().mean().round(4) * 100).to_string())
print("\ntype 分布:\n", sub["type"].value_counts().to_string())
print("\ncurrency 分布:\n", sub["mat_currency"].value_counts(dropna=False).to_string())
print("\nrelease_date 样例:\n", sub["release_date"].dropna().head(5).tolist())
print("\nmetacritic 缺失:", sub["metacritic_score"].isna().sum(),
      "| recommendations_total 缺失:", sub["recommendations_total"].isna().sum())
print("\n价格非数字/负值异常(mat_final_price):", (sub["mat_final_price"] < 0).sum(),
      "负值条数; 缺失:", sub["mat_final_price"].isna().sum())
print("mat_discount_percent 超出 0-100:", ((sub["mat_discount_percent"] < 0) | (sub["mat_discount_percent"] > 100)).sum())
print("release_date 为空:", sub["release_date"].isna().sum())
