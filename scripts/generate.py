#!/usr/bin/env python3
"""Generate a source-grounded research digest from arXiv records."""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1] / "content"
SHANGHAI = timezone(timedelta(hours=8))
ATOM = {"a": "http://www.w3.org/2005/Atom"}
ARXIV_LINK = re.compile(r"https://arxiv\.org/abs/\d{4}\.\d{4,5}(?!\d)")
JSON_EXAMPLE = {
    "title": "日报标题",
    "summary": "研究摘要",
    "tags": ["4DGS"],
    "highlights": ["一句话说明重点"],
    "markdown": "## 论文标题\n[arXiv](https://arxiv.org/abs/0000.00000)\n正文",
}


def request_data(request, timeout):
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        print(f"Temporary network error for {request.host}; retry {attempt}/2")
        time.sleep(attempt * 2)


def collect_papers(now):
    params = urllib.parse.urlencode({
        "search_query": "cat:cs.CV OR cat:cs.AI OR cat:cs.RO",
        "start": 0,
        "max_results": 180,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    request = urllib.request.Request(
        "https://export.arxiv.org/api/query?" + params,
        headers={"User-Agent": "VisionResearchDaily/2.0"},
    )
    root = ET.fromstring(request_data(request, timeout=55))
    cutoff = now - timedelta(days=8)
    papers = {}
    for entry in root.findall("a:entry", ATOM):
        url = entry.findtext("a:id", "", ATOM).replace("http://", "https://")
        if "/api/errors" in url:
            raise RuntimeError("arXiv returned an error feed")
        url = re.sub(r"v\d+$", "", url)
        if not ARXIV_LINK.fullmatch(url):
            continue
        published = entry.findtext("a:published", "", ATOM)
        if datetime.fromisoformat(published.replace("Z", "+00:00")) < cutoff:
            continue
        papers[url] = {
            "id": url.rsplit("/", 1)[-1],
            "title": " ".join(entry.findtext("a:title", "", ATOM).split()),
            "summary": " ".join(entry.findtext("a:summary", "", ATOM).split())[:1200],
            "url": url,
            "published": published,
        }
    return papers


def archived_links():
    links = set()
    for path in CONTENT.glob("*.json"):
        issue = json.loads(path.read_text(encoding="utf-8"))
        links.update(ARXIV_LINK.findall(issue.get("markdown", "")))
        links.update(paper["url"] for paper in issue.get("papers", []) if "url" in paper)
    return links


def parse_digest(response, papers):
    choice = response["choices"][0]
    finish_reason = choice.get("finish_reason")
    print(f"DeepSeek finish_reason={finish_reason}")
    if finish_reason != "stop":
        raise ValueError(f"DeepSeek did not complete generation ({finish_reason})")
    content = choice["message"].get("content") or ""
    if not content.strip():
        raise ValueError("DeepSeek returned an empty response")
    digest = json.loads(content)
    if not isinstance(digest, dict):
        raise ValueError("Expected a JSON object for the digest")
    for field in ("title", "summary", "markdown"):
        value = digest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Expected non-empty text in {field}")
    for field in ("tags", "highlights"):
        value = digest.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"Expected a list of strings in {field}")
    links = list(dict.fromkeys(ARXIV_LINK.findall(digest["markdown"])))
    if not 1 <= len(links) <= 6 or any(url not in papers for url in links):
        raise ValueError("Digest contains missing, excessive, or unknown arXiv links")
    if len(digest["markdown"]) < 350:
        raise ValueError("Digest is shorter than 350 characters")
    return {field: digest[field] for field in JSON_EXAMPLE} | {
        "papers": [papers[url] for url in links],
    }


def generate_digest(key, papers):
    prompt = (
        "从给定的 arXiv 记录中筛选与 3DGS、4DGS、VGGT、几何基础模型、世界模型相关的重点论文。"
        "优先最近24小时，必要时扩展至7天。优先选3至6篇，相关论文不足时按实际数量写。"
        "逐篇概括方法、差异、对稀疏同步多机位4DGS或可控生成的价值与复现状态。"
        "只使用输入给出的真实日期、链接和指标；代码状态缺少资料时写未核实。"
        "title 只写主题，不加日期，归档日期由系统显示。"
        "summary 用两至三句概括，详细内容放在 markdown。"
        "markdown 正文使用 Markdown 链接并逐篇附上完整 arXiv 链接。"
        "严格按以下 JSON 结构输出，示例中的内容不能出现在日报中：\n"
        + json.dumps(JSON_EXAMPLE, ensure_ascii=False)
    )
    sources = json.dumps(list(papers.values()), ensure_ascii=False)
    for attempt, max_tokens in enumerate((8192, 12288), start=1):
        limit = "控制正文在 1000 至 2200 字。" if attempt == 1 else "重新生成更简洁的完整正文，每篇最多两段，全文不超过 1300 字。"
        payload = {
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": "你是科研日报编辑。仅返回一个完整 JSON 对象，保留来源证据。"},
                {"role": "user", "content": f"{prompt}\n{limit}\n来源记录：\n{sources}"},
            ],
        }
        request = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        raw = request_data(request, timeout=120)
        try:
            return parse_digest(json.loads(raw), papers)
        except (ValueError, KeyError, IndexError, TypeError) as error:
            print(f"Digest validation failed on attempt {attempt}: {error}")
            if attempt == 2:
                raise RuntimeError("No valid DeepSeek digest after two attempts") from error


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def generate_issue(now):
    day = now.date().isoformat()
    path = CONTENT / f"{day}.json"
    if path.exists():
        print(f"Issue already exists for {day}; skipping")
        return "published"
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is required to generate a new issue")

    seen = archived_links()
    papers = {url: paper for url, paper in collect_papers(now).items() if url not in seen}
    print(f"Eligible arXiv records after deduplication: {len(papers)}")
    if not papers:
        print("No new arXiv records for this issue; keeping the archive")
        return "no_new"

    digest = generate_digest(key, papers)
    digest.update(date=day, kind="自动生成 · 网页日报")
    digest["markdown"] += "\n\n---\n\n*由模型根据 arXiv 元数据生成，复现状态及指标请以官方论文为准。*"
    write_json(path, digest)
    print(f"Published content: {day} ({len(digest['papers'])} papers)")
    return "published"


def main():
    started = datetime.now(SHANGHAI)
    day = started.date().isoformat()
    status = "failed"
    try:
        status = generate_issue(started)
    finally:
        write_json(CONTENT / "checks" / f"{day}.json", {
            "date": day, "status": status,
            "checked_at": datetime.now(SHANGHAI).isoformat(timespec="seconds"),
        })


if __name__ == "__main__":
    main()
