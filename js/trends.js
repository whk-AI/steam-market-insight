'use strict';

(function () {
  const Core = window.InsightCore;
  const { PALETTE, $ } = Core;

  const state = {
    games: [],
    source: 'api',
    years: [],
    yearData: new Map(),
    selectedYear: 2026,
    playing: false,
    timer: null,
  };

  const charts = [];

  function buildYearData() {
    const minYear = 2009;
    const maxYear = 2026;
    const map = new Map();
    for (let year = minYear; year <= maxYear; year += 1) {
      const list = state.games.filter((game) => game.year === year);
      map.set(year, {
        year,
        list,
        count: list.length,
        rating: list.length ? Core.weightedRating(list) : null,
        price: list.length ? Core.average(list, (game) => game.price) : null,
        reviews: Core.sum(list, (game) => game.total_reviews),
        types: countTypes(list),
        top: list.slice().sort((a, b) => b.total_reviews - a.total_reviews).slice(0, 3),
      });
    }
    state.years = Array.from({ length: maxYear - minYear + 1 }, (_, index) => minYear + index);
    state.yearData = map;
  }

  function countTypes(list) {
    const map = new Map();
    list.forEach((game) => map.set(game.type, (map.get(game.type) || 0) + 1));
    return [...map.entries()].sort((a, b) => b[1] - a[1]);
  }

  function initChart(id) {
    const el = $(id);
    if (!el) return null;
    const chart = echarts.init(el);
    charts.push(chart);
    return chart;
  }

  function yearLabel(year) {
    return `${year}`;
  }

  function selectedIndex() {
    return Math.max(0, state.years.indexOf(state.selectedYear));
  }

  function markLine() {
    return {
      silent: true,
      symbol: 'none',
      lineStyle: { color: '#c63b2f', type: 'dashed', width: 1.5 },
      label: { color: '#c63b2f', fontSize: 9, formatter: `${state.selectedYear}` },
      data: [{ xAxis: yearLabel(state.selectedYear) }],
    };
  }

  /* ---------------- 顶部 ---------------- */
  function renderKpis() {
    const latest = state.yearData.get(2026);
    document.querySelectorAll('[data-kpi="span"]').forEach((el) => (el.textContent = `${state.years[0]}—${state.years[state.years.length - 1]}`));
    document.querySelectorAll('[data-kpi="games"]').forEach((el) => (el.textContent = state.games.length));
    document.querySelectorAll('[data-kpi="latest"]').forEach((el) => (el.textContent = latest ? latest.count : 0));
    document.querySelectorAll('[data-kpi="price"]').forEach((el) => (el.textContent = Core.fmt1(Core.average(state.games, (game) => game.price))));
  }

  /* ---------------- 时间轴 ---------------- */
  function renderTimeline() {
    const host = $('yearTimeline');
    host.innerHTML = state.years.map((year) => {
      const data = state.yearData.get(year);
      const active = year === state.selectedYear;
      return `
        <button class="timeline__year${active ? ' is-active' : ''}" type="button"
          data-year="${year}" aria-pressed="${active}" title="${year} 年 · ${data.count} 款">
          ${year}
        </button>`;
    }).join('');
    host.querySelectorAll('button').forEach((button) => {
      button.addEventListener('click', () => {
        stopPlay();
        setYear(Number(button.dataset.year));
      });
    });
  }

  function setYear(year, options = {}) {
    if (!state.yearData.has(year)) return;
    state.selectedYear = year;
    renderTimeline();
    renderYearCard();
    renderYearly();
    renderPrice();
    renderTypeShare();
    renderYearTable();
    updateUrl();
    if (!options.fromPlay) stopPlay();
  }

  function shiftYear(delta) {
    const index = selectedIndex();
    let next = index + delta;
    while (next >= 0 && next < state.years.length && state.yearData.get(state.years[next]).count === 0) next += delta;
    if (next < 0 || next >= state.years.length) return;
    setYear(state.years[next]);
  }

  /* ---------------- 年度组合图 ---------------- */
  let yearlyChart = null;
  let yearlyOption = null;
  let priceChart = null;
  let priceOption = null;
  let shareChart = null;
  let shareOption = null;

  function chartYearly() {
    const chart = initChart('chart-yearly');
    if (!chart) return;
    yearlyOption = () => {
      const rows = state.years.map((year) => state.yearData.get(year));
      return {
        ...Core.chartBase(),
        grid: { left: 46, right: 50, top: 42, bottom: 30 },
        legend: {
          top: 2,
          left: 'center',
          itemWidth: 11,
          itemHeight: 7,
          textStyle: { color: '#6f604c', fontSize: 9 },
          data: ['上架数量', '加权好评率'],
        },
        tooltip: {
          ...Core.chartBase().tooltip,
          trigger: 'axis',
          axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(198,59,47,.06)' } },
          formatter: (params) => {
            const row = rows[params[0].dataIndex];
            if (!row) return '';
            return `${row.year} 年<br>上架：${row.count} 款<br>加权好评率：${row.rating == null ? '—' : Core.fmt1(row.rating) + '%'}<br>当前均价：${row.price == null ? '—' : '¥' + Core.fmt1(row.price)}<br>评价总量：${Core.formatWan(row.reviews)} 条`;
          },
        },
        xAxis: {
          type: 'category',
          data: state.years.map((year) => yearLabel(year)),
          ...Core.axisStyle,
          axisLabel: { ...Core.axisStyle.axisLabel, fontSize: 8, interval: 0 },
        },
        yAxis: [
          {
            type: 'value',
            name: '上架数量 / 款',
            min: 0,
            max: 50,
            ...Core.axisStyle,
            nameTextStyle: { ...Core.axisStyle.nameTextStyle, padding: [0, 0, 4, 0] },
          },
          {
            type: 'value',
            name: '好评率 /%',
            min: 60,
            max: 100,
            ...Core.axisStyle,
            splitLine: { show: false },
            nameTextStyle: { ...Core.axisStyle.nameTextStyle, padding: [0, 0, 4, 0] },
          },
        ],
        series: [
          {
            name: '上架数量',
            type: 'bar',
            barMaxWidth: 18,
            data: rows.map((row) => ({
              value: row.count,
              itemStyle: {
                color: row.year === state.selectedYear ? '#c63b2f' : '#2f7f74',
                borderColor: '#211c15',
                borderWidth: 1,
              },
            })),
            label: {
              show: true,
              position: 'top',
              color: '#211c15',
              fontSize: 8,
              formatter: (params) => (params.value > 0 ? params.value : ''),
            },
            markLine: markLine(),
          },
          {
            name: '加权好评率',
            type: 'line',
            yAxisIndex: 1,
            data: rows.map((row) => row.rating),
            connectNulls: false,
            symbol: 'circle',
            symbolSize: 4,
            lineStyle: { color: '#c63b2f', width: 2 },
            itemStyle: { color: '#c63b2f', borderColor: '#fbf3e2', borderWidth: 1 },
          },
        ],
      };
    };
    chart.setOption(yearlyOption(), true);
    chart.on('click', (params) => {
      const year = state.years[params.dataIndex];
      if (year != null) {
        stopPlay();
        setYear(year);
      }
    });
    yearlyChart = chart;
  }

  function renderYearly() {
    if (yearlyChart && yearlyOption) yearlyChart.setOption(yearlyOption(), true);
  }

  /* ---------------- 价格趋势 ---------------- */
  let priceRows = [];

  function chartPrice() {
    const chart = initChart('chart-price');
    if (!chart) return;
    priceOption = () => {
      priceRows = state.years
        .map((year) => state.yearData.get(year))
        .filter((row) => row && row.count > 0);
      return {
        ...Core.chartBase(),
        grid: { left: 42, right: 18, top: 20, bottom: 28 },
        tooltip: {
          ...Core.chartBase().tooltip,
          trigger: 'axis',
          formatter: (params) => {
            const row = priceRows[params[0].dataIndex];
            return row ? `${row.year} 年<br>当前均价：${row.price == null ? '—' : '¥' + Core.fmt1(row.price)}<br>上架：${row.count} 款` : '';
          },
        },
        xAxis: {
          type: 'category',
          data: priceRows.map((row) => yearLabel(row.year)),
          ...Core.axisStyle,
          axisLabel: { ...Core.axisStyle.axisLabel, fontSize: 8, interval: 0 },
        },
        yAxis: {
          type: 'value',
          name: '元',
          min: 0,
          max: 200,
          ...Core.axisStyle,
        },
        series: [{
          type: 'line',
          data: priceRows.map((row) => Number(row.price.toFixed(1))),
          connectNulls: false,
          symbol: 'circle',
          symbolSize: (value, params) => (state.years[params.dataIndex] === state.selectedYear ? 7 : 4),
          lineStyle: { color: '#2f7f74', width: 2 },
          itemStyle: { color: '#2f7f74', borderColor: '#fbf3e2', borderWidth: 2 },
          areaStyle: { color: 'rgba(47,127,116,.12)' },
          markLine: markLine(),
        }],
      };
    };
    chart.setOption(priceOption(), true);
    chart.on('click', (params) => {
      const row = priceRows[params.dataIndex];
      if (row) {
        stopPlay();
        setYear(row.year);
      }
    });
    priceChart = chart;
  }

  function renderPrice() {
    if (priceChart && priceOption) priceChart.setOption(priceOption(), true);
  }

  /* ---------------- 类型份额 ---------------- */
  const SHARE_TYPES = ['动作', '休闲', '冒险', '独立', '模拟'];
  let shareRows = [];

  function chartTypeShare() {
    const chart = initChart('chart-type-share');
    if (!chart) return;
    shareOption = () => {
      shareRows = state.years
        .map((year) => state.yearData.get(year))
        .filter((row) => row && row.count > 0);
      const series = SHARE_TYPES.map((type, index) => ({
        name: type,
        type: 'line',
        stack: 'share',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 0 },
        areaStyle: { opacity: 0.74 },
        itemStyle: { color: PALETTE[index] },
        emphasis: { focus: 'series' },
        markLine: index === 0 ? markLine() : undefined,
        data: shareRows.map((row) => {
          const total = row.count || 0;
          const count = row.types.find(([name]) => name === type)?.[1] || 0;
          return total ? Number(((count / total) * 100).toFixed(1)) : 0;
        }),
      }));

      series.push({
        name: '其他',
        type: 'line',
        stack: 'share',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 0 },
        areaStyle: { opacity: 0.6 },
        itemStyle: { color: '#b8a37f' },
        emphasis: { focus: 'series' },
        data: shareRows.map((row) => {
          const total = row.count || 0;
          const known = SHARE_TYPES.reduce((sum, type) => sum + (row.types.find(([name]) => name === type)?.[1] || 0), 0);
          return total ? Number((((total - known) / total) * 100).toFixed(1)) : 0;
        }),
      });

      return {
        ...Core.chartBase(),
        grid: { left: 42, right: 16, top: 46, bottom: 28 },
        legend: {
          top: 2,
          left: 'center',
          itemWidth: 10,
          itemHeight: 7,
          textStyle: { color: '#6f604c', fontSize: 9 },
          data: [...SHARE_TYPES, '其他'],
        },
        tooltip: {
          ...Core.chartBase().tooltip,
          trigger: 'axis',
          formatter: (params) => {
            const row = shareRows[params[0].dataIndex];
            if (!row) return '';
            return `${row.year} 年 · 共 ${row.count} 款<br>` + params.map((item) => `${item.marker}${item.seriesName}：${item.value}%`).join('<br>');
          },
        },
        xAxis: {
          type: 'category',
          data: shareRows.map((row) => yearLabel(row.year)),
          ...Core.axisStyle,
          axisLabel: { ...Core.axisStyle.axisLabel, fontSize: 8, interval: 0 },
        },
        yAxis: {
          type: 'value',
          min: 0,
          max: 100,
          name: '份额 /%',
          ...Core.axisStyle,
        },
        series,
      };
    };
    chart.setOption(shareOption(), true);
    chart.on('click', (params) => {
      const row = shareRows[params.dataIndex];
      if (row) {
        stopPlay();
        setYear(row.year);
      }
    });
    shareChart = chart;
  }

  function renderTypeShare() {
    if (shareChart && shareOption) shareChart.setOption(shareOption(), true);
  }

  /* ---------------- 年卡 / 明细 ---------------- */
  function renderYearCard() {
    const row = state.yearData.get(state.selectedYear);
    const prev = state.yearData.get(state.selectedYear - 1);
    const games = row ? row.list : [];
    $('yearFocus').textContent = state.selectedYear;
    $('yearCount').textContent = row ? row.count : 0;
    $('yearRating').textContent = row && row.rating != null ? Core.fmt1(row.rating) : '—';
    $('yearPrice').textContent = row && row.price != null ? Core.fmt1(row.price) : '—';
    $('yearReviews').textContent = row ? Core.formatWan(row.reviews) : '0';

    if (prev && row) {
      const delta = row.count - prev.count;
      const ratingDelta = row.rating != null && prev.rating != null ? row.rating - prev.rating : null;
      const countText = `${delta > 0 ? '+' : ''}${delta} 款`;
      const ratingText = ratingDelta == null ? '口碑 —' : `${ratingDelta > 0 ? '+' : ''}${Core.fmt1(ratingDelta)} 分`;
      $('yearDelta').innerHTML = `较 ${state.selectedYear - 1} 年 <span class="${delta >= 0 ? 'up' : 'down'}">${countText}</span> · ${ratingText}`;
    } else {
      $('yearDelta').textContent = '样本起点，没有上一年可比';
    }

    $('yearTopGames').innerHTML = games.length
      ? games.slice(0, 3).map((game, index) => `
        <li>
          <span class="no">0${index + 1}</span>
          <span class="name">${Core.escapeHtml(game.name)}</span>
          <span class="score">${Core.fmt1(game.rating)}%</span>
        </li>`).join('')
      : '<li><span class="no">—</span><span class="name">这一年没有样本</span><span class="score">—</span></li>';

    const note = state.selectedYear === 2026
      ? '2026 是样本峰值：近年抓取更偏向新游，不直接代表全市场。'
      : state.selectedYear <= 2011
        ? '老游戏样本不多，但口碑普遍更高；它们被时间筛过一遍。'
        : row && row.count === 0
          ? '这一年没有抓到样本，时间轴会跳过。'
          : '价格与好评率是当前快照，不是当年首发数据。';
    $('yearNote').textContent = note;
  }

  function renderYearTable() {
    const body = $('yearTableBody');
    body.innerHTML = state.years.slice().reverse().map((year) => {
      const row = state.yearData.get(year);
      const top = row.top[0];
      return `
        <tr data-year="${year}" class="${year === state.selectedYear ? 'is-selected' : ''}">
          <td><strong>${year}</strong></td>
          <td class="num">${row.count}</td>
          <td class="num">${row.rating == null ? '—' : Core.fmt1(row.rating)}</td>
          <td class="num">${row.price == null ? '—' : '¥' + Core.fmt1(row.price)}</td>
          <td class="num">${Core.formatWan(row.reviews)}</td>
          <td class="muted">${top ? Core.escapeHtml(top.name) : '—'}</td>
        </tr>`;
    }).join('');
    body.querySelectorAll('tr').forEach((tr) => {
      tr.addEventListener('click', () => {
        stopPlay();
        setYear(Number(tr.dataset.year));
      });
    });
    $('yearTableCount').textContent = `${state.years.length} 行`;
  }

  /* ---------------- 播放与 URL ---------------- */
  function stopPlay() {
    if (state.timer) window.clearInterval(state.timer);
    state.timer = null;
    state.playing = false;
    const button = $('playYears');
    if (button) {
      button.textContent = '▶ 播放 18 年';
      button.setAttribute('aria-pressed', 'false');
    }
  }

  function startPlay() {
    if (state.playing) {
      stopPlay();
      return;
    }
    state.playing = true;
    const button = $('playYears');
    button.textContent = '❚❚ 暂停';
    button.setAttribute('aria-pressed', 'true');
    if (state.selectedYear !== 2009) setYear(2009, { fromPlay: true });
    state.timer = window.setInterval(() => {
      const index = selectedIndex();
      let next = index + 1;
      while (next < state.years.length && state.yearData.get(state.years[next]).count === 0) next += 1;
      if (next >= state.years.length) {
        stopPlay();
        return;
      }
      setYear(state.years[next], { fromPlay: true });
    }, 900);
  }

  function updateUrl() {
    try {
      const params = new URLSearchParams(location.search);
      params.set('year', String(state.selectedYear));
      history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
    } catch (error) { }
  }

  function readUrl() {
    try {
      const year = Number(new URLSearchParams(location.search).get('year'));
      if (state.yearData.has(year)) state.selectedYear = year;
    } catch (error) { }
  }

  function bindEvents() {
    $('playYears').addEventListener('click', startPlay);
    $('resetYear').addEventListener('click', () => {
      stopPlay();
      setYear(2026);
    });
    document.addEventListener('keydown', (event) => {
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        stopPlay();
        shiftYear(-1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        stopPlay();
        shiftYear(1);
      }
    });
    window.addEventListener('resize', Core.debounce(() => charts.forEach((chart) => chart.resize()), 140));
  }

  async function init() {
    try {
      const result = await Core.loadGames();
      state.games = result.games;
      state.source = result.source;
      const online = await Core.loadOnlineMeta();
      Core.setMeta({ source: state.source, online });
      buildYearData();
      readUrl();
      renderKpis();
      renderTimeline();
      chartYearly();
      chartPrice();
      chartTypeShare();
      bindEvents();
      renderYearCard();
      renderYearTable();
      renderYearly();
      renderPrice();
      renderTypeShare();
    } catch (error) {
      console.error(error);
      document.querySelector('.insight-shell').insertAdjacentHTML('afterbegin', '<p class="empty-state">数据加载失败：请通过 npm start 启动，或确认 js/data.js 存在。</p>');
    }
  }

  init();
})();
