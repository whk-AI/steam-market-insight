# -*- coding: utf-8 -*-
"""
查重小练习（第七周例会待办）
题目：围绕「在线 TOP10」和「自身数据集」做数据查重，
      回答：数据里有没有重复项？重复在哪？清洗前后对比？
数据源：data/games.json（原始数据）+ games_clean.csv（清洗后）+ online_top10.json（爬虫在线榜）
运行：F:/编程/python.exe "查重小练习.py"
答案即代码。
"""
import json
import os

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

print('=' * 60)
print('练习 A：自身数据集查重（games.json 原始数据）')
print('=' * 60)
# 题目：读入 data/games.json，分别按 appid 和 name 查重，
#       找出重复项，再看清洗产物 games_clean.csv 里还剩多少重复
raw = pd.read_json(os.path.join(PROJECT_ROOT, 'data', 'games.json'))
print(f'原始数据：{len(raw)} 行')
dup_appid = raw[raw.duplicated(subset=['appid'])]
dup_name = raw[raw.duplicated(subset=['name'])]
print(f'按 appid 查重：重复 {len(dup_appid)} 行')
print(f'按 name 查重：重复 {len(dup_name)} 行')
if len(dup_name) > 0:
    print('重复的游戏名：')
    print(dup_name[['appid', 'name', 'year']].to_string(index=False))
print()

clean = pd.read_csv(os.path.join(SCRIPT_DIR, 'games_clean.csv'))
print(f'清洗产物：{len(clean)} 行')
print(f'清洗后按 name 查重：重复 {clean.duplicated(subset=["name"]).sum()} 行')
print(f'清洗后按 appid 查重：重复 {clean.duplicated(subset=["appid"]).sum()} 行')
print('结论：第七周练习四已按 name 去重（145 → 123 行），清洗产物无重复 ✓')
print()

print('=' * 60)
print('练习 B：在线 TOP10 查重（online_top10.json）')
print('=' * 60)
# 题目：读入爬虫产物 online_top10.json，检查 top 榜单里有没有重复 appid / 重复名
top_path = os.path.join(SCRIPT_DIR, 'online_top10.json')
with open(top_path, encoding='utf-8') as f:
    payload = json.load(f)
top = payload['top']
print(f"榜单条目：{len(top)} 条（抓取时间 {payload.get('fetchedAt')}）")
appids = [t['appid'] for t in top]
dup = len(appids) - len(set(appids))
print(f"按 appid 查重：重复 {dup} 项 → {'无重复 ✓' if dup == 0 else '有重复！'}")
print()
print('当前在线 TOP10：')
for t in top:
    print(f"  #{t['rank']}  appid={t['appid']}  在线={t['peak_in_game']}  上周排名={t['last_week_rank']}")
print()

print('=' * 60)
print('练习 C：为什么查重重要（重复数据的危害）')
print('=' * 60)
# 题目：模拟"未去重"会导致什么统计错误——把重复行翻倍，对比均价
fake = pd.concat([clean, clean.iloc[[0]]])  # 人为复制第一行
print(f'正常数据均价：{clean["price"].mean():.2f} 元')
print(f'人为复制 1 行后均价：{fake["price"].mean():.2f} 元（重复项会污染统计口径）')
print('结论：同一条记录出现多次会让 均值/占比/TOP榜 全部失真，')
print('      所以每次拿到新数据第一件事就是查重（duplicated / drop_duplicates）✓')
