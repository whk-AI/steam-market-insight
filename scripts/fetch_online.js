/**
 * 只刷新 data/online.json 的独立脚本。
 *
 * 数据源优先级：
 *   ① Steam 官方榜单接口 ISteamChartsService/GetMostPlayedGames/v1/（不需要 API key）
 *      返回 rank / appid / last_week_rank / peak_in_game，直接就是完整榜单
 *   ② 接口失败时退回商店 mostplayed 页面解析（精确取榜单表格里的行）
 *
 * 名字：用 store 的 appdetails 接口批量补（一请求拿 10 个），补不到就留空。
 *
 * 运行：node scripts/fetch_online.js
 * 失败：console.error 后 exit(1)，不覆盖旧的 data/online.json。
 */
'use strict';

const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const readline = require('node:readline');
const { spawnSync } = require('node:child_process');

const CONFIG = {
  UA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
  REQUEST_TIMEOUT_MS: 20000,
  MAX_RETRY: 3,
  RETRY_DELAY_MS: 2000,
  OUTPUT_FILE: path.join(__dirname, '..', 'data', 'online.json'),
  PROXY_PORT: 7897,
  TOP_N: 30,
  MIN_TOP: 10,
  CHARTS_API: 'https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/',
  CHARTS_PAGE: 'https://store.steampowered.com/charts/mostplayed?cc=cn&l=schinese',
  APPDETAILS: 'https://store.steampowered.com/api/appdetails',
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchJson(url, retryLeft = CONFIG.MAX_RETRY) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': CONFIG.UA, Accept: 'application/json' },
      signal: AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT_MS),
    });
    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    return await res.json();
  } catch (err) {
    if (retryLeft > 0) {
      const wait = Math.min(CONFIG.RETRY_DELAY_MS * Math.pow(2, CONFIG.MAX_RETRY - retryLeft), 30000);
      console.log(`    ⚠ 请求失败(${err.message})，${wait}ms 后重试，剩余 ${retryLeft} 次`);
      await sleep(wait);
      return fetchJson(url, retryLeft - 1);
    }
    throw err;
  }
}

async function fetchText(url, retryLeft = CONFIG.MAX_RETRY) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': CONFIG.UA, Accept: 'text/html,application/xhtml+xml' },
      signal: AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT_MS),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.text();
  } catch (err) {
    if (retryLeft > 0) {
      const wait = Math.min(CONFIG.RETRY_DELAY_MS * Math.pow(2, CONFIG.MAX_RETRY - retryLeft), 30000);
      console.log(`    ⚠ 榜单页面失败(${err.message})，${wait}ms 后重试，剩余 ${retryLeft} 次`);
      await sleep(wait);
      return fetchText(url, retryLeft - 1);
    }
    throw err;
  }
}

function writeJsonAtomic(filePath, data) {
  const tmpPath = filePath + '.tmp';
  fs.writeFileSync(tmpPath, JSON.stringify(data, null, 2), 'utf-8');
  fs.renameSync(tmpPath, filePath);
}

/** ① 官方榜单接口：不需要 key，直接返回完整 rank 列表 */
async function fetchFromChartsApi() {
  const data = await fetchJson(CONFIG.CHARTS_API);
  const ranks = data && data.response && Array.isArray(data.response.ranks) ? data.response.ranks : [];
  if (ranks.length < CONFIG.MIN_TOP) {
    throw new Error(`官方榜单只返回 ${ranks.length} 条`);
  }
  return ranks.slice(0, CONFIG.TOP_N).map((r, i) => ({
    rank: Number(r.rank) || i + 1,
    appid: Number(r.appid),
    last_week_rank: r.last_week_rank == null ? null : Number(r.last_week_rank),
    peak_in_game: Number(r.peak_in_game) || null,
    current_players: null,
  }));
}

/** ② 兜底：解析 mostplayed 页面里的榜单表格行，只取表格内的 appid */
async function fetchFromChartsPage() {
  const html = await fetchText(CONFIG.CHARTS_PAGE);
  // 榜单表格的每一次排名都带 /apps/<id>/ 链接，先把所有 id 抓出来再去重
  const ids = [...new Set([...html.matchAll(/\/apps\/(\d+)/g)].map((m) => Number(m[1])))];
  if (ids.length < CONFIG.MIN_TOP) throw new Error(`页面只解析到 ${ids.length} 个 appid`);
  return ids.slice(0, CONFIG.TOP_N).map((appid, i) => ({
    rank: i + 1,
    appid,
    last_week_rank: null,
    peak_in_game: null,
    current_players: null,
  }));
}

