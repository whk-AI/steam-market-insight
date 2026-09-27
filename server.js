/**
 * ============================================================
 *  Steam 市场洞察 · 迷你本地服务器
 * ============================================================
 *  作用：让项目"不只是纯前端" —— 前端通过 /api/games 接口拿数据，
 *        而不是直接 fetch 静态文件。
 *
 *  运行方式（在项目根目录执行）：
 *      npm start            （等价于 node server.js）
 *      然后浏览器打开 http://localhost:8080/
 *
 *  提供的服务：
 *      GET  /api/games      -> data/games.json（真实游戏数据）
 *      GET  /api/meta       -> data/meta.json （数据更新时间等元信息）
 *      其他路径             -> 静态文件（html/css/js/图片）
 *
 *  实现说明：只用了 Node 内置的 http / fs 模块，零第三方依赖。
 * ============================================================
 */
'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const PORT = Number(process.env.PORT) || 8080;
const ROOT = __dirname; // 服务器根目录 = 项目根目录

// 常见文件类型的 Content-Type 对照表
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.csv': 'text/csv; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.txt': 'text/plain; charset=utf-8',
};

/** 读取并返回项目里的一个 JSON 文件（供 /api 使用） */
function sendJson(res, fileName) {
  const filePath = path.join(ROOT, 'data', fileName);
  fs.readFile(filePath, 'utf-8', (err, text) => {
    if (err) {
      // 文件不存在：说明爬虫还没跑成功过
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: '数据尚未生成，请先运行 npm run crawl' }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(text);
  });
}

/** 返回静态文件（带路径穿越防护：不许访问项目目录之外的文件） */
function sendStaticFile(res, pathname) {
  // pathname 形如 /pratice/第三周小页面.html，join 后解析出真实路径
  let filePath = path.normalize(path.join(ROOT, pathname));

  // 安全校验：解析后的路径必须以 ROOT 开头，防止用 ../ 跳出项目目录
  if (filePath !== ROOT && !filePath.startsWith(ROOT + path.sep)) {
    res.writeHead(403, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end('403 禁止访问');
    return;
  }

  // 目录路径：尝试找该目录下的 index.html
  if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
    filePath = path.join(filePath, 'index.html');
  }

  fs.readFile(filePath, (err, buf) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 找不到文件');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(buf);
  });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const pathname = decodeURIComponent(url.pathname);

  // ---- API 路由 ----
  if (pathname === '/api/games') return sendJson(res, 'games.json');
  if (pathname === '/api/meta') return sendJson(res, 'meta.json');

  // ---- 静态文件 ----
  sendStaticFile(res, pathname === '/' ? '/index.html' : pathname);
});

server.listen(PORT, () => {
  console.log(`✔ Steam 市场洞察服务器已启动`);
  console.log(`  首页：  http://localhost:${PORT}/`);
  console.log(`  数据接口：http://localhost:${PORT}/api/games`);
  console.log(`  元信息：http://localhost:${PORT}/api/meta`);
});
