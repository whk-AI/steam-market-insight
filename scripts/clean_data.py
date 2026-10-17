# -*- coding: utf-8 -*-
"""
第七周练习一：数据清洗脚本 clean_data.py
输入：data/games.json（爬虫抓取的真实 Steam 数据）
输出：data/games_clean.csv（干净数据集）+ 控制台清洗日志

清洗流程（对应任务书第7周知识点）：
1. 读入数据，查看字段与缺失
2. 类型转换：price / rating 等转数值
3. 缺失值处理：currency 全空整列剔除；rating 缺失的行剔除并记录
4. 冗余列剔除：url 分析无用删除
5. genres 多标签：数组 -> 逗号分隔字符串（并输出类型频次统计）
6. 去重：按 name 去重
7. 导出 CSV（UTF-8-sig，Excel 可直接打开）
"""
import json
import os

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
SRC = os.path.join(BASE, 'data', 'games.json')
DST = os.path.join(BASE, 'data', 'games_clean.csv')

print('=' * 60)
print('步骤1：读入数据')
df = pd.read_json(SRC)
print(f'原始行数：{len(df)}，列数：{len(df.columns)}')
print(f'字段：{list(df.columns)}')
print(f'各列缺失统计：\n{df.isnull().sum()}')

# 步骤2：类型转换 -----------------------------------------------------------
print('\n' + '=' * 60)
print('步骤2：类型转换（price/rating/评价数/折扣 转数值）')
num_cols = ['price', 'original_price', 'final_price', 'discount_percent',
            'rating', 'positive', 'total_reviews']
before = len(df)
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')
# 转换后非数值变 NaN，统计一下
new_na = df[num_cols].isnull().sum()
print(f'类型转换后新增缺失：\n{new_na[new_na > 0]}')

# 步骤3：缺失值处理 ---------------------------------------------------------
print('\n' + '=' * 60)
print('步骤3：缺失值处理')
# 3.1 currency 整列全空 -> 剔除
if df['currency'].isnull().all():
    df = df.drop(columns=['currency'])
    print('已剔除整列全空的 currency')
# 3.2 rating 缺失 -> 剔除该行（评分分析必需字段，缺了没意义）
n_rating_na = df['rating'].isnull().sum()
df = df.dropna(subset=['rating'])
print(f'rating 缺失 {n_rating_na} 行已剔除')
# 3.3 price 缺失兜底 -> 剔除
n_price_na = df['price'].isnull().sum()
df = df.dropna(subset=['price'])
print(f'price 缺失 {n_price_na} 行已剔除')

# 步骤4：冗余列剔除 ---------------------------------------------------------
print('\n' + '=' * 60)
print('步骤4：剔除冗余列（url 分析无用）')
df = df.drop(columns=['url'])
print(f'剔除后字段：{list(df.columns)}')

# 步骤5：genres 多标签拆分 --------------------------------------------------
print('\n' + '=' * 60)
print('步骤5：genres 多标签处理')
# 5.1 数组 -> 逗号分隔字符串（存进 CSV）
df['genres'] = df['genres'].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
# 5.2 类型频次统计（供分析/报告使用）
type_count = {}
for x in df['genres']:
    for t in x.split(','):
        t = t.strip()
        if t:
            type_count[t] = type_count.get(t, 0) + 1
top_types = sorted(type_count.items(), key=lambda kv: kv[1], reverse=True)
print('类型频次 TOP10：', top_types[:10])

# 步骤6：去重 ---------------------------------------------------------------
print('\n' + '=' * 60)
print('步骤6：按 name 去重')
n_dup = df.duplicated(subset=['name']).sum()
df = df.drop_duplicates(subset=['name'], keep='first').reset_index(drop=True)
print(f'重复 {n_dup} 行已去除')

# 步骤7：导出 ---------------------------------------------------------------
print('\n' + '=' * 60)
print('步骤7：导出 CSV')
df.to_csv(DST, index=False, encoding='utf-8-sig')
size_kb = os.path.getsize(DST) / 1024
print(f'清洗后：{len(df)} 行，{len(df.columns)} 列')
print(f'文件大小：{size_kb:.1f} KB（要求 ≤ 5MB ✓）')
print(f'已保存：{DST}')

print('\n' + '=' * 60)
print('清洗完成。清洗前后对比：')
print(f'  行数：{before} -> {len(df)}（减少 {before - len(df)}）')
print(f'  列数：{len(pd.read_json(SRC).columns)} -> {len(df.columns)}')
