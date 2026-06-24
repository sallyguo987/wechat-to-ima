#!/usr/bin/env node

/**
 * 微信文章多关键词搜索编排器
 *
 * 功能：多关键词搜索 → 合并去重 → 日期过滤 → 出 JSON
 *
 * 用法:
 *   node search_orchestrator.js --keywords '["南康家具","南康 实木家具"]' --start 2026-04-01 --end 2026-06-23 --out ./output --max 50
 *
 * 或通过模块调用:
 *   const { searchMultiKeyword } = require('./search_orchestrator.js');
 *   const result = await searchMultiKeyword(keywords, { dateStart, dateEnd, outDir, maxPerKeyword });
 */

const path = require('path');
const fs = require('fs');
const { searchWechatArticles } = require('./search_wechat.js');

// ── 工具函数 ──

function normalizeTitle(title) {
  return (title || '').replace(/[\s\p{P}\p{S}]/gu, '').toLowerCase();
}

function jaccardSimilarity(a, b) {
  const setA = new Set(a.split(''));
  const setB = new Set(b.split(''));
  const intersection = new Set([...setA].filter(x => setB.has(x)));
  const union = new Set([...setA, ...setB]);
  return union.size === 0 ? 1 : intersection.size / union.size;
}

function isInDateRange(datetime, start, end) {
  if (!datetime) return 'no_date';
  if (datetime >= start && datetime <= end + ' 23:59:59') return 'in_range';
  return 'out_of_range';
}

function deduplicateArticles(articles) {
  const seenUrls = new Set();
  const kept = [];
  const normalizedTitles = [];
  let dupCount = 0;

  for (const article of articles) {
    if (article.url && seenUrls.has(article.url)) { dupCount++; continue; }
    const normTitle = normalizeTitle(article.title);
    let isDuplicate = false;
    for (let i = 0; i < kept.length; i++) {
      if (jaccardSimilarity(normTitle, normalizedTitles[i]) >= 0.85) {
        isDuplicate = true;
        break;
      }
    }
    if (isDuplicate) { dupCount++; continue; }
    if (article.url) seenUrls.add(article.url);
    kept.push(article);
    normalizedTitles.push(normTitle);
  }
  return { articles: kept, dupCount };
}

// ── 主逻辑 ──

