'use strict';

/* =========================================================
   0. 常量与工具
   ========================================================= */

const PALETTE = ['#c63b2f', '#2f7f74', '#d99b2b', '#7a5aa8', '#4f7d38', '#3f6f8f', '#a9683a', '#8e4b6b', '#6b7a3f', '#b25a3a'];
const RANK_COLORS = ['#d4af37', '#c0c0c0', '#cd7f32', '#2f7f74', '#2f7f74', '#2f7f74', '#8a7f6d', '#8a7f6d', '#8a7f6d', '#8a7f6d'];
const REDUCED = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const state = {
  games: [],
  online: { fetchedAt: '', top: [] },
  meta: null,
  fallback: false,
  // 'api' = 走 server.js 的 /api/*；'snapshot' = 读 js/data.js
  source: 'api',
  sort: { key: 'rating', dir: 'desc' },
};

const $ = (id) => document.getElementById(id);
const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sum(list, pick) {
  return list.reduce((total, item) => total + (Number(pick(item)) || 0), 0);
}

function average(list, pick) {
  return list.length ? sum(list, pick) / list.length : 0;
}

function fmt1(value) {
  return Number(value || 0).toFixed(1);
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN');
}

function formatWan(value) {
  const n = Number(value) || 0;
  if (n >= 10000) {
    const wan = n / 10000;
    return `${wan >= 100 ? wan.toFixed(1) : wan.toFixed(1)}万`;
  }
  return formatNumber(n);
}

function formatPrice(price) {
  const p = Number(price) || 0;
  return p <= 0 ? '免费' : `¥${p}`;
}

function formatDateTime(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  // 项目数据按北京时间展示，显式 +8 小时，避免访问者时区不同导致时间跳变
  const local = new Date(date.getTime() + 8 * 60 * 60 * 1000);
  return local.toISOString().slice(0, 16).replace('T', ' ');
}

function debounce(fn, wait) {
  let timer = null;
  return function debounced(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}

/* =========================================================
   1. 数据接入与字段归一化
   ========================================================= */

async function fetchJson(url, timeout = 4200) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { cache: 'no-store', signal: controller.signal });
    if (!response.ok) throw new Error(`${url} → HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

function readLocalGames() {
  // data.js 里是顶层 const，脚本之间共享词法作用域；用 typeof 防止文件缺失时报错
  return typeof games !== 'undefined' && Array.isArray(games) ? games : [];
}

function readLocalOnline() {
  return typeof online !== 'undefined' && online && Array.isArray(online.top)
    ? online
    : { fetchedAt: '', top: [] };
}

/**
 * 统一 data.js / data/games.json 的字段差异：
 * - genres 数组 → 逗号字符串
 * - discount_percent → discount
 * - final_price / price 取实际售价
 * - 没有 positive 时，用 rating × total_reviews 估算
 */
function normalizeGame(raw) {
  const totalReviews = Number(raw.total_reviews) || 0;
  const rating = Number(raw.rating) || 0;
  const positive = raw.positive != null
    ? Number(raw.positive) || 0
    : Math.round((rating / 100) * totalReviews);
  const genres = Array.isArray(raw.genres)
    ? raw.genres.filter(Boolean).join(',')
    : String(raw.genres || '');

  return {
    appid: Number(raw.appid),
    name: String(raw.name || '未知游戏'),
    price: Number(raw.final_price != null ? raw.final_price : raw.price) || 0,
    discount: clamp(Number(raw.discount_percent != null ? raw.discount_percent : raw.discount) || 0, 0, 100),
    type: String(raw.type || '未知'),
    genres,
    year: Number(raw.year) || 0,
    rating: clamp(rating, 0, 100),
    positive,
    total_reviews: totalReviews,
    url: String(raw.url || `https://store.steampowered.com/app/${raw.appid}/`),
  };
}

function normalizeOnline(raw) {
  const top = (Array.isArray(raw && raw.top) ? raw.top : [])
    .map((item, index) => ({
      rank: Number(item.rank) || index + 1,
      appid: Number(item.appid),
      current_players: Number(
        item.current_players != null ? item.current_players : item.peak_in_game
      ) || 0,
      last_week_rank: item.last_week_rank != null ? Number(item.last_week_rank) : null,
    }))
    .filter((item) => item.appid > 0)
    .sort((a, b) => a.rank - b.rank)
    .slice(0, 10);

  return {
    fetchedAt: String((raw && raw.fetchedAt) || ''),
    source: String((raw && raw.source) || ''),
    top,
  };
}

