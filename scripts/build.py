#!/usr/bin/env python3
"""Build daily articles, a deduplicated paper catalog, and detail pages."""
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
import mistune

from collect_wechat import article_index, canonical_url
from collect_github import ASIA_SHANGHAI

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CONTENT = ROOT / "content"
(SITE / "issues").mkdir(parents=True, exist_ok=True)
(SITE / "papers").mkdir(parents=True, exist_ok=True)
markdown = mistune.create_markdown(plugins=["table", "strikethrough", "url"])
PAPER_LINK = re.compile(r'\[([^\]\n]{2,200})\]\(https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?(?:[?#][^)]*)?\)')
PAPER_URL = re.compile(r'https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?')
PAPER_ID = re.compile(r'^\d{4}\.\d{4,5}$')
from topics import TOPICS as PAPER_TOPICS


(SITE / "topics.json").write_text(json.dumps(list(PAPER_TOPICS), ensure_ascii=False) + "\n", encoding="utf-8")

source_config = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
github_index = SITE / "github.json"
if not github_index.exists():
    github_index.write_text('{"status":"pending","repositories":[],"events":[]}\n', encoding="utf-8")
github_archive = json.loads(github_index.read_text(encoding="utf-8"))
repositories = {repo["id"]: repo for repo in github_archive["repositories"]}
related_by_paper = {}
github_by_day = {}
EVENT_LABELS = {"new": "新仓库", "discovered": "首次收录", "release": "版本发布"}
for event in github_archive["events"]:
    repo = repositories[event["repository_id"]]
    if event["kind"] != "discovered":
        day = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(ASIA_SHANGHAI).date().isoformat()
        github_by_day.setdefault(day, []).append((repo, event))
    for pid in repo["paper_ids"]:
        related_by_paper.setdefault(pid, []).append((repo, event))

wechat = source_config["wechat"]
article_path = SITE / "articles.json"
previous = json.loads(article_path.read_text(encoding="utf-8")) if article_path.exists() else {}
article_archive = article_index(previous, wechat)
article_rows = {article["url"]: article for article in article_archive["articles"]}
for article in wechat["articles"]:
    if article["account"] not in wechat["accounts"]:
        raise ValueError("Add the article's public account to sources.json first")
    datetime.strptime(article["date"], "%Y-%m-%d")
    parsed = urlsplit(article["url"])
    if article["account"] == "量子位" and parsed.scheme == "https" and parsed.netloc == "www.qbitai.com":
        url = f"https://www.qbitai.com{parsed.path}"
    else:
        url = canonical_url(article["url"])
    article_rows[url] = {**article, "url": url}