async function searchMultiKeyword(keywords, opts = {}) {
  const {
    dateStart = null,
    dateEnd = null,
    outDir = './output',
    maxPerKeyword = 50,
    verbose = true,
  } = opts;

  fs.mkdirSync(outDir, { recursive: true });
  const rawDir = path.join(outDir, 'raw');
  fs.mkdirSync(rawDir, { recursive: true });

  const log = (...args) => { if (verbose) console.error(...args); };

  log('========================================');
  log('  微信公众号多关键词搜索编排器');
  if (dateStart) log(`  日期范围: ${dateStart} 至 ${dateEnd}`);
  log('========================================\n');

  // 阶段1: 多关键词搜索
  const allArticles = [];
  const keywordStats = [];

  for (let i = 0; i < keywords.length; i++) {
    const kw = keywords[i];
    const rawFile = path.join(rawDir, `keyword_${String(i + 1).padStart(2, '0')}_${kw.replace(/\s+/g, '_')}.json`);

    let articles;
    if (fs.existsSync(rawFile)) {
      log(`[${i + 1}/${keywords.length}] "${kw}" → 使用缓存`);
      articles = (JSON.parse(fs.readFileSync(rawFile, 'utf-8'))).articles || [];
      keywordStats.push({ keyword: kw, articles_found: articles.length, from_cache: true });
    } else {
      log(`[${i + 1}/${keywords.length}] 搜索: "${kw}" ...`);
      const t0 = Date.now();
      try {
        articles = await searchWechatArticles(kw, maxPerKeyword, false);
        const duration = Date.now() - t0;
        log(`  → ${articles.length} 篇 (${duration}ms)`);
        fs.writeFileSync(rawFile, JSON.stringify({ query: kw, total: articles.length, articles }, null, 2), 'utf-8');
        keywordStats.push({ keyword: kw, articles_found: articles.length, duration_ms: duration, from_cache: false });
      } catch (err) {
        log(`  → 搜索失败: ${err.message}`);
        keywordStats.push({ keyword: kw, articles_found: 0, error: err.message });
        articles = [];
      }
    }

    articles.forEach(a => { a.source_keyword = kw; });
    allArticles.push(...articles);
  }

  const totalBeforeDedup = allArticles.length;
  log(`\n合并前: ${totalBeforeDedup}`);

  // 阶段2: 去重
  const { articles: deduped, dupCount } = deduplicateArticles(allArticles);
  log(`去重后: ${deduped.length} (移除 ${dupCount})`);

  fs.writeFileSync(path.join(outDir, 'merged_all.json'), JSON.stringify({
    total_before_dedup: totalBeforeDedup,
    total_after_dedup: deduped.length,
    articles: deduped,
  }, null, 2), 'utf-8');

  // 阶段3: 日期过滤（如果指定了日期范围）
  let inRange = deduped;
  let outOfRange = [];
  let noDate = [];

  if (dateStart && dateEnd) {
    inRange = [];
    for (const article of deduped) {
      const status = isInDateRange(article.datetime, dateStart, dateEnd);
      if (status === 'in_range') inRange.push(article);
      else if (status === 'no_date') noDate.push(article);
      else outOfRange.push(article);
    }
    inRange.sort((a, b) => (b.datetime || '').localeCompare(a.datetime || ''));
    log(`日期范围内: ${inRange.length} | 未知: ${noDate.length} | 范围外: ${outOfRange.length}`);
  }

  // 阶段4: 输出
  const stats = {
    search_time: new Date().toISOString(),
    date_range: dateStart ? { start: dateStart, end: dateEnd } : null,
    keywords_searched: keywordStats,
    total_before_dedup: totalBeforeDedup,
    total_after_dedup: deduped.length,
    total_in_date_range: inRange.length,
    total_out_of_range: outOfRange.length,
    total_no_date: noDate.length,
  };

  fs.writeFileSync(path.join(outDir, 'stats.json'), JSON.stringify(stats, null, 2), 'utf-8');

  const filteredOutput = {
    date_range: dateStart ? { start: dateStart, end: dateEnd } : null,
    total_in_range: inRange.length,
    total_no_date: noDate.length,
    articles: inRange,
    articles_no_date: noDate,
  };

  fs.writeFileSync(path.join(outDir, 'filtered.json'), JSON.stringify(filteredOutput, null, 2), 'utf-8');

  log('\n========================================');
  log(`  完成! 范围内: ${inRange.length} 篇`);
  log(`  数据: ${outDir}/filtered.json`);
  log('========================================');

  return { stats, filtered: filteredOutput, all: deduped };
}

// ── CLI ──

async function cli() {
  const args = process.argv.slice(2);
  let keywords = [];
  let dateStart = null, dateEnd = null;
  let outDir = './output';
  let maxPer = 50;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--keywords') { try { keywords = JSON.parse(args[++i]); } catch { console.error('keywords 需为 JSON 数组'); process.exit(1); } }
    else if (args[i] === '--start') { dateStart = args[++i]; }
    else if (args[i] === '--end') { dateEnd = args[++i]; }
    else if (args[i] === '--out') { outDir = args[++i]; }
    else if (args[i] === '--max') { maxPer = parseInt(args[++i]) || 50; }
  }

  if (keywords.length === 0) {
    console.log('\n用法: node search_orchestrator.js --keywords \'["词1","词2"]\' [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--out ./output] [--max 50]\n');
    process.exit(0);
  }

  const result = await searchMultiKeyword(keywords, { dateStart, dateEnd, outDir, maxPerKeyword: maxPer });
  console.log(JSON.stringify(result.stats, null, 2));
}

module.exports = { searchMultiKeyword };

if (require.main === module) cli().catch(err => { console.error(err); process.exit(1); });
