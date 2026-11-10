#!/usr/bin/env python3
"""Build daily articles, a deduplicated paper catalog, and detail pages."""
import html
import json
import re
from datetime import datetime
from pathlib import Path
import mistune

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CONTENT = ROOT / "content"
(SITE / "issues").mkdir(parents=True, exist_ok=True)
(SITE / "papers").mkdir(parents=True, exist_ok=True)
markdown = mistune.create_markdown(plugins=["table", "strikethrough", "url"])
PAPER_LINK = re.compile(r'\[([^\]\n]{2,200})\]\(https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?(?:[?#][^)]*)?\)')
PAPER_URL = re.compile(r'https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?')
PAPER_ID = re.compile(r'^\d{4}\.\d{4,5}$')

def safe(value):
    return html.escape(str(value or ""), quote=True)

def tags_html(tags):
    return "".join('<span class="tag">' + safe(x) + '</span>' for x in tags)

def header(prefix):
    return (f'<header class="site-header"><div class="header-inner">'
            f'<a class="brand" href="{prefix}"><span class="brand-mark">◈</span>'
            f'<span>3D <em>VISION</em> DAILY</span></a>'
            f'<nav class="site-nav"><a href="{prefix}#today">今日</a>'
            f'<a href="{prefix}#papers">论文库</a><a href="{prefix}#favorites">我的收藏</a>'
            f'<a href="{prefix}#archive">历史日报</a></nav></div></header>')

def shell(title, description, body, prefix="../", extra_script=""):
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="description" content="{safe(description)}">'
            f'<title>{safe(title)} · 3D Vision Research Hub</title>'
            f'<link rel="stylesheet" href="{prefix}assets/style.css"></head>'
            f'<body>{header(prefix)}{body}'
            f'<footer class="site-footer">3D VISION RESEARCH HUB · RESEARCH FIRST, EVIDENCE FIRST.</footer>'
            f'<script src="{prefix}assets/research-store.js" defer></script>{extra_script}</body></html>')

def paper_record(pid, title, date, tags, source="digest", abstract="", published=""):
    return {"id":pid, "title":title, "url":f"https://arxiv.org/abs/{pid}",
            "first_seen":date, "last_seen":date, "digests":[date],
            "tags":list(tags), "abstract":abstract, "published":published,
            "source":source, "code_url":None, "code_status":"未核实"}

def merge_paper(catalog, record):
    pid = record["id"]
    if not PAPER_ID.fullmatch(pid):
        return
    if pid not in catalog:
        catalog[pid] = record
        return
    old = catalog[pid]
    old["first_seen"] = min(old["first_seen"], record["first_seen"])
    old["last_seen"] = max(old["last_seen"], record["last_seen"])
    old["digests"] = sorted(set(old["digests"] + record["digests"]), reverse=True)
    old["tags"] = list(dict.fromkeys(old["tags"] + record["tags"]))
    if record.get("abstract") and not old.get("abstract"):
        old["abstract"] = record["abstract"]
    if record.get("published") and not old.get("published"):
        old["published"] = record["published"]
    if record.get("source") == "arxiv_metadata":
        old["title"] = record["title"]
        old["source"] = "arxiv_metadata"

