"""Index public WeChat article links from configured RSS feeds."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request

if __package__:
    from .collect_github import ARXIV_ID, ASIA_SHANGHAI, ROOT
    from .generate import request_data
else:
    from collect_github import ARXIV_ID, ASIA_SHANGHAI, ROOT
    from generate import request_data

INDEX = ROOT / "site" / "articles.json"
if __package__:
    from .topics import TOPICS
else:
    from topics import TOPICS


class FeedDescription(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs).get("href") or "")

    def handle_data(self, data):
        self.parts.append(data)


def canonical_url(value):
    url = urlsplit(value)
    if url.scheme != "https" or url.netloc != "mp.weixin.qq.com":
        raise ValueError("Expected a public WeChat article URL")
    if url.path.startswith("/s/") and len(url.path) > 3:
        return "https://mp.weixin.qq.com" + url.path
    params = parse_qs(url.query)
    keys = ("__biz", "mid", "idx", "sn")
    if url.path == "/s" and all(key in params for key in keys):
        return "https://mp.weixin.qq.com/s?" + urlencode({key: params[key][0] for key in keys})
    raise ValueError("Expected a public WeChat article permalink")


def from_feed(data, account, now):
    channel = ET.fromstring(data).find("channel")
    if channel is None or channel.findtext("title", "").strip().casefold() != account.casefold():
        raise ValueError("RSS account name does not match the configured source")
    items = channel.findall("item")
    newest = None
    articles = []
    for item in items:
        title = item.findtext("title", "").strip()
        published = parsedate_to_datetime(item.findtext("pubDate", ""))
        if published.tzinfo is None:
            raise ValueError("RSS publication date has no timezone")
        if published > now:
            continue
        newest = max(newest, published) if newest else published
        if published < now - timedelta(days=7):
            continue
        description = FeedDescription()
        description.feed(item.findtext("description", ""))
        tags = [topic for topic, pattern in TOPICS.items()
                if re.search(pattern, title + " " + " ".join(description.parts), re.I)]
        if not tags:
            continue
        papers = sorted({pid for link in description.links for pid in ARXIV_ID.findall(link)})
        articles.append({
            "account": account, "title": title, "url": canonical_url(item.findtext("link", "")),
            "date": published.astimezone(ASIA_SHANGHAI).date().isoformat(), "tags": tags, "paper_ids": papers,
        })
    return articles, newest


def article_index(previous, config):
    return {
        "sources": {
            account: previous.get("sources", {}).get(account, {"state": "pending"})
            if feed else {"state": "manual"}
            for account, feed in config["accounts"].items()
        },
        "articles": previous.get("articles", []),
    }


def main():
    config = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))["wechat"]
    previous = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    archive = article_index(previous, config)
    rows = {article["url"]: article for article in archive["articles"]}
    now = datetime.now(ASIA_SHANGHAI)
    failed = False
    for account, feed in config["accounts"].items():
        if not feed:
            continue
        try:
            request = Request(feed, headers={"User-Agent": "VisionResearchDaily/3.0"})
            articles, newest = from_feed(request_data(request, timeout=12), account, now)
            rows.update((article["url"], article) for article in articles)
            state = "ok" if newest and now - newest <= timedelta(days=14) else "stale"
            archive["sources"][account] = {"state": state, "newest": newest.date().isoformat() if newest else ""}
            print(f"WeChat {account}: {state}, {len(articles)} matching articles")
        except (HTTPError, URLError, TimeoutError, ET.ParseError, ValueError) as error:
            failed = True
            archive["sources"][account] = {"state": "failed"}
            print(f"WeChat {account}: {type(error).__name__}; keeping archived articles")
    archive["articles"] = sorted(rows.values(), key=lambda item: item["date"], reverse=True)
    temp = INDEX.with_suffix(".tmp")
    temp.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(INDEX)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
