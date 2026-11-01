
(function () {
  const Core = window.InsightCore;
  const { RATING_BANDS, PALETTE, $ } = Core;

  const state = {
    games: [],
    source: 'api',
    bandKey: '',
    type: '',
    query: '',
    minReviews: 1000,
    range: null,
    sortKey: 'rating',
    sortDir: 'desc',
    selectedAppid: null,
  };

  const charts = [];
  let lastFocus = null;

  const MIN_REVIEW_OPTIONS = [
    { value: 0, label: '全部' },
    { value: 100, label: '100+' },
    { value: 1000, label: '1000+' },
    { value: 10000, label: '1万+' },
    { value: 100000, label: '10万+' },
  ];

  function bandByKey(key) {
    return RATING_BANDS.find((band) => band.key === key) || null;
  }

  function typeFilteredGames() {
    return state.games.filter((game) => {
      if (state.type && game.type !== state.type) return false;
      if (state.query && !game.name.toLowerCase().includes(state.query.toLowerCase())) return false;
      return true;
    });
  }

  function filteredGames() {
    const base = typeFilteredGames();
    return base.filter((game) => {
      if (state.bandKey && Core.bandOf(game.rating).key !== state.bandKey) return false;
      if (state.range && (game.rating < state.range[0] || game.rating >= state.range[1])) return false;
      return true;
    });
  }

  function sortedGames(list) {
    const dir = state.sortDir === 'asc' ? 1 : -1;
    return list.slice().sort((a, b) => {
      const av = a[state.sortKey];
      const bv = b[state.sortKey];
      if (typeof av === 'string') return av.localeCompare(bv, 'zh-CN') * dir;
      return (Number(av) - Number(bv)) * dir;
    });
  }

  function initChart(id) {
    const el = $(id);
    if (!el) return null;
    const chart = echarts.init(el);
    charts.push(chart);
    return chart;
  }

  /* ---------------- 顶部 KPI ---------------- */
  function renderKpis() {
    const totalReviews = Core.sum(state.games, (game) => game.total_reviews);
    const mixed = state.games.filter((game) => {
      const key = Core.bandOf(game.rating).key;
      return key === 'mixed' || key === 'negative';
    }).length;
    document.querySelectorAll('[data-kpi="games"]').forEach((el) => (el.textContent = state.games.length));
    document.querySelectorAll('[data-kpi="weighted"]').forEach((el) => (el.textContent = `${Core.fmt1(Core.weightedRating(state.games))}%`));
    document.querySelectorAll('[data-kpi="reviews"]').forEach((el) => (el.textContent = Core.formatWan(totalReviews)));
    document.querySelectorAll('[data-kpi="mixed"]').forEach((el) => (el.textContent = mixed));
  }

  /* ---------------- 分档卡 ---------------- */
  function renderBandCards() {
    const base = typeFilteredGames();
    const total = base.length || 1;
    const host = $('bandCards');
    host.innerHTML = RATING_BANDS.map((band) => {
      const count = base.filter((game) => Core.bandOf(game.rating).key === band.key).length;
      const active = state.bandKey === band.key;
      return `
        <button class="band-card${active ? ' is-active' : ''}" type="button"
          data-band="${band.key}" aria-pressed="${active}"
          style="--band-color:${band.color}">
          <span class="band-card__label">${band.label}</span>
          <strong class="band-card__count">${count}</strong>
          <span class="band-card__share">${((count / total) * 100).toFixed(1)}% · ${band.short}</span>
          <span class="band-card__bar"><i style="--w:${(count / total) * 100}%"></i></span>
        </button>`;
    }).join('');

    host.querySelectorAll('.band-card').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.dataset.band;
        state.bandKey = state.bandKey === key ? '' : key;
        state.range = null;
        renderAllFilters();
      });
    });
  }

  /* ---------------- 分布直方图 ---------------- */
  function chartHistogram() {
    const chart = initChart('chart-histogram');
    if (!chart) return;

    function option() {
      const base = typeFilteredGames();
      const bins = Array.from({ length: 10 }, (_, index) => {
        const from = index * 10;
        const to = from + 10;
        const list = base.filter((game) => game.rating >= from && game.rating < (to === 100 ? 101 : to));
        return {
          from,
          to,
          count: list.length,
          weighted: list.length ? Core.weightedRating(list) : 0,
          color: Core.bandOf(from + 5).color,
        };
      });
      const selectedBand = bandByKey(state.bandKey);

      return {
        ...Core.chartBase(),
        grid: { left: 34, right: 14, top: 28, bottom: 28 },
        tooltip: {
          ...Core.chartBase().tooltip,
          formatter: (params) => {
            const bin = bins[params.dataIndex];
            return `${bin.from}–${bin.to} 分<br>游戏数：${bin.count} 款<br>占当前样本：${((bin.count / Math.max(1, base.length)) * 100).toFixed(1)}%<br><span style="color:#f2c94c">点击筛选这一档</span>`;
          },
        },
        xAxis: {
          type: 'category',
          data: bins.map((bin) => (bin.to === 100 ? '90–100' : `${bin.from}–${bin.to}`)),
          ...Core.axisStyle,
          axisLabel: { ...Core.axisStyle.axisLabel, fontSize: 9 },
        },
        yAxis: {
          type: 'value',
          ...Core.axisStyle,
          splitLine: { lineStyle: { color: 'rgba(33,28,21,.12)', type: 'dashed' } },
        },
        series: [{
          type: 'bar',
          barMaxWidth: 28,
          data: bins.map((bin) => {
            const selected = state.range
              ? state.range[0] === bin.from
              : selectedBand
                ? selectedBand.key === Core.bandOf(bin.from + 5).key
                : false;
            return {
              value: bin.count,
              itemStyle: {
                color: selected ? '#c63b2f' : bin.color,
                opacity: (state.range || selectedBand) && !selected ? 0.28 : 1,
                borderColor: '#211c15',
                borderWidth: 1,
              },
            };
          }),
          label: {
            show: true,
            position: 'top',
            color: '#211c15',
            fontSize: 9,
          },
        }],
      };
    }

    chart.setOption(option(), true);
    chart.on('click', (params) => {
      const from = params.dataIndex * 10;
      const to = from === 90 ? 101 : from + 10;
      const same = state.range && state.range[0] === from;
      state.range = same ? null : [from, to];
      state.bandKey = '';
      renderAllFilters();
    });
    return { chart, option };
  }

  /* ---------------- 类型口碑 ---------------- */
  function chartTypeRating() {
    const chart = initChart('chart-type-rating');
    if (!chart) return;

    function option() {
      const map = new Map();
      state.games.forEach((game) => {
        if (!map.has(game.type)) map.set(game.type, []);
        map.get(game.type).push(game);
      });
      const rows = [...map.entries()].map(([type, list]) => ({
        type,
        count: list.length,
        rating: Core.weightedRating(list),
      })).sort((a, b) => a.rating - b.rating);

      return {
        ...Core.chartBase(),
        grid: { left: 74, right: 42, top: 10, bottom: 22 },
        tooltip: {
          ...Core.chartBase().tooltip,
          formatter: (params) => {
            const row = rows[params.dataIndex];
            return `${row.type}<br>样本：${row.count} 款<br>加权好评率：${Core.fmt1(row.rating)}%<br><span style="color:#f2c94c">点击按类型筛选</span>`;
          },
        },
        xAxis: {
          type: 'value',
          min: 0,
          max: 100,
          ...Core.axisStyle,
          axisLabel: { ...Core.axisStyle.axisLabel, fontSize: 9 },
        },
        yAxis: {
          type: 'category',
          data: rows.map((row) => `${row.type}`),
          ...Core.axisStyle,
          axisLabel: {
            ...Core.axisStyle.axisLabel,
            fontSize: 10,
            fontWeight: 700,
            formatter: (value) => value,
          },
        },
        series: [{
          type: 'bar',
          barMaxWidth: 17,
          data: rows.map((row) => ({
            value: row.rating,
            itemStyle: {
              color: state.type === row.type ? '#c63b2f' : (row.count < 4 ? '#b8a37f' : '#2f7f74'),
              opacity: state.type && state.type !== row.type ? 0.28 : 1,
              borderColor: '#211c15',
              borderWidth: 1,
            },
          })),
          label: {
            show: true,
            position: 'right',
            color: '#211c15',
            fontSize: 9,
            formatter: (params) => `${Core.fmt1(params.value)}%  (${rows[params.dataIndex].count})`,
          },
        }],
      };
    }

    chart.setOption(option(), true);
    chart.on('click', (params) => {
      const row = params.dataIndex;
      const type = chart.getOption().yAxis[0].data[row];
      state.type = state.type === type ? '' : type;
      syncTypeSelect();
      renderAllFilters();
    });
    return { chart, option };
  }

  /* ---------------- 可信榜 ---------------- */
  function renderRankings() {
    const pool = state.games.filter((game) => game.total_reviews >= state.minReviews);
    const top = pool.slice().sort((a, b) => b.rating - a.rating || b.total_reviews - a.total_reviews).slice(0, 6);
    const bottom = pool.slice().sort((a, b) => a.rating - b.rating || b.total_reviews - a.total_reviews).slice(0, 6);

    const rowHtml = (game, index) => {
      const band = Core.bandOf(game.rating);
      return `
        <li>
          <button class="rank-row" type="button" data-appid="${game.appid}">
            <span class="rank-row__no">${String(index + 1).padStart(2, '0')}</span>
            <span class="rank-row__main">
              <span class="rank-row__name">${Core.escapeHtml(game.name)}</span>
              <span class="rank-row__meta">${Core.escapeHtml(game.type)} · ${game.year || '—'} · ${Core.formatWan(game.total_reviews)} 条评价</span>
            </span>
            <span class="rank-row__score">
              <strong style="color:${band.color}">${Core.fmt1(game.rating)}</strong>
              <small>好评率</small>
            </span>
            <span class="rank-row__bar"><i style="--w:${game.rating}%;--bar:${band.color}"></i></span>
          </button>
        </li>`;
    };

    $('topRanking').innerHTML = top.length ? top.map(rowHtml).join('') : '<li class="table-empty">这个门槛下没有足够样本。</li>';
    $('bottomRanking').innerHTML = bottom.length ? bottom.map(rowHtml).join('') : '<li class="table-empty">这个门槛下没有足够样本。</li>';
    $('topRankHint').textContent = `${pool.length} 款达到 ${state.minReviews ? Core.formatNumber(state.minReviews) + ' 条' : '任意评价数'}`;
    $('bottomRankHint').textContent = `${pool.length} 款样本`;
    document.querySelectorAll('.rank-row').forEach((button) => {
      button.addEventListener('click', () => {
        const game = state.games.find((item) => item.appid === Number(button.dataset.appid));
        if (game) openDrawer(game);
      });
    });
  }

  /* ---------------- 评价数 × 分数散点 ---------------- */
  function chartScatter() {
    const chart = initChart('chart-review-scatter');
    if (!chart) return;

    function option() {
      return {
        ...Core.chartBase(),
        grid: { left: 48, right: 20, top: 22, bottom: 38 },
        tooltip: {
          ...Core.chartBase().tooltip,
          formatter: (params) => {
            const game = state.games[params.dataIndex];
            return `${Core.escapeHtml(game.name)}<br>类型：${Core.escapeHtml(game.type)}<br>好评率：${Core.fmt1(game.rating)}%<br>评价数：${Core.formatNumber(game.total_reviews)} 条<br>价格：${Core.formatPrice(game.price)}<br><span style="color:#f2c94c">点击按该口碑筛选</span>`;
          },
        },
        xAxis: {
          type: 'log',
          name: '评价数',
          nameLocation: 'middle',
          nameGap: 26,
          min: 1,
          ...Core.axisStyle,
          axisLabel: {
            ...Core.axisStyle.axisLabel,
            fontSize: 9,
            formatter: (value) => (value >= 10000 ? `${value / 10000}万` : value),
          },
        },
        yAxis: {
          type: 'value',
          name: '好评率 /%',
          min: 30,
          max: 100,
          ...Core.axisStyle,
        },
        series: [{
          type: 'scatter',
          data: state.games.map((game) => [Math.max(1, game.total_reviews), game.rating]),
          symbolSize: (value) => Math.max(7, Math.min(34, Math.sqrt(value[0]) / 32)),
          itemStyle: {
            color: (params) => Core.bandOf(params.value[1]).color,
            opacity: (params) => (state.bandKey && Core.bandOf(params.value[1]).key !== state.bandKey ? 0.22 : 0.82),
            borderColor: '#211c15',
            borderWidth: 1,
          },
          emphasis: {
            scale: 1.25,
            itemStyle: { borderWidth: 2 },
          },
        }],
      };
    }

    chart.setOption(option(), true);
    chart.on('click', (params) => {
      const game = state.games[params.dataIndex];
      if (!game) return;
      const band = Core.bandOf(game.rating).key;
      state.bandKey = state.bandKey === band ? '' : band;
      state.range = null;
      syncBandSelect();
      renderAllFilters();
    });
    return { chart, option };
  }

  /* ---------------- 表格 ---------------- */
  function renderTable() {
    const list = sortedGames(filteredGames());
    const body = $('tableBody');
    const empty = $('tableEmpty');
    const wrap = $('tableWrap');
    body.innerHTML = list.map((game) => {
      const band = Core.bandOf(game.rating);
      const selected = state.selectedAppid === game.appid;
      return `
        <tr data-appid="${game.appid}" class="${selected ? 'is-selected' : ''}" tabindex="0">
          <td><span class="rating-mark" style="--mark:${band.color}"></span>${Core.escapeHtml(game.name)}</td>
          <td class="muted">${Core.escapeHtml(game.type)}</td>
          <td class="num">${Core.formatPrice(game.price)}</td>
          <td class="num">${Core.fmt1(game.rating)}</td>
          <td class="num">${Core.formatNumber(game.total_reviews)}</td>
          <td class="num muted">${game.year || '—'}</td>
        </tr>`;
    }).join('');

    empty.hidden = list.length > 0;
    wrap.querySelector('table').hidden = list.length === 0;
    wrap.hidden = false;
    $('filterCount').textContent = `${list.length} / ${state.games.length}`;
    $('tableCount').textContent = `${list.length} 行`;

    body.querySelectorAll('tr').forEach((row) => {
      const open = () => {
        const game = state.games.find((item) => item.appid === Number(row.dataset.appid));
        if (game) openDrawer(game);
      };
      row.addEventListener('click', open);
      row.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          open();
        }
      });
    });
  }

  function fillSelects() {
    const typeSelect = $('typeFilter');
    const counts = new Map();
    state.games.forEach((game) => counts.set(game.type, (counts.get(game.type) || 0) + 1));
    const options = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    typeSelect.innerHTML = '<option value="">全部类型</option>' + options.map(([type, count]) => `<option value="${Core.escapeHtml(type)}">${Core.escapeHtml(type)} · ${count}</option>`).join('');

    const bandSelect = $('bandFilter');
    bandSelect.innerHTML = '<option value="">全部口碑</option>' + RATING_BANDS.map((band) => `<option value="${band.key}">${band.label} · ${band.short}</option>`).join('');
  }

  function syncTypeSelect() {
    $('typeFilter').value = state.type;
  }

  function syncBandSelect() {
    $('bandFilter').value = state.bandKey;
  }

  function updateUrl() {
    try {
      const params = new URLSearchParams();
      if (state.bandKey) params.set('band', state.bandKey);
      if (state.type) params.set('type', state.type);
      if (state.query) params.set('q', state.query);
      if (state.minReviews) params.set('min', state.minReviews);
      const url = `${location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
      history.replaceState(null, '', url);
    } catch (error) {
      // file:// 下可能不支持，忽略即可
    }
  }

  function readUrl() {
    try {
      const params = new URLSearchParams(location.search);
      const band = params.get('band');
      if (band && bandByKey(band)) state.bandKey = band;
      state.type = params.get('type') || '';
      state.query = params.get('q') || '';
      const min = Number(params.get('min'));
      if (MIN_REVIEW_OPTIONS.some((option) => option.value === min)) state.minReviews = min;
      $('searchFilter').value = state.query;
    } catch (error) { }
  }

  function renderFilterSummary() {
    const list = filteredGames();
    const parts = [`当前显示 ${list.length} 款`];
    parts.push(state.type ? `类型：${state.type}` : '全类型');
    if (state.bandKey) parts.push(`口碑：${bandByKey(state.bandKey).label}`);
    else if (state.range) parts.push(`分数：${state.range[0]}–${state.range[1]}`);
    else parts.push('全部口碑');
    $('filterSummary').textContent = parts.join(' · ');
    $('resetBand').disabled = !state.bandKey && !state.range && !state.type;
  }

  function renderMinReviewSeg() {
    const host = $('minReviewSeg');
    host.innerHTML = MIN_REVIEW_OPTIONS.map((option) => `
      <button type="button" data-min="${option.value}" class="${state.minReviews === option.value ? 'is-active' : ''}" aria-pressed="${state.minReviews === option.value}">${option.label}</button>`).join('');
    host.querySelectorAll('button').forEach((button) => {
      button.addEventListener('click', () => {
        state.minReviews = Number(button.dataset.min);
        renderMinReviewSeg();
        renderRankings();
        updateUrl();
      });
    });
  }

  function renderAllFilters() {
    renderBandCards();
    renderHistogram();
    renderTypeRating();
    renderRankings();
    renderScatter();
    renderTable();
    renderFilterSummary();
    syncTypeSelect();
    syncBandSelect();
    updateUrl();
  }

  let histogramChart = null;
  let typeChart = null;
  let scatterChart = null;

  function renderHistogram() {
    if (!histogramChart) return;
    histogramChart.setOption(histogramChart.__option(), true);
  }

  function renderTypeRating() {
    if (!typeChart) return;
    typeChart.setOption(typeChart.__option(), true);
  }

  function renderScatter() {
    if (!scatterChart) return;
    scatterChart.setOption(scatterChart.__option(), true);
  }

  function openDrawer(game) {
    lastFocus = document.activeElement;
    state.selectedAppid = game.appid;
    const band = Core.bandOf(game.rating);
    $('drawerType').textContent = `${game.type} · ${game.year || '年份未知'}`;
    $('drawerName').textContent = game.name;
    $('drawerRating').textContent = Core.fmt1(game.rating);
    $('drawerBand').textContent = `${band.label} · ${band.short}`;
    $('drawerBand').style.background = band.color;
    $('drawerBand').style.color = band.light ? '#211c15' : '#fbf3e2';
    $('drawerMeter').style.width = `${game.rating}%`;
    $('drawerReviews').textContent = `${Core.formatNumber(game.total_reviews)} 条`;
    $('drawerPrice').textContent = Core.formatPrice(game.price);
    $('drawerYear').textContent = game.year || '—';
    $('drawerMainType').textContent = game.type;
    $('drawerTags').textContent = game.genres || '暂无标签';
    $('drawerLink').href = game.url;
    $('drawerBackdrop').hidden = false;
    $('gameDrawer').hidden = false;
    $('gameDrawer').setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
    requestAnimationFrame(() => $('gameDrawer').classList.add('is-open'));
    $('drawerClose').focus();
    try {
      const params = new URLSearchParams(location.search);
      params.set('game', String(game.appid));
      history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
    } catch (error) { }
    renderTable();
  }

  function closeDrawer() {
    const drawer = $('gameDrawer');
    drawer.classList.remove('is-open');
    drawer.setAttribute('aria-hidden', 'true');
    $('drawerBackdrop').hidden = true;
    document.body.classList.remove('drawer-open');
    window.setTimeout(() => {
      drawer.hidden = true;
    }, 220);
    state.selectedAppid = null;
    try {
      const params = new URLSearchParams(location.search);
      params.delete('game');
      history.replaceState(null, '', `${location.pathname}${params.toString() ? '?' + params.toString() : ''}`);
    } catch (error) { }
    renderTable();
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
  }

  function bindEvents() {
    $('resetBand').addEventListener('click', () => {
      state.bandKey = '';
      state.range = null;
      state.type = '';
      renderAllFilters();
    });

    $('typeFilter').addEventListener('change', (event) => {
      state.type = event.target.value;
      renderAllFilters();
    });

    $('bandFilter').addEventListener('change', (event) => {
      state.bandKey = event.target.value;
      state.range = null;
      renderAllFilters();
    });

    const search = $('searchFilter');
    search.addEventListener('input', Core.debounce(() => {
      state.query = search.value.trim();
      renderAllFilters();
    }, 140));

    $('resetTable').addEventListener('click', () => {
      state.bandKey = '';
      state.type = '';
      state.query = '';
      state.range = null;
      state.sortKey = 'rating';
      state.sortDir = 'desc';
      search.value = '';
      renderAllFilters();
      updateSortHeaders();
    });

    document.querySelectorAll('.game-table thead button[data-sort]').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.dataset.sort;
        if (state.sortKey === key) state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
        else {
          state.sortKey = key;
          state.sortDir = key === 'name' || key === 'type' ? 'asc' : 'desc';
        }
        updateSortHeaders();
        renderTable();
      });
    });

    $('drawerClose').addEventListener('click', closeDrawer);
    $('drawerBackdrop').addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !$('gameDrawer').hidden) closeDrawer();
    });

    window.addEventListener('resize', Core.debounce(() => charts.forEach((chart) => chart.resize()), 140));
  }

  function updateSortHeaders() {
    document.querySelectorAll('.game-table thead button[data-sort]').forEach((button) => {
      const active = button.dataset.sort === state.sortKey;
      button.querySelector('span').textContent = active ? (state.sortDir === 'asc' ? '↑' : '↓') : '↕';
    });
  }

  async function init() {
    try {
      const result = await Core.loadGames();
      state.games = result.games;
      state.source = result.source;
      const online = await Core.loadOnlineMeta();
      Core.setMeta({ source: state.source, online });

      fillSelects();
      readUrl();
      syncTypeSelect();
      syncBandSelect();
      renderKpis();
      renderMinReviewSeg();

      const histogram = chartHistogram();
      const typeRating = chartTypeRating();
      const scatter = chartScatter();
      histogramChart = histogram?.chart || null;
      typeChart = typeRating?.chart || null;
      scatterChart = scatter?.chart || null;
      histogramChart.__option = histogram?.option || (() => ({}));
      typeChart.__option = typeRating?.option || (() => ({}));
      scatterChart.__option = scatter?.option || (() => ({}));

      bindEvents();
      updateSortHeaders();
      renderBandCards();
      renderRankings();
      renderTable();
      renderFilterSummary();
    } catch (error) {
      console.error(error);
      document.querySelector('.insight-shell').insertAdjacentHTML('afterbegin', '<p class="empty-state">数据加载失败：请通过 npm start 启动，或确认 js/data.js 存在。</p>');
    }
  }

  init();
})();
