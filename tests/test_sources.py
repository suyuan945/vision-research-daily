import unittest
from datetime import datetime
from unittest.mock import patch
from urllib.error import URLError

from scripts import collect_github, collect_wechat


NOW = datetime.fromisoformat("2026-11-14T11:00:00+08:00")
REPO = {
    "id": 10, "full_name": "test/splat", "created_at": "2026-11-11T00:00:00Z", "size": 10,
    "description": "A Gaussian splatting renderer",
    "license": {"spdx_id": "MIT"},
}
RELEASE = {
    "id": 20, "published_at": "2026-11-12T00:00:00Z", "tag_name": "v1",
    "assets": [{"name": "weights.safetensors"}, {"name": "guide.pdf"}],
}


class GithubTests(unittest.TestCase):
    def test_repo_and_release_keep_separate_events_across_retries(self):
        def fetch(path, *, raw=False):
            if path.startswith("/search"):
                return {"items": [REPO]}
            if raw:
                return "Paper: https://arxiv.org/abs/2611.12345"
            if "/releases" in path:
                return [RELEASE, {**RELEASE, "id": 99, "draft": True}]
            return REPO

        config = {"topics": {"3DGS": "splat", "动态重建": "splat"}, "watch": {"test/splat": "高斯渲染"}}
        with patch.object(collect_github, "github", side_effect=fetch):
            result = collect_github.collect(config, {}, NOW, 7)
            repeated = collect_github.collect(config, result, NOW.replace(day=15), 7)
        self.assertEqual(len(repeated["repositories"]), 1)
        self.assertEqual(len(repeated["events"]), 2)
        self.assertEqual(repeated["events"][0]["weights"], ["weights.safetensors"])
        self.assertEqual(repeated["events"][0]["first_seen"], "2026-11-14")
        self.assertEqual(repeated["repositories"][0]["paper_ids"], ["2611.12345"])

    def test_failed_search_preserves_history(self):
        previous = {"events": [{"id": "old", "date": "2026-11-11"}]}
        with patch.object(collect_github, "github", side_effect=URLError("failed")):
            result = collect_github.collect({"topics": {"3DGS": "splat"}, "watch": {}}, previous, NOW, 7)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["events"], previous["events"])


class WechatTests(unittest.TestCase):
    def test_public_url_is_normalized_and_article_has_source_date(self):
        data = b"""<rss><channel><title>CV</title><item><title>4DGS reconstruction</title>
        <link>https://mp.weixin.qq.com/s/published?source=rss</link>
        <pubDate>Thu, 12 Nov 2026 23:00:00 +0800</pubDate>
        <description><![CDATA[<a href="https://arxiv.org/abs/2611.12345">paper</a>]]></description>
        </item></channel></rss>"""
        articles, newest = collect_wechat.from_feed(data, "CV", NOW)
        self.assertEqual(articles[0]["url"], "https://mp.weixin.qq.com/s/published")
        self.assertEqual(articles[0]["paper_ids"], ["2611.12345"])
        self.assertEqual(articles[0]["date"], "2026-11-12")
        self.assertEqual(newest.day, 12)
        with self.assertRaises(ValueError):
            collect_wechat.from_feed(data, "Different account", NOW)
