# -*- coding: utf-8 -*-

import os

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(SCRIPT_DIR, 'games_clean.csv')
OUT_MD = os.path.join(SCRIPT_DIR, '第八周统计洞察报告.md')

df = pd.read_csv(CSV)
print(f'读取清洗数据：{len(df)} 行 × {len(df.columns)} 列\n')

# 价格字段可能有 NaN，先转数值
df['price'] = pd.to_numeric(df['price'], errors='coerce')
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
df['total_reviews'] = pd.to_numeric(df['total_reviews'], errors='coerce')
df['discount_percent'] = pd.to_numeric(df['discount_percent'], errors='coerce')

print('练习一：整体画像（描述性统计）')
# 题目：对 价格 / 好评率 / 评价总数 三个核心指标做 describe，
#       回答：均价多少？中位数多少？最贵/最便宜？好评率平均多少？
desc = df[['price', 'rating', 'total_reviews']].describe().round(2)
print(desc)
print()

print('练习二：类型分组统计（groupby + agg）')
# 题目：按主类型 type 分组，统计 游戏数 / 平均价格 / 平均好评率，
#       观察"哪个类型最卷（数量多）""哪个类型最贵/口碑最好"
g = df.groupby('type').agg(
    游戏数=('name', 'count'),
    平均价格=('price', 'mean'),
    平均好评率=('rating', 'mean'),
).round(2).sort_values('游戏数', ascending=False)
print(g)
print()

print('练习三：价格分箱（免费 / 低价 / 中价 / 高价 / 豪华）')
# 题目：用 pd.cut 把 price 分成 5 段，统计每段的游戏数量占比，
#       回答：免费游戏占多少？主流价位在哪一段？
bins = [0, 0.01, 20, 60, 100, float('inf')]
labels = ['免费(0)', '<20', '20-60', '60-100', '>100']
df['价位段'] = pd.cut(df['price'], bins=bins, labels=labels, right=False)
price_cut = df['价位段'].value_counts().sort_index()
price_pct = (price_cut / len(df) * 100).round(1)
print(pd.DataFrame({'数量': price_cut, '占比%': price_pct}))
print()

print('练习四：榜单与折扣（Top 游戏 + 折扣分析）')
# 题目：①好评率 Top10（评价数≥500 过滤，避免小样本刷榜）
#       ②当前打折游戏占比 + 平均折扣力度
#       ③免费游戏里好评率 Top5
top_rated = (df[df['total_reviews'] >= 500]
             .sort_values('rating', ascending=False)
             .head(10)[['name', 'rating', 'total_reviews', 'price']])
print('好评率 Top10（评价数≥500）：')
print(top_rated.to_string(index=False))
print()
on_sale = df[df['discount_percent'] > 0]
print(f"打折游戏：{len(on_sale)} 款 / {len(df)} 款，占 {len(on_sale) / len(df) * 100:.1f}%")
print(f"平均折扣力度：{on_sale['discount_percent'].mean():.1f}%")
free = df[df['price'] == 0]
print()
print('免费游戏好评率 Top5：')
print(free.sort_values('rating', ascending=False).head(5)[['name', 'rating', 'total_reviews']].to_string(index=False))
print()

print('练习五：数据洞察提炼（≥3条，自动写入报告）')
# 题目：基于上面的统计结果，提炼 ≥3 条对"Steam 市场"有价值的洞察，
#       数字全部由代码算出，不允许拍脑袋 —— 这就是任务书要的"洞察≥3条"
free_rate = len(free) / len(df) * 100
avg_price_paid = df[df['price'] > 0]['price'].mean()
most_type = g['游戏数'].idxmax()
most_type_cnt = int(g['游戏数'].max())
best_rating_type = g['平均好评率'].idxmax()
best_rating_val = g['平均好评率'].max()
high_rating = df[df['rating'] >= 90]
high_rating_rate = len(high_rating) / len(df) * 100
main_bucket = price_cut.idxmax()
main_bucket_pct = price_pct.max()

insights = [
    f"① 免费策略主导流量：免费游戏占全部游戏的 {free_rate:.1f}%，付费游戏均价 {avg_price_paid:.1f} 元，" 
    f"说明 Steam 市场“免费吸量、付费变现”模式占主流。",
    f"② 类型结构集中：{most_type} 类游戏数量最多（{most_type_cnt} 款），" 
    f"但口碑最好的类型是 {best_rating_type}（平均好评率 {best_rating_val:.1f}%），"
    f"供给多 ≠ 口碑好，{most_type} 类竞争最激烈。",
    f"③ 口碑分化明显：好评率≥90 的优质游戏仅占 {high_rating_rate:.1f}%，"
    f"大部分游戏集中在 80-90 分区间，头部与长尾差距大，口碑是稀缺资产。",
    f"④ 主流价位段为「{main_bucket}」，占 {main_bucket_pct:.1f}%；"
    f"当前 {len(on_sale)} 款在打折（平均 {on_sale['discount_percent'].mean():.1f}%），"
    f"折扣促销是主要转化手段。",
]

print('自动生成的洞察（已写入报告文件）：')
for ins in insights:
    print(f'  {ins}')

md = f"""# 第八周统计洞察报告（Steam 游戏市场）

> 数据源：games_clean.csv（第七周清洗产物，{len(df)} 款游戏）
> 生成时间：由「第八周练练合集.py」自动输出，数字全部可复现

## 一、整体画像
- 均价：{df['price'].mean():.2f} 元 / 中位数：{df['price'].median():.2f} 元
- 平均好评率：{df['rating'].mean():.2f}% / 平均评价数：{df['total_reviews'].mean():.0f}
- 最贵游戏：{df.loc[df['price'].idxmax(), 'name']}（{df['price'].max():.2f} 元）
- 免费游戏占比：{free_rate:.1f}%

## 二、类型×价格 交叉统计
{ g.to_markdown() if False else g.to_string() }

## 三、价格分箱
{ pd.DataFrame({'数量': price_cut, '占比%': price_pct}).to_string() }

## 四、好评率 Top10（评价数≥500）
{ top_rated.to_string(index=False) }

## 五、洞察（≥3条，供周报直接使用）
"""
for i, ins in enumerate(insights, 1):
    md += f"{ins}\n"

md += """
---
*本报告为第八周产出物，对应平台 v1（第十周）的「指标卡 + 分布图」数据基础。*
"""
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write(md)
print(f'\n报告已保存：{OUT_MD}')
