#!/usr/bin/env python3
"""
生成自包含的 HTML 浏览页面，用于查看/筛选/导出微信文章搜索结果。

用法:
    python build_viewer.py --input merged_all.json --stats stats.json --out viewer.html \
        --title "南康家具 · 文章速览" --date-start 2026-04-01 --date-end 2026-06-23
"""

import json
import argparse
from datetime import date


def esc_js(s):
    """将字符串转义为 JS 安全的字面量。"""
    return json.dumps(s, ensure_ascii=False)


def build_html(articles, stats, keywords, title, date_start, date_end):
    """返回完整的自包含 HTML 字符串。"""
    today = date.today().isoformat()
    data = {"stats": stats, "keywords": keywords, "articles": articles}
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
  .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
  .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 32px 24px; border-radius: 12px; margin-bottom: 20px; text-align: center; }}
  .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
  .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
  .header .date-range {{ margin-top: 8px; font-size: 13px; opacity: 0.75; }}
  .stats-panel {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .stat-card {{ background: #fff; border-radius: 10px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); cursor: pointer; transition: all 0.2s; }}
  .stat-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.12); transform: translateY(-1px); }}
  .stat-card.active {{ border: 2px solid #667eea; }}
  .stat-card .num {{ font-size: 32px; font-weight: 700; color: #764ba2; }}
  .stat-card .label {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; align-items: center; }}
  .toolbar input, .toolbar select, .toolbar button {{ padding: 8px 14px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; outline: none; font-family: inherit; }}
  .toolbar input {{ flex: 1; min-width: 200px; }}
  .toolbar input:focus, .toolbar select:focus {{ border-color: #764ba2; }}
  .toolbar button {{ background: #764ba2; color: #fff; border: none; cursor: pointer; font-weight: 500; white-space: nowrap; transition: background 0.2s; }}
  .toolbar button:hover {{ background: #5a3d8a; }}
  .toolbar button.secondary {{ background: #fff; color: #764ba2; border: 1px solid #764ba2; }}
  .toolbar button.secondary:hover {{ background: #f5f0ff; }}
  .toolbar button.active-filter {{ background: #ff7875; }}
  .result-count {{ font-size: 13px; color: #888; margin-left: auto; white-space: nowrap; }}
  .article-card {{ background: #fff; border-radius: 10px; padding: 18px 20px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s; position: relative; }}
  .article-card:hover {{ box-shadow: 0 3px 12px rgba(0,0,0,0.1); }}
  .article-card .title {{ font-size: 17px; font-weight: 600; color: #222; margin-bottom: 8px; line-height: 1.5; padding-right: 70px; }}
  .article-card .title a {{ color: inherit; text-decoration: none; }}
  .article-card .title a:hover {{ color: #764ba2; }}
  .article-card .meta {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 13px; color: #888; margin-bottom: 6px; align-items: center; }}
  .article-card .meta .source {{ color: #764ba2; font-weight: 500; }}
  .article-card .summary {{ font-size: 14px; color: #666; line-height: 1.7; margin-bottom: 10px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
  .article-card .tags {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }}
  .article-card .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; background: #f0e6ff; color: #764ba2; }}
  .article-card .tag.no-date {{ background: #fff2e8; color: #d46b08; }}
  .article-card .tag.in-range {{ background: #e6fffb; color: #08979c; }}
  .article-card .copy-btn {{ position: absolute; top: 18px; right: 18px; padding: 4px 10px; font-size: 12px; background: #f0f0f0; border: none; border-radius: 4px; cursor: pointer; color: #666; }}
  .article-card .copy-btn:hover {{ background: #764ba2; color: #fff; }}
  .article-card .copy-btn.copied {{ background: #52c41a; color: #fff; }}
  .empty-state {{ text-align: center; padding: 60px 20px; color: #999; }}
  .pagination {{ display: flex; justify-content: center; gap: 8px; margin-top: 20px; flex-wrap: wrap; }}
  .pagination button {{ padding: 8px 14px; border: 1px solid #ddd; border-radius: 6px; background: #fff; cursor: pointer; font-size: 14px; }}
  .pagination button:hover {{ border-color: #764ba2; color: #764ba2; }}
  .pagination button.active {{ background: #764ba2; color: #fff; border-color: #764ba2; }}
  @media (max-width: 640px) {{
    .container {{ padding: 12px; }}
    .header {{ padding: 24px 16px; }}
    .header h1 {{ font-size: 22px; }}
    .toolbar {{ flex-direction: column; }}
    .toolbar input {{ width: 100%; }}
    .article-card .copy-btn {{ position: static; margin-top: 8px; }}
    .article-card .title {{ padding-right: 0; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{title}</h1>
    <div class="subtitle">多关键词搜索 · 去重 · 日期过滤</div>
    <div class="date-range">📅 搜索范围：{date_start or '不限'} ～ {date_end or '不限'} | ⏰ 生成时间：{today}</div>
  </div>
  <div class="stats-panel" id="statsPanel"></div>
  <div class="toolbar">
    <input type="text" id="searchInput" placeholder="🔍 搜索文章标题或摘要...">
    <select id="keywordFilter"><option value="">🏷 全部关键词</option></select>
    <select id="monthFilter"><option value="">📅 全部月份</option></select>
    <button id="sortBtn" onclick="toggleSort()">📅 最新优先</button>
    <button class="secondary" onclick="copyAllLinks()">📋 复制全部链接</button>
    <button class="secondary" onclick="exportJSON()">⬇ 导出JSON</button>
    <span class="result-count" id="resultCount"></span>
  </div>
  <div id="articleList"></div>
  <div class="pagination" id="pagination"></div>
  <div class="empty-state" id="emptyState" style="display:none">📭<p>没有找到匹配的文章</p></div>
</div>
<script>
var DATA = {data_json};
var sortAsc = false;
var dateFilterOn = {'true' if date_start else 'false'};
var currentPage = 1;
var pageSize = 20;
var dateStart = {esc_js(date_start or '')};
var dateEnd = {esc_js(date_end or '')};

function init() {{
  initStats(); initFilters(); applyAll();
}}

function initStats() {{
  var s = DATA.stats;
  var kwMap = {{}};
  DATA.keywords.forEach(function(k) {{ kwMap[k.label||k.keyword] = k.articles_found; }});
  var html = [
    '<div class="stat-card" onclick="setDateFilter(true)" id="statInRange"><div class="num">' + s.total_in_date_range + '</div><div class="label">📅 日期范围内</div></div>',
    '<div class="stat-card" onclick="setDateFilter(false)" id="statAll"><div class="num">' + DATA.articles.length + '</div><div class="label">🔍 全部文章</div></div>',
    '<div class="stat-card"><div class="num">' + s.total_before_dedup + '</div><div class="label">📥 搜索原始</div></div>',
    '<div class="stat-card"><div class="num">' + Object.keys(kwMap).length + '</div><div class="label">🏷 关键词</div></div>',
  ];
  document.getElementById('statsPanel').innerHTML = html.join('');
  updateStatHighlight();
}}

function updateStatHighlight() {{
  var e1=document.getElementById('statInRange'), e2=document.getElementById('statAll');
  if(e1)e1.classList.toggle('active',dateFilterOn);
  if(e2)e2.classList.toggle('active',!dateFilterOn);
}}

function setDateFilter(on) {{ dateFilterOn=on; updateStatHighlight(); applyAll(); }}

function initFilters() {{
  var kw=document.getElementById('keywordFilter'), seen=new Set();
  DATA.articles.forEach(function(a){{ seen.add(a.source_keyword); }});
  Array.from(seen).sort().forEach(function(k){{ var o=document.createElement('option');o.value=k;o.textContent=k;kw.appendChild(o); }});
  var ms=document.getElementById('monthFilter'), months=new Set();
  DATA.articles.filter(function(a){{return a.has_date;}}).forEach(function(a){{months.add(a.datetime.substring(0,7));}});
  Array.from(months).sort().reverse().forEach(function(m){{ var o=document.createElement('option');o.value=m;o.textContent=m;ms.appendChild(o); }});
}}

function getFiltered() {{
  var q=document.getElementById('searchInput').value.toLowerCase();
  var kw=document.getElementById('keywordFilter').value;
  var mo=document.getElementById('monthFilter').value;
  return DATA.articles.filter(function(a){{
    if(dateFilterOn && !a.in_range) return false;
    if(kw && a.source_keyword!==kw) return false;
    if(mo && (!a.has_date || !a.datetime.startsWith(mo))) return false;
    if(q && !a.title.toLowerCase().includes(q) && !(a.summary||'').toLowerCase().includes(q)) return false;
    return true;
  }});
}}

function applyAll() {{
  currentPage=1;
  var f=getFiltered();
  f.sort(function(a,b){{ var da=a.datetime||''; var db=b.datetime||''; return sortAsc?da.localeCompare(db):db.localeCompare(da); }});
  renderList(f);
}}

function esc(s) {{ var d=document.createElement('div'); d.textContent=s; return d.innerHTML; }}

var currentFiltered;
function renderList(filtered) {{
  currentFiltered=filtered;
  var c=document.getElementById('articleList'), e=document.getElementById('emptyState'), p=document.getElementById('pagination');
  var total=filtered.length, tp=Math.ceil(total/pageSize);
  if(currentPage>tp)currentPage=tp||1;
  document.getElementById('resultCount').textContent='共 '+total+' 篇 第 '+currentPage+'/'+tp+' 页';
  if(total===0){{c.innerHTML='';p.innerHTML='';e.style.display='block';return;}}
  e.style.display='none';
  var s=(currentPage-1)*pageSize, pi=filtered.slice(s,s+pageSize);
  c.innerHTML=pi.map(function(a,i){{ var idx=s+i, ds=a.date_text||'日期未知', nd=!a.has_date, ir=a.in_range;
    return '<div class="article-card">'+
      '<button class="copy-btn" onclick="copyOne('+idx+',this)">📋 复制</button>'+
      '<div class="title"><a href="'+a.url+'" target="_blank">'+esc(a.title)+'</a></div>'+
      '<div class="meta"><span class="source">📢 '+esc(a.source||'未知来源')+'</span><span>'+(nd?'⚠️ ':'')+ds+'</span></div>'+
      '<div class="summary">'+esc(a.summary||'(无摘要)')+'</div>'+
      '<div class="tags"><span class="tag">🔑 '+esc(a.source_keyword)+'</span>'+
        (nd?'<span class="tag no-date">日期未知</span>':ir?'<span class="tag in-range">✓ 范围内</span>':'<span class="tag no-date">范围外</span>')+
      '</div></div>';
  }}).join('');
  var ph='';
  if(tp>1) for(var pg=1;pg<=tp;pg++) ph+='<button class="'+(pg===currentPage?'active':'')+'" onclick="goPage('+pg+')">'+pg+'</button>';
  p.innerHTML=ph;
}}

function goPage(pg){{ currentPage=pg; currentFiltered=getFiltered(); var asc=sortAsc; currentFiltered.sort(function(a,b){{var da=a.datetime||'';var db=b.datetime||'';return asc?da.localeCompare(db):db.localeCompare(da);}}); renderList(currentFiltered); }}
function toggleSort(){{ sortAsc=!sortAsc; document.getElementById('sortBtn').textContent=sortAsc?'📅 最早优先':'📅 最新优先'; applyAll(); }}
function copyOne(idx,btn){{ currentFiltered=getFiltered(); var asc=sortAsc; currentFiltered.sort(function(a,b){{var da=a.datetime||'';var db=b.datetime||'';return asc?da.localeCompare(db):db.localeCompare(da);}}); var a=currentFiltered[idx]; if(!a)return; navigator.clipboard.writeText(a.title+'\\n'+a.url).then(function(){{btn.textContent='✅';btn.classList.add('copied');setTimeout(function(){{btn.textContent='📋 复制';btn.classList.remove('copied');}},2000);}}); }}
function copyAllLinks(){{ currentFiltered=getFiltered(); var asc=sortAsc; currentFiltered.sort(function(a,b){{var da=a.datetime||'';var db=b.datetime||'';return asc?da.localeCompare(db):db.localeCompare(da);}}); var t=currentFiltered.map(function(a){{return a.title+'\\n'+a.url;}}).join('\\n\\n'); navigator.clipboard.writeText(t).then(function(){{alert('已复制 '+currentFiltered.length+' 篇链接');}}); }}
function exportJSON(){{ currentFiltered=getFiltered(); var asc=sortAsc; currentFiltered.sort(function(a,b){{var da=a.datetime||'';var db=b.datetime||'';return asc?da.localeCompare(db):db.localeCompare(da);}}); var b=new Blob([JSON.stringify(currentFiltered,null,2)],{{type:'application/json'}}); var u=URL.createObjectURL(b),el=document.createElement('a');el.href=u;el.download='articles_export.json';el.click();URL.revokeObjectURL(u); }}

var st;
document.getElementById('searchInput').addEventListener('input',function(){{clearTimeout(st);st=setTimeout(applyAll,300);}});
document.getElementById('keywordFilter').addEventListener('change',applyAll);
document.getElementById('monthFilter').addEventListener('change',applyAll);
document.addEventListener('DOMContentLoaded',init);
</script>
</body>
</html>'''


def prepare_articles(raw_articles, date_start, date_end):
    """将原始文章数据转换为页面需要的格式。"""
    result = []
    for a in raw_articles:
        dt = a.get("datetime", "")
        in_range = True
        if date_start and date_end:
            in_range = date_start <= dt <= date_end + " 23:59:59"
        result.append({
            "title": a.get("title", ""),
            "url": a.get("url", ""),
            "summary": a.get("summary", ""),
            "datetime": dt,
            "date_text": a.get("date_text", ""),
            "date_description": a.get("date_description", ""),
            "source": a.get("source", ""),
            "source_keyword": a.get("source_keyword", ""),
            "has_date": bool(dt),
            "in_range": in_range,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="生成文章浏览HTML页面")
    parser.add_argument("--input", required=True, help="merged_all.json 或 filtered.json")
    parser.add_argument("--stats", required=True, help="stats.json")
    parser.add_argument("--out", default="viewer.html", help="输出HTML文件路径")
    parser.add_argument("--title", default="微信公众号文章速览", help="页面标题")
    parser.add_argument("--date-start", default=None, help="日期起始 YYYY-MM-DD")
    parser.add_argument("--date-end", default=None, help="日期结束 YYYY-MM-DD")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        merged = json.load(f)
    with open(args.stats, "r", encoding="utf-8") as f:
        stats = json.load(f)

    articles = prepare_articles(
        merged.get("articles", merged if isinstance(merged, list) else []),
        args.date_start,
        args.date_end,
    )
    keywords = stats.get("keywords_searched", [])

    html = build_html(articles, stats, keywords, args.title, args.date_start, args.date_end)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    in_range = sum(1 for a in articles if a["in_range"])
    print(f"✅ 已生成: {args.out}")
    print(f"   {len(articles)} 篇文章 ({in_range} 篇在日期范围内)")


if __name__ == "__main__":
    main()
