/**
 * ============================================================
 *  Steam 实时数据爬虫（教学版）
 * ============================================================
 *  目标：从 Steam 官方公开接口抓取真实游戏数据，
 *        生成 data/games.json + data/meta.json 供前端使用。
 *
 *  运行方式（在项目根目录执行）：
 *      node scripts/crawler.js            完整抓取
 *      node scripts/crawler.js --limit 10 只抓 10 款（快速测试用）
 *
 *  技术要点（第九周学习时对照）：
 *   1. 使用 Node.js 内置 fetch（Node 18+），不需要安装任何第三方库
 *   2. 分 4 步：拿游戏池 -> 抓详情 -> 抓好评率 -> 汇总写文件
 *   3. 爬虫三原则：限速（别把人家服务器打爆）、重试（网络会抖）、
 *      原子写（抓失败不能把旧数据覆盖掉）
 * ============================================================
 */
'use strict';

const fs = require('node:fs');
const path = require('node:path');

// ================== 配置区（想改什么改这里） ==================
const CONFIG = {
  // 伪装成浏览器 UA：部分 Steam 接口会拒绝陌生客户端
  UA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',

  // 单个请求的超时时间（毫秒）
  REQUEST_TIMEOUT_MS: 15000,

  // 单个请求失败后的重试次数
  MAX_RETRY: 2,

  // 重试前的等待时间（毫秒）
  RETRY_DELAY_MS: 1500,

  // 并发批次大小：每批同时发几个请求（4 个比较礼貌）
  BATCH_SIZE: 4,

  // 每批之间的停顿（毫秒）：给 Steam 服务器"喘口气"
  BATCH_DELAY_MS: 600,

  // 游戏池来源：Steam 首页的多个榜单
  POOL_SOURCES: ['top_sellers', 'new_releases', 'specials'],

  // 每个榜单最多取多少个 appid
  MAX_PER_SOURCE: 50,

  // 搜索接口补充池：首页榜单每个只回 10~30 款，搜索接口能一次拿 100 款
  SEARCH_POOLS: [
    { filter: 'topsellers', count: 100, label: '热销' },
    { filter: 'newreleases', count: 100, label: '新品' },
    { filter: 'specials', count: 100, label: '特惠' },
  ],

  // 输出目录（项目根目录下的 data/）
  OUTPUT_DIR: path.join(__dirname, '..', 'data'),
};

// ================== 工具函数 ==================

/** 阻塞等待 ms 毫秒（限速用） */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 从榜单/搜索条目里解析出 appid。
 * 注意：搜索接口返回的 item 只有 name 和 logo 两个字段，
 *       appid 藏在 logo 图片的 URL 里（形如 .../apps/578080/...）。
 */
function extractAppId(item) {
  if (!item) return null;
  if (Number.isInteger(item.id)) return item.id;
  const m = /\/apps\/(\d+)\//.exec(item.logo || '');
  return m ? Number(m[1]) : null;
}

/**
 * 带重试的 JSON 请求
 * 第 1 次失败 -> 等 1.5s 重试 -> 再失败 -> 等 3s 重试 -> 再失败就抛错
 * 调用方决定这个错误是"跳过这一条"还是"整个退出"
 */
async function fetchJson(url, retryLeft = CONFIG.MAX_RETRY) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': CONFIG.UA, Accept: 'application/json' },
      signal: AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT_MS),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    if (retryLeft > 0) {
      console.log(`    ⚠ 请求失败(${err.message})，${CONFIG.RETRY_DELAY_MS}ms 后重试，剩余 ${retryLeft} 次`);
      await sleep(CONFIG.RETRY_DELAY_MS);
      return fetchJson(url, retryLeft - 1);
    }
    throw err;
  }
}

/**
 * 原子写入 JSON 文件
 * 先写到 `xxx.json.tmp`，成功后再改名覆盖正式文件。
 * 这样即使写入中途断电/报错，旧的正式文件也完好无损。
 */
function writeJsonAtomic(filePath, data) {
  const tmpPath = filePath + '.tmp';
  fs.writeFileSync(tmpPath, JSON.stringify(data, null, 2), 'utf-8');
  fs.renameSync(tmpPath, filePath);
}

// ================== 第 1 步：获取游戏池（appid 列表） ==================

/**
 * 从 Steam 官方接口拿一批 appid。
 * 主来源：featuredcategories（首页各榜单），失败则退回 search 接口。
 */
