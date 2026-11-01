'use strict';

/* =========================================================
   口碑分析 / 市场趋势 共用的数据与工具层
   - 优先读 server.js 的 /api/games
   - 失败时回退到 data.js 的窗口变量，双击 file:// 也能看
   ========================================================= */
(function () {
  const RATING_BANDS = [
    { key: 'masterpiece', label: '好评如潮', short: '95+', min: 95, max: 100.1, color: '#1f6f4a', light: false },
    { key: 'very-positive', label: '特别好评', short: '80–95', min: 80, max: 95, color: '#4c9a2a', light: true },
    { key: 'mostly-positive', label: '多半好评', short: '70–80', min: 70, max: 80, color: '#c3a227', light: true },
    { key: 'mixed', label: '褒贬不一', short: '40–70', min: 40, max: 70, color: '#c47a24', light: false },
    { key: 'negative', label: '差评', short: '<40', min: 0, max: 40, color: '#a83b38', light: false },
  ];

  const PALETTE = ['#c63b2f', '#2f7f74', '#d99b2b', '#7a5aa8', '#4f7d38', '#3f6f8f', '#a9683a', '#8e4b6b', '#6b7a3f', '#b25a3a'];

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

  function fmt1(value) {
    return Number(value || 0).toFixed(1);
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString('zh-CN');
  }

  function formatWan(value) {
    const n = Number(value) || 0;
    if (n >= 10000) return `${(n / 10000).toFixed(1)}万`;
    return formatNumber(n);
  }

  function formatPrice(value) {
    const n = Number(value) || 0;
    return n <= 0 ? '免费' : `¥${n}`;
  }

  function formatDateTime(iso) {
    const date = new Date(iso);
    if (!iso || Number.isNaN(date.getTime())) return '—';
    const local = new Date(date.getTime() + 8 * 60 * 60 * 1000);
    return local.toISOString().slice(0, 16).replace('T', ' ');
  }

  function average(list, pick) {
    return list.length ? list.reduce((s, item) => s + (Number(pick(item)) || 0), 0) / list.length : 0;
  }

  function sum(list, pick) {
    return list.reduce((s, item) => s + (Number(pick(item)) || 0), 0);
  }

  function weightedRating(list) {
    const reviews = sum(list, (g) => g.total_reviews);
    return reviews ? (sum(list, (g) => g.positive) / reviews) * 100 : 0;
  }

  function bandOf(rating) {
    return RATING_BANDS.find((band) => rating >= band.min && rating < band.max) || RATING_BANDS[4];
  }

  function debounce(fn, wait) {
    let timer = null;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function normalize(raw) {
    const reviews = Number(raw.total_reviews) || 0;
    const rating = clamp(Number(raw.rating) || 0, 0, 100);
    const positive = raw.positive != null
      ? Number(raw.positive) || 0
      : Math.round((rating / 100) * reviews);
    return {
      appid: Number(raw.appid),
      name: String(raw.name || '未知游戏'),
      price: Number(raw.final_price != null ? raw.final_price : raw.price) || 0,
      discount: clamp(Number(raw.discount_percent != null ? raw.discount_percent : raw.discount) || 0, 0, 100),
      type: String(raw.type || '未知'),
      genres: Array.isArray(raw.genres) ? raw.genres.filter(Boolean).join(',') : String(raw.genres || ''),
      year: Number(raw.year) || 0,
      rating,
      positive,
      total_reviews: reviews,
      url: String(raw.url || `https://store.steampowered.com/app/${raw.appid}/`),
    };
  }

  /**
   * 统一数据入口：API 优先，失败回退 data.js。
   * 返回 { games, source }；source 用于页面角标。
   */
  async function loadGames() {
    let raw = null;
    let source = 'snapshot';
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3200);
      const response = await fetch('/api/games', { cache: 'no-store', signal: controller.signal });
      clearTimeout(timer);
      if (response.ok) {
        const data = await response.json();
        if (Array.isArray(data) && data.length) {
          raw = data;
          source = 'api';
        }
      }
    } catch (error) {
      // file:// 或服务未启动：静默回退到本地快照
      raw = null;
    }

    if (!raw && typeof games !== 'undefined' && Array.isArray(games)) {
      raw = games;
      source = 'snapshot';
    }
    if (!raw || !raw.length) throw new Error('没有可用的游戏数据');

    return {
      games: raw.map(normalize).filter((game) => game.appid),
      source,
    };
  }

  async function loadOnlineMeta() {
    try {
      const response = await fetch('/api/online', { cache: 'no-store' });
      if (response.ok) return await response.json();
    } catch (error) {}
    return typeof online !== 'undefined' ? online : { fetchedAt: '', top: [] };
  }

  function setMeta(state) {
    const stamp = formatDateTime(state.online.fetchedAt);
    document.querySelectorAll('[data-updated]').forEach((el) => {
      el.textContent = `数据更新：${stamp}`;
    });
    document.querySelectorAll('[data-source-tag]').forEach((el) => {
      el.hidden = false;
      el.textContent = state.source === 'api' ? '本地快照' : '离线快照';
    });
  }

  function chartBase() {
    return {
      backgroundColor: 'transparent',
      animationDuration: 550,
      animationEasing: 'cubicOut',
      textStyle: { fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif' },
      tooltip: {
        trigger: 'item',
        confine: true,
        backgroundColor: 'rgba(33, 28, 21, 0.96)',
        borderColor: '#f2c94c',
        borderWidth: 1,
        padding: [9, 11],
        textStyle: { color: '#f8efd9', fontSize: 12, lineHeight: 18 },
      },
    };
  }

  const axisStyle = {
    axisLine: { lineStyle: { color: 'rgba(33, 28, 21, 0.38)' } },
    axisTick: { show: false },
    axisLabel: { color: '#6f604c', fontSize: 10 },
    nameTextStyle: { color: '#6f604c', fontSize: 10 },
    splitLine: { lineStyle: { color: 'rgba(33, 28, 21, 0.10)', type: 'dashed' } },
  };

  window.InsightCore = {
    RATING_BANDS,
    PALETTE,
    $,
    clamp,
    escapeHtml,
    fmt1,
    formatNumber,
    formatWan,
    formatPrice,
    formatDateTime,
    average,
    sum,
    weightedRating,
    bandOf,
    debounce,
    normalize,
    loadGames,
    loadOnlineMeta,
    setMeta,
    chartBase,
    axisStyle,
  };
})();
