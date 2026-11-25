(function () {
  'use strict';

  const $ = (selector, root) => (root || document).querySelector(selector);
  const $$ = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const number = new Intl.NumberFormat('zh-CN');
  const compact = new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 });
  const state = {
    agg: null,
    reviews: [],
    top500: [],
    online: null,
    newReleases: null,
    model: null,
    characters: [],
    selectedGenre: null,
    seasonYear: 2024,
    seasonTimer: null,
    repGrade: 'S',
    archiveGenre: '',
    diceTimer: null,
  };

  const GRADE = {
    S: { label: '好评如潮', min: 95, max: 100, color: '#ffc857' },
    A: { label: '特别好评', min: 85, max: 95, color: '#b6f34a' },
    B: { label: '多半好评', min: 70, max: 85, color: '#66c0f4' },
    C: { label: '褒贬不一', min: 0, max: 70, color: '#ff6b6b' },
  };

  const ONLINE_NAMES = {
    730: 'Counter-Strike 2',
    570: 'Dota 2',
    578080: 'PUBG: BATTLEGROUNDS',
    4115450: 'Phantom Blade Zero',
    3419430: 'Bongo Cat',
    431960: 'Wallpaper Engine',
    1422450: 'Deadlock',
    1172470: 'Apex Legends™',
    1938090: 'Call of Duty®',
    440: 'Team Fortress 2',
    2507950: 'Delta Force',
    252490: 'Rust',
    1867240: 'WARDOGS',
    3393110: 'AION 2',
    2868840: 'Slay the Spire 2',
    4262460: 'ROB RUN',
    4348910: 'Probably Stolen - Cyberpunk Shopkeeper Sim',
    322170: 'Geometry Dash',
    271590: 'Grand Theft Auto V',
  };
  const PARTIAL_YEARS = new Set([2026]);

  const TYPE_CN = {
    Action: '动作', Casual: '休闲', Adventure: '冒险', Indie: '独立',
    Simulation: '模拟', RPG: '角色扮演', Strategy: '策略', Sports: '体育',
    'Free To Play': '免费开玩', Racing: '竞速', '其他': '其他',
  };

  const GENRE_CN = {
    Indie: '独立', Action: '动作', Adventure: '冒险', Casual: '休闲',
    Simulation: '模拟', Strategy: '策略', RPG: '角色扮演',
    'Free To Play': '免费开玩', Sports: '体育', Racing: '竞速',
    'Massively Multiplayer': '大型多人在线', 'Early Access': '抢先体验',
    'Animation & Modeling': '动画与建模', 'Audio Production': '音频制作',
    'Design & Illustration': '设计与插画', Education: '教育',
    'Game Development': '游戏开发', 'Photo Editing': '图片编辑',
    'Software Training': '软件培训', Utilities: '工具',
    'Video Production': '视频制作', 'Web Publishing': '网页发布',
  };

  function genreLabel(value) {
    const raw = String(value == null ? '' : value).trim();
    if (TYPE_CN[raw]) return TYPE_CN[raw];
    if (GENRE_CN[raw]) return GENRE_CN[raw];
    // archive 里有一批历史字段是 GBK 被当 UTF-8 读出的替换字符；
    // 这些行不强行猜具体类型，统一标成“未知”，但保留原值参与模型计算。
    if (!raw || raw === '未知' || raw === 'δ֪' || /[\uFFFD]/.test(raw)) return '未知';
    return raw;
  }

  const CHARACTER_ORDER = ['Indie', 'Casual', 'Adventure', 'Action', 'RPG', 'Free To Play', 'Strategy', 'Simulation', 'Sports', 'Racing'];

  function fmt(value, digits) {
    if (value == null || Number.isNaN(Number(value))) return '—';
    return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: digits == null ? 0 : digits });
  }

  function price(value) {
    if (value == null || Number.isNaN(Number(value))) return '—';
    if (Number(value) === 0) return '免费';
    return '$' + Number(value).toFixed(2);
  }

  function share(value) {
    return (Number(value) || 0).toFixed(1) + '%';
  }

  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }

  async function apiWithFallback(primary, fallback) {
    try {
      const response = await fetch(primary, { cache: 'no-store' });
      if (response.ok) return await response.json();
    } catch (error) {
      // 静态服务器没有 /api 路由时，继续尝试数据文件
    }
    const response = await fetch(fallback, { cache: 'no-store' });
    if (!response.ok) throw new Error(fallback + ' ' + response.status);
    return response.json();
  }

  async function loadData(primary, fallback, bundleKey) {
    // file:// 下浏览器不允许 fetch 本地 JSON，优先读取离线 bundle；
    // http(s) 下仍读最新 JSON，保证每日更新后刷新页面就能看到新数据。
    if (location.protocol === 'file:' && bundleKey && window.__LOBBY_DATA__ && window.__LOBBY_DATA__[bundleKey]) {
      return window.__LOBBY_DATA__[bundleKey];
    }
    // 静态页默认只读本地 JSON，避免没有后端时每次打开都产生 6 条 404。
    // 若部署了接口，在页面里设置 window.__USE_API__ = true 再启用接口。
    if (window.__USE_API__ !== true) {
      const response = await fetch(fallback, { cache: 'no-store' });
      if (!response.ok) throw new Error(fallback + ' ' + response.status);
      return response.json();
    }
    return apiWithFallback(primary, fallback);
  }

  function setBootError(message) {
    const hint = $('#boot-hint');
    if (hint) {
      hint.textContent = message;
      hint.classList.add('is-error');
    }
  }

  function hideBoot() {
    const boot = $('#boot');
    if (!boot) return;
    const video = $('#boot-video');
    if (video) video.pause();
    document.body.classList.remove('is-booting');
    boot.classList.add('is-gone');
    window.setTimeout(() => { boot.remove(); }, 600);
  }

  // 进入页背景是本地预渲染的 8 秒 3D 穿门动画；自动播放被拦截时静默回退到 poster。
  function initBootVideo() {
    const video = $('#boot-video');
    if (!video) return;
    document.body.classList.add('is-booting');
    const play = () => {
      if (video.paused) video.play().catch(() => {});
    };
    video.addEventListener('error', () => {
      video.classList.add('is-error');
    });
    play();
    document.addEventListener('pointerdown', play, { once: true });
  }

  function typeOf(genre) {
    const row = state.agg.type_dist.find((item) => item.name === genre);
    return row || { name: genre, name_cn: TYPE_CN[genre] || genre, count: 0, share: 0, avgPrice: 0, avgRating: 0, ratingCount: 0 };
  }

  function onlineName(appid, fallback) {
    if (fallback) return fallback;
    const top = state.top500.find((item) => Number(item.appid) === Number(appid));
    if (top) return top.name;
    if (ONLINE_NAMES[appid]) return ONLINE_NAMES[appid];
    const lookup = state.agg.name_lookup || {};
    return lookup[appid] || lookup[String(appid)] || 'APP ' + appid;
  }

  // 本地封面优先：先读 assets/covers/{appid}.jpg；缺失时回退 Steam header，
  // 再失败才使用本地 Steam 标识，避免断网/新游缺图时出现破图或空行。
  window.__steamCoverFallback = function (img) {
    if (!img) return;
    const stage = img.dataset.fb || 'local';
    if (stage === 'local') {
      img.dataset.fb = 'remote';
      img.src = img.dataset.remote || ('https://cdn.akamai.steamstatic.com/steam/apps/' + img.dataset.appid + '/header.jpg');
      return;
    }
    if (stage === 'remote') {
      img.dataset.fb = 'logo';
      img.classList.add('is-fallback');
      img.src = 'assets/steam-logo.png';
      return;
    }
    img.style.visibility = 'hidden';
  };

  function coverMarkup(appid, cls, alt) {
    const local = 'assets/covers/' + appid + '.jpg';
    const remote = 'https://cdn.akamai.steamstatic.com/steam/apps/' + appid + '/header.jpg';
    return '<img class="' + cls + '" data-appid="' + appid + '" data-fb="local" data-remote="' + remote + '" src="' + local + '" alt="' + esc(alt || '') + '" loading="eager" onerror="window.__steamCoverFallback(this)">';
  }

  // 统一 TOP10 口径：缺失名次用第 11 名补位；显示时按“当前在线”重排，并保留来源榜位。
  function normalizedTop(online) {
    const all = online && Array.isArray(online.top) ? online.top.slice() : [];
    const rows = all.slice(0, 10).map((row) => Object.assign({}, row));
    const pool = all.slice(10);
    if (online && online.next) pool.push(Object.assign({ rank: 11 }, online.next));
    const used = new Set(rows.filter((row) => Number(row.current_players) > 0).map((row) => Number(row.appid)));
    rows.forEach((row, index) => {
      if (Number(row.current_players) > 0) return;
      const candidate = pool.find((item) => Number(item.current_players) > 0 && !used.has(Number(item.appid)));
      if (!candidate) return;
      rows[index] = Object.assign({}, candidate, { rank: row.rank || index + 1, promoted_from: candidate.rank || 11 });
      used.add(Number(candidate.appid));
    });
    return rows
      .map((row) => Object.assign({}, row, { source_rank: Number(row.rank) || 0 }))
      .sort((a, b) => (Number(b.current_players) || 0) - (Number(a.current_players) || 0))
      .map((row, index) => Object.assign({}, row, { rank: index + 1 }));
  }

  function isPartialYear(year) {
    return PARTIAL_YEARS.has(Number(year));
  }

  function typeGames(genre) {
    return (state.agg.top_by_type && state.agg.top_by_type[genre]) || [];
  }

  function reviewMap() {
    const map = new Map();
    state.reviews.forEach((item) => map.set(Number(item.appid), item));
    return map;
  }

  function initMeta() {
    const agg = state.agg;
    const online = state.online;
    const total = agg.meta.totalGames;
    $('#hall-total').textContent = fmt(total);
    $('#hall-types').textContent = '10';
    $('#hall-reviewed').textContent = fmt(state.reviews.length || agg.meta.reviewsUpdated);
    $('#snapshot-label').textContent = agg.meta.builtAt ? '全量快照' : '本地快照';
    $('#snapshot-time').textContent = agg.meta.builtAt
      ? agg.meta.builtAt.slice(0, 10)
      : '2026-10-18';
    $('#season-year').textContent = String(state.seasonYear);
    $('#archive-count').textContent = fmt(state.top500.length) + ' 条';

    if (online && online.top && online.top.length) {
      const time = new Date(online.fetchedAt);
      const text = Number.isNaN(time.getTime())
        ? online.fetchedAt
        : time.toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-');
      $('#arena-updated').textContent = text;

      const rows = normalizedTop(online);
      const valid = rows.filter((row) => Number(row.current_players) > 0);
      const missing = rows.filter((row) => !(Number(row.current_players) > 0));
      const promoted = rows.find((row) => Number(row.promoted_from) > 0);
      const promotedText = promoted
        ? '源榜第 ' + promoted.source_rank + ' 名缺数，用第 ' + promoted.promoted_from + ' 名补足 10 行'
        : '';
      const sourceNote = /GetMostPlayedGames/i.test(online.source || '')
        ? '（榜单与在线数：Steam 官方接口）'
        : /Steam\s*charts/i.test(online.source || '')
          ? '（榜单：SteamCharts；在线数：Steam 官方接口）'
          : '';
      const total = valid.reduce((sum, row) => sum + Number(row.current_players), 0);
      if (valid.length && total) {
        const top3 = valid.slice(0, 3).reduce((sum, row) => sum + Number(row.current_players), 0);
        const share = (top3 / total) * 100;
        $('#brief-attention').textContent = share.toFixed(1) + '%';
        const thesisAttention = $('#thesis-attention');
        if (thesisAttention) thesisAttention.textContent = share.toFixed(1) + '%';
        $('#brief-attention-text').textContent =
          'TOP3 占 TOP10 在线 ' + compact.format(total) + ' 中的 ' + share.toFixed(1) + '%；'
          + '10 名有效（按当前在线重排' + (promotedText ? '；' + promotedText : '') + '）。';
        const y = time.getFullYear();
        const m = String(time.getMonth() + 1).padStart(2, '0');
        const d = String(time.getDate()).padStart(2, '0');
        const hh = String(time.getHours()).padStart(2, '0');
        const mm = String(time.getMinutes()).padStart(2, '0');
        const stamp = Number.isNaN(time.getTime()) ? online.fetchedAt : y + '-' + m + '-' + d + ' ' + hh + ':' + mm;
        $('#brief-live').textContent = 'TOP10 为 ' + stamp + ' 快照'
          + '（10 名有效，按当前在线重排' + (promotedText ? '；' + promotedText : '') + '）';
        $('#arena-intro').textContent =
          '只统计 Steam 实时在线 TOP10，不叫“平台总在线”；这是 ' + stamp + ' 的'
          + '10 名有效快照（按当前在线重排' + (promotedText ? '；' + promotedText : '') + '）'
          + sourceNote + '。';
      }
    }

    const liveNode = $('#live-time');
    if (liveNode && online && online.top && online.top.length) {
      const liveTime = new Date(online.fetchedAt);
      if (!Number.isNaN(liveTime.getTime())) {
        const mmdd = `${String(liveTime.getMonth() + 1).padStart(2, '0')}-${String(liveTime.getDate()).padStart(2, '0')}`;
        const hhmm = `${String(liveTime.getHours()).padStart(2, '0')}:${String(liveTime.getMinutes()).padStart(2, '0')}`;
        liveNode.textContent = `· 在线数据 ${mmdd} ${hhmm}`;
        liveNode.hidden = false;
      }
    }
  }

  function initLobby() {
    state.characters = CHARACTER_ORDER.map((genre) => typeOf(genre));
    $$('.char').forEach((button) => {
      const genre = button.dataset.genre;
      if (!genre) return;
      const row = typeOf(genre);
      const count = button.querySelector('.char__count');
      if (count) count.textContent = fmt(row.count);
      button.addEventListener('click', () => openDossier(genre));
      button.addEventListener('mouseenter', () => {
        if (state.diceTimer) window.clearTimeout(state.diceTimer);
        state.diceTimer = window.setTimeout(() => setStageGlow(genre), 60);
      });
    });
    initWorld();
    initHallLinks();
    initHallMatrix();
    bindHallView();
  }

  function initHallMatrix() {
    const wrap = $('#hall-matrix');
    if (!wrap || !state.agg || !state.agg.type_pairs) return;
    const genres = CHARACTER_ORDER.filter((genre) => typeOf(genre).count > 0);
    const pairMap = new Map();
    state.agg.type_pairs.forEach((pair) => {
      pairMap.set(pair.a + '|' + pair.b, pair.count);
      pairMap.set(pair.b + '|' + pair.a, pair.count);
    });
    const max = Math.max.apply(null, state.agg.type_pairs.map((pair) => pair.count).concat([1]));
    wrap.innerHTML = '<div class="matrix-grid" style="--n:' + genres.length + '">' +
      '<span class="matrix-cell matrix-corner">类型 × 类型</span>' +
      genres.map((genre) => '<span class="matrix-label matrix-label--col">' + esc(TYPE_CN[genre] || genre) + '</span>').join('') +
      genres.map((row) => '<span class="matrix-label">' + esc(TYPE_CN[row] || row) + '</span>' +
        genres.map((col) => {
          if (row === col) return '<span class="matrix-cell matrix-cell--diag">—</span>';
          const count = pairMap.get(row + '|' + col) || 0;
          const alpha = (count / max).toFixed(2);
          const label = (TYPE_CN[row] || row) + ' × ' + (TYPE_CN[col] || col);
          return '<span class="matrix-cell" data-a="' + row + '" data-b="' + col + '" data-count="' + count + '" title="' + esc(label + '：' + fmt(count) + ' 款') + '" style="--a:' + alpha + '">' + (count ? fmt(count) : '') + '</span>';
        }).join('')).join('') +
      '</div><p class="matrix-result" id="matrix-result">颜色越深，共享游戏越多；点格子看精确数量。</p>';
    wrap.addEventListener('click', (event) => {
      const cell = event.target.closest('.matrix-cell[data-a]');
      if (!cell) return;
      $$('.matrix-cell').forEach((node) => node.classList.remove('is-hot'));
      cell.classList.add('is-hot');
      const a = TYPE_CN[cell.dataset.a] || cell.dataset.a;
      const b = TYPE_CN[cell.dataset.b] || cell.dataset.b;
      const result = $('#matrix-result');
      if (result) result.textContent = a + ' × ' + b + '：' + fmt(cell.dataset.count) + ' 款游戏同时属于两个类型（可重叠计数）。';
    });
  }

  function bindHallView() {
    const stage = $('#hall-stage');
    const matrix = $('#hall-matrix');
    const buttons = $$('[data-hall-view]');
    if (!stage || !matrix || !buttons.length) return;
    const hint = $('.hall__hint');
    const networkHint = hint ? hint.innerHTML : '';
    const matrixHint = '<span>颜色深 = 共享多</span><span>CLICK 定格</span><span>TOGGLE 回关系网</span>';
    buttons.forEach((button) => {
      button.addEventListener('click', () => {
        const view = button.dataset.hallView;
        buttons.forEach((node) => node.classList.toggle('is-active', node === button));
        stage.hidden = view !== 'network';
        matrix.hidden = view !== 'matrix';
        if (hint) hint.innerHTML = view === 'matrix' ? matrixHint : networkHint;
      });
    });
  }

  function initHallLinks() {
    const svg = $('#hall-links');
    const stage = $('#hall-stage');
    const hall = $('.hall');
    if (!svg || !stage || !hall || !state.agg || !state.agg.type_pairs) return;

    const chars = $$('.char');
    const genres = new Set(chars.map((node) => node.dataset.genre));
    const pairs = state.agg.type_pairs
      .filter((pair) => genres.has(pair.a) && genres.has(pair.b))
      .slice(0, 20);
    if (!pairs.length) return;

    let frame = 0;
    const draw = () => {
      frame = 0;
      const rect = stage.getBoundingClientRect();
      const pos = {};
      chars.forEach((node) => {
        const box = node.getBoundingClientRect();
        pos[node.dataset.genre] = {
          x: box.left - rect.left + box.width / 2,
          y: box.top - rect.top + box.height * 0.5,
        };
      });
      svg.setAttribute('viewBox', '0 0 ' + rect.width + ' ' + rect.height);
      const max = Math.max.apply(null, pairs.map((pair) => pair.count)) || 1;
      svg.innerHTML = pairs.map((pair) => {
        const a = pos[pair.a];
        const b = pos[pair.b];
        if (!a || !b) return '';
        const width = (0.8 + (pair.count / max) * 1.8).toFixed(2);
        return '<line data-a="' + pair.a + '" data-b="' + pair.b + '" x1="' + a.x.toFixed(1) + '" y1="' + a.y.toFixed(1) + '" x2="' + b.x.toFixed(1) + '" y2="' + b.y.toFixed(1) + '" style="stroke-width:' + width + ';opacity:' + (0.3 + (pair.count / max) * 0.35).toFixed(2) + '"></line>';
      }).join('');
    };

    const highlight = (genre, active) => {
      hall.classList.toggle('links-hover', active);
      const related = new Set([genre]);
      pairs.forEach((pair) => {
        if (pair.a === genre) related.add(pair.b);
        if (pair.b === genre) related.add(pair.a);
      });
      $$('.hall-links line').forEach((line) => {
        const hot = active && (line.dataset.a === genre || line.dataset.b === genre);
        line.classList.toggle('is-hot', hot);
        line.classList.toggle('is-dim', active && !hot);
      });
      chars.forEach((node) => {
        node.classList.toggle('is-related', active && related.has(node.dataset.genre));
      });
    };

    chars.forEach((node) => {
      node.addEventListener('mouseenter', () => highlight(node.dataset.genre, true));
      node.addEventListener('focus', () => highlight(node.dataset.genre, true));
      node.addEventListener('mouseleave', () => highlight(node.dataset.genre, false));
      node.addEventListener('blur', () => highlight(node.dataset.genre, false));
    });
    window.addEventListener('resize', () => {
      if (frame) return;
      frame = window.requestAnimationFrame(draw);
    });
    draw();
  }

  function initWorld() {
    const world = $('#world');
    if (!world) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const spot = $('#world-spot');
    const cursor = $('#world-cursor');
    const ring = $('#pointer-ring');
    const root = document.documentElement;
    let raf = 0;
    let mx = 0;
    let my = 0;
    document.addEventListener('pointermove', (event) => {
      if (raf) return;
      raf = window.requestAnimationFrame(() => {
        raf = 0;
        mx = (event.clientX / window.innerWidth - 0.5) * 36;
        my = (event.clientY / window.innerHeight - 0.5) * 18;
        world.style.setProperty('--wx', mx.toFixed(1) + 'px');
        world.style.setProperty('--wy', my.toFixed(1) + 'px');
        root.style.setProperty('--mx', (event.clientX / window.innerWidth - 0.5).toFixed(3));
        root.style.setProperty('--my', (event.clientY / window.innerHeight - 0.5).toFixed(3));
        if (spot) {
          spot.style.setProperty('--sx', event.clientX + 'px');
          spot.style.setProperty('--sy', event.clientY + 'px');
        }
        if (cursor) {
          cursor.style.setProperty('--sx', event.clientX + 'px');
          cursor.style.setProperty('--sy', event.clientY + 'px');
        }
        if (ring) {
          ring.style.setProperty('--sx', event.clientX + 'px');
          ring.style.setProperty('--sy', event.clientY + 'px');
          ring.classList.add('is-active');
        }
      });
    });
    document.addEventListener('pointerdown', (event) => {
      if (cursor) cursor.classList.add('is-down');
      if (ring) ring.classList.add('is-down');
      if (event.target.closest('button, a, input, select, .dossier, .topbar, .boot')) return;
      const ripple = document.createElement('span');
      ripple.className = 'world__ripple';
      ripple.style.left = event.clientX + 'px';
      ripple.style.top = event.clientY + 'px';
      world.appendChild(ripple);
      window.setTimeout(() => ripple.remove(), 900);
    });
    document.addEventListener('pointerup', () => {
      if (cursor) cursor.classList.remove('is-down');
      if (ring) ring.classList.remove('is-down');
    });
  }

  function setStageGlow(genre) {
    $$('.char').forEach((node) => node.classList.toggle('is-active', node.dataset.genre === genre));
  }

  function initSeason() {
    const rows = state.agg.year_price_rating.filter((row) => row.year >= 2010 && row.year <= 2025);
    const max = Math.max.apply(null, rows.map((row) => row.count)) || 1;
    const eventYears = new Set([2017, 2020, 2024, 2025]);
    const bars = $('#season-bars');
    bars.innerHTML = rows.map((row) => {
      const height = Math.max(3, (row.count / max) * 100);
      return '<button class="season-bar' + (eventYears.has(row.year) ? ' is-event' : '') + '" type="button" data-year="' + row.year + '" title="' + row.year + ' · ' + fmt(row.count) + ' 款">' +
        '<i style="height:' + height.toFixed(2) + '%"></i><span>' + row.year + '</span></button>';
    }).join('');
    bars.addEventListener('click', (event) => {
      const button = event.target.closest('.season-bar');
      if (!button) return;
      setSeason(Number(button.dataset.year));
    });
    const events = $('#season-events');
    if (events) {
      events.addEventListener('click', (event) => {
        const button = event.target.closest('.season-event');
        if (!button) return;
        stopSeason();
        setSeason(Number(button.dataset.year));
      });
    }
    $('#season-play').addEventListener('click', toggleSeason);
    setSeason(state.seasonYear);
  }

  function setSeason(year) {
    const rows = state.agg.year_price_rating;
    const row = rows.find((item) => item.year === year);
    if (!row) return;
    state.seasonYear = year;
    const partial = isPartialYear(year);
    $('#season-year').textContent = String(year) + (partial ? '*' : '');
    const partialNode = $('#season-partial');
    if (partialNode) partialNode.hidden = !partial;
    $('#season-count').textContent = fmt(row.count);
    $('#season-hits').textContent = fmt(row.hits);
    $('#season-price').textContent = Number(row.avgPrice || 0).toFixed(2);
    $('#season-free').textContent = fmt(row.free);
    $$('.season-bar').forEach((bar) => bar.classList.toggle('is-active', Number(bar.dataset.year) === year));
    $$('.season-event').forEach((card) => card.classList.toggle('is-active', Number(card.dataset.year) === year));
    const play = $('#season-play');
    if (year >= 2025) {
      stopSeason();
    }
    void play;
  }

  function toggleSeason() {
    if (state.seasonTimer) {
      stopSeason();
      return;
    }
    setSeason(2010);
    $('#season-play').textContent = '⏸ 暂停回放';
    $('#season-play').classList.add('is-playing');
    state.seasonTimer = window.setInterval(() => {
      if (state.seasonYear >= 2025) {
        stopSeason();
        return;
      }
      setSeason(state.seasonYear + 1);
    }, 760);
  }

  function stopSeason() {
    if (state.seasonTimer) window.clearInterval(state.seasonTimer);
    state.seasonTimer = null;
    const button = $('#season-play');
    if (button) {
      button.textContent = '▶ 播放 16 年';
      button.classList.remove('is-playing');
    }
  }

  function initPrice() {
    if (!state.agg || !window.echarts) return;
    const bands = (state.agg.price_bands || []).filter((row) => row.band !== '未定价');
    const bandBox = $('#price-bands');
    if (bandBox && bands.length) {
      const chart = window.echarts.getInstanceByDom(bandBox) || window.echarts.init(bandBox);
      chart.setOption({
        animation: false,
        grid: { left: 44, right: 18, top: 26, bottom: 34 },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(8,16,24,.97)',
          borderColor: 'rgba(102,192,244,.4)',
          textStyle: { color: '#eaf4fb', fontSize: 11 },
          formatter: (params) => '<b>' + esc(params[0].name) + '</b><br>游戏数：' + fmt(params[0].value) + ' 款',
        },
        xAxis: {
          type: 'category',
          data: bands.map((row) => row.band),
          axisLabel: { color: '#8da4b5', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(142,163,184,.3)' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value',
          name: '款',
          nameTextStyle: { color: '#5f788b', fontSize: 10 },
          axisLabel: { color: '#8da4b5', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(142,163,184,.12)' } },
        },
        series: [{
          type: 'bar',
          barWidth: 26,
          data: bands.map((row, index) => ({
            value: row.count,
            itemStyle: { color: ['#c63b2f', '#d99b2b', '#66c0f4', '#2ec4b6', '#b48cff', '#ff9b8a'][index] },
          })),
          label: { show: true, position: 'top', color: '#dce9f3', fontSize: 9, formatter: (params) => fmt(params.value) },
        }],
      }, true);
    }

    const typeBox = $('#price-type');
    if (!typeBox) return;
    const rows = (state.agg.type_dist || []).filter((row) => row.name !== '其他' && row.count > 0);
    const chart = window.echarts.getInstanceByDom(typeBox) || window.echarts.init(typeBox);
    chart.setOption({
      animation: false,
      grid: { left: 44, right: 20, top: 24, bottom: 36 },
      tooltip: {
        backgroundColor: 'rgba(8,16,24,.97)',
        borderColor: 'rgba(102,192,244,.4)',
        textStyle: { color: '#eaf4fb', fontSize: 11 },
        formatter: (params) => '<b>' + esc(params.name) + '</b><br>均价：$' + params.value[0] + '<br>样本好评率：' + params.value[1] + '%<br>游戏数：' + fmt(params.value[2]),
      },
      xAxis: {
        type: 'value',
        name: '有价均价 / USD',
        nameTextStyle: { color: '#5f788b', fontSize: 10 },
        axisLabel: { color: '#8da4b5', fontSize: 10, formatter: '${value}' },
        splitLine: { lineStyle: { color: 'rgba(142,163,184,.12)' } },
      },
      yAxis: {
        type: 'value',
        name: '好评率 / %',
        min: 50,
        max: 100,
        nameTextStyle: { color: '#5f788b', fontSize: 10 },
        axisLabel: { color: '#8da4b5', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(142,163,184,.12)' } },
      },
      series: [{
        type: 'scatter',
        data: rows.map((row, index) => ({
          name: row.name_cn || row.name,
          value: [row.avgPrice, row.avgRating, row.count],
          itemStyle: { color: ['#c63b2f', '#d99b2b', '#66c0f4', '#2ec4b6', '#b48cff', '#ff9b8a', '#c7f36b', '#ffd166', '#8fb9ff', '#f28b82'][index % 10], opacity: .9 },
        })),
        symbolSize: (value) => Math.max(8, Math.min(28, Math.sqrt(value[2]) / 18)),
        label: { show: true, position: 'top', formatter: (params) => params.name, color: '#dce9f3', fontSize: 9 },
        labelLayout: { hideOverlap: true },
      }],
    }, true);
  }

  function initOnline() {
    const online = state.online;
    const list = $('#arena-list');
    if (!online || !online.top || !online.top.length) {
      list.innerHTML = '<div class="rep-item"><b>实时接口暂不可用</b><span>—</span></div>';
      $('#arena-total').textContent = '—';
      return;
    }
    const top = normalizedTop(online).filter((row) => Number(row.current_players) > 0);
    const valid = top.filter((row) => Number(row.current_players) > 0);
    const missing = top.filter((row) => !(Number(row.current_players) > 0));
    const promoted = top.find((row) => Number(row.promoted_from) > 0);
    const promotedText = promoted
      ? '源榜第 ' + promoted.source_rank + ' 名缺数，用第 ' + promoted.promoted_from + ' 名补足 10 行'
      : '';
    const max = Math.max.apply(null, valid.map((row) => Number(row.current_players) || 0)) || 1;
    const total = valid.reduce((sum, row) => sum + (Number(row.current_players) || 0), 0);
    const top3 = valid.slice(0, 3).reduce((sum, row) => sum + (Number(row.current_players) || 0), 0);
    const lastValid = valid[valid.length - 1];
    const ratio = lastValid && Number(lastValid.current_players) > 0
      ? (Number(valid[0].current_players) / Number(lastValid.current_players)).toFixed(1)
      : '—';
    $('#arena-total').textContent = valid.length ? compact.format(total) : '—';
    $('#arena-total-label').textContent = missing.length
      ? 'TOP10 在线合计（' + valid.length + ' 款有效）'
      : 'TOP10 在线合计';
    const takeaway = $('#arena-takeaway');
    if (takeaway && valid.length) {
      const pct = total ? ((top3 / total) * 100).toFixed(1) : '—';
      takeaway.innerHTML = '<b>结论</b> 前 3 名占 TOP10 在线的 ' + pct + '%，第 1 名是第 '
        + valid.length + ' 名的 ' + ratio + ' 倍。这个差距不是“谁更好玩”造成的，是结构差：榜首这类长期运营的竞技服靠赛季、饰品和社区把人留住，新游再热也攒不够这种常年在线。'
        + (promotedText ? '（' + promotedText + '；显示顺序按当前在线重排，补位者不是原榜第 ' + promoted.source_rank + ' 名。）' : '')
        + (missing.length ? '（有 ' + missing.length + ' 个名次接口没返回，显示“—”，不当作 0 混进总数。）' : '');
    }
    const medals = ['🥇', '🥈', '🥉'];
    list.innerHTML = top.map((row) => {
      const displayRank = Number(row.rank) || 0;
      const sourceRank = Number(row.source_rank) || displayRank;
      const last = Number(row.last_week_rank) || sourceRank;
      const trend = last > sourceRank ? 'up' : last < sourceRank ? 'down' : '';
      const trendText = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '—';
      const players = Number(row.current_players) || 0;
      const width = players > 0 ? Math.max(2, (players / max) * 100) : 0;
      return '<div class="arena-row">' +
        '<span class="arena-row__rank">' + String(displayRank).padStart(2, '0') + '</span>' +
        '<span class="arena-row__medal">' + (medals[displayRank - 1] || '') + '</span>' +        coverMarkup(row.appid, 'arena-thumb', onlineName(row.appid, row.name)) +
        '<span class="arena-row__name">' + esc(onlineName(row.appid, row.name)) + '</span>' +
        '<span class="arena-row__bar"><i style="width:' + width + '%"></i></span>' +
        '<span class="arena-row__num">' + (players > 0 ? compact.format(players) : '—') + '</span>' +
        '<span class="arena-row__trend ' + trend + '">' + trendText + '</span></div>';
    }).join('');
  }

  function initNewReleases() {
    const data = state.newReleases || {};
    const list = $('#new-release-list');
    const note = $('#new-release-note');
    if (!list) return;
    const items = Array.isArray(data.items) ? data.items : [];
    if (!items.length) {
      list.innerHTML = '<p class="new-release__empty">上周新游快照暂未接通。</p>';
      if (note) note.textContent = '没有可用的上周新游数据。';
      return;
    }
    list.innerHTML = items.map((item) => {
      const date = String(item.date || '').slice(5).replace('-', '/');
      const price = item.price ? item.price : '以商店为准';
      return '<div class="new-release__row">' +
        '<span class="new-release__rank">' + String(item.rank).padStart(2, '0') + '</span>' +
        '<span class="new-release__date">' + esc(date) + '</span>' +
        '<div class="new-release__game">' + coverMarkup(item.appid, 'new-release__thumb', item.name) +
          '<div><div class="new-release__name">' + esc(item.name) + '</div>' +
          '<div class="new-release__sub">APP ' + item.appid + ' · ' + esc(price) + '</div></div></div>' +
        '<a class="new-release__store" href="' + esc(item.store || ('https://store.steampowered.com/app/' + item.appid + '/')) + '" target="_blank" rel="noopener">打开商店 ↗</a>' +
        '</div>';
    }).join('');
    if (note) {
      const when = data.fetchedAt ? new Date(data.fetchedAt).toLocaleString('zh-CN', { hour12: false }) : '—';
      note.textContent = (data.downloadsNote || 'Steam 不公开下载量；本页只提供商店下载入口。') + ' 抓取：' + when + '。';
    }
  }

  function initModelLab() {
    const root = $('#model-lab');
    if (!root) return;
    const model = window.MODEL_DATA || state.model;
    const prob = $('#model-prob');
    const bar = $('#model-bar');
    const mark = $('#model-base-mark');
    const verdict = $('#model-verdict');
    const metrics = $('#model-metrics');
    const note = $('#model-note');
    const form = $('#model-form');
    const mainSelect = $('#model-main');
    const freeSelect = $('#model-free');
    const yearInput = $('#model-year');
    const genreBox = $('#model-genres');
    const genreCount = $('#model-genre-count');
    const dots = $('#model-dots');
    const dotsCaption = $('#model-dots-caption');
    const drivers = $('#model-drivers');
    const explain = $('#model-explain');
    const presets = $('#model-presets');

    if (!model || !Array.isArray(model.features) || typeof window.ModelLab === 'undefined') {
      root.classList.add('is-missing');
      prob.textContent = '—';
      verdict.textContent = '模型文件尚未接通；页面不显示假概率。';
      note.textContent = '运行 scripts/train_hot12.py 生成 data/ml/model.json 后，本区自动出现试算。';
      return;
    }

    const mainFeatures = model.features.filter((item) => item.kind === 'main_genre');
    const genreFeatures = model.features.filter((item) => item.kind === 'genre').slice(0, 10);
    mainSelect.innerHTML = mainFeatures.map((item) =>
      '<option value="' + esc(item.value) + '">' + esc(genreLabel(item.value)) + '</option>'
    ).join('');
    if (mainFeatures.some((item) => item.value === 'Indie')) mainSelect.value = 'Indie';

    genreBox.innerHTML = genreFeatures.map((item) =>
      '<label class="model-genre" data-genre="' + esc(item.value) + '">' +
        '<input type="checkbox" value="' + esc(item.value) + '">' +
        '<span>' + esc(genreLabel(item.value)) + '</span>' +
      '</label>'
    ).join('');

    const updateGenreState = () => {
      const boxes = $$('input[type="checkbox"]', genreBox);
      let checked = boxes.filter((box) => box.checked);
      // 兜底：键盘/脚本一次改多个 checkbox 时，也不允许超过 5 个。
      if (checked.length > 5) {
        checked.slice(5).forEach((box) => { box.checked = false; });
        checked = boxes.filter((box) => box.checked);
      }
      genreCount.textContent = checked.length + ' / 5';
      boxes.forEach((box) => {
        const label = box.closest('.model-genre');
        if (!label) return;
        label.classList.toggle('is-on', box.checked);
        const blocked = checked.length >= 5 && !box.checked;
        label.classList.toggle('is-disabled', blocked);
        box.disabled = blocked;
      });
    };

    genreBox.addEventListener('change', () => {
      updateGenreState();
      render();
    });
    updateGenreState();

    const readInput = () => ({
      main_genre: mainSelect.value,
      is_free: Number(freeSelect.value) || 0,
      year: Number(yearInput.value) || 2025,
      genres: $$('input[type="checkbox"]:checked', genreBox).map((box) => box.value),
    });

    const featureContributions = (input) => {
      const rows = [];
      model.features.forEach((feature) => {
        const coef = Number(feature.coef) || 0;
        if (feature.kind === 'main_genre' && input.main_genre === feature.value) {
          rows.push({ label: '主类型 · ' + genreLabel(feature.value), value: coef });
        } else if (feature.kind === 'genre' && input.genres.indexOf(feature.value) !== -1) {
          rows.push({ label: '标签 · ' + genreLabel(feature.value), value: coef });
        } else if (feature.kind === 'numeric') {
          const raw = feature.name === 'year' ? input.year : input.is_free;
          const std = Number(feature.std) || 0;
          const z = std ? (raw - Number(feature.mean)) / std : 0;
          rows.push({
            label: feature.name === 'year' ? '发售年份' : (input.is_free ? '免费模式' : '付费模式'),
            value: coef * z,
          });
        }
      });
      return rows
        .filter((row) => Math.abs(row.value) >= 0.01)
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    };

    const renderDots = (pct, base) => {
      const hot = Math.max(0, Math.min(100, Math.round(pct)));
      dots.innerHTML = Array.from({ length: 100 }, (_, index) =>
        '<span class="' + (index < hot ? 'is-hot' : '') + '"></span>'
      ).join('');
      dotsCaption.textContent = '≈ ' + hot + ' / 100 款达到 1,000 条评价；测试集实际基准约 ' +
        Math.max(0, Math.min(100, Math.round(base * 100))) + ' / 100。';
    };

    const renderDrivers = (rows) => {
      if (!rows.length) {
        drivers.innerHTML = '<p class="model-drivers__title">为什么是这个数</p>' +
          '<p class="model-drivers__empty">这次输入没有触发明显的正/负向特征；模型基本停在截距附近。</p>';
        return;
      }
      const max = Math.max.apply(null, rows.map((row) => Math.abs(row.value)).concat([0.01]));
      drivers.innerHTML = '<p class="model-drivers__title">为什么是这个数 <small>对数几率贡献，不是因果</small></p>' +
        rows.slice(0, 4).map((row) => {
          const width = Math.max(3, Math.round(Math.abs(row.value) / max * 100));
          const up = row.value >= 0;
          return '<div class="model-driver">' +
            '<span class="model-driver__name">' + esc(row.label) + '</span>' +
            '<i class="model-driver__track"><b class="' + (up ? 'is-up' : 'is-down') +
              '" style="width:' + width + '%"></b></i>' +
            '<b class="model-driver__value ' + (up ? 'is-up' : 'is-down') + '">' +
              (up ? '+' : '') + row.value.toFixed(2) + '</b>' +
          '</div>';
        }).join('');
    };

    const render = () => {
      try {
        const input = readInput();
        const p = window.ModelLab.predict(model, input);
        const m = model.metrics.logistic_test || (model.metrics && model.metrics.selected_test) || {};
        const base = Number(m.base_rate || model.base_rate_test || 0);
        const pct = Math.max(0, Math.min(100, p * 100));
        const rows = featureContributions(input);
        prob.textContent = pct.toFixed(1) + '%';
        bar.style.width = pct.toFixed(1) + '%';
        mark.style.left = Math.max(0, Math.min(100, base * 100)).toFixed(1) + '%';
        const delta = (pct - base * 100).toFixed(1);
        verdict.textContent = (p >= base ? '高于' : '低于') + '测试集基准 ' + Math.abs(delta) +
          ' 个百分点；概率是样本估计，不是保证，也不是因果。';
        renderDots(pct, base);
        renderDrivers(rows);
        const positives = rows.filter((row) => row.value > 0).slice(0, 2).map((row) => row.label);
        const negatives = rows.filter((row) => row.value < 0).slice(0, 2).map((row) => row.label);
        const direction = pct >= base * 100 ? '高' : '低';
        explain.textContent = '把这款游戏放进测试集：模型估计 ' + pct.toFixed(1) +
          '%，' + direction + '于 ' + (base * 100).toFixed(1) + '% 的基准。' +
          (positives.length ? '往上推的是 ' + positives.join('、') + '；' : '') +
          (negatives.length ? '往下拉的是 ' + negatives.join('、') + '。' : '') +
          ' 这些是模型相关性，不是“类型决定成败”。';
        const selectedLabel = model.selected === 'histgb' ? '逻辑回归（页面）' : '逻辑回归';
        metrics.innerHTML = [
          ['测试样本', fmt(m.n)],
          ['测试正例', fmt(m.positives)],
          ['基准正例率', share(base * 100)],
          ['PR-AUC', m.pr_auc == null ? '—' : Number(m.pr_auc).toFixed(3)],
          ['Brier', m.brier == null ? '—' : Number(m.brier).toFixed(3)],
          ['Top10% 命中', m.top10_hit == null ? '—' : share(m.top10_hit * 100)],
          ['验证集 PR-AUC', model.metrics.logistic_val ? Number(model.metrics.logistic_val.pr_auc).toFixed(3) : '—'],
          ['模型选择', selectedLabel],
        ].map(([key, value]) => '<div><span>' + key + '</span><b>' + value + '</b></div>').join('');
        const coverage = model.coverage || {};
        note.textContent = '训练 2015–2021 / 验证 2022 / 测试 2023–2025；样本 ' + fmt(coverage.sample) +
          '，标注成功 ' + fmt(coverage.labeled_ok) + '（' + share((coverage.coverage || 0) * 100) + '）。' +
          ' 特征只用发售时的主类型、标签、免费/付费、年份；price 是快照价，未入模。' +
          ' 数据：archive 2026-11-19；标签抓取 2026-11-20。' +
          ' 测试 PR-AUC 未过 base+0.05 门槛，本页只作回测试算。' +
          ' 页面推理用逻辑回归代理，若离线最佳为 HistGB 会在模型卡标注。';
      } catch (error) {
        console.error(error);
        prob.textContent = '—';
        verdict.textContent = '输入无法计算；请检查模型文件和输入值。';
      }
    };

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      render();
    });

    const presetData = {
      indie: { main: 'Indie', free: '0', year: '2025', genres: [] },
      liveops: { main: 'Action', free: '1', year: '2025', genres: ['Free To Play', 'Action'] },
      strategy: { main: 'Strategy', free: '0', year: '2025', genres: ['Strategy', 'Simulation'] },
    };
    const setPresetActive = (key) => {
      $$('.model-presets button', presets).forEach((button) => {
        button.classList.toggle('is-active', button.dataset.preset === key);
      });
    };
    const applyPreset = (key) => {
      const preset = presetData[key];
      if (!preset) return;
      if (mainFeatures.some((item) => item.value === preset.main)) mainSelect.value = preset.main;
      freeSelect.value = preset.free;
      yearInput.value = preset.year;
      $$('input[type="checkbox"]', genreBox).forEach((box) => {
        box.checked = preset.genres.indexOf(box.value) !== -1;
      });
      updateGenreState();
      setPresetActive(key);
      render();
    };
    presets.addEventListener('click', (event) => {
      const button = event.target.closest('[data-preset]');
      if (button) applyPreset(button.dataset.preset);
    });
    form.addEventListener('input', () => {
      setPresetActive('');
      render();
    });

    $('#model-reset').addEventListener('click', () => {
      mainSelect.value = mainFeatures.some((item) => item.value === 'Indie') ? 'Indie' : (mainFeatures[0] && mainFeatures[0].value) || '';
      freeSelect.value = '0';
      yearInput.value = '2025';
      $$('input[type="checkbox"]', genreBox).forEach((box) => { box.checked = false; });
      updateGenreState();
      setPresetActive('');
      render();
    });
    render();
  }

  function initReputation() {
    const map = reviewMap();
    const games = state.reviews.map((item) => {
      const top = state.top500.find((row) => Number(row.appid) === Number(item.appid));
      return Object.assign({}, item, {
        name: top ? top.name : 'APP ' + item.appid,
        genre: top ? top.main_genre : '其他',
        recommendations: top ? top.recommendations : 0,
      });
    });
    const grades = { S: [], A: [], B: [], C: [] };
    games.forEach((game) => {
      const rating = Number(game.rating) || 0;
      if (rating >= 95) grades.S.push(game);
      else if (rating >= 85) grades.A.push(game);
      else if (rating >= 70) grades.B.push(game);
      else grades.C.push(game);
    });
    const wrap = $('#rep-grades');
    wrap.innerHTML = Object.keys(GRADE).map((key) => {
      const grade = GRADE[key];
      return '<button class="grade grade--' + key.toLowerCase() + (state.repGrade === key ? ' is-active' : '') + '" data-grade="' + key + '" type="button">' +
        '<b>' + key + '</b><span>' + grade.label + '</span><span>' + fmt(grades[key].length) + ' 款</span></button>';
    }).join('');
    wrap.addEventListener('click', (event) => {
      const button = event.target.closest('[data-grade]');
      if (!button) return;
      state.repGrade = button.dataset.grade;
      $$('.grade').forEach((node) => node.classList.toggle('is-active', node === button));
      renderReputation(games, grades);
    });
    renderReputation(games, grades);
    renderReputationCloud();
    void map;
  }

  function renderReputationCloud() {
    const cloud = $('#rep-cloud');
    if (!cloud || !window.echarts) return;
    const totals = new Map();
    Object.values(state.agg.sub_tag_dist || {}).forEach((list) => {
      (list || []).forEach((item) => {
        const tag = String(item.tag || '').trim();
        if (!tag || tag === '未标注' || tag === '其他') return;
        totals.set(tag, (totals.get(tag) || 0) + (Number(item.count) || 0));
      });
    });
    const tags = Array.from(totals.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 72)
      .map(([name, value]) => ({ name, value }));
    const palette = ['#66c0f4', '#c7f36b', '#ffd166', '#b48cff', '#2ec4b6', '#ff9b8a'];
    const option = {
      animation: false,
      tooltip: {
        backgroundColor: 'rgba(8,16,24,.97)',
        borderColor: 'rgba(102,192,244,.4)',
        textStyle: { color: '#eaf4fb', fontSize: 11 },
        formatter: (params) => '<b>' + esc(params.name) + '</b><br>样本内出现：' + fmt(params.value) + ' 次',
      },
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '96%',
        height: '96%',
        sizeRange: [12, 54],
        rotationRange: [0, 0],
        gridSize: 5,
        drawOutOfBound: false,
        textStyle: {
          fontFamily: '"Microsoft YaHei", "PingFang SC", sans-serif',
          fontWeight: 700,
          color: (params) => palette[params.dataIndex % palette.length],
        },
        emphasis: { textStyle: { textShadowBlur: 14, textShadowColor: 'rgba(102,192,244,.55)' } },
        data: tags,
      }],
    };
    let chart = window.echarts.getInstanceByDom(cloud);
    if (!chart) chart = window.echarts.init(cloud);
    chart.setOption(option, true);
    chart.off('click');
    chart.on('click', (params) => showTagResult(params.name, totals.get(params.name) || 0));

    const pills = $('#tag-pills');
    if (pills) {
      pills.innerHTML = tags.slice(0, 8).map((item) => '<button type="button" data-tag="' + esc(item.name) + '">#' + esc(item.name) + ' <b>' + fmt(item.value) + '</b></button>').join('');
      pills.querySelectorAll('[data-tag]').forEach((button) => {
        button.addEventListener('click', () => {
          pills.querySelectorAll('[data-tag]').forEach((node) => node.classList.toggle('is-active', node === button));
          showTagResult(button.dataset.tag, totals.get(button.dataset.tag) || 0);
        });
      });
    }
  }

  function showTagResult(tag, sampleCount) {
    const result = $('#tag-result');
    if (!result) return;
    const rows = state.top500.filter((game) => String(game.sub_tags || '').includes(tag)).slice(0, 6);
    const countText = rows.length
      ? 'TOP500 里找到 ' + rows.length + ' 款；全量标签出现 ' + fmt(sampleCount) + ' 次（按类型重复计）。'
      : 'TOP500 里暂无代表作品；全量标签出现 ' + fmt(sampleCount) + ' 次（按类型重复计）。';
    result.innerHTML = '<b>#' + esc(tag) + '</b> · ' + countText +
      (rows.length ? '<br>' + rows.map((game) => '<span class="tag-game">' + esc(game.name) + ' · ' + (Number(game.rating) ? Number(game.rating).toFixed(1) : '—') + '</span>').join('') : '');
  }

  function renderReputation(games, grades) {
    const selected = grades[state.repGrade] || [];
    const list = $('#rep-list');
    list.innerHTML = selected.slice(0, 8).map((game) => (
      '<div class="rep-item"><span><b>' + esc(game.name) + '</b><small>' + esc(TYPE_CN[game.genre] || game.genre) + ' · 评价数 ' + compact.format(game.total_reviews || 0) + '</small></span><span>' + Number(game.rating || 0).toFixed(1) + '</span></div>'
    )).join('') || '<div class="rep-item"><b>暂无该段位样本</b></div>';
    const gradesEl = $('#rep-grades');
    if (gradesEl) {
      const subtitle = gradesEl.parentElement && gradesEl.parentElement.querySelector('.grades-note');
      if (subtitle) subtitle.textContent = '当前显示 ' + fmt(selected.length) + ' 款 · 点击 S/A/B/C 切换榜单';
    }
  }

  function initArchive() {
    const genres = Array.from(new Set(state.top500.map((row) => row.main_genre).filter(Boolean))).sort();
    const select = $('#archive-genre');
    select.innerHTML = '<option value="">全部大类</option>' + genres.map((genre) => '<option value="' + esc(genre) + '">' + esc(TYPE_CN[genre] || genre) + '</option>').join('');
    const input = $('#archive-search');
    const render = () => {
      const query = input.value.trim().toLowerCase();
      const rows = state.top500.filter((row) => {
        if (state.archiveGenre && row.main_genre !== state.archiveGenre) return false;
        if (!query) return true;
        return String(row.name).toLowerCase().includes(query) || String(row.appid).includes(query);
      });
      const body = $('#archive-body');
      body.innerHTML = rows.slice(0, 500).map((row, index) => (
        '<tr data-appid="' + row.appid + '"><td class="dim">' + String(index + 1).padStart(3, '0') + '</td>' +
        '<td><span class="archive-game"><img class="game-thumb" src="https://cdn.akamai.steamstatic.com/steam/apps/' + row.appid + '/header.jpg" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'"><span>' + esc(row.name) + '</span></span></td><td>' + esc(TYPE_CN[row.main_genre] || row.main_genre) + '</td>' +
        '<td class="dim">' + (row.year || '—') + '</td><td class="gold">' + price(row.price) + '</td>' +
        '<td>' + (row.rating ? Number(row.rating).toFixed(1) + '%' : '—') + '</td>' +
        '<td class="gold">' + compact.format(row.recommendations || 0) + '</td></tr>'
      )).join('');
      $('#archive-count').textContent = fmt(rows.length) + ' / ' + fmt(state.top500.length) + ' 条';
    };
    input.addEventListener('input', render);
    select.addEventListener('change', () => { state.archiveGenre = select.value; render(); });
    $('#archive-body').addEventListener('click', (event) => {
      const row = event.target.closest('tr[data-appid]');
      if (!row) return;
      const game = state.top500.find((item) => Number(item.appid) === Number(row.dataset.appid));
      if (game) openDossier(game.main_genre, game.sub_tags);
    });
    render();
  }

  function openDossier(genre, focusTag) {
    const row = typeOf(genre);
    if (!row) return;
    state.selectedGenre = genre;
    setStageGlow(genre);
    $('#dossier').classList.add('is-open');
    $('#dossier').setAttribute('aria-hidden', 'false');
    $('#dossier-backdrop').classList.add('is-open');
    $('#dossier-kicker').textContent = 'ROLE FILE · ' + String(CHARACTER_ORDER.indexOf(genre) + 1).padStart(2, '0');
    $('#dossier-glyph').textContent = genre === '其他' ? '?' : genre.slice(0, 1);
    $('#dossier-name').textContent = row.name_cn || TYPE_CN[genre] || genre;
    $('#dossier-en').textContent = (row.name || genre).toUpperCase() + ' · ' + fmt(row.count) + ' GAMES';
    $('#dossier-count').textContent = fmt(row.count);
    $('#dossier-share').textContent = share(row.share);
    $('#dossier-price').textContent = price(row.avgPrice);
    $('#dossier-rating').textContent = row.avgRating ? Number(row.avgRating).toFixed(1) + '%' : '—';
    ensureDossierNote();
    renderDossierTrend(genre);
    renderDossierTags(genre, focusTag);
    renderDossierGames(genre, focusTag);
  }

  function closeDossier() {
    $('#dossier').classList.remove('is-open');
    $('#dossier').setAttribute('aria-hidden', 'true');
    $('#dossier-backdrop').classList.remove('is-open');
    setStageGlow(null);
  }

  function renderDossierTrend(genre) {
    const chart = window.echarts && window.echarts.getInstanceByDom($('#dossier-trend'));
    const source = (state.agg.type_x_year || []).find((row) => row.name === genre);
    const values = source ? source.values : {};
    const years = [];
    for (let year = 2010; year <= 2025; year += 1) years.push(String(year));
    const option = {
      animation: false,
      grid: { left: 28, right: 8, top: 12, bottom: 20 },
      xAxis: { type: 'category', data: years, axisLabel: { color: '#9a8062', fontSize: 7, interval: 3 }, axisLine: { show: false }, axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: '#9a8062', fontSize: 7 }, splitLine: { lineStyle: { color: 'rgba(36,31,24,.09)' } } },
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(36,31,24,.95)', textStyle: { color: '#f8efd9', fontSize: 10 } },
      series: [{ type: 'line', data: years.map((year) => Number(values[year]) || 0), symbol: 'none', lineStyle: { color: '#c4583b', width: 1.6 }, areaStyle: { color: 'rgba(196,88,59,.18)' } }],
    };
    if (chart) chart.setOption(option, true);
    else if (window.echarts) window.echarts.init($('#dossier-trend')).setOption(option);
  }

  function renderDossierTags(genre, focusTag) {
    const tags = ((state.agg.sub_tag_dist[genre] || []).slice(0, 12));
    const wrap = $('#dossier-tags');
    wrap.innerHTML = tags.map((item) => '<button class="chip" data-tag="' + esc(item.tag) + '">' + esc(item.tag) + '<b>' + fmt(item.count) + '</b></button>').join('') || '<span class="dossier__note">该类型暂无小标签统计</span>';
    wrap.querySelectorAll('[data-tag]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.tag === focusTag);
      button.addEventListener('click', () => {
        $('#dossier-tags').querySelectorAll('[data-tag]').forEach((node) => node.classList.toggle('is-active', node === button));
        renderDossierGames(genre, button.dataset.tag);
      });
    });
  }

  function renderDossierGames(genre, focusTag) {
    const games = typeGames(genre);
    const rows = games.filter((game) => Number(game.recommendations) > 0 && game.rating != null && (!focusTag || String(game.sub_tags || '').includes(focusTag)));
    const wrap = $('#dossier-games');
    $('#dossier-games-count').textContent = rows.length + ' 款 · 按推荐数';
    if (!rows.length) {
      const tagRow = (state.agg.sub_tag_dist[genre] || []).find((item) => item.tag === focusTag);
      const totalTag = tagRow ? Number(tagRow.count) : 0;
      wrap.innerHTML = '<div class="dossier__note">' + (totalTag
        ? 'TOP 榜内暂无代表作品（全量 ' + fmt(totalTag) + ' 款，未进前 50）'
        : '该小标签下无匹配游戏') + '</div>';
      return;
    }
    wrap.innerHTML = rows.slice(0, 6).map((game) => (
      '<a class="game-row" href="' + esc(game.url || '#') + '" target="_blank" rel="noreferrer"><img class="game-thumb game-thumb--row" src="https://cdn.akamai.steamstatic.com/steam/apps/' + game.appid + '/header.jpg" alt="" loading="lazy" onerror="this.style.visibility=\'hidden\'"><span><b>' + esc(game.name) + '</b><small>' + esc(game.genres || '') + ' · ' + (game.year || '年份未知') + '</small></span><span>' + (game.rating ? Number(game.rating).toFixed(1) : '—') + '</span></a>'
    )).join('');
  }

  function ensureDossierNote() {
    if ($('#dossier-tags-note')) return;
    const tags = $('#dossier-tags');
    if (!tags) return;
    const note = document.createElement('p');
    note.id = 'dossier-tags-note';
    note.className = 'dossier__note';
    note.textContent = '类型统计与代表作品按 Steam 多主类型归属，数量可重叠；小标签数量基于描述关键词推断，非官方精确值';
    tags.insertAdjacentElement('afterend', note);
  }

  function initArchiveGenreScroll() {
    $$('.char').forEach((button) => {
      if (button.dataset.genre) button.addEventListener('mouseleave', () => setStageGlow(null));
    });
    $('#dossier-close').addEventListener('click', closeDossier);
    $('#dossier-backdrop').addEventListener('click', closeDossier);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') closeDossier();
    });
  }

  function initCycle() {
    const box = $('#cycle-chart');
    if (!box || !window.echarts || !state.agg) return;
    const years = (state.agg.type_x_year_years || []).filter((y) => /^\d+$/.test(y) && Number(y) >= 2010 && Number(y) <= 2025);
    const rows = (state.agg.type_x_year || []).filter((row) => row.name !== '其他');
    if (!years.length || !rows.length) return;
    const counts = rows.map((row) => years.map((year) => Number(row.values[year]) || 0));
    const yearlyTotal = years.map((_, xi) => counts.reduce((sum, row) => sum + row[xi], 0));
    const maxCount = Math.max(...counts.flat());
    let mode = 'share';
    const chart = window.echarts.init(box);

    function render() {
      const data = [];
      rows.forEach((row, yi) => years.forEach((year, xi) => {
        const count = counts[yi][xi];
        const share = yearlyTotal[xi] ? (count / yearlyTotal[xi]) * 100 : 0;
        data.push({
          value: [xi, yi, mode === 'share' ? Number(share.toFixed(1)) : count],
          raw: count,
          share: share,
          year: year,
          row: yi,
        });
      }));
      const max = mode === 'share'
        ? Math.max(...data.map((item) => item.value[2]))
        : maxCount;
      chart.setOption({
        backgroundColor: 'transparent',
        animationDuration: 420,
        grid: { left: 86, right: 44, top: 18, bottom: 56 },
        tooltip: {
          backgroundColor: 'rgba(7, 15, 22, .96)',
          borderColor: 'rgba(102, 192, 244, .35)',
          textStyle: { color: '#e7f2fa', fontSize: 11 },
          formatter: (params) => {
            const item = data[params.dataIndex];
            const row = rows[item.row];
            return row.name_cn + ' · ' + item.year + '<br>上架：' + item.raw.toLocaleString('en-US') + ' 款<br>份额：' + item.share.toFixed(1) + '%';
          },
        },
        xAxis: {
          type: 'category',
          data: years,
          axisLabel: { color: '#8ea5b7', fontSize: 9, rotate: 45 },
          axisLine: { lineStyle: { color: 'rgba(142, 165, 183, .24)' } },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'category',
          data: rows.map((row) => row.name_cn),
          axisLabel: { color: '#cfe0ec', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(142, 165, 183, .24)' } },
          axisTick: { show: false },
        },
        visualMap: {
          min: 0,
          max: max || 1,
          calculable: false,
          orient: 'vertical',
          right: 4,
          top: 'center',
          itemWidth: 9,
          itemHeight: 88,
          text: mode === 'share' ? ['份额高', '份额低'] : ['上架多', '上架少'],
          textStyle: { color: '#8ea5b7', fontSize: 9 },
          inRange: { color: ['#0b1a24', '#15445b', '#2f8fae', '#66c0f4', '#f2c94c'] },
        },
        series: [{
          type: 'heatmap',
          data: data,
          itemStyle: { borderColor: 'rgba(6, 14, 21, .8)', borderWidth: 2 },
          emphasis: { itemStyle: { borderColor: '#f2c94c', borderWidth: 1 } },
        }],
      }, true);
    }

    $('#cycle-top').innerHTML = rows.map((row) => {
      const first = Number(row.values[years[0]]) || 0;
      const last = Number(row.values[years[years.length - 1]]) || 0;
      return { name: row.name_cn, delta: last - first, last: last };
    }).sort((a, b) => b.delta - a.delta).slice(0, 4).map((row, index) => (
      '<li><span>' + String(index + 1).padStart(2, '0') + '</span><b>' + esc(row.name) + '</b><em>+' + row.delta.toLocaleString('en-US') + '</em></li>'
    )).join('');

    $$('[data-cycle-mode]').forEach((button) => {
      button.addEventListener('click', () => {
        mode = button.dataset.cycleMode;
        $$('[data-cycle-mode]').forEach((node) => node.classList.toggle('is-on', node === button));
        render();
      });
    });
    chart.on('click', (params) => {
      const item = data[params.dataIndex];
      if (item) openDossier(rows[item.row].name);
    });
    window.addEventListener('resize', () => chart.resize());
    render();
  }

  function renderSensitivity() {
    const box = $('#sensitivity');
    if (!box || !state.reviews.length) return;
    const thresholds = [0, 100, 1000, 10000];
    const lines = thresholds.map((threshold) => {
      const sample = state.reviews.filter((item) => Number(item.total_reviews) >= threshold);
      const counts = { S: 0, A: 0, B: 0, C: 0 };
      sample.forEach((item) => {
        const rating = Number(item.rating) || 0;
        if (rating >= 95) counts.S += 1;
        else if (rating >= 85) counts.A += 1;
        else if (rating >= 70) counts.B += 1;
        else counts.C += 1;
      });
      return '≥' + (threshold === 0 ? '0' : threshold.toLocaleString('en-US')) + ' 评：' +
        'S ' + counts.S + ' / A ' + counts.A + ' / B ' + counts.B + ' / C ' + counts.C +
        '（n=' + sample.length + '）';
    });
    box.textContent = '评价数门槛敏感性：' + lines.join('；') + '。分档方向稳定，但小样本档位会更少。';
  }

  function initNav() {
    const links = $$('.topnav a');
    const wings = ['brief', 'lobby', 'cycle', 'season', 'price', 'reputation', 'archive'].map((id) => document.getElementById(id)).filter(Boolean);
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        links.forEach((link) => link.classList.toggle('is-active', link.getAttribute('href') === '#' + visible.target.id));
      }, { rootMargin: '-30% 0px -55% 0px', threshold: [0.05, 0.3, 0.6] });
      wings.forEach((wing) => observer.observe(wing));

      // 单独一个宽松的观察器：wing 一进入视口大半就加 is-live，触发两侧角色入场
      const enterObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('is-live');
        });
      }, { rootMargin: '0px 0px -15% 0px', threshold: 0.2 });
      wings.forEach((wing) => enterObserver.observe(wing));
    }
  }

  function bindEnter() {
    const print = $('#print-report');
    if (print) print.addEventListener('click', () => window.print());
    const button = $('#enter-hall');
    if (!button) return;
    button.addEventListener('click', () => {
      hideBoot();
      const stage = $('#hall-stage');
      if (stage) stage.classList.add('is-live');
      $('#brief').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // 封面放大：用 fixed 预览层，不改变表格/榜单布局，也不会被 overflow 裁切。
  function initThumbZoom() {
    if ($('.thumb-zoom')) return;
    const box = document.createElement('div');
    box.className = 'thumb-zoom';
    box.setAttribute('aria-hidden', 'true');
    const image = document.createElement('img');
    image.alt = '';
    box.appendChild(image);
    document.body.appendChild(box);

    const move = (event) => {
      const width = 360;
      const height = 190;
      // 跟随鼠标：右下偏移；靠边时翻到左侧/上方，保证不出视口。
      let left = event.clientX + 18;
      let top = event.clientY + 18;
      if (left + width > window.innerWidth - 12) left = event.clientX - width - 18;
      if (top + height > window.innerHeight - 12) top = event.clientY - height - 18;
      box.style.left = Math.max(12, left) + 'px';
      box.style.top = Math.max(12, top) + 'px';
    };

    const hide = () => box.classList.remove('is-visible');

    document.addEventListener('pointerover', (event) => {
      const target = event.target instanceof Element ? event.target.closest('.arena-thumb, .game-thumb, .new-release__thumb') : null;
      if (!target || !target.getAttribute('src')) return;
      image.src = target.currentSrc || target.src;
      box.classList.add('is-visible');
      move(event);
    });
    document.addEventListener('pointermove', (event) => {
      if (box.classList.contains('is-visible')) move(event);
    });
    document.addEventListener('pointerout', (event) => {
      if (event.target instanceof Element && event.target.closest('.arena-thumb, .game-thumb, .new-release__thumb')) hide();
    });
    window.addEventListener('scroll', hide, { passive: true });
  }

  function resizePrintCharts() {
    if (!window.echarts) return;
    $$('.chart, .cycle__chart, #dossier-trend').forEach((node) => {
      const chart = window.echarts.getInstanceByDom(node);
      if (chart) chart.resize();
    });
  }

  window.addEventListener('beforeprint', resizePrintCharts);
  window.addEventListener('afterprint', resizePrintCharts);

  async function init() {
    bindEnter();
    initBootVideo();
    initThumbZoom();
    initArchiveGenreScroll();
    try {
      const [agg, reviews, top500, online, newReleases, model] = await Promise.all([
        loadData('/api/market/agg', 'data/market/market_agg.json', 'agg'),
        loadData('/api/market/reviews', 'data/market/reviews_enriched.json', 'reviews'),
        loadData('/api/market/top500', 'data/market/top500.json', 'top500'),
        loadData('/api/online', 'data/online.json', 'online').catch(() => ({ top: [] })),
        loadData('/api/new-releases', 'data/new_releases.json', 'newReleases').catch(() => ({ items: [] })),
        loadData('/api/ml/model', 'data/ml/model.json', 'model').catch(() => null),
      ]);
      state.agg = agg;
      state.reviews = reviews.items || [];
      state.top500 = top500;
      state.online = online;
      state.newReleases = newReleases;
      state.model = model;
      $('#boot-hint').textContent = '已接通 150,279 款全量快照';
      initMeta();
      initLobby();
      initCycle();
      initSeason();
      initPrice();
      initOnline();
      initNewReleases();
      initModelLab();
      initReputation();
      renderSensitivity();
      initArchive();
      initNav();
      window.setTimeout(() => $('#boot-hint').textContent = '已接通 150,279 款全量快照 · 点击进入', 400);
    } catch (error) {
      console.error(error);
      setBootError('数据未接通：请用 VSCode Live Server 打开本页，或在项目根目录运行 node server.js 后访问 http://localhost:8081/');
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