async function loadData() {
  const localGames = readLocalGames();
  const localOnline = readLocalOnline();
  const results = await Promise.allSettled([
    fetchJson('/api/games'),
    fetchJson('/api/meta'),
    fetchJson('/api/online'),
  ]);

  let rawGames = null;
  let rawMeta = null;
  let rawOnline = null;

  if (results[0].status === 'fulfilled' && Array.isArray(results[0].value) && results[0].value.length) {
    rawGames = results[0].value;
  }
  if (results[1].status === 'fulfilled' && results[1].value) {
    rawMeta = results[1].value;
  }
  if (results[2].status === 'fulfilled' && results[2].value) {
    rawOnline = results[2].value;
  }

  const gamesOk = rawGames && rawGames.length;
  const onlineOk = rawOnline && Array.isArray(rawOnline.top) && rawOnline.top.length;
  state.fallback = !gamesOk || !onlineOk;
  state.source = (gamesOk && onlineOk) ? 'api' : 'snapshot';

  state.games = (gamesOk ? rawGames : localGames).map(normalizeGame).filter((g) => g.appid);
  state.online = normalizeOnline(onlineOk ? rawOnline : localOnline);
  state.meta = rawMeta || null;

  // 后端失败时 body 加 no-motion，CSS 会把卡片直接显示，数字也不再滚动
  if (state.fallback) {
    document.body.classList.add('no-motion');
  }
}

/* =========================================================
   2. 指标计算（全部从 state.games / state.online 实时算）
   ========================================================= */

