'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

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

// 只有文本类资源值得 gzip；图片本身已经压缩过
const COMPRESSIBLE = new Set(['.html', '.css', '.js', '.json', '.csv', '.svg', '.txt']);

/** 读取并返回项目里的一个 JSON 文件（供 /api 使用） */
function sendJson(res, fileName) {
  const filePath = path.join(ROOT, 'data', fileName);
  fs.readFile(filePath, 'utf-8', (err, text) => {
    if (err) {
      // 文件不存在：说明爬虫还没跑成功过
      res.writeHead(404, {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      });
      res.end(JSON.stringify({ error: '数据尚未生成，请先运行 npm run crawl' }));
      return;
    }
    // 数据接口必须每次回源：实时榜单不能被浏览器缓存
    res.writeHead(200, {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      Pragma: 'no-cache',
    });
    res.end(text);
  });
}

/** 返回静态文件（带路径穿越防护：不许访问项目目录之外的文件） */
function sendStaticFile(req, res, pathname) {
  // pathname 形如 /practice/第三周小页面.html，join 后解析出真实路径
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
    const headers = {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      // HTML 不缓存，保证改完页面刷新就能看到；其余静态资源短缓存
      'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=3600',
    };

    const acceptsGzip = /\bgzip\b/.test(String(req.headers['accept-encoding'] || ''));
    if (acceptsGzip && COMPRESSIBLE.has(ext) && buf.length > 1024) {
      zlib.gzip(buf, (gzipErr, gzipped) => {
        if (gzipErr) {
          res.writeHead(200, headers);
          res.end(buf);
          return;
        }
        headers['Content-Encoding'] = 'gzip';
        headers['Vary'] = 'Accept-Encoding';
        headers['Content-Length'] = gzipped.length;
        res.writeHead(200, headers);
        res.end(gzipped);
      });
      return;
    }

    headers['Content-Length'] = buf.length;
    res.writeHead(200, headers);
    res.end(buf);
  });
}

// 宽容解码：非法百分号编码（如裸 / 畸形 %E4）会让 decodeURIComponent 抛 URIError，
// 一个坏请求就能把整个服务器打挂 —— 这里逐段降级解码，保证不会崩。
function safeDecode(s) {
  try {
    return decodeURIComponent(s);
  } catch (err) {
    return s.replace(/%[0-9A-Fa-f]{2}/g, (m) => {
      try {
        return decodeURIComponent(m);
      } catch {
        return m;
      }
    });
  }
}

const server = http.createServer((req, res) => {
  // 注意：URL 里出现非法百分号编码时，直接 decodeURIComponent 会抛错并让服务器退出。
  let pathname;
  try {
    pathname = safeDecode(new URL(req.url, `http://localhost:${PORT}`).pathname);
  } catch (err) {
    pathname = safeDecode(req.url || '/');
  }

  // ---- API 路由 ----
  if (pathname === '/api/games') return sendJson(res, 'games.json');
  if (pathname === '/api/meta') return sendJson(res, 'meta.json');
  if (pathname === '/api/online') return sendJson(res, 'online.json');

  // ---- 静态文件 ----
  sendStaticFile(req, res, pathname === '/' ? '/index.html' : pathname);
});

server.listen(PORT, () => {
  console.log(`✔ Steam 市场洞察服务器已启动`);
  console.log(`  首页：  http://localhost:${PORT}/`);
  console.log(`  数据接口：http://localhost:${PORT}/api/games`);
  console.log(`  元信息：http://localhost:${PORT}/api/meta`);
  console.log(`  实时榜单：http://localhost:${PORT}/api/online`);
});
