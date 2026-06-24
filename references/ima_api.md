# IMA OpenAPI 参考

## 概述

IMA（ima.qq.com）提供了 OpenAPI 接口，用于管理知识库内容。API 需要凭证认证。

## 获取凭证

访问 https://ima.qq.com/agent-interface 申请 API 密钥，获得：
- `client_id` - 客户端标识
- `api_key` - API 密钥

凭证存放路径（技能脚本默认读取位置）：
```
~/.config/ima/client_id
~/.config/ima/api_key
```

## API 基础信息

- **Base URL**: `https://ima.qq.com/openapi/wiki/v1`
- **认证方式**: 每个请求 Header 中携带:
  - `ima-openapi-clientid: <client_id>`
  - `ima-openapi-apikey: <api_key>`
- **Content-Type**: `application/json`

## 核心接口

### 1. 搜索知识库

```
POST /search_knowledge_base
```

**请求体**:
```json
{
  "query": "知识库名称",
  "cursor": "",
  "limit": 10
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "info_list": [
      {
        "kb_name": "南康家具",
        "kb_id": "Dv1yX9ksTw715..."
      }
    ]
  }
}
```

### 2. 导入 URL 到知识库

```
POST /import_urls
```

**请求体**:
```json
{
  "knowledge_base_id": "<kb_id>",
  "urls": [
    "https://mp.weixin.qq.com/s/...",
    "https://example.com/article.html"
  ]
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "results": {
      "https://mp.weixin.qq.com/s/...": {
        "ret_code": 0,
        "media_id": "weburl_xxx"
      }
    }
  }
}
```

- `ret_code: 0` 表示导入成功
- `media_id` 为导入后知识库中的条目 ID
- 支持微信公众号链接（`mp.weixin.qq.com`）、普通网页链接、新闻转载等
- 每批次最多建议 10 个 URL

### 3. 获取知识库内容列表

```
POST /get_knowledge_list
```

**请求体**:
```json
{
  "knowledge_base_id": "<kb_id>",
  "cursor": "",
  "limit": 50
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "knowledge_list": [
      {
        "media_id": "weburl_xxx",
        "media_type": 2,
        "title": "文章标题",
        "status": 2
      }
    ],
    "is_end": true,
    "next_cursor": ""
  }
}
```

media_type 含义: 1=文件, 2=网页, 3=文档, 6=微信文章, 7=笔记, 99=文件夹

## 已知限制

1. **无批量删除 API**: 目前 `delete_knowledge` 接口不可用，误导入的条目需手动在 IMA 客户端中删除
2. **搜狗反爬**: 搜狗微信搜索结果中的跳转链接有强反爬机制，`import_urls` 传搜狗链接可能导致只抓到"搜狗搜索"标题。建议优先使用搜索引擎找到的 `mp.weixin.qq.com` 原文链接或新闻网站的全文转载链接
3. **内容解析延迟**: 导入后 IMA 需要几秒到十几秒抓取和解析网页内容，`ret_code: 0` 只表示任务已接收
4. **不支持批量添加文本/笔记**: `import_urls` 只能导入 URL，如需添加纯文本笔记需用其他方式

## 替代 URL 策略

当搜狗链接无法直接用于 IMA 导入时，通过以下方式获取可用 URL：

1. **用文章标题 + "mp.weixin.qq.com" 搜索** → 微信原文链接（最佳）
2. **用文章标题 + "转载" 搜索** → 新闻网站全文转载链接
3. **搜 "site:mp.weixin.qq.com 文章标题"** → 直接定位微信公众号原文