function computeStats() {
  const games = state.games;
  const totalReviews = sum(games, (g) => g.total_reviews);
  const positive = sum(games, (g) => g.positive);
  const free = games.filter((g) => g.price <= 0);
  const paid = games.filter((g) => g.price > 0);
  const onlineTop = state.online.top;

  const typeMap = new Map();
  for (const game of games) {
    const item = typeMap.get(game.type) || { name: game.type, count: 0, priceSum: 0 };
    item.count += 1;
    item.priceSum += game.price;
    typeMap.set(game.type, item);
  }
  const typeStats = [...typeMap.values()]
    .map((item) => ({
      name: item.name,
      count: item.count,
      avgPrice: item.count ? item.priceSum / item.count : 0,
      share: games.length ? (item.count / games.length) * 100 : 0,
    }))
    .sort((a, b) => b.count - a.count);

  const yearMap = new Map();
  for (const game of games) {
    if (!game.year) continue;
    const item = yearMap.get(game.year) || { year: game.year, count: 0, positive: 0, reviews: 0 };
    item.count += 1;
    item.positive += game.positive;
    item.reviews += game.total_reviews;
    yearMap.set(game.year, item);
  }
  const yearStats = [...yearMap.values()]
    .sort((a, b) => a.year - b.year)
    .map((item) => ({
      year: item.year,
      count: item.count,
      avgRating: item.reviews ? (item.positive / item.reviews) * 100 : 0,
      reviews: item.reviews,
    }));

  const genreMap = new Map();
  for (const game of games) {
    for (const tag of game.genres.split(',').map((s) => s.trim()).filter(Boolean)) {
      genreMap.set(tag, (genreMap.get(tag) || 0) + 1);
    }
  }
  const genreStats = [...genreMap.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  const typeYearMap = new Map();
  for (const game of games) {
    if (!game.year) continue;
    const key = `${game.type}__${game.year}`;
    typeYearMap.set(key, (typeYearMap.get(key) || 0) + 1);
  }

  const top3 = onlineTop.slice(0, 3);
  const top3Players = sum(top3, (item) => item.current_players);
  const onlineTotal = sum(onlineTop, (item) => item.current_players);

  return {
    total: games.length,
    avgPrice: average(games, (g) => g.price),
    paidAvgPrice: average(paid, (g) => g.price),
    weightedRating: totalReviews ? (positive / totalReviews) * 100 : 0,
    arithmeticRating: average(games, (g) => g.rating),
    freeCount: free.length,
    paidCount: paid.length,
    freeShare: games.length ? (free.length / games.length) * 100 : 0,
    typeStats,
    yearStats,
    genreStats,
    typeYearMap,
    onlineTotal,
    top3Share: onlineTotal ? (top3Players / onlineTotal) * 100 : 0,
    reviews: totalReviews,
  };
}

let stats = null;

/* =========================================================
   3. DOM 渲染
   ========================================================= */

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function animateNumber(el, target, decimals = 0) {
  if (!el) return;
  const final = Number(target) || 0;
  if (state.fallback || REDUCED) {
    el.textContent = final.toFixed(decimals);
    return;
  }
  const duration = 800;
  const start = performance.now();
  const from = 0;
  const tick = (now) => {
    const progress = clamp((now - start) / duration, 0, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = (from + (final - from) * eased).toFixed(decimals);
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function renderHeader() {
  const fetchedAt = state.online.fetchedAt;
  const stamp = formatDateTime(fetchedAt);
  setText('update-time', `数据更新：${stamp}`);
  setText('hero-fetched', stamp);

  const tag = $('fallback-tag');
  if (tag) {
    if (!state.fallback) {
      tag.hidden = true;
      tag.textContent = '';
      tag.removeAttribute('title');
    } else {
      tag.hidden = false;
      tag.textContent = `（本地快照模式 · ${stamp}）`;
      tag.title = '未能连接本地服务 /api/*，正在显示 js/data.js 的静态快照；运行 npm start 后访问 http://localhost:8080 可看到实时数据';
    }
  }
}

function renderHero() {
  setText('hero-games', stats.total);
  setText('chip-games', stats.total);
  setText('chip-price', fmt1(stats.avgPrice));
  setText('chip-rating', fmt1(stats.weightedRating));
  setText('chip-free', fmt1(stats.freeShare));
  setText('hero-online', (stats.onlineTotal / 10000).toFixed(1));

  animateNumber($('hero-games'), stats.total, 0);
  animateNumber($('chip-games'), stats.total, 0);
  animateNumber($('chip-price'), stats.avgPrice, 1);
  animateNumber($('chip-rating'), stats.weightedRating, 1);
  animateNumber($('chip-free'), stats.freeShare, 1);
  animateNumber($('hero-online'), stats.onlineTotal / 10000, 1);
}

function onlineName(item) {
  const game = state.games.find((g) => g.appid === item.appid);
  if (game) return game.name;
  const fallback = typeof appNameFallback !== 'undefined' ? appNameFallback[String(item.appid)] : '';
  return fallback || `AppID ${item.appid}`;
}

function renderTop10() {
  const wrap = $('top10-list');
  if (!wrap) return;
  const top = state.online.top.slice(0, 10);
  if (!top.length) {
    wrap.innerHTML = '<p class="table-empty">实时在线数据暂不可用</p>';
    return;
  }
  const max = Math.max(...top.map((item) => item.current_players), 1);
  wrap.innerHTML = top.map((item) => {
    const color = RANK_COLORS[item.rank - 1] || RANK_COLORS[9];
    const width = Math.max(2, (item.current_players / max) * 100);
    const name = onlineName(item);
    const last = item.last_week_rank;
    const trend = last == null ? 'flat' : item.rank < last ? 'up' : item.rank > last ? 'down' : 'flat';
    const arrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—';
    const trendTitle = last == null ? '上周排名未知' : `上周第 ${last} 名`;
    return `
      <div class="top10__row" title="${escapeHtml(name)} · 当前在线 ${formatNumber(item.current_players)} 人">
        <span class="medal medal--${item.rank}">${String(item.rank).padStart(2, '0')}</span>
        <span class="top10__name">${escapeHtml(name)}</span>
        <span class="top10__bar"><i style="width:${width}%;background:${color}"></i></span>
        <span class="top10__players">${formatWan(item.current_players)}</span>
        <span class="top10__trend top10__trend--${trend}" title="${trendTitle}">${arrow}</span>
        <span class="top10__dot" aria-hidden="true"></span>
      </div>`;
  }).join('');
}

const PRICE_BANDS = [
  { label: '免费', min: 0, max: 0 },
  { label: '1–30 元', min: 1, max: 30 },
  { label: '31–60 元', min: 31, max: 60 },
  { label: '61–100 元', min: 61, max: 100 },
  { label: '101–200 元', min: 101, max: 200 },
  { label: '200+ 元', min: 201, max: Infinity },
];

function renderPriceWall() {
  const wrap = $('price-wall');
  if (!wrap) return;
  wrap.innerHTML = PRICE_BANDS.map((band) => {
    const games = state.games.filter((g) => g.price >= band.min && g.price <= band.max);
    const discounts = games.map((g) => g.discount).filter((d) => d > 0).sort((a, b) => b - a);
    const visible = Math.min(games.length, 12);
    const badges = [];

    for (let i = 0; i < visible; i += 1) {
      const discount = discounts[i];
      const text = discount ? `-${discount}%` : (band.min === 0 ? 'FREE' : '原价');
      const plain = discount ? '' : ' discount-badge--plain';
      badges.push(`<span class="discount-badge${plain}">${text}</span>`);
    }
    if (games.length > visible) {
      badges.push(`<span class="discount-badge discount-badge--more">+${games.length - visible}</span>`);
    }

    return `
      <div class="price-band">
        <div class="price-band__badges">${badges.join('')}</div>
        <div class="price-band__name">${band.label}</div>
        <div class="price-band__count">${games.length}<small> 款</small></div>
      </div>`;
  }).join('');
}

const RATING_BANDS = [
  { label: '好评如潮', min: 95, max: 100, bg: '#1f6f4a' },
  { label: '特别好评', min: 80, max: 94.999, bg: '#4c9a2a', light: true },
  { label: '多半好评', min: 70, max: 79.999, bg: '#9ab52f', light: true },
  { label: '褒贬不一', min: 40, max: 69.999, bg: '#c47a24' },
  { label: '差评', min: 0, max: 39.999, bg: '#a83b38' },
];

function renderRatingWall() {
  const wrap = $('rating-wall');
  if (!wrap) return;
  wrap.innerHTML = RATING_BANDS.map((band) => {
    const count = state.games.filter((g) => g.rating >= band.min && g.rating <= band.max).length;
    return `
      <div class="rating-tag ${band.light ? 'rating-tag--light' : ''}" style="--tag-bg:${band.bg}" title="${band.label}：${count} 款">
        <span class="rating-tag__label">${band.label}</span>
        <span class="rating-tag__count">${count}<small> 款</small></span>
      </div>`;
  }).join('');
}

function findGame(...keywords) {
  return state.games.find((game) => keywords.some((keyword) => game.name.includes(keyword)));
}

function renderCases() {
  const wrap = $('case-grid');
  if (!wrap) return;
  const cases = [
    { game: findGame('Stardew', '星露谷'), label: '星露谷', tag: '口碑天花板', color: '#9bff3d' },
    { game: findGame('博德之门3', 'Baldur'), label: '博德之门3', tag: '高分神作', color: '#2f7f74' },
    { game: findGame('都市：天际线2', '城市天际线2', 'Cities: Skylines'), label: '城市天际线2', tag: '在线高但口碑争议', color: '#d99b2b' },
    { game: findGame('PUBG'), label: 'PUBG', tag: '流量大但好评不高', color: '#e25d5d' },
  ];
  wrap.innerHTML = cases.map((item) => {
    const game = item.game;
    if (!game) return '';
    return `
      <div class="case-card" style="--case-color:${item.color}">
        <div class="case-card__name">${escapeHtml(item.label)}</div>
        <div class="case-card__score">${fmt1(game.rating)}</div>
        <div class="case-card__tag">${item.tag}</div>
      </div>`;
  }).join('');
}

/* =========================================================
   4. 明细表：一次渲染、前端筛选/排序
   ========================================================= */

function fillTypeFilter() {
  const select = $('type-filter');
  if (!select) return;
  const types = [...new Set(state.games.map((g) => g.type))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
  select.innerHTML = '<option value="">全部类型</option>' + types
    .map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`)
    .join('');
}

function tableRows() {
  const type = ($('type-filter') && $('type-filter').value) || '';
  const keyword = ($('search-input') && $('search-input').value.trim().toLowerCase()) || '';
  const rows = state.games.filter((game) => {
    if (type && game.type !== type) return false;
    if (keyword && !game.name.toLowerCase().includes(keyword)) return false;
    return true;
  });

  const { key, dir } = state.sort;
  const factor = dir === 'asc' ? 1 : -1;
  rows.sort((a, b) => {
    if (key === 'name' || key === 'type') {
      return a[key].localeCompare(b[key], 'zh-CN') * factor;
    }
    return ((Number(a[key]) || 0) - (Number(b[key]) || 0)) * factor;
  });
  return rows;
}

function renderTable() {
  const tbody = $('games-tbody');
  if (!tbody) return;
  const rows = tableRows();
  setText('table-count', `${rows.length} 款`);

  tbody.innerHTML = rows.length
    ? rows.map((game) => `
      <tr>
        <td title="${escapeHtml(game.name)}">${escapeHtml(game.name)}</td>
        <td>${escapeHtml(game.type)}</td>
        <td>${formatPrice(game.price)}</td>
        <td>${fmt1(game.rating)}</td>
        <td>${formatNumber(game.total_reviews)}</td>
        <td>${game.year || '—'}</td>
      </tr>`).join('')
    : '<tr><td class="table-empty" colspan="6">没有匹配的游戏</td></tr>';

  const table = $('games-table');
  if (table) {
    table.querySelectorAll('th button').forEach((button) => {
      const active = button.dataset.sort === state.sort.key;
      button.setAttribute('aria-sort', active ? (state.sort.dir === 'asc' ? 'ascending' : 'descending') : 'none');
    });
  }
}

function bindTable() {
  const typeFilter = $('type-filter');
  const search = $('search-input');
  if (typeFilter) typeFilter.addEventListener('change', renderTable);
  if (search) search.addEventListener('input', debounce(renderTable, 120));

  const table = $('games-table');
  if (table) {
    table.querySelectorAll('th button').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.dataset.sort;
        if (state.sort.key === key) {
          state.sort.dir = state.sort.dir === 'asc' ? 'desc' : 'asc';
        } else {
          state.sort = { key, dir: key === 'name' || key === 'type' ? 'asc' : 'desc' };
        }
        renderTable();
      });
    });
  }

  const toggle = $('table-toggle');
  const wrap = $('table-wrap');
  if (toggle && wrap) {
    toggle.addEventListener('click', () => {
      const open = wrap.hidden;
      wrap.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.innerHTML = open
        ? '收起游戏明细 <span aria-hidden="true">↑</span>'
        : '查看全部 123 款游戏明细 <span aria-hidden="true">→</span>';
      if (open) wrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
}

/* =========================================================
   5. ECharts：只保留 4 张真正需要图的图
   ========================================================= */

const charts = {};

function chartBase() {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif', color: '#6f604c' },
    tooltip: {
      backgroundColor: 'rgba(248, 239, 217, 0.98)',
      borderColor: '#211c15',
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: '#211c15', fontSize: 12 },
      extraCssText: 'box-shadow:4px 4px 0 rgba(33,28,21,.18);',
    },
  };
}

function initCharts() {
  if (typeof echarts === 'undefined') return;
  const rose = $('chart-type-rose');
  const trend = $('chart-trend');
  const wordcloud = $('chart-wordcloud');
  const heatmap = $('chart-heatmap');

  if (rose) charts.rose = echarts.init(rose);
  if (trend) charts.trend = echarts.init(trend);
  if (wordcloud) charts.wordcloud = echarts.init(wordcloud);
  if (heatmap) charts.heatmap = echarts.init(heatmap);
}

function renderRose() {
  if (!charts.rose) return;
  const data = stats.typeStats.map((item) => ({
    name: item.name,
    value: item.count,
    share: item.share,
  }));

  charts.rose.setOption({
    ...chartBase(),
    color: PALETTE,
    tooltip: {
      ...chartBase().tooltip,
      trigger: 'item',
      formatter: (params) => `${params.name}<br/>游戏数：${params.value} 款<br/>占比：${params.percent}%`,
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      left: 0,
      top: 'center',
      itemWidth: 8,
      itemHeight: 8,
      itemGap: 10,
      textStyle: { color: '#6f604c', fontSize: 11 },
      pageTextStyle: { color: '#6f604c' },
    },
    series: [{
      name: '类型数量',
      type: 'pie',
      radius: ['38%', '64%'],
      center: ['59%', '50%'],
      roseType: 'radius',
      avoidLabelOverlap: true,
      itemStyle: { borderColor: '#f8efd9', borderWidth: 2 },
      label: { show: false },
      emphasis: {
        scale: true,
        scaleSize: 5,
        label: {
          show: true,
          color: '#eaf3fa',
          fontSize: 12,
          fontWeight: 700,
          formatter: '{b}\n{c} 款',
        },
      },
      data,
    }],
  }, true);
}

function renderTrend() {
  if (!charts.trend) return;
  const years = stats.yearStats.map((item) => item.year);
  const counts = stats.yearStats.map((item) => item.count);
  const ratings = stats.yearStats.map((item) => Number(fmt1(item.avgRating)));

  charts.trend.setOption({
    ...chartBase(),
    color: ['#2f7f74', '#c63b2f'],
    tooltip: {
      ...chartBase().tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(102,192,244,.06)' } },
      formatter: (params) => {
        const year = params[0].axisValue;
        const bar = params.find((p) => p.seriesName === '上架数量');
        const line = params.find((p) => p.seriesName === '加权好评率');
        return `${year} 年<br/>上架：${bar ? bar.value : 0} 款<br/>加权好评率：${line ? line.value : '—'}%`;
      },
    },
    legend: {
      top: 0,
      left: 'center',
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { color: '#6f604c', fontSize: 11 },
      data: ['上架数量', '加权好评率'],
    },
    grid: { left: 44, right: 56, top: 44, bottom: 34 },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: 'rgba(33,28,21,.28)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6f604c', fontSize: 10, interval: 0 },
    },
    yAxis: [
      {
        type: 'value',
        name: '款',
        nameTextStyle: { color: '#5f7489', fontSize: 10, padding: [0, 0, 4, 0] },
        min: 0,
        max: 50,
        splitLine: { lineStyle: { color: 'rgba(33,28,21,.10)' } },
        axisLabel: { color: '#6f604c', fontSize: 10 },
      },
      {
        type: 'value',
        name: '好评率 %',
        nameTextStyle: { color: '#5f7489', fontSize: 10, padding: [0, 0, 4, 0] },
        min: 60,
        max: 100,
        splitLine: { show: false },
        axisLabel: { color: '#6f604c', fontSize: 10, formatter: '{value}' },
      },
    ],
    series: [
      {
        name: '上架数量',
        type: 'bar',
        data: counts,
        barWidth: 12,
        itemStyle: {
          borderRadius: [2, 2, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#7fb7a8' },
            { offset: 1, color: '#2f7f74' },
          ]),
        },
        emphasis: { itemStyle: { color: '#a8d4c7' } },
      },
      {
        name: '加权好评率',
        type: 'line',
        yAxisIndex: 1,
        data: ratings,
        smooth: false,
        connectNulls: false,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: '#c63b2f' },
        itemStyle: { color: '#c63b2f', borderColor: '#f8efd9', borderWidth: 2 },
        emphasis: { scale: 1.5 },
      },
    ],
  }, true);
}

function renderWordcloud() {
  if (!charts.wordcloud) return;
  charts.wordcloud.setOption({
    ...chartBase(),
    tooltip: {
      ...chartBase().tooltip,
      formatter: (params) => `${params.name}<br/>出现次数：${params.value} 次`,
    },
    series: [{
      type: 'wordCloud',
      shape: 'circle',
      left: 'center',
      top: 'center',
      width: '98%',
      height: '94%',
      sizeRange: [15, 62],
      rotationRange: [-30, 30],
      rotationStep: 15,
      gridSize: 4,
      drawOutOfBound: false,
      textStyle: {
        fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
        fontWeight: 700,
        color: (params) => PALETTE[params.dataIndex % PALETTE.length],
      },
      emphasis: {
        textStyle: {
          textShadowBlur: 12,
          textShadowColor: 'rgba(102, 192, 244, 0.45)',
        },
      },
      data: stats.genreStats.map((item) => ({ name: item.name, value: item.count })),
    }],
  }, true);
}

function renderHeatmap() {
  if (!charts.heatmap) return;
  const years = Array.from({ length: 2026 - 2009 + 1 }, (_, i) => 2009 + i);
  const types = stats.typeStats.map((item) => item.name);
  const cells = [];
  let maxValue = 1;

  for (let y = 0; y < types.length; y += 1) {
    for (let x = 0; x < years.length; x += 1) {
      const value = stats.typeYearMap.get(`${types[y]}__${years[x]}`) || 0;
      maxValue = Math.max(maxValue, value);
      cells.push([x, y, value]);
    }
  }

  charts.heatmap.setOption({
    ...chartBase(),
    tooltip: {
      ...chartBase().tooltip,
      formatter: (params) => {
        const [x, y, value] = params.value;
        return `${types[y]} · ${years[x]} 年<br/>游戏数：${value} 款`;
      },
    },
    grid: { left: 64, right: 44, top: 10, bottom: 46 },
    xAxis: {
      type: 'category',
      data: years,
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(33,28,21,.28)' } },
      axisTick: { show: false },
      axisLabel: { color: '#6f604c', fontSize: 9, rotate: 45 },
    },
    yAxis: {
      type: 'category',
      data: types,
      inverse: true,
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(33,28,21,.32)' } },
      axisTick: { show: false },
      axisLabel: { color: '#3a3227', fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max: Math.max(8, maxValue),
      calculable: false,
      orient: 'vertical',
      right: 0,
      top: 'center',
      itemWidth: 10,
      itemHeight: 110,
      itemGap: 8,
      textStyle: { color: '#6f604c', fontSize: 9 },
      inRange: {
        color: ['#efe0c4', '#e3cda6', '#d3b17a', '#c48c52', '#bd6338', '#a83f2b', '#7f2118'],
      },
    },
    series: [{
      name: '类型 × 年份',
      type: 'heatmap',
      data: cells,
      label: {
        show: true,
        fontSize: 9,
        formatter: (params) => {
          const value = params.value[2];
          if (value < 5) return '';
          return value >= 12 ? `{w|${value}}` : `{d|${value}}`;
        },
        rich: {
          w: { color: '#f8efd9', fontSize: 9, fontWeight: 700 },
          d: { color: '#211c15', fontSize: 9, fontWeight: 700 },
        },
      },
      itemStyle: { borderColor: '#d8c7ab', borderWidth: 1 },
      emphasis: {
        itemStyle: { borderColor: '#211c15', borderWidth: 1, shadowBlur: 6, shadowColor: 'rgba(198,59,47,.25)' },
      },
    }],
  }, true);
}

function resizeCharts() {
  Object.values(charts).forEach((chart) => {
    if (chart && !chart.isDisposed()) chart.resize();
  });
}

/* =========================================================
   6. 章节入场与图表尺寸
   ========================================================= */

function observeSections() {
  const sections = [...document.querySelectorAll('.chapter, .annual')];
  if (!('IntersectionObserver' in window) || state.fallback || REDUCED) {
    sections.forEach((section) => section.classList.add('is-in'));
    requestAnimationFrame(resizeCharts);
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      requestAnimationFrame(resizeCharts);
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

  sections.forEach((section) => observer.observe(section));
}

/* =========================================================
   7. 启动
   ========================================================= */

function renderAll() {
  stats = computeStats();
  renderHeader();
  renderHero();
  renderTop10();
  renderPriceWall();
  renderRatingWall();
  renderCases();
  fillTypeFilter();
  renderTable();
  bindTable();
  initCharts();
  renderRose();
  renderTrend();
  renderWordcloud();
  renderHeatmap();
  observeSections();

  // 年度海报里的 123 也参与数字动画
  const annualNumber = document.querySelector('.annual__title strong[data-count]');
  if (annualNumber) animateNumber(annualNumber, stats.total, 0);
}

/* 顶栏导航：按当前滚动章节切换高亮 */
function initNavSpy() {
  const links = Array.from(document.querySelectorAll('.topnav__link'));
  const sections = ['chapter-reviews', 'chapter-trends']
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  if (!links.length || !sections.length) return;

  const update = () => {
    const marker = window.scrollY + 150;
    let activeHash = '#top';
    sections.forEach((section) => {
      if (section.offsetTop <= marker) activeHash = `#${section.id}`;
    });
    links.forEach((link) => {
      const on = link.getAttribute('href') === activeHash;
      link.classList.toggle('is-active', on);
      if (on) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
  };

  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(() => {
      update();
      ticking = false;
    });
  }, { passive: true });
  window.addEventListener('resize', update);
  update();
}

async function boot() {
  try {
    await loadData();
    renderAll();
    initNavSpy();
  } catch (error) {
    // 极端情况：data.js 也缺失时，至少把错误暴露在页面上
    document.body.classList.add('no-motion');
    setText('update-time', '数据加载失败');
    const tag = $('fallback-tag');
    if (tag) {
      tag.hidden = false;
      tag.textContent = '（数据不可用）';
    }
    console.error('[Steam insight] 初始化失败', error);
  }
}

window.addEventListener('resize', debounce(resizeCharts, 160));
window.addEventListener('load', resizeCharts);

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