articles = sorted(article_rows.values(), key=lambda item: item["date"], reverse=True)
article_archive["articles"] = articles
article_path.write_text(
    json.dumps(article_archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

def safe(value):
    return html.escape(str(value or ""), quote=True)

def tags_html(tags):
    return "".join('<span class="tag">' + safe(x) + '</span>' for x in tags)

def github_links(updates):
    return "".join(
        f'<li>{EVENT_LABELS[event["kind"]]} · '
        f'<a href="{safe(event["url"])}">{safe(repo["name"])}'
        f'{(" · " + safe(event["version"])) if event.get("version") else ""}</a></li>'
        for repo, event in updates
    )

def article_links(rows):
    return "".join(
        f'<li><a href="{safe(article["url"])}">{safe(article["title"])}</a>'
        f' · {safe(article["account"])}</li>' for article in rows
    )

def header(prefix):
    return (f'<header class="site-header"><div class="header-inner">'
            f'<a class="brand" href="{prefix}"><span class="brand-mark" aria-hidden="true">◈</span>'
            f'<span>Vision <em>Research</em></span></a>'
            f'<nav class="site-nav" aria-label="主导航"><a href="{prefix}#today">今日</a>'
            f'<a href="{prefix}#papers">论文</a><a href="{prefix}#opensource">开源</a>'
            f'<a href="{prefix}#articles">文章</a><a href="{prefix}#favorites">收藏</a>'
            f'<a href="{prefix}#archive">历史</a></nav></div></header>')

def shell(title, description, body, prefix="../", extra_script=""):
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="description" content="{safe(description)}">'
            f'<title>{safe(title)} · Vision Research Hub</title>'
            f'<link rel="stylesheet" href="{prefix}assets/style.css"></head>'
            f'<body>{header(prefix)}{body}'
            f'<footer class="site-footer"><span>Vision Research Hub</span>'
            f'<a href="https://github.com/suyuan945/vision-research-daily/actions">查看更新记录 ↗</a></footer>'
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
    github_updates = github_by_day.get(date, [])
    if github_updates:
        body += f"<h2>同日 GitHub 动态</h2><ul>{github_links(github_updates)}</ul>"
    article_updates = [article for article in articles if article["date"] == date]
    if article_updates:
        body += f"<h2>同日技术文章</h2><ul>{article_links(article_updates)}</ul>"
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
                  | {"url": f"issues/{date}.html", "paper_ids": [paper["id"] for paper in item.get("papers", []) if "id" in paper]})
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

metadata_path = CONTENT / "paper-metadata" / "arxiv.json"
if metadata_path.exists():
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for pid, paper in papers.items():
        if pid not in metadata or paper["source"] == "arxiv_metadata":
            continue
        original = metadata[pid]
        if paper["title"] != original["title"]:
            paper["aliases"] = [paper["title"]]
        paper.update(title=original["title"], abstract=original["abstract"],
                     published=original["published"], source="arxiv_metadata")

for pid, paper in papers.items():
    title = paper["title"]
    heading_topics = [label for label, match in PAPER_TOPICS.items() if re.search(match, title, re.I)]
    abstract_topics = [label for label, match in PAPER_TOPICS.items()
                       if re.search(match, paper["abstract"], re.I)]
    paper["tags"] = list(dict.fromkeys(heading_topics + abstract_topics)) or ["待分类"]
    description = paper["abstract"] or "历史日报中收录的论文；详细资料请访问 arXiv 原文核实。"
    dates = "".join(f'<a href="../issues/{safe(d)}.html">{safe(d)}</a> ' for d in paper["digests"])
    # Details only display verified metadata or explicitly labelled historical index data.
    abstract = (f'<h2>摘要（arXiv 元数据）</h2><p>{safe(paper["abstract"])}</p>'
                if paper.get("abstract") else
                '<p class="site-note">该论文来自历史日报索引；目前没有导入经核实的原文摘要，名称可能为历史简写。</p>')
    related = related_by_paper.get(pid, [])
    related_html = ""
    if related:
        related_html = (
            "<h2>相关仓库动态</h2><p>以下仓库的 README 提及这篇论文。</p>"
            f"<ul>{github_links(related[:10])}</ul>"
        )
    linked_articles = [article for article in articles if pid in article.get("paper_ids", [])]
    if linked_articles:
        related_html += f"<h2>相关解读</h2><ul>{article_links(linked_articles)}</ul>"
    main = (f'<main class="article-shell paper-detail" data-paper-id="{safe(pid)}">'
            f'<a class="article-back" href="../#papers?date={safe(paper["first_seen"])}">← 返回收录日</a>'
            f'<div class="article-header"><div class="article-kicker">ARXIV · {safe(pid)}</div>'
            f'<h1>{safe(title)}</h1><p class="article-intro">首次收录：{safe(paper["first_seen"])}'
            f'{(" · arXiv 提交：" + safe(paper["published"][:10]) + " UTC") if paper["published"] else ""}'
            f' · 代码状态：未核实</p><div class="tag-list">{tags_html(paper["tags"])}</div></div>'
            f'<div class="paper-actions"><button class="btn save-paper" data-paper-id="{safe(pid)}" type="button">☆ 收藏论文</button>'
            f'<button class="outline-btn ai-paper" data-paper-id="{safe(pid)}" type="button">✦ 复制 ChatGPT 解读问题</button>'
            f'<a class="outline-btn" href="https://arxiv.org/abs/{pid}" target="_blank" rel="noopener noreferrer">arXiv 原文 ↗</a></div>'
            f'<div class="paper-personal"><label for="paper-status">研究状态</label>'
            f'<select id="paper-status" class="paper-status" data-paper-id="{safe(pid)}">'
            f'<option value="unread">待读</option><option value="reading">精读中</option>'
            f'<option value="reproduce">待复现</option><option value="done">已完成</option></select></div>'
            f'<article class="prose">{abstract}{related_html}<h2>历史收录</h2><p>{dates}</p>'
            f'<h2>下一步研究</h2><p>点击上方“复制 ChatGPT 解读问题”，粘贴至 ChatGPT 对话，'
            f'可以继续分析方法机制、4DGS 适用性、复现条件与实验规划。</p></article>'
            f'</main>')
    (SITE / "papers" / f"{pid}.html").write_text(
        shell(title, description, main, extra_script='<script src="../assets/paper-detail.js" defer></script>'),
        encoding="utf-8"
    )

ordered_papers = sorted(papers.values(), key=lambda d:(d["last_seen"], d["id"]), reverse=True)
checks = []
for file in sorted((CONTENT / "checks").glob("*.json"), reverse=True):
    checks.append(json.loads(file.read_text(encoding="utf-8")))
(SITE / "paper-checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(SITE / "papers.json").write_text(json.dumps(ordered_papers, ensure_ascii=False, indent=2), encoding="utf-8")
(SITE / "index.json").write_text(json.dumps(sorted(issues,key=lambda d:d["date"],reverse=True),ensure_ascii=False,indent=2),encoding="utf-8")
print(f"Built {len(issues)} digests and {len(ordered_papers)} unique arXiv paper records")