async function getAppIdPool() {
  const pool = new Set();

  // 主来源：首页榜单接口（无需 Key）
  try {
    const data = await fetchJson('https://store.steampowered.com/api/featuredcategories');
    for (const source of CONFIG.POOL_SOURCES) {
      const items = data[source] && data[source].items ? data[source].items : [];
      items.slice(0, CONFIG.MAX_PER_SOURCE).forEach((it) => {
        if (it && Number.isInteger(it.id)) pool.add(it.id);
      });
      console.log(`  [榜单] ${source}: ${items.length} 款`);
    }
  } catch (err) {
    console.log(`  ⚠ 榜单接口失败(${err.message})，改用搜索接口兜底`);
  }

  // 备用来源：搜索接口（filter=topsellers 热销榜）
  if (pool.size === 0) {
    try {
      const data = await fetchJson(
        'https://store.steampowered.com/search/results/?json=1&cc=cn&l=schinese&filter=topsellers&start=0&count=100'
      );
      if (data.items) {
        data.items.forEach((it) => {
          const aid = extractAppId(it);
          if (aid) pool.add(aid);
        });
        console.log(`  [搜索兜底] topsellers: ${data.items.length} 款`);
      }
    } catch (err) {
      console.log(`  ⚠ 搜索兜底也失败(${err.message})`);
    }
  }

  // 补充来源：搜索接口拉更全的榜单（首页榜单只回 10~30 款，这里一次 100 款）
  for (const sp of CONFIG.SEARCH_POOLS) {
    try {
      const data = await fetchJson(
        `https://store.steampowered.com/search/results/?json=1&cc=cn&l=schinese&filter=${sp.filter}&start=0&count=${sp.count}`
      );
      const before = pool.size;
      if (data.items) {
        data.items.forEach((it) => {
          const aid = extractAppId(it);
          if (aid) pool.add(aid);
        });
        console.log(`  [搜索补充] ${sp.label}: 新增 ${pool.size - before} 款`);
      }
    } catch (err) {
      console.log(`  ⚠ 搜索补充[${sp.label}]失败(${err.message})，跳过`);
    }
  }

  // 两个来源全失败 -> 明确退出，绝不写空文件覆盖旧数据
  if (pool.size === 0) {
    throw new Error('游戏池获取失败：Steam 接口当前不可达，已保留上次数据。请稍后重试 npm run crawl');
  }

  const appids = [...pool].sort((a, b) => a - b);
  console.log(`  ✔ 游戏池去重后共 ${appids.length} 款`);
  return appids;
}

// ================== 第 2+3 步：抓单款游戏的详情 + 好评率 ==================

/**
 * 抓取并组装一款游戏的数据。
 * 单个游戏失败不会拖垮整体：返回 { ok:false } 由主流程统计。
 */
async function fetchOneGame(appid) {
  try {
    // ---- 2a. 详情接口 ----
    const detail = await fetchJson(
      `https://store.steampowered.com/api/appdetails?appids=${appid}&cc=cn&l=schinese`
    );
    const d = detail[String(appid)];
    // 有些游戏在国区下架/接口异常，success 为 false，直接跳过
    if (!d || !d.success || !d.data) return { ok: false, appid, error: 'appdetails 无数据' };

    const info = d.data;

    // 只要真正的"游戏"（排除 DLC、软件、视频等，保持数据集干净）
    if (info.type !== 'game') return { ok: false, appid, error: `类型是 ${info.type}，跳过` };

    // 价格：Steam 返回的是"分"，除以 100 转成"元"；免费游戏为 0
    const priceOverview = info.price_overview || {};
    const isFree = info.is_free === true;
    const price = isFree ? 0 : priceOverview.final != null ? Math.round(priceOverview.final / 100) : null;
    const originalPrice = isFree ? 0 : priceOverview.initial != null ? Math.round(priceOverview.initial / 100) : null;

    // 类型：取 genres 第一个作为主分类
    const genres = Array.isArray(info.genres) ? info.genres.map((g) => g.description) : [];

    // 年份：从发行日期字符串里抠出 4 位数字年份
    const dateStr = info.release_date && info.release_date.date ? info.release_date.date : '';
    const yearMatch = /\d{4}/.exec(dateStr);
    const year = yearMatch ? Number(yearMatch[0]) : null;

    const game = {
      appid,
      name: info.name || String(appid),
      price,
      original_price: originalPrice,
      final_price: price,
      discount_percent: priceOverview.discount_percent != null ? priceOverview.discount_percent : 0,
      currency: priceOverview.currency || null,
      rating: null, // 好评率，下面填
      positive: null,
      total_reviews: null,
      type: genres[0] || '未知',
      genres,
      year,
      release_date: dateStr || null,
      url: `https://store.steampowered.com/app/${appid}`,
    };

    // ---- 3. 好评率接口（官方评价汇总）----
    try {
      const reviews = await fetchJson(
        `https://store.steampowered.com/appreviews/${appid}?json=1&language=all&purchase_type=all&num_per_page=0`
      );
      const q = reviews && reviews.query_summary;
      if (q && q.total_reviews > 0) {
        game.positive = q.total_positive;
        game.total_reviews = q.total_reviews;
        // 好评率 = 好评数 / 总数 * 100，保留 1 位小数
        game.rating = Math.round((q.total_positive / q.total_reviews) * 1000) / 10;
      }
    } catch {
      // 好评率失败不致命，rating 保持 null
    }

    return { ok: true, game };
  } catch (err) {
    return { ok: false, appid, error: err.message };
  }
}

