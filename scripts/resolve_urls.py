#!/usr/bin/env python3
"""
解析搜狗微信搜索结果中的跳转链接，获取真实的目标 URL。

用法:
    python resolve_urls.py --input filtered.json --output resolved.json

搜狗反爬虫很强，解析成功率不高。优先使用搜索引擎找转载链接作为替代。
"""

import json
import re
import time
import argparse
from pathlib import Path
from urllib.request import Request, urlopen

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def resolve_sogou_url(sogou_url: str, timeout: int = 15) -> dict:
    """跟随搜狗跳转链接，获取最终目标 URL。"""
    result = {"sogou_url": sogou_url, "resolved_url": None, "is_wechat": False, "error": None}
    try:
        req = Request(sogou_url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as resp:
            final_url = resp.url
            result["resolved_url"] = final_url
            result["is_wechat"] = "mp.weixin.qq.com" in final_url
            result["status_code"] = resp.status

            if not result["is_wechat"]:
                html = resp.read().decode("utf-8", errors="replace")
                # 尝试从 JS 中提取微信链接
                match = re.search(r"var\s+msg_link\s*=\s*['\"](https?://mp\.weixin\.qq\.com[^'\"]+)", html)
                if not match:
                    match = re.search(r"url\s*\+=\s*'([^']*)'", html)
                    parts = re.findall(r"url\s*\+=\s*'([^']*)'", html)
                    if parts:
                        joined = "".join(parts)
                        if "mp.weixin.qq.com" in joined:
                            result["resolved_url"] = joined
                            result["is_wechat"] = True
                            result["extracted_from_js"] = True
                else:
                    result["resolved_url"] = match.group(1)
                    result["is_wechat"] = True
                    result["extracted_from_js"] = True

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


def main():
    parser = argparse.ArgumentParser(description="解析搜狗URL为原始微信URL")
    parser.add_argument("--input", required=True, help="输入JSON（含articles数组）")
    parser.add_argument("--output", default="resolved_urls.json", help="输出JSON文件")
    parser.add_argument("--delay", type=float, default=0.8, help="请求间隔秒数")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    articles = data.get("articles", data if isinstance(data, list) else [])

    print(f"📋 共 {len(articles)} 篇文章需要解析URL\n")

    resolved = []
    for i, article in enumerate(articles):
        url = article.get("url", "")
        title = article.get("title", "")[:50]
        print(f"[{i+1}/{len(articles)}] {title}...")
        result = resolve_sogou_url(url)
        resolved.append({**article, **result})

        if result["is_wechat"]:
            print(f"  ✅ {result['resolved_url'][:80]}...")
        elif result["error"]:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  ⚠️ 非微信链接")

        time.sleep(args.delay)

    success = sum(1 for r in resolved if r["is_wechat"])
    print(f"\n{'='*50}")
    print(f"📊 完成: {success}/{len(resolved)} 成功")

    output = {"total": len(resolved), "success": success, "articles": resolved}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"💾 已保存: {args.output}")


if __name__ == "__main__":
    main()
