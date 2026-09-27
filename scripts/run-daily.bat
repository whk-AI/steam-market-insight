@echo off
rem ============================================
rem  每日自动更新 Steam 数据（Windows 计划任务用）
rem  进入项目目录 -> 运行爬虫 -> 输出到日志
rem ============================================
cd /d F:\steam-market-insight
node scripts/crawler.js >> data\crawler.log 2>&1
