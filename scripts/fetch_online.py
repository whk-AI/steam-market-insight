# -*- coding: utf-8 -*-
"""
第七周练习二：爬虫脚本 fetch_online.py
调用 Steam 官方公开接口 GetMostPlayedGames，抓取"当前在线 Top10"并保存为 JSON。
对应任务书第7周爬虫基础（选做但建议完成），输出供第10周首页"实时在线 TOP10"模块使用。

接口：https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/
返回：ranks 数组，每项含 rank / appid / concurrent_in_game / peak_in_game
说明：接口不返回游戏名，前端展示时用 data/games.json 里的 appid 映射 name。

实现：用 Python 标准库 urllib（不依赖 requests，开箱即用）；
      如果你装了 requests，等价写法：
      resp = requests.get(URL, timeout=10); data = resp.json()
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

URL = 'https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/'
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
DST = os.path.join(BASE, 'data', 'online_top10.json')
TOP_N = 10  # 只取前10


def fetch_most_played():
    """请求接口并解析 JSON，失败抛异常。"""
    print(f'请求中：{URL}')
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode('utf-8'))
    ranks = body.get('response', {}).get('ranks', [])
    print(f'接口返回 {len(ranks)} 个条目')
    return ranks


def main():
    ranks = fetch_most_played()

    # 取前 TOP_N 名，只保留需要的字段
    # 注意：接口 v1 实际字段为 rank / appid / last_week_rank / peak_in_game，
    #       peak_in_game 即"当前在线人数"；last_week_rank 供前端做"名次升降"动画
    top = []
    for r in ranks[:TOP_N]:
        top.append({
            'rank': r.get('rank'),
            'appid': r.get('appid'),
            'last_week_rank': r.get('last_week_rank'),
            'peak_in_game': r.get('peak_in_game'),
        })

    # 保存：带抓取时间戳（前端显示"数据更新时间"用）
    payload = {
        'fetchedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source': 'Steam GetMostPlayedGames 官方接口',
        'top': top,
    }
    with open(DST, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'已保存 {len(top)} 条到 {DST}')
    for t in top:
        print(f"  #{t['rank']}  appid={t['appid']}  在线人数={t['peak_in_game']}  上周排名={t['last_week_rank']}")

    # 请求频率控制说明：官方接口无 key，也建议至少间隔 60s 以上再调一次，避免限流
    print('\n注意：请求频率控制——本脚本单次调用，若要做定时刷新，建议间隔 ≥60 秒。')


if __name__ == '__main__':
    main()
