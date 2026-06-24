---
name: wechat-to-ima
description: "微信公众号文章搜索、整理并导入 IMA 知识库的完整工作流。支持多关键词搜索、日期过滤、智能去重、HTML 浏览页面生成、以及通过 IMA OpenAPI 批量导入文章链接到知识库。This skill should be used when the user wants to search WeChat public account articles by keywords, filter by date range, generate a browseable viewer page, and import articles into an IMA knowledge base. Triggers: 搜索微信公众号文章, 导入IMA知识库, 微信文章批量导入, 搜狗微信搜索, WeChat article search and IMA import, 把微信文章导入知识库."
agent_created: true
---

# 微信公众号文章 → IMA 知识库 工作流

## 概述

本技能提供从"搜索微信公众号文章"到"导入 IMA 知识库"的完整管线：

```
搜索 → 去重 → 日期过滤 → [可选: 生成HTML浏览页] → IMA导入
```

每个环节都有独立的脚本，可单独使用或串联。

## 前置条件

### Node.js 依赖（搜索脚本）

```bash
npm install cheerio
```

### Python 依赖（导入脚本）

```bash
pip install requests   # resolve_urls.py 需要（可选）
# ima_import.py 使用标准库，无需额外依赖
```

### IMA API 凭证（导入时需要）

1. 访问 https://ima.qq.com/agent-interface 申请 API 密钥
2. 保存凭证文件:
   ```bash
   mkdir -p ~/.config/ima
   echo "your_client_id" > ~/.config/ima/client_id
   echo "your_api_key" > ~/.config/ima/api_key
   ```

## 工作流

### 步骤 1: 搜索文章

```bash
# 用编排器执行多关键词搜索
node scripts/search_orchestrator.js \
  --keywords '["关键词1", "关键词2 组词", "地域+关键词"]' \
  --start 2026-04-01 \
  --end 2026-06-23 \
  --out ./output \
  --max 50
```

**输出文件:**
- `output/merged_all.json` - 去重后的全部文章
- `output/filtered.json` - 日期范围内的文章
- `output/stats.json` - 搜索统计信息
- `output/raw/` - 每个关键词的原始搜索结果（缓存用）

**关键词策略**: 使用 3-5 个变体以获取更全面的结果。例如：
- 核心词: `"南康家具"`
- 组词: `"南康 实木家具"`
- 地域限定: `"赣州南康家具"`
- 产业/行业视角: `"南康家居产业"`, `"南康家具产业"`

### 步骤 2: 生成 HTML 浏览页面（可选）

```bash
python scripts/build_viewer.py \
  --input output/merged_all.json \
  --stats output/stats.json \
  --out viewer.html \
  --title "主题 · 微信公众号文章速览" \
  --date-start 2026-04-01 \
  --date-end 2026-06-23
```

生成自包含的 HTML 页面，支持关键词筛选、月份筛选、搜索、复制链接、导出 JSON。

### 步骤 3: 解析搜狗 URL（可选，成功率低）

搜狗链接有强反爬机制，直接通过 HTTP 跟随重定向大概率失败。仅在确实需要原始微信 URL 时尝试：

```bash
python scripts/resolve_urls.py \
  --input output/filtered.json \
  --output output/resolved_urls.json \
  --delay 0.8
```

### 步骤 4: 导入 IMA 知识库

```bash
python scripts/ima_import.py \
  --kb "知识库名称" \
  --input output/filtered.json \
  --out output/import_result.json
```

**输入的 JSON 格式**: 脚本接受 `filtered.json` 格式（含 `articles` 数组），每个元素需有 `url` 字段；也支持 `import_url` 字段（优先使用）。如果直接有微信公众号原文链接（`mp.weixin.qq.com/s/...`）最佳。

**传入搜狗链接的问题**: IMA 可能只能抓到"搜狗搜索"标题而非真实文章内容。此时需在导入前用步骤 3 解析，或用搜索引擎找到原文/转载链接替换。

## 搜索不到原文 URL 时的策略

当搜狗反爬导致无法获取 `mp.weixin.qq.com` 原文链接时，按以下优先级获取可用的导入 URL：

1. **用文章标题搜索微信原文**: `"文章完整标题" site:mp.weixin.qq.com`
2. **用文章标题 + "转载" 搜索**: 找新闻网站的全文转载
3. **直接传搜狗链接给 IMA**: 部分情况下 IMA 服务端能处理跳转（但不保证）
4. **用转载 URL 替代**: 新闻转载内容基本一致，可替代原文

## 脚本说明

| 脚本 | 语言 | 用途 |
|------|------|------|
| `scripts/search_wechat.js` | Node | 单关键词搜狗微信搜索（也可单独使用） |
| `scripts/search_orchestrator.js` | Node | 多关键词搜索编排 + 去重 + 日期过滤 |
| `scripts/resolve_urls.py` | Python | 解析搜狗跳转链接获取真实 URL |
| `scripts/build_viewer.py` | Python | 生成自包含 HTML 浏览页面 |
| `scripts/ima_import.py` | Python | 通过 IMA OpenAPI 批量导入 URL 到知识库 |

## IMA API 关键信息

- Base URL: `https://ima.qq.com/openapi/wiki/v1`
- 认证头: `ima-openapi-clientid` + `ima-openapi-apikey`
- 核心接口: `search_knowledge_base`（查找知识库）、`import_urls`（导入链接）
- 详细 API 参考见 `references/ima_api.md`

## 常见问题

**Q: 搜狗搜索返回 0 结果？**
尝试换关键词变体，或等待几分钟后重试（搜狗有频率限制）。

**Q: IMA 导入后内容不对（标题显示"搜狗搜索"）？**
说明传入了搜狗反爬页面 URL。需要换用微信公众号原文链接或新闻转载链接。

**Q: 想导入的文章不在日期范围内怎么办？**
修改 `search_orchestrator.js` 的 `--start`/`--end` 参数，或将 `filtered.json` 的 `articles_no_date` 合并到 `articles`。

**Q: 如何获取知识库确切的 kb_id？**
运行 `ima_import.py` 会通过名称自动搜索匹配；也可手动调用 `search_knowledge_base` API。