issues = []
papers = {}
for file in sorted(CONTENT.glob("*.json")):
    item = json.loads(file.read_text(encoding="utf-8"))
    date = item.get("date", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        continue
    datetime.strptime(date, "%Y-%m-%d")
    title = item.get("title", "技术日报")
    kind = item.get("kind", "技术日报")
    subtitle = item.get("summary", "")
    topic_tags = item.get("tags", [])
    md_text = item.get("markdown", "")
    body = markdown(md_text)
    body = re.sub(r"(<table>.*?</table>)", r'<div class="table-scroll">\1</div>', body, flags=re.S)
    article = (
        f'<main class="article-shell"><a class="article-back" href="../#archive">← 返回历史日报</a>'
        f'<div class="article-header"><div class="article-kicker">{safe(date)} / {safe(kind)}</div>'
        f'<h1>{safe(title)}</h1><p class="article-intro">{safe(subtitle)}</p>'
        f'<div class="tag-list">{tags_html(topic_tags)}</div></div>'
        f'<article class="prose">{body}</article>'
        f'<div class="article-end"><a href="../#papers">浏览论文库 ↗</a></div></main>'
    )
    (SITE / "issues" / f"{date}.html").write_text(
        shell(title, subtitle, article), encoding="utf-8"
    )
    issues.append({key: item[key] for key in ("date","title","summary","kind","tags","highlights") if key in item}
                  | {"url":f"issues/{date}.html"})
    for paper in item.get("papers", []):
        pid = paper.get("id") or PAPER_URL.search(paper.get("url","")).group(1) if PAPER_URL.search(paper.get("url","")) else paper.get("id")
        if not pid or not PAPER_ID.fullmatch(pid):
            continue
        record = paper_record(pid, paper.get("title") or pid, date, topic_tags,
                              "arxiv_metadata", paper.get("summary",""),
                              paper.get("published",""))
        merge_paper(papers, record)
    for match in PAPER_LINK.finditer(md_text):
        label, pid = match.group(1).strip(), match.group(2)
        merge_paper(papers, paper_record(pid, label, date, topic_tags))

for pid, paper in papers.items():
    title = paper["title"]
    description = paper["abstract"] or "历史日报中收录的论文；详细资料请访问 arXiv 原文核实。"
    dates = "".join(f'<a href="../issues/{safe(d)}.html">{safe(d)}</a> ' for d in paper["digests"])
    # Details only display verified metadata or explicitly labelled historical index data.
    abstract = (f'<h2>摘要（arXiv 元数据）</h2><p>{safe(paper["abstract"])}</p>'
                if paper.get("abstract") else
                '<p class="site-note">该论文来自历史日报索引；目前没有导入经核实的原文摘要，名称可能为历史简写。</p>')
    main = (f'<main class="article-shell paper-detail" data-paper-id="{safe(pid)}">'
            f'<a class="article-back" href="../#papers">← 返回论文库</a>'
            f'<div class="article-header"><div class="article-kicker">ARXIV · {safe(pid)}</div>'
            f'<h1>{safe(title)}</h1><p class="article-intro">首次收录：{safe(paper["first_seen"])}'
            f' · 代码状态：未核实</p><div class="tag-list">{tags_html(paper["tags"])}</div></div>'
            f'<div class="paper-actions"><button class="btn save-paper" data-paper-id="{safe(pid)}" type="button">☆ 收藏论文</button>'
            f'<button class="outline-btn ai-paper" data-paper-id="{safe(pid)}" type="button">✦ 复制 ChatGPT 解读问题</button>'
            f'<a class="outline-btn" href="https://arxiv.org/abs/{pid}" target="_blank" rel="noopener noreferrer">arXiv 原文 ↗</a></div>'
            f'<div class="paper-personal"><label for="paper-status">研究状态</label>'
            f'<select id="paper-status" class="paper-status" data-paper-id="{safe(pid)}">'
            f'<option value="unread">待读</option><option value="reading">精读中</option>'
            f'<option value="reproduce">待复现</option><option value="done">已完成</option></select></div>'
            f'<article class="prose">{abstract}<h2>历史收录</h2><p>{dates}</p>'
            f'<h2>下一步研究</h2><p>点击上方“复制 ChatGPT 解读问题”，粘贴至 ChatGPT 对话，'
            f'可以继续分析方法机制、4DGS 适用性、复现条件与实验规划。</p></article>'
            f'</main>')
    (SITE / "papers" / f"{pid}.html").write_text(
        shell(title, description, main, extra_script='<script src="../assets/paper-detail.js" defer></script>'),
        encoding="utf-8"
    )

ordered_papers = sorted(papers.values(), key=lambda d:(d["last_seen"], d["id"]), reverse=True)
(SITE / "papers.json").write_text(json.dumps(ordered_papers, ensure_ascii=False, indent=2), encoding="utf-8")
(SITE / "index.json").write_text(json.dumps(sorted(issues,key=lambda d:d["date"],reverse=True),ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Built {len(issues)} digests and {len(ordered_papers)} unique arXiv paper records")
