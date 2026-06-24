#!/usr/bin/env node

/**
 * 微信公众号文章搜索工具
 * 通过搜狗微信搜索获取微信公众号文章
 */

const https = require('https');
const cheerio = require('cheerio');
const zlib = require('zlib');

// 可配置 User-Agent 池（固定 20 个），每次请求随机选一个，避免固定 UA
const USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/123.0.0.0 Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/122.0.0.0 Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
  'Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
  'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
  'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36',
  'Mozilla/5.0 (Linux; Android 13; Mi 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
];

function getRandomUserAgent() {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

const HEADERS = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
  'Accept-Encoding': 'identity',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'Host': 'weixin.sogou.com',
  'Referer': 'https://weixin.sogou.com/',
};

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function decompressBody(buffer, contentEncoding) {
  if (!contentEncoding) return buffer;
  const encoding = String(contentEncoding).toLowerCase();
  try {
    if (encoding.includes('gzip')) return zlib.gunzipSync(buffer);
    if (encoding.includes('deflate')) return zlib.inflateSync(buffer);
    if (encoding.includes('br')) return zlib.brotliDecompressSync(buffer);
  } catch {
    // 解压失败时直接返回原始数据，避免影响主流程
  }
  return buffer;
}

async function request(options) {
  const { url, method = 'GET', headers = {}, timeoutMs = 15000, retries = 0 } = options;
  const lastErrorPrefix = `Request failed: ${method} ${url}`;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const result = await new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const reqOptions = {
          hostname: urlObj.hostname,
          path: urlObj.pathname + urlObj.search,
          method,
          headers,
        };
        const req = https.request(reqOptions, (res) => {
          const chunks = [];
          res.on('data', (chunk) => chunks.push(chunk));
          res.on('end', () => {
            const raw = Buffer.concat(chunks);
            const body = decompressBody(raw, res.headers['content-encoding']);
            resolve({ statusCode: res.statusCode || 0, headers: res.headers, body });
          });
        });
        req.on('error', reject);
        req.setTimeout(timeoutMs, () => { req.destroy(); reject(new Error('Request timeout')); });
        req.end();
      });
      return result;
    } catch (e) {
      if (attempt >= retries) throw new Error(`${lastErrorPrefix}: ${e.message}`);
      await sleep(300 + attempt * 300);
    }
  }
  throw new Error(`${lastErrorPrefix}: unexpected`);
}

async function requestText(options) {
  const resp = await request(options);
  return { ...resp, text: resp.body.toString('utf-8') };
}

function extractCookies(headers) {
  const cookies = [];
  const setCookieHeader = headers['set-cookie'];
  if (setCookieHeader) {
    setCookieHeader.forEach(cookie => {
      const cookieValue = cookie.split(';')[0];
      if (cookieValue) cookies.push(cookieValue);
    });
  }
  return cookies.join('; ');
}

async function getSogouCookie() {
  try {
    const resp = await request({
      url: 'https://v.sogou.com/v?ie=utf8&query=&p=40030600',
      headers: {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding': 'identity',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'User-Agent': getRandomUserAgent(),
      },
      timeoutMs: 10000,
      retries: 1,
    });
    const cookies = extractCookies(resp.headers);
    const cookieObj = {};
    if (cookies) {
      cookies.split('; ').forEach(cookie => {
        const [key, value] = cookie.split('=');
        if (key && value) cookieObj[key.trim()] = value.trim();
      });
    }
    return { cookieStr: cookies || '', cookieObj };
  } catch {
    return { cookieStr: '', cookieObj: {} };
  }
}

async function httpGet(url, cookieStr = '') {
  const headers = { ...HEADERS, 'User-Agent': getRandomUserAgent() };
  if (cookieStr) headers['Cookie'] = cookieStr;
  const resp = await requestText({ url, headers, timeoutMs: 30000, retries: 1 });
  return resp.text;
}

function parseArticlesFromSearchHtml(html, maxResults) {
  const articles = [];
  const $ = cheerio.load(html);
  const $newsList = $('ul.news-list');
  if ($newsList.length === 0) return [];

  $newsList.find('li').each((_, element) => {
    if (articles.length >= maxResults) return false;
    const article = parseArticle($, element);
    if (article) articles.push(article);
  });
  return articles;
}