/** 用 appdetails 批量补名字，一次请求拿全部 */
async function fillNames(top) {
  const want = new Set(top.map((t) => t.appid));
  const found = new Map();
  const csvPath = path.join(__dirname, '..', 'data', 'market', 'market_full.csv');

  if (fs.existsSync(csvPath)) {
    const rl = readline.createInterface({ input: fs.createReadStream(csvPath, 'utf8'), crlfDelay: Infinity });
    let first = true;
    for await (const line of rl) {
      if (first) { first = false; continue; }
      const cells = parseCsvLine(line);
      const id = Number((cells[0] || '').replace(/^\uFEFF/, ''));
      if (want.has(id) && !found.has(id)) {
        found.set(id, cells[1] || '');
        if (found.size === want.size) { rl.close(); break; }
      }
    }
  }

  for (const item of top) item.name = found.get(item.appid) || '';

  // 库里没有的新游（2026 年发售），逐个问 appdetails，失败就留空
  for (const item of top.filter((t) => !t.name)) {
    try {
      const d = await fetchJson(`${CONFIG.APPDETAILS}?appids=${item.appid}&l=schinese&cc=cn`, 1);
      const e = d && d[String(item.appid)];
      if (e && e.success && e.data && e.data.name) item.name = e.data.name;
    } catch (err) {
      console.log(`    ⚠ appid ${item.appid} 名字没查到：${err.message}`);
    }
  }
  return top;
}

/** 单行 CSV 解析，处理双引号和 "" 转义 */
function parseCsvLine(line) {
  const out = [];
  let cur = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') { cur += '"'; i += 1; } else { quoted = false; }
      } else cur += ch;
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      out.push(cur); cur = '';
    } else cur += ch;
  }
  out.push(cur);
  return out;
}

/** ③ 逐款查当前在线；404/无数据保留 null，不拿 peak 冒充当前。 */
async function fillCurrentPlayers(top) {
  for (const item of top) {
    try {
      const d = await fetchJson(
        `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=${item.appid}&format=json`,
        1
      );
      if (d && d.response && d.response.result === 1) {
        item.current_players = Number(d.response.player_count);
      }
    } catch (err) {
      console.log(`    ⚠ appid ${item.appid} 当前在线没查到：${err.message}`);
    }
  }
  return top;
}

async function fetchOnlineTop() {
  let top = null;
  try {
    top = await fetchFromChartsApi();
    console.log('    [在线榜] 使用官方 GetMostPlayedGames 接口');
  } catch (err) {
    console.log(`    ⚠ 官方接口失败：${err.message}，退回商店页面解析`);
    top = await fetchFromChartsPage();
  }

  await fillNames(top);
  await fillCurrentPlayers(top);

  const named = top.filter((t) => t.current_players != null).length;
  if (named === 0) throw new Error('TOP10 的在线人数全部为空');

  return {
    fetchedAt: new Date().toISOString(),
    source: 'Steam GetMostPlayedGames + GetNumberOfCurrentPlayers（当前在线）',
    top,
  };
}

function isProxyReady() {
  return new Promise((resolve) => {
    const socket = net.connect({ host: '127.0.0.1', port: CONFIG.PROXY_PORT });
    const timer = setTimeout(() => {
      socket.destroy();
      resolve(false);
    }, 600);
    socket.once('connect', () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(true);
    });
    socket.once('error', () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => resolve(false));
  });
}

async function retryWithProxy() {
  if (process.env.FETCH_ONLINE_PROXY === '1') return false;
  if (!(await isProxyReady())) return false;

  console.log('    检测到 127.0.0.1:7897，改用代理重试一次…');
  const result = spawnSync(process.execPath, ['--use-env-proxy', __filename], {
    stdio: 'inherit',
    env: {
      ...process.env,
      FETCH_ONLINE_PROXY: '1',
      HTTPS_PROXY: `http://127.0.0.1:${CONFIG.PROXY_PORT}`,
      HTTP_PROXY: `http://127.0.0.1:${CONFIG.PROXY_PORT}`,
      NO_PROXY: '127.0.0.1,localhost',
    },
  });
  process.exit(result.status == null ? 1 : result.status);
}

async function main() {
  console.log('[fetch_online] 只刷新 data/online.json，不抓游戏详情');
  const online = await fetchOnlineTop();
  writeJsonAtomic(CONFIG.OUTPUT_FILE, online);
  console.log(`[fetch_online] 已写入 ${CONFIG.OUTPUT_FILE}`);
  console.log(`[fetch_online] fetchedAt=${online.fetchedAt}，top=${online.top.length}`);
  for (const t of online.top) {
    console.log(`  #${t.rank} ${t.appid} ${t.name || '（无名字）'} ${t.current_players == null ? '—' : t.current_players}`);
  }
}

main().catch(async (err) => {
  console.error(`[fetch_online] 直连失败：${err.message}`);
  await retryWithProxy();
  console.error('[fetch_online] 未写入 data/online.json，旧快照保持不变');
  process.exit(1);
});
