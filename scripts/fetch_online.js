/**
 * 只刷新 data/online.json 的独立脚本。
 * 抓取顺序与 scripts/crawler.js 的 fetchOnlineTop() 一致：
 *   ① 有 STEAM_API_KEY 时用 GetMostPlayedGames API
 *   ② 否则抓 mostplayed HTML 的前 10 个 appid
 *   ③ 逐个请求 GetNumberOfCurrentPlayers 取“当前在线”
 *
 * 运行：node scripts/fetch_online.js
 * 失败：console.error 后 exit(1)，不覆盖旧的 data/online.json。
 */
'use strict';

const fs = require('node:fs');
const net = require('node:net');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

// ================== 配置区（与 crawler.js 保持一致） ==================
const CONFIG = {
  UA: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
  REQUEST_TIMEOUT_MS: 20000,
  MAX_RETRY: 3,
  RETRY_DELAY_MS: 2000,
  OUTPUT_FILE: path.join(__dirname, '..', 'data', 'online.json'),
  PROXY_PORT: 7897,
};

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** 带重试的 JSON 请求（从 crawler.js 原样复制） */
async function fetchJson(url, retryLeft = CONFIG.MAX_RETRY) {
  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': CONFIG.UA, Accept: 'application/json' },
      signal: AbortSignal.timeout(CONFIG.REQUEST_TIMEOUT_MS),
    });
    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}`);
      err.status = res.status;
      err.retryAfter = Number(res.headers.get('retry-after')) || 0;
      throw err;
    }
    return await res.json();
  } catch (err) {
    if (retryLeft > 0) {
      const backoff = err.status === 429 && err.retryAfter > 0
        ? err.retryAfter * 1000
        : CONFIG.RETRY_DELAY_MS * Math.pow(2, CONFIG.MAX_RETRY - retryLeft);
      const wait = Math.min(backoff, 30000);
      console.log(`    ⚠ 请求失败(${err.message})，${wait}ms 后重试，剩余 ${retryLeft} 次`);
      await sleep(wait);
      return fetchJson(url, retryLeft - 1);
    }
    throw err;
  }
}

/** 带重试的文本请求（从 crawler.js 原样复制） */
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
      const wait = CONFIG.RETRY_DELAY_MS * Math.pow(2, CONFIG.MAX_RETRY - retryLeft);
      console.log(`    ⚠ 榜单页面失败(${err.message})，${wait}ms 后重试，剩余 ${retryLeft} 次`);
      await sleep(wait);
      return fetchText(url, retryLeft - 1);
    }
    throw err;
  }
}

/** 原子写入：先写 .tmp，再 rename；失败不会动旧文件 */
function writeJsonAtomic(filePath, data) {
  const tmpPath = filePath + '.tmp';
  fs.writeFileSync(tmpPath, JSON.stringify(data, null, 2), 'utf-8');
  fs.renameSync(tmpPath, filePath);
}

/** 抓 TOP10，与 crawler.js 的 fetchOnlineTop() 保持一致 */
async function fetchOnlineTop() {
  const apiKey = process.env.STEAM_API_KEY;
  let ids = [];

  if (apiKey) {
    try {
      const url = `https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/?key=${encodeURIComponent(apiKey)}`;
      const data = await fetchJson(url);
      const ranks = data && data.response && Array.isArray(data.response.ranks) ? data.response.ranks : [];
      ids = [...new Set(ranks.map((item) => Number(item.appid)).filter(Boolean))].slice(0, 10);
      if (ids.length === 10) {
        console.log('    [在线榜] 使用 GetMostPlayedGames API');
      } else {
        ids = [];
      }
    } catch (err) {
      console.log(`    ⚠ GetMostPlayedGames 失败：${err.message}，改用 HTML 榜单`);
    }
  } else {
    console.log('    [在线榜] 未配置 STEAM_API_KEY，跳过官方 API，使用 HTML 榜单');
  }

  if (ids.length < 10) {
    const html = await fetchText('https://store.steampowered.com/charts/mostplayed?cc=cn&l=schinese');
    ids = [...new Set([...html.matchAll(/\/apps\/(\d+)/g)].map((m) => Number(m[1])))].slice(0, 10);
  }

  if (ids.length < 10) {
    throw new Error(`mostplayed 榜单只解析到 ${ids.length} 个 appid，页面结构可能变了`);
  }

  const top = [];
  for (let i = 0; i < ids.length; i += 1) {
    const appid = ids[i];
    let current = null;
    try {
      const data = await fetchJson(
        `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=${appid}&format=json`
      );
      if (data && data.response && data.response.result === 1) {
        current = Number(data.response.player_count);
      }
    } catch (err) {
      console.log(`    ⚠ 在线人数获取失败 appid ${appid}：${err.message}`);
    }
    top.push({
      rank: i + 1,
      appid,
      current_players: Number.isFinite(current) ? current : null,
    });
    console.log(`    ${i + 1}/10 appid ${appid}: ${Number.isFinite(current) ? current : '失败'}`);
  }

  if (top.every((x) => x.current_players == null)) {
    throw new Error('TOP10 的在线人数全部获取失败');
  }

  return {
    fetchedAt: new Date().toISOString(),
    source: 'Steam charts + GetNumberOfCurrentPlayers',
    top,
  };
}

/** 检测 Clash 代理端口是否已监听（用于失败后的代理重试） */
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
  });
}

/**
 * 直连失败后，如果 127.0.0.1:7897 可用，用 Node 的 --use-env-proxy
 * 带着代理重跑一次；子进程带 FETCH_ONLINE_PROXY=1，避免无限递归。
 */
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
}

main().catch(async (err) => {
  console.error(`[fetch_online] 直连失败：${err.message}`);
  await retryWithProxy();
  console.error('[fetch_online] 未写入 data/online.json，旧快照保持不变');
  process.exit(1);
});
