# -*- coding: utf-8 -*-
"""校验教程中的迷你示例"""
import pandas as pd

raw = pd.DataFrame({
    "id": [1, 2, 2, 3],
    "name": [" 游戏A ", "游戏B", "游戏B", None],
    "price_cents": [990, None, 5000, 3000],
    "release_date": ["2020-01-05", "2019-03-02", "bad-date", "2018-07-11"],
})

clean = (
    raw.drop_duplicates("id")
       .dropna(subset=["name"])
       .assign(price=lambda d: d["price_cents"] / 100)
       .assign(year=lambda d: pd.to_datetime(d["release_date"], errors="coerce").dt.year)
       .drop(columns=["price_cents"])
       .sort_values("id")
)
print(clean.to_string())
