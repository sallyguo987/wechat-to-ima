#!/usr/bin/env python3
"""
批量导入 URL 到 IMA 知识库。

用法:
    # 从 filtered.json 导入到指定知识库
    python ima_import.py --kb "南康家具" --input filtered.json

    # 指定凭证目录和知识库名称
    python ima_import.py --kb "我的知识库" --input articles.json --cred-dir ~/.config/ima

凭证存放:
    ~/.config/ima/client_id   — IMA OpenAPI Client ID
    ~/.config/ima/api_key     — IMA OpenAPI API Key

获取凭证: https://ima.qq.com/agent-interface
"""

import json
import sys
import time
import argparse
from pathlib import Path
from urllib.request import Request, urlopen

API_BASE = "https://ima.qq.com/openapi/wiki/v1"
DEFAULT_CRED_DIR = Path.home() / ".config" / "ima"


def load_credentials(cred_dir):
    """从文件读取 IMA API 凭证。"""
    d = Path(cred_dir)
    cid = (d / "client_id").read_text().strip()
    akey = (d / "api_key").read_text().strip()
    if not cid or not akey:
        raise SystemExit("❌ 凭证为空，请先配置 ~/.config/ima/client_id 和 api_key")
    return cid, akey


def api_post(endpoint, data, cid, akey, timeout=30):
    """调用 IMA OpenAPI。"""
    url = f"{API_BASE}/{endpoint}"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("ima-openapi-clientid", cid)
    req.add_header("ima-openapi-apikey", akey)
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def find_knowledge_base(cid, akey, name):
    """通过名称搜索知识库，返回 kb_id，未找到返回 None。"""
    resp = api_post("search_knowledge_base", {"query": name, "cursor": "", "limit": 10}, cid, akey)
    for kb in resp.get("data", {}).get("info_list", []):
        kb_name = kb.get("kb_name") or kb.get("name", "")
        if name in kb_name:
            return kb.get("kb_id") or kb.get("id")
    return None


def load_articles(input_path):
    """加载文章 JSON（兼容 filtered.json 和自定义格式）。
    标准格式: {"articles": [{"title":"...", "url":"...", "import_url":"...", ...}, ...]}
    也支持: {"articles": [{"import_url":"..."}, ...]} 和纯 URL 列表。
    """
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", data if isinstance(data, list) else [])
    if not articles:
        raise SystemExit(f"❌ 输入文件无数据: {input_path}")

    urls = []
    for a in articles:
        if isinstance(a, str):
            urls.append(a)
        else:
            url = a.get("import_url") or a.get("url", "")
            if url:
                urls.append(url)

    if not urls:
        raise SystemExit("❌ 输入文件中没有找到可导入的URL")

    return articles, urls


def import_urls(kb_id, urls, cid, akey, batch_size=10):
    """分批导入 URL，返回 (success_count, fail_count, results_dict)。"""
    ok = fail = 0
    results = {}

    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"\n📦 第{batch_num}批 ({len(batch)}篇)")

        resp = api_post("import_urls", {"knowledge_base_id": kb_id, "urls": batch}, cid, akey)
        code = resp.get("code")
        if code is not None and code != 0:
            print(f"  ❌ API错误: {resp.get('msg')}")
            fail += len(batch)
            continue

        for url, r in (resp.get("data", {}).get("results", {})).items():
            ret = r.get("ret_code") if r.get("ret_code") is not None else r.get("code", -1)
            if ret == 0:
                ok += 1
                mid = r.get("media_id", "?")
                print(f"  ✅ {mid[:50]}")
            else:
                fail += 1
                print(f"  ❌ {url[:60]}... → ret_code={ret}")
            results[url] = r

        if i + batch_size < len(urls):
            time.sleep(1)

    return ok, fail, results


def main():
    parser = argparse.ArgumentParser(description="批量导入URL到IMA知识库")
    parser.add_argument("--kb", required=True, help="知识库名称（如 '南康家具'）")
    parser.add_argument("--input", required=True, help="文章JSON文件路径（filtered.json）")
    parser.add_argument("--cred-dir", default=str(DEFAULT_CRED_DIR), help="凭证目录")
    parser.add_argument("--out", default=None, help="导入结果输出文件（默认 stdout 不保存）")
    parser.add_argument("--batch", type=int, default=10, help="每批导入数量（默认10）")
    args = parser.parse_args()

    print("=" * 60)
    print(f"📤 批量导入 URL → IMA知识库「{args.kb}」")
    print("=" * 60)

    # 1. 加载凭证
    cid, akey = load_credentials(args.cred_dir)
    print("✅ 凭证就绪")

    # 2. 查找知识库
    kb_id = find_knowledge_base(cid, akey, args.kb)
    if not kb_id:
        print(f'❌ 未找到知识库"{args.kb}"，请确认名称正确且凭证有效')
        sys.exit(1)
    print(f"✅ 知识库: {args.kb} ({kb_id})")

    # 3. 加载文章
    articles, urls = load_articles(args.input)
    wechat_count = sum(1 for u in urls if "mp.weixin.qq.com" in u)
    print(f"\n📋 共 {len(urls)} 篇 ({wechat_count} 篇微信原文)")

    # 4. 导入
    ok, fail, results = import_urls(kb_id, urls, cid, akey, args.batch)

    # 5. 结果
    output = {
        "kb_name": args.kb,
        "kb_id": kb_id,
        "total": len(urls),
        "success": ok,
        "failed": fail,
        "results": results,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n📁 结果: {args.out}")

    print(f"\n{'=' * 60}")
    print(f"📊 导入完成: ✅ {ok} 成功, ❌ {fail} 失败")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
