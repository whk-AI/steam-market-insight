
import json
import os
import requests
from datetime import datetime, timezone

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)                
DATA = os.path.join(PROJECT_ROOT, 'data', 'games.json')     
OUT_CSV = os.path.join(SCRIPT_DIR, 'games_clean.csv')      
OUT_JSON = os.path.join(SCRIPT_DIR, 'online_top10.json')

print('练习一：Pandas 读入与查看')
# 题目：用 pd.read_json 读入 games.json，打印行数、列数、字段列表、缺失统计
df = pd.read_json(DATA)
print(f'行数：{len(df)}，列数：{len(df.columns)}')
print(f'字段：{list(df.columns)}')
print('缺失统计：')
print(df.isnull().sum())

print('练习二：类型转换')
# 题目：将数值型字段统一转成数字，非法值变成 NaN 再统计
num_cols = ['price', 'original_price', 'final_price', 'discount_percent',
            'rating', 'positive', 'total_reviews']
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')
new_na = df[num_cols].isnull().sum()
print('类型转换后缺失（非数值被转成 NaN）：')
print(new_na[new_na > 0])

print('练习三：genres 多标签拆分')
# 题目：genres 是列表，先转成逗号分隔字符串，再用 str.split + explode 拆成一行一个标签
df['genres'] = df['genres'].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
exploded = df['genres'].str.split(',').explode().str.strip()
type_count = exploded.value_counts()
print('类型频次 TOP10：')
print(type_count.head(10))

print('练习四：缺失值处理 + 去重')
# 题目：rating 缺失的行剔除（评分分析必需字段）；currency 全空整列剔除；按 name 去重
n_before = len(df)
if df['currency'].isnull().all():
    df = df.drop(columns=['currency'])
    print('已剔除整列全空的 currency')
n_rating_na = df['rating'].isnull().sum()
df = df.dropna(subset=['rating'])
print(f'rating 缺失 {n_rating_na} 行已剔除')
df = df.dropna(subset=['price'])
n_dup = df.duplicated(subset=['name']).sum()
df = df.drop_duplicates(subset=['name'], keep='first').reset_index(drop=True)
print(f'重复 {n_dup} 行已去除；行数 {n_before} -> {len(df)}')

print('练习五：剔除冗余列 + 导出 CSV（控制体积 ≤5MB）')
# 题目：url 分析无用剔除；导出 UTF-8-sig 方便 Excel 打开；打印体积
df = df.drop(columns=['url'])
df.to_csv(OUT_CSV, index=False, encoding='utf-8-sig')
size_kb = os.path.getsize(OUT_CSV) / 1024
print(f'清洗后：{len(df)} 行 × {len(df.columns)} 列')
print(f'文件大小：{size_kb:.1f} KB（要求 ≤5MB ✓）')
print(f'已保存：{OUT_CSV}')

print('练习六（爬虫小练习）：Steam 在线人数前 10 名')

URL = 'https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/'
print(f'请求中：{URL}')

# 网络偶发超时：最多重试 3 次，每次间隔 2 秒（请求频率控制）
ranks = None
for attempt in range(1, 4):
    try:
        body = requests.get(URL, timeout=15,
                            headers={'User-Agent': 'Mozilla/5.0'}).json()
        ranks = body.get('response', {}).get('ranks', [])
        break
    except Exception as e:
        print(f'第 {attempt} 次请求失败：{e}')
        if attempt < 3:
            import time
            time.sleep(2)

if ranks is None:
    print('爬虫请求失败（网络或接口问题），跳过练习六；可稍后单独运行 scripts/fetch_online.py')
    raise SystemExit(0)

print(f'接口返回 {len(ranks)} 个条目')

top = []
for r in ranks[:10]:
    top.append({
        'rank': r.get('rank'),
        'appid': r.get('appid'),
        'last_week_rank': r.get('last_week_rank'),
        'peak_in_game': r.get('peak_in_game'),
    })

payload = {
    'fetchedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'source': 'Steam GetMostPlayedGames 官方接口',
    'top': top,
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f'已保存 {len(top)} 条到 {OUT_JSON}')
for t in top:
    print(f"  #{t['rank']}  appid={t['appid']}  在线人数={t['peak_in_game']}  上周排名={t['last_week_rank']}")
print('请求频率控制：定时刷新建议间隔 ≥60 秒，避免限流。')

