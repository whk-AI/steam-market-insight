/* ============================================================
   Steam 游戏市场洞察 · 数据新闻渲染
   数据接入：/api/games + /api/meta + /api/online；失败回退 data.js
   图表：ECharts 5 + echarts-wordcloud（全部本地）
   ============================================================ */

(function () {
  'use strict';

  const API = {
    games: '/api/games',
    meta: '/api/meta',
    online: '/api/online',
  };

  const PALETTE = [
    '#66c0f4', '#2ec4b6', '#f5a623', '#b18cff', '#a4d007',
    '#4aa8e0', '#5eead4', '#f08a5d', '#c4b5fd', '#84cc16',
  ];

  const TEXT = '#eaf4ff';
  const MUTED = '#8fa7bd';
  const MUTED_2 = '#6f879c';
  const ACCENT = '#66c0f4';
  const PANEL = '#0b1622';
  const GRID_LINE = 'rgba(102, 192, 244, 0.08)';
  const AXIS_LINE = 'rgba(102, 192, 244, 0.18)';

  const PRICE_BANDS = [
    { label: '免费', min: 0, max: 0 },
    { label: '1–30 元', min: 1, max: 30 },
    { label: '30–60 元', min: 30, max: 60 },
    { label: '60–90 元', min: 60, max: 90 },
    { label: '90–150 元', min: 90, max: 150 },
    { label: '150–250 元', min: 150, max: 250 },
    { label: '250 元以上', min: 250, max: Infinity },
  ];

  const RATING_BANDS = [
    { label: '95–100 分', min: 95, max: 100.1 },
    { label: '90–95 分', min: 90, max: 95 },
    { label: '80–90 分', min: 80, max: 90 },
    { label: '70–80 分', min: 70, max: 80 },
    { label: '60–70 分', min: 60, max: 70 },
    { label: '60 分以下', min: 0, max: 60 },
  ];

  const STACK_TYPES = ['动作', '模拟', '角色扮演', '冒险', '独立', '其他'];

  const charts = {};
  const state = {
    games: [],
    online: { fetchedAt: null, top: [] },
    meta: null,
    source: 'local',
  };

  const reducedMotion = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------- 基础工具 ---------------- */

  function toNumber(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function clamp(n, min, max) {
    return Math.min(max, Math.max(min, n));
  }

  function formatNumber(n) {
    return new Intl.NumberFormat('zh-CN').format(Math.round(n));
  }

  function formatWan(n) {
    if (n >= 10000) {
      return `${(n / 10000).toFixed(1).replace(/\.0$/, '')}万`;
    }
    if (n >= 1000) {
      return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}千`;
    }
    return formatNumber(n);
  }

  function formatPrice(n) {
    return n === 0 ? '免费' : `¥${Math.round(n)}`;
  }

  function formatDateTime(iso) {
    if (!iso) return '—';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return String(iso);
    const bj = new Date(date.getTime() + 8 * 60 * 60 * 1000);
    const pad = (n) => String(n).padStart(2, '0');
    return `${bj.getUTCFullYear()}-${pad(bj.getUTCMonth() + 1)}-${pad(bj.getUTCDate())} ${pad(bj.getUTCHours())}:${pad(bj.getUTCMinutes())}`;
  }

  function truncate(text, max) {
    const value = String(text || '');
    return value.length > max ? `${value.slice(0, max)}…` : value;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function average(list) {
    return list.length ? list.reduce((sum, n) => sum + n, 0) / list.length : 0;
  }

  /* 按评价数加权的好评率 */
  function weightedRating(list) {
    const valid = list.filter((g) => g.rating > 0);
    const reviews = valid.reduce((sum, g) => sum + (g.total_reviews || 0), 0);
    if (!reviews) return average(valid.map((g) => g.rating));
    return valid.reduce((sum, g) => sum + g.rating * (g.total_reviews || 0), 0) / reviews;
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function debounce(fn, wait) {
    let timer = null;
    return function debounced() {
      window.clearTimeout(timer);
      timer = window.setTimeout(fn, wait);
    };
  }

  /* ---------------- 数据加载 / 归一化 ---------------- */

  function readFallback() {
    let fallbackGames = [];
    let fallbackOnline = { fetchedAt: null, top: [] };
    let fallbackNames = {};

    try {
      if (typeof games !== 'undefined' && Array.isArray(games)) fallbackGames = games;
      if (typeof online !== 'undefined' && online && Array.isArray(online.top)) fallbackOnline = online;
      if (typeof appNameFallback !== 'undefined' && appNameFallback) fallbackNames = appNameFallback;
    } catch (error) {
      console.warn('本地回退数据读取失败', error);
    }

    return { games: fallbackGames, online: fallbackOnline, names: fallbackNames };
  }

  function fetchJson(url, timeout = 2200) {
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeout);
    return fetch(url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
      .then((res) => {
        if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
        return res.json();
      })
      .finally(() => window.clearTimeout(timer));
  }

  function unwrapGames(payload) {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.games)) return payload.games;
    if (payload && Array.isArray(payload.data)) return payload.data;
    return [];
  }

  function unwrapOnline(payload) {
    if (!payload) return null;
    if (Array.isArray(payload.top)) return payload;
    if (Array.isArray(payload.games)) return { ...payload, top: payload.games };
    if (payload.data && Array.isArray(payload.data.top)) return payload.data;
    return null;
  }

  function normalizeGenres(value, type) {
    let list = [];

    if (Array.isArray(value)) {
      list = value;
    } else if (typeof value === 'string') {
      list = value.split(/[,，、|/]/);
    }

    const cleaned = list
      .map((item) => String(item || '').trim())
      .filter(Boolean);

    if (!cleaned.length) cleaned.push(type || '其他');
    return Array.from(new Set(cleaned));
  }

  function normalizeGames(rawList) {
    return rawList
      .map((raw) => {
        const appid = toNumber(raw.appid ?? raw.app_id ?? raw.id, 0);
        const name = String(raw.name || `AppID ${appid}`);
        let price = raw.price;

        if (price == null) price = raw.final_price;
        if (price == null && raw.price_overview) price = raw.price_overview.final / 100;
        price = Math.max(0, toNumber(price, 0));

        let totalReviews = toNumber(
          raw.total_reviews ?? raw.reviews ?? raw.review_count,
          0,
        );

        let rating = raw.rating == null ? null : Number(raw.rating);
        if (rating == null && raw.positive != null && totalReviews > 0) {
          rating = (Number(raw.positive) / totalReviews) * 100;
        }
        rating = clamp(toNumber(rating, 0), 0, 100);

        let year = toNumber(raw.year, 0);
        if (!year && raw.release_date) {
          const match = /(\d{4})/.exec(String(raw.release_date));
          if (match) year = Number(match[1]);
        }

        // 已核实：Valheim 的发售年份不是 2026
        if (appid === 892970) year = 2022;

        const type = String(raw.type || '').trim()
          || (Array.isArray(raw.genres) && raw.genres[0])
          || '其他';
        const genres = normalizeGenres(raw.genres, type);

        return {
          appid,
          name,
          price,
          rating,
          total_reviews: totalReviews,
          type,
          genres,
          year,
          discount: toNumber(raw.discount ?? raw.discount_percent, 0),
        };
      })
      .filter((g) => g.appid && g.name);
  }

  function normalizeOnline(raw, gamesList, fallbackNames) {
    const byAppId = new Map(gamesList.map((g) => [g.appid, g]));
    const topRaw = raw && Array.isArray(raw.top) ? raw.top : [];
    const top = topRaw.slice(0, 10).map((item, index) => {
      const appid = toNumber(item.appid ?? item.app_id, 0);
      const value = toNumber(
        item.peak_in_game ?? item.current_players ?? item.player_count ?? item.online,
        0,
      );
      const rank = toNumber(item.rank, index + 1);
      const lastRank = toNumber(item.last_week_rank ?? item.last_rank, rank);
      const local = byAppId.get(appid);
      const name = item.name
        || (local && local.name)
        || (fallbackNames && fallbackNames[appid])
        || `AppID ${appid}`;

      return { appid, name, value, rank, lastRank };
    }).sort((a, b) => a.rank - b.rank);

    return {
      fetchedAt: (raw && (raw.fetchedAt || raw.fetched_at || raw.time)) || null,
      top,
    };
  }

  async function loadData() {
    const fallback = readFallback();
    const results = await Promise.allSettled([
      fetchJson(API.games),
      fetchJson(API.meta),
      fetchJson(API.online),
    ]);

    const gamesResult = results[0];
    const metaResult = results[1];
    const onlineResult = results[2];

    const apiGames = gamesResult.status === 'fulfilled' ? unwrapGames(gamesResult.value) : [];
    const rawGames = apiGames.length ? apiGames : fallback.games;
    const gamesList = normalizeGames(rawGames);

    const apiOnline = onlineResult.status === 'fulfilled'
      ? unwrapOnline(onlineResult.value)
      : null;
    const rawOnline = apiOnline && apiOnline.top.length ? apiOnline : fallback.online;
    const onlineData = normalizeOnline(rawOnline, gamesList, fallback.names);

    return {
      games: gamesList,
      online: onlineData,
      meta: metaResult.status === 'fulfilled' ? metaResult.value : null,
      source: apiGames.length ? 'api' : 'local',
    };
  }

  /* ---------------- 统计 ---------------- */

  function deriveStats(gamesList, onlineData) {
    const totalGames = gamesList.length;
    const prices = gamesList.map((g) => g.price);
    const ratings = gamesList.filter((g) => g.rating > 0).map((g) => g.rating);
    const freeGames = gamesList.filter((g) => g.price === 0);
    const paidGames = gamesList.filter((g) => g.price > 0);

    const typeMap = new Map();
    gamesList.forEach((game) => {
      if (!typeMap.has(game.type)) typeMap.set(game.type, []);
      typeMap.get(game.type).push(game);
    });

    const typeStats = Array.from(typeMap.entries())
      .map(([name, list]) => ({
        name,
        count: list.length,
        share: totalGames ? (list.length / totalGames) * 100 : 0,
        avgPrice: average(list.map((g) => g.price)),
        rating: weightedRating(list),
      }))
      .sort((a, b) => b.count - a.count);

    const yearMap = new Map();
    gamesList.forEach((game) => {
      if (!game.year) return;
      if (!yearMap.has(game.year)) yearMap.set(game.year, []);
      yearMap.get(game.year).push(game);
    });

    const yearStats = Array.from(yearMap.entries())
      .map(([year, list]) => ({
        year,
        count: list.length,
        rating: weightedRating(list),
      }))
      .sort((a, b) => a.year - b.year);

    const genreMap = new Map();
    gamesList.forEach((game) => {
      game.genres.forEach((genre) => {
        genreMap.set(genre, (genreMap.get(genre) || 0) + 1);
      });
    });

    const genreStats = Array.from(genreMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    const priceBands = PRICE_BANDS.map((band) => {
      const list = gameBand(gamesList, band.min, band.max);
      return {
        label: band.label,
        total: list.length,
        types: STACK_TYPES.map((type) => ({
          type,
          count: list.filter((g) => (type === '其他' ? !STACK_TYPES.includes(g.type) : g.type === type)).length,
        })),
      };
    });

    const ratingBands = RATING_BANDS.map((band) => {
      const list = gamesList.filter((g) => g.rating >= band.min && g.rating < band.max);
      const free = list.filter((g) => g.price === 0).length;
      return {
        label: band.label,
        total: list.length,
        free,
        paid: list.length - free,
      };
    });

    const onlineTotal = onlineData.top.reduce((sum, item) => sum + item.value, 0);
    const top3 = onlineData.top.slice(0, 3).reduce((sum, item) => sum + item.value, 0);
    const freeRating = weightedRating(freeGames);
    const paidRating = weightedRating(paidGames);
    const action = typeStats.find((item) => item.name === '动作') || { count: 0, share: 0, avgPrice: 0 };
    const simulation = typeStats.find((item) => item.name === '模拟') || { avgPrice: 0 };
    const year2026 = yearStats.find((item) => item.year === 2026) || { count: 0 };

    return {
      totalGames,
      avgPrice: average(prices),
      weightedRating: weightedRating(gamesList),
      freeShare: totalGames ? (freeGames.length / totalGames) * 100 : 0,
      freeCount: freeGames.length,
      typeStats,
      yearStats,
      genreStats,
      priceBands,
      ratingBands,
      onlineTotal,
      top3Share: onlineTotal ? (top3 / onlineTotal) * 100 : 0,
      freeRating,
      paidRating,
      ratingGap: paidRating - freeRating,
      action,
      simulation,
      year2026: year2026.count,
      maxRating: ratings.length ? Math.max(...ratings) : 0,
      highRatingCount: gamesList.filter((g) => g.rating >= 90).length,
    };
  }

  function gameBand(list, min, max) {
    return list.filter((game) => {
      if (min === 0 && max === 0) return game.price === 0;
      return game.price >= min && game.price < max;
    });
  }

  /* ---------------- 图表公共样式 ---------------- */

  function baseTooltip() {
    return {
      backgroundColor: 'rgba(7, 17, 26, 0.97)',
      borderColor: 'rgba(102, 192, 244, 0.34)',
      borderWidth: 1,
      padding: [10, 13],
      textStyle: { color: TEXT, fontSize: 12, lineHeight: 19 },
      extraCssText: 'box-shadow: 0 16px 40px rgba(0,0,0,.46); border-radius: 8px;',
    };
  }

  function axisLabel(extra) {
    return Object.assign({ color: MUTED, fontSize: 10.5 }, extra || {});
  }

  function splitLine() {
    return { lineStyle: { color: GRID_LINE, type: 'dashed' } };
  }

  function chartOf(id) {
    return charts[id] || null;
  }

  /* ---------------- 图表：TOP10 ---------------- */

  function renderTop10(onlineData) {
    const chart = chartOf('chart-top10');
    if (!chart) return;

    const rows = onlineData.top.slice().sort((a, b) => b.rank - a.rank);
    if (!rows.length) {
      chart.clear();
      chart.setOption({
        title: {
          text: '暂无实时在线数据',
          left: 'center',
          top: 'middle',
          textStyle: { color: MUTED, fontSize: 14, fontWeight: 400 },
        },
      });
      return;
    }

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 700,
      textStyle: { fontFamily: getComputedStyle(document.body).fontFamily },
      grid: { left: 340, right: 92, top: 10, bottom: 18, containLabel: false },
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'item',
        formatter: (params) => {
          const row = rows[params.dataIndex];
          const trend = row.lastRank > row.rank
            ? `↑ 上升 ${row.lastRank - row.rank} 位`
            : row.lastRank < row.rank
              ? `↓ 下降 ${row.rank - row.lastRank} 位`
              : '— 与上周持平';
          return `<b>#${row.rank} ${escapeHtml(row.name)}</b><br/>`
            + `当前在线：${formatNumber(row.value)} 人（${formatWan(row.value)}）<br/>`
            + `上周排名：第 ${row.lastRank} 名<br/>`
            + `名次变化：${trend}`;
        },
      }),
      xAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: axisLabel({ formatter: (value) => formatWan(value) }),
        splitLine: splitLine(),
      },
      yAxis: {
        type: 'category',
        data: rows.map((row) => row.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          interval: 0,
          formatter: (value, index) => {
            const row = rows[index];
            return `{rank|${String(row.rank).padStart(2, '0')}}  `
              + `{name|${truncate(value, 21)}}`;
          },
          rich: {
            rank: {
              color: MUTED_2, fontSize: 11, fontWeight: 600, width: 26, align: 'right',
            },
            name: {
              color: '#cfe6f7', fontSize: 13, width: 248, align: 'right',
            },
          },
        },
      },
      series: [{
        type: 'bar',
        barWidth: 22,
        showBackground: true,
        backgroundStyle: { color: 'rgba(102, 192, 244, 0.055)' },
        data: rows.map((row) => row.value),
        itemStyle: {
          borderRadius: [0, 3, 3, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#1d4e70' },
            { offset: 1, color: '#66c0f4' },
          ]),
        },
        emphasis: {
          itemStyle: { color: '#9bdcff' },
        },
        label: {
          show: true,
          position: 'right',
          distance: 9,
          formatter: (params) => {
            const row = rows[params.dataIndex];
            const trendKey = row.lastRank > row.rank ? 'up'
              : row.lastRank < row.rank ? 'down' : 'flat';
            const arrow = trendKey === 'up' ? '↑' : trendKey === 'down' ? '↓' : '—';
            return `{value|${formatWan(params.value)}}  {${trendKey}|${arrow}}`;
          },
          rich: {
            value: { color: '#bfe7ff', fontSize: 12.5, fontWeight: 600 },
            up: { color: '#ff7b7b', fontSize: 13, fontWeight: 700 },
            down: { color: '#6ee7b7', fontSize: 13, fontWeight: 700 },
            flat: { color: '#6f879c', fontSize: 13 },
          },
        },
      }],
    }, true);
  }

  /* ---------------- 图表：类型玫瑰 ---------------- */

  function renderTypeRose(typeStats) {
    const chart = chartOf('chart-type-rose');
    if (!chart) return;

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 700,
      color: PALETTE,
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'item',
        formatter: (params) => {
          const item = typeStats[params.dataIndex];
          return `<b>${escapeHtml(params.name)}</b><br/>`
            + `游戏数：${item.count} 款<br/>`
            + `占样本：${item.share.toFixed(1)}%<br/>`
            + `平均售价：${item.avgPrice.toFixed(1)} 元`;
        },
      }),
      legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 2,
        top: 'middle',
        itemWidth: 7,
        itemHeight: 7,
        itemGap: 10,
        icon: 'circle',
        textStyle: { color: MUTED, fontSize: 10.5 },
        pageTextStyle: { color: MUTED },
        pageIconColor: ACCENT,
      },
      graphic: [{
        type: 'text',
        left: '39%',
        top: '52%',
        style: {
          text: `${typeStats.length}\n类主类型`,
          textAlign: 'center',
          textVerticalAlign: 'middle',
          fill: '#dcecf8',
          fontSize: 20,
          fontWeight: 600,
          lineHeight: 24,
        },
      }],
      series: [{
        name: '主类型',
        type: 'pie',
        radius: ['34%', '70%'],
        center: ['39%', '52%'],
        roseType: 'radius',
        selectedMode: 'single',
        selectedOffset: 8,
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#0b1622',
          borderWidth: 2,
          borderRadius: 3,
        },
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 5,
          itemStyle: { shadowBlur: 18, shadowColor: 'rgba(102, 192, 244, 0.3)' },
        },
        data: typeStats.map((item, index) => ({
          name: item.name,
          value: item.count,
          itemStyle: { color: PALETTE[index % PALETTE.length] },
        })),
      }],
    }, true);
  }

  /* ---------------- 图表：价格带 ---------------- */

  function renderPrice(stats) {
    const chart = chartOf('chart-price');
    if (!chart) return;

    const labels = stats.priceBands.map((band) => band.label);
    const series = STACK_TYPES.map((type, index) => ({
      name: type,
      type: 'bar',
      stack: 'price',
      barWidth: '48%',
      itemStyle: { color: PALETTE[index % PALETTE.length] },
      emphasis: { focus: 'series' },
      data: stats.priceBands.map((band) => {
        const row = band.types.find((item) => item.type === type);
        return row ? row.count : 0;
      }),
    }));

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 650,
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(102, 192, 244, 0.06)' } },
        formatter: (params) => {
          const index = params[0].dataIndex;
          const band = stats.priceBands[index];
          const rows = params
            .filter((item) => item.value > 0)
            .map((item) => `${item.marker} ${item.seriesName}：${item.value} 款`)
            .join('<br/>');
          return `<b>${band.label}</b><br/>${rows}<br/>合计：${band.total} 款`;
        },
      }),
      legend: {
        top: 0,
        left: 0,
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 12,
        icon: 'roundRect',
        textStyle: { color: MUTED, fontSize: 10.5 },
      },
      grid: { left: 40, right: 16, top: 38, bottom: 32 },
      xAxis: {
        type: 'category',
        data: labels,
        axisLine: { lineStyle: { color: AXIS_LINE } },
        axisTick: { show: false },
        axisLabel: axisLabel({ interval: 0, fontSize: 9.5, rotate: 22 }),
      },
      yAxis: {
        type: 'value',
        name: '款',
        nameTextStyle: { color: MUTED_2, fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: axisLabel(),
        splitLine: splitLine(),
      },
      series,
    }, true);
  }

  /* ---------------- 图表：年度趋势 ---------------- */

  function renderTrend(yearStats) {
    const chart = chartOf('chart-trend');
    if (!chart) return;

    const years = yearStats.map((item) => item.year);
    chart.setOption({
      animationDuration: reducedMotion ? 0 : 700,
      textStyle: { fontFamily: getComputedStyle(document.body).fontFamily },
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'axis',
        axisPointer: { type: 'cross', crossStyle: { color: 'rgba(102,192,244,.3)' } },
        formatter: (params) => {
          const index = params[0].dataIndex;
          const item = yearStats[index];
          return `<b>${item.year} 年</b><br/>`
            + `样本游戏数：${item.count} 款<br/>`
            + `加权好评率：${item.rating.toFixed(1)}%`;
        },
      }),
      legend: {
        top: 4,
        left: 'center',
        itemWidth: 9,
        itemHeight: 9,
        itemGap: 14,
        icon: 'circle',
        textStyle: { color: MUTED, fontSize: 10.5 },
      },
      grid: { left: 46, right: 48, top: 42, bottom: 32 },
      xAxis: {
        type: 'category',
        data: years,
        axisLine: { lineStyle: { color: AXIS_LINE } },
        axisTick: { show: false },
        axisLabel: axisLabel({ interval: 0, fontSize: 9.5 }),
      },
      yAxis: [
        {
          type: 'value',
          name: '样本数',
          nameTextStyle: { color: MUTED_2, fontSize: 10 },
          min: 0,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: axisLabel(),
          splitLine: splitLine(),
        },
        {
          type: 'value',
          name: '好评率 %',
          nameTextStyle: { color: MUTED_2, fontSize: 10 },
          min: 60,
          max: 100,
          interval: 10,
          axisLine: { show: false },
          axisTick: { show: false },
          axisLabel: axisLabel({ formatter: '{value}%' }),
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '当年样本数',
          type: 'bar',
          barWidth: '42%',
          data: yearStats.map((item) => item.count),
          itemStyle: {
            borderRadius: [2, 2, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#66c0f4' },
              { offset: 1, color: 'rgba(35, 111, 151, 0.32)' },
            ]),
          },
          emphasis: { itemStyle: { color: '#9bdcff' } },
        },
        {
          name: '加权好评率',
          type: 'line',
          yAxisIndex: 1,
          data: yearStats.map((item) => Number(item.rating.toFixed(1))),
          smooth: false,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#f5a623' },
          itemStyle: { color: '#f5a623', borderColor: '#0b1622', borderWidth: 1 },
          emphasis: { scale: 1.6 },
        },
      ],
    }, true);
  }

  /* ---------------- 图表：口碑分布 ---------------- */

  function renderRating(stats) {
    const chart = chartOf('chart-rating');
    if (!chart) return;

    const rows = stats.ratingBands.slice().reverse();
    const labels = rows.map((band) => band.label);
    const totalFree = stats.freeCount;
    const totalPaid = stats.totalGames - stats.freeCount;

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 650,
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(102, 192, 244, 0.06)' } },
        formatter: (params) => {
          const index = params[0].dataIndex;
          const band = rows[index];
          const list = params.map((item) => {
            const base = item.seriesName === '免费' ? totalFree : totalPaid;
            const share = base ? ((item.value / base) * 100).toFixed(1) : '0.0';
            return `${item.marker} ${item.seriesName}：${item.value} 款（占该组 ${share}%）`;
          }).join('<br/>');
          return `<b>${band.label}</b><br/>${list}<br/>合计：${band.total} 款`;
        },
      }),
      legend: {
        top: 0,
        left: 0,
        itemWidth: 8,
        itemHeight: 8,
        itemGap: 16,
        icon: 'roundRect',
        textStyle: { color: MUTED, fontSize: 10.5 },
      },
      grid: { left: 92, right: 80, top: 36, bottom: 28 },
      xAxis: {
        type: 'value',
        name: '款',
        nameTextStyle: { color: MUTED_2, fontSize: 10 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: axisLabel(),
        splitLine: splitLine(),
      },
      yAxis: {
        type: 'category',
        data: labels,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: axisLabel({ fontSize: 11 }),
      },
      series: [
        {
          name: '免费',
          type: 'bar',
          barWidth: 14,
          data: rows.map((band) => band.free),
          itemStyle: { color: '#2ec4b6', borderRadius: [0, 2, 2, 0] },
          label: {
            show: true,
            position: 'right',
            color: '#8fe3d8',
            fontSize: 10,
            formatter: (params) => (params.value > 0 ? params.value : ''),
          },
        },
        {
          name: '付费',
          type: 'bar',
          barWidth: 14,
          data: rows.map((band) => band.paid),
          itemStyle: { color: '#66c0f4', borderRadius: [0, 2, 2, 0] },
          label: {
            show: true,
            position: 'right',
            color: '#bfe7ff',
            fontSize: 10,
            formatter: (params) => (params.value > 0 ? params.value : ''),
          },
        },
      ],
    }, true);
  }

  /* ---------------- 图表：词云 ---------------- */

  function renderWordCloud(genreStats) {
    const chart = chartOf('chart-wordcloud');
    if (!chart) return;

    const words = genreStats.map((item, index) => ({
      name: item.name,
      value: item.count,
      textStyle: { color: PALETTE[index % PALETTE.length] },
    }));

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 500,
      tooltip: Object.assign(baseTooltip(), {
        trigger: 'item',
        formatter: (params) => `<b>${escapeHtml(params.name)}</b><br/>出现：${params.value} 款游戏`,
      }),
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        width: '96%',
        height: '88%',
        left: 'center',
        top: 'center',
        sizeRange: [13, 46],
        rotationRange: [0, 0],
        rotationStep: 0,
        gridSize: 7,
        drawOutOfBound: false,
        layoutAnimation: !reducedMotion,
        textStyle: {
          fontFamily: 'Inter, "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif',
          fontWeight: 650,
        },
        emphasis: {
          textStyle: {
            shadowBlur: 14,
            shadowColor: 'rgba(102, 192, 244, 0.45)',
          },
        },
        data: words,
      }],
    }, true);
  }

  /* ---------------- 图表：热力图 ---------------- */

  function renderHeatmap(stats) {
    const chart = chartOf('chart-heatmap');
    if (!chart) return;

    const years = stats.yearStats.map((item) => item.year);
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const fullYears = [];
    for (let year = minYear; year <= maxYear; year += 1) fullYears.push(year);

    const types = stats.typeStats.map((item) => item.name);
    const typeIndex = new Map(types.map((type, index) => [type, index]));
    const yearIndex = new Map(fullYears.map((year, index) => [year, index]));

    const counts = new Map();

    // 直接按游戏重新计算，避免丢失年份内类型分布
    const data = [];
    state.games.forEach((game) => {
      if (!yearIndex.has(game.year)) return;
      const key = `${game.year}|${game.type}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    });

    counts.forEach((count, key) => {
      const parts = key.split('|');
      const year = Number(parts[0]);
      const type = parts.slice(1).join('|');
      if (!typeIndex.has(type) || !yearIndex.has(year)) return;
      data.push([yearIndex.get(year), typeIndex.get(type), count]);
    });

    const maxCount = Math.max(5, ...counts.values());

    chart.setOption({
      animationDuration: reducedMotion ? 0 : 600,
      tooltip: Object.assign(baseTooltip(), {
        formatter: (params) => {
          const [x, y, value] = params.value;
          return `<b>${types[y]}</b><br/>${fullYears[x]} 年：${value} 款`;
        },
      }),
      grid: { left: 112, right: 72, top: 12, bottom: 58 },
      xAxis: {
        type: 'category',
        data: fullYears,
        axisLine: { lineStyle: { color: AXIS_LINE } },
        axisTick: { show: false },
        axisLabel: axisLabel({ rotate: 45, fontSize: 9 }),
        splitArea: { show: false },
      },
      yAxis: {
        type: 'category',
        data: types,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: axisLabel({ fontSize: 10 }),
        splitArea: { show: false },
      },
      visualMap: {
        min: 0,
        max: maxCount,
        calculable: false,
        orient: 'vertical',
        right: 6,
        top: 'middle',
        itemWidth: 10,
        itemHeight: 140,
        text: ['多', '少'],
        textStyle: { color: MUTED_2, fontSize: 10 },
        inRange: {
          color: ['#183247', '#21506c', '#2b6f95', '#3d8fba', '#66c0f4', '#a9e3ff'],
        },
      },
      series: [{
        name: '类型 × 年份',
        type: 'heatmap',
        data,
        label: {
          show: true,
          fontSize: 10,
          fontWeight: 600,
          formatter: (params) => {
            const value = params.value[2];
            if (value < 5) return '';
            return value >= 12 ? `{dark|${value}}` : `{light|${value}}`;
          },
          rich: {
            dark: { color: '#06121c', fontSize: 10, fontWeight: 700 },
            light: { color: '#e6f7ff', fontSize: 10, fontWeight: 700 },
          },
        },
        itemStyle: {
          borderColor: 'rgba(7, 15, 23, 0.92)',
          borderWidth: 2,
          borderRadius: 2,
        },
        emphasis: {
          itemStyle: {
            borderColor: '#bfe7ff',
            borderWidth: 1,
            shadowBlur: 12,
            shadowColor: 'rgba(102, 192, 244, 0.4)',
          },
        },
      }],
    }, true);
  }

  /* ---------------- 页面数字 / 文案 ---------------- */

  function countUp(el, target, decimals = 0) {
    if (!el || !Number.isFinite(target)) return;
    if (reducedMotion) {
      el.textContent = target.toFixed(decimals);
      return;
    }

    const start = performance.now();
    const duration = 900;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = (target * eased).toFixed(decimals);
      if (progress < 1) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
  }

  function renderPageStats(stats, onlineData) {
    const snapshot = formatDateTime(onlineData.fetchedAt);
    const onlineWan = onlineData.top.length
      ? (stats.onlineTotal / 10000).toFixed(1).replace(/\.0$/, '')
      : '—';

    setText('data-updated', snapshot);
    setText('hero-snapshot', snapshot);
    setText('footer-updated', snapshot);
    setText('hero-online-title', onlineWan);
    setText('hero-online', onlineWan);
    setText('online-total', `${onlineWan} 万`);
    setText('stat-top3', `${stats.top3Share.toFixed(1)}%`);
    setText('stat-2026', stats.year2026);
    setText('stat-action-share', `${stats.action.share.toFixed(1)}%`);
    setText('stat-action-price', `${stats.action.avgPrice.toFixed(1)} 元`);
    setText('stat-sim-price', `${stats.simulation.avgPrice.toFixed(1)} 元`);
    const freeRounded = Math.round(stats.freeRating * 10) / 10;
    const paidRounded = Math.round(stats.paidRating * 10) / 10;
    setText('stat-free', freeRounded.toFixed(1));
    setText('stat-paid', paidRounded.toFixed(1));
    setText('stat-gap', (paidRounded - freeRounded).toFixed(1));

    countUp(document.getElementById('hero-games'), stats.totalGames, 0);
    countUp(document.getElementById('hero-online'), Number(onlineWan), 1);

    document.querySelectorAll('.js-source').forEach((el) => {
      el.textContent = ` · 快照 ${snapshot}`;
    });

    const summary = document.querySelector('#appendix summary');
    if (summary) {
      summary.innerHTML = `查看全部 ${stats.totalGames} 款游戏 <span aria-hidden="true">→</span>`;
    }
  }

  function renderTable(gamesList) {
    const tbody = document.getElementById('games-table');
    if (!tbody) return;

    const rows = gamesList.slice().sort((a, b) => b.rating - a.rating);
    const fragment = document.createDocumentFragment();

    rows.forEach((game) => {
      const tr = document.createElement('tr');
      const cells = [
        game.name,
        game.type,
        formatPrice(game.price),
        `${game.rating.toFixed(1)}%`,
        formatNumber(game.total_reviews),
        game.year || '—',
      ];

      cells.forEach((value, index) => {
        const td = document.createElement('td');
        td.textContent = value;
        if (index === 0) td.title = game.name;
        tr.appendChild(td);
      });

      fragment.appendChild(tr);
    });

    tbody.replaceChildren(fragment);
  }

  /* ---------------- 初始化 ---------------- */

  function initCharts() {
    const ids = [
      'chart-top10',
      'chart-type-rose',
      'chart-price',
      'chart-trend',
      'chart-rating',
      'chart-wordcloud',
      'chart-heatmap',
    ];

    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      charts[id] = echarts.init(el, null, { renderer: 'canvas' });
    });
  }

  function setupReveal() {
    const elements = Array.from(document.querySelectorAll('.reveal'));

    if (!('IntersectionObserver' in window) || reducedMotion) {
      elements.forEach((el) => el.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          const chartEl = entry.target.querySelector('.chart');
          if (chartEl && charts[chartEl.id]) charts[chartEl.id].resize();
        } else {
          entry.target.classList.remove('is-visible');
        }
      });
    }, {
      threshold: 0.16,
      rootMargin: '0px 0px -8% 0px',
    });

    elements.forEach((el) => observer.observe(el));
  }

  function setupResize() {
    const resizeAll = debounce(() => {
      Object.values(charts).forEach((chart) => chart.resize());
    }, 140);

    window.addEventListener('resize', resizeAll);
  }

  function renderAll() {
    const stats = deriveStats(state.games, state.online);

    renderPageStats(stats, state.online);
    renderTop10(state.online);
    renderTypeRose(stats.typeStats);
    renderPrice(stats);
    renderTrend(stats.yearStats);
    renderRating(stats);
    renderWordCloud(stats.genreStats);
    renderHeatmap(stats);
    renderTable(state.games);

    setupReveal();

    if (state.source === 'local') {
      console.info('[Steam] 使用本地 data.js 回退数据');
    }
  }

  async function boot() {
    initCharts();
    setupResize();

    try {
      const data = await loadData();
      state.games = data.games;
      state.online = data.online;
      state.meta = data.meta;
      state.source = data.source;
      renderAll();
    } catch (error) {
      console.error('[Steam] 渲染失败', error);
      // 最后一道兜底：直接用 data.js，不允许页面空白
      const fallback = readFallback();
      state.games = normalizeGames(fallback.games);
      state.online = normalizeOnline(fallback.online, state.games, fallback.names);
      state.source = 'local';
      renderAll();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
}());