// ================== 第 4 步：主流程 ==================

async function main() {
  console.log('========== Steam 爬虫启动 ==========');
  const startTime = Date.now();

  // 支持 --limit N：快速测试只抓 N 款
  const limitArg = process.argv.findIndex((a) => a === '--limit');
  const limit = limitArg > -1 ? Number(process.argv[limitArg + 1]) : 0;

  // 确保输出目录存在
  fs.mkdirSync(CONFIG.OUTPUT_DIR, { recursive: true });

  // 第 1 步：游戏池
  console.log('[1/4] 获取游戏池...');
  let appids = await getAppIdPool();
  if (limit > 0) {
    appids = appids.slice(0, limit);
    console.log(`  （--limit ${limit} 测试模式，只抓前 ${limit} 款）`);
  }

  // 第 2+3 步：分批抓详情 + 好评率
  console.log(`[2/4] 开始抓取 ${appids.length} 款游戏（每批 ${CONFIG.BATCH_SIZE} 个，批间隔 ${CONFIG.BATCH_DELAY_MS}ms）...`);
  const games = [];
  const failed = [];
  for (let i = 0; i < appids.length; i += CONFIG.BATCH_SIZE) {
    const batch = appids.slice(i, i + CONFIG.BATCH_SIZE);
    const results = await Promise.all(batch.map(fetchOneGame)); // 一批内并发
    for (const r of results) {
      if (r.ok) games.push(r.game);
      else failed.push(r);
    }
    if ((i / CONFIG.BATCH_SIZE) % 10 === 0) {
      console.log(`  进度：${Math.min(i + CONFIG.BATCH_SIZE, appids.length)}/${appids.length}，成功 ${games.length}，失败 ${failed.length}`);
    }
    await sleep(CONFIG.BATCH_DELAY_MS); // 批间停顿：礼貌爬取
  }

  // 第 4 步：汇总写文件
  console.log(`[3/4] 汇总：成功 ${games.length}，失败 ${failed.length}（失败不会覆盖已有数据）`);
  games.sort((a, b) => a.appid - b.appid);

  const gamesPath = path.join(CONFIG.OUTPUT_DIR, 'games.json');
  const metaPath = path.join(CONFIG.OUTPUT_DIR, 'meta.json');

  // 元信息：前端用来展示"数据更新时间"
  const meta = {
    fetchedAt: new Date().toISOString(),
    durationSec: Math.round((Date.now() - startTime) / 1000),
    gameCount: games.length,
    poolTotal: appids.length,
    successCount: games.length,
    failCount: failed.length,
    failedAppids: failed.map((f) => f.appid),
    sources: [...CONFIG.POOL_SOURCES, ...CONFIG.SEARCH_POOLS.map((s) => s.label)],
  };

  writeJsonAtomic(gamesPath, games); // 原子写入：旧数据安全
  writeJsonAtomic(metaPath, meta);
  console.log(`[4/4] ✔ 完成！用时 ${meta.durationSec}s`);
  console.log(`      → ${gamesPath}（${games.length} 款游戏）`);
  console.log(`      → ${metaPath}（抓取时间 ${meta.fetchedAt}）`);
}

// 顶层错误兜底：明确报错 + 非 0 退出码（方便定时任务判断成败）
main().catch((err) => {
  console.error(`\n✘ 爬虫失败：${err.message}`);
  process.exit(1);
});
