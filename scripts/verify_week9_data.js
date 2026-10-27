/**
 * 第 9 周首页数据校验脚本
 * 用 Node 执行：node scripts/verify_week9_data.js
 * 检查 js/data.js 是否与 pratice(python)/games_clean.csv、online_top10.json 完全一致。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');

// 1. 在沙箱里执行 data.js，取出三个全局变量
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(read('js/data.js') + '\n;__result = { games, online, appNameFallback };', sandbox);
const { games, online, appNameFallback } = sandbox.__result;

// 2. 用本地 papaparse 解析 CSV（支持引号内的逗号）
const Papa = require(path.join(root, 'js', 'papaparse.min.js'));
const csv = Papa.parse(read('pratice(python)/games_clean.csv'), {
  header: true,
  skipEmptyLines: true,
}).data;

const errors = [];
const near = (a, b) => Math.abs(Number(a) - Number(b)) < 0.001;

if (games.length !== 123) errors.push(`games 数量应为 123，实际 ${games.length}`);
if (csv.length !== 123) errors.push(`CSV 行数应为 123，实际 ${csv.length}`);

const byAppId = new Map(games.map((g) => [String(g.appid), g]));
for (const row of csv) {
  const game = byAppId.get(String(row.appid));
  if (!game) {
    errors.push(`缺少 appid=${row.appid}（${row.name}）`);
    continue;
  }
  if (game.name !== row.name.trim()) errors.push(`appid=${row.appid} name 不一致`);
  if (Number(game.price) !== Number(row.price)) errors.push(`appid=${row.appid} price 不一致`);
  if (!near(game.rating, row.rating)) errors.push(`appid=${row.appid} rating 不一致`);
  if (Number(game.total_reviews) !== Number(row.total_reviews)) errors.push(`appid=${row.appid} total_reviews 不一致`);
  if (game.type !== row.type.trim()) errors.push(`appid=${row.appid} type 不一致`);
  if (game.genres !== row.genres.trim()) errors.push(`appid=${row.appid} genres 不一致`);
  if (Number(game.year) !== Number(row.year)) errors.push(`appid=${row.appid} year 不一致`);
  if (Number(game.discount) !== Number(row.discount_percent)) errors.push(`appid=${row.appid} discount 不一致`);
}

// 3. 校验 online 快照
const onlineJson = JSON.parse(read('pratice(python)/online_top10.json'));
if (online.fetchedAt !== onlineJson.fetchedAt) errors.push('online.fetchedAt 不一致');
if (online.top.length !== onlineJson.top.length) errors.push('online.top 数量不一致');
online.top.forEach((item, i) => {
  ['rank', 'appid', 'peak_in_game', 'last_week_rank'].forEach((key) => {
    if (Number(item[key]) !== Number(onlineJson.top[i][key])) {
      errors.push(`online.top[${i}].${key} 不一致`);
    }
  });
});

// 4. 打印关键统计（与页面指标卡口径一致）
const sum = (arr) => arr.reduce((a, b) => a + b, 0);
const avgPrice = sum(games.map((g) => g.price)) / games.length;
const avgRating = sum(games.map((g) => g.rating)) / games.length;
const free = games.filter((g) => g.price === 0).length;
const onlineSum = sum(online.top.map((o) => o.peak_in_game));
const typeCount = {};
games.forEach((g) => (typeCount[g.type] = (typeCount[g.type] || 0) + 1));

console.log('games        :', games.length);
console.log('online.top   :', online.top.length);
console.log('平均价格     :', avgPrice.toFixed(1));
console.log('平均好评率   :', avgRating.toFixed(1));
console.log('免费占比     :', ((free / games.length) * 100).toFixed(1) + '%');
console.log('在线总人数   :', onlineSum);
console.log('类型分布     :', typeCount);
console.log('补充名称映射 :', appNameFallback);
console.log(errors.length ? `❌ 校验失败 ${errors.length} 项：\n` + errors.join('\n') : '✅ 校验通过：data.js 与原始数据完全一致');
process.exitCode = errors.length ? 1 : 0;