function parseArticle($, element) {
  try {
    const $elem = $(element);
    const $titleLink = $elem.find('h3 a');
    if ($titleLink.length === 0) return null;

    const title = $titleLink.text().trim();
    let url = $titleLink.attr('href') || '';
    if (url.startsWith('/')) url = `https://weixin.sogou.com${url}`;

    const summary = $elem.find('p.txt-info').text().trim();

    let datetime = '';
    let dateText = '';
    let source = '';
    let timeDescription = '';

    const $sourceBox = $elem.find('.s-p');
    if ($sourceBox.length > 0) {
      const $dateScript = $sourceBox.find('.s2 script');
      if ($dateScript.length > 0) {
        const scriptText = $dateScript.text();
        const timestampMatch = scriptText.match(/(\d{10})/);
        if (timestampMatch) {
          const timestamp = parseInt(timestampMatch[1]) * 1000;
          const date = new Date(timestamp);
          const chinaTime = new Date(date.getTime() + 8 * 60 * 60 * 1000);
          const y = chinaTime.getUTCFullYear();
          const m = String(chinaTime.getUTCMonth() + 1).padStart(2, '0');
          const d = String(chinaTime.getUTCDate()).padStart(2, '0');
          datetime = `${y}-${m}-${d} ${String(chinaTime.getUTCHours()).padStart(2, '0')}:${String(chinaTime.getUTCMinutes()).padStart(2, '0')}:${String(chinaTime.getUTCSeconds()).padStart(2, '0')}`;
          dateText = `${y}年${m}月${d}日`;

          const now = new Date();
          const diffMs = now - new Date(timestamp);
          const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
          const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
          if (diffDays > 0) timeDescription = `${diffDays}天前`;
          else if (diffHours > 0) timeDescription = `${diffHours}小时前`;
          else { const dm = Math.floor(diffMs / 60000); timeDescription = dm > 0 ? `${dm}分钟前` : '刚刚'; }
        }
      }

      const $sourceSpan = $sourceBox.find('.all-time-y2');
      const $sourceLink = $sourceBox.find('a.account');
      if ($sourceSpan.length > 0) source = $sourceSpan.text().trim();
      else if ($sourceLink.length > 0) source = $sourceLink.text().trim();
    }

    return { title, url, summary, datetime, date_text: dateText, date_description: timeDescription || dateText, source };
  } catch (error) {
    console.error('解析文章失败:', error.message);
    return null;
  }
}

async function searchWechatArticles(query, maxResults = 10, resolveRealUrl = false) {
  maxResults = Math.min(maxResults, 50);
  const articles = [];
  let page = 1;
  const pagesNeeded = Math.ceil(maxResults / 10);

  while (articles.length < maxResults && page <= pagesNeeded) {
    try {
      const { cookieStr } = await getSogouCookie();
      const encodedQuery = encodeURIComponent(query);
      const url = `https://weixin.sogou.com/weixin?query=${encodedQuery}&s_from=input&_sug_=n&type=2&page=${page}&ie=utf8`;
      const html = await httpGet(url, cookieStr);
      const remaining = maxResults - articles.length;
      const parsed = parseArticlesFromSearchHtml(html, remaining);
      if (parsed.length === 0) break;
      articles.push(...parsed);
      page++;
      if (page <= pagesNeeded) await sleep(500 + Math.random() * 1000);
    } catch (error) {
      console.error(`请求第${page}页失败:`, error.message);
      break;
    }
  }

  return articles.slice(0, maxResults);
}

// CLI entry
async function main() {
  const args = process.argv.slice(2);
  let query = '', num = 10, output = '', resolveRealUrl = false;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-n' || args[i] === '--num') { num = parseInt(args[++i]) || 10; }
    else if (args[i] === '-o' || args[i] === '--output') { output = args[++i] || ''; }
    else if (args[i] === '-r' || args[i] === '--resolve-url') { resolveRealUrl = true; }
    else if (!args[i].startsWith('-')) { query = args[i]; }
  }

  if (!query) {
    console.log('\n微信公众号文章搜索工具\n\n用法:\n  node search_wechat.js <关键词> [-n 数量] [-o 输出文件]\n\n选项:\n  -n, --num <数量>       返回数量（默认10，最大50）\n  -o, --output <文件>    输出JSON\n');
    process.exit(0);
  }

  try {
    console.error(`正在搜索: "${query}"...`);
    const articles = await searchWechatArticles(query, num, resolveRealUrl);
    const result = { query, total: articles.length, articles };
    const jsonOutput = JSON.stringify(result, null, 2);
    if (output) { require('fs').writeFileSync(output, jsonOutput, 'utf-8'); console.error(`已保存: ${output}`); }
    console.log(jsonOutput);
  } catch (error) {
    console.error('搜索失败:', error.message);
    process.exit(1);
  }
}

module.exports = { searchWechatArticles };
if (require.main === module) main();
