import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from scripts import generate
from scripts.topics import classify, ARXIV_QUERIES


class ResearchCoverageTests(unittest.TestCase):
    def test_generation_families_are_independent(self):
        self.assertEqual(classify("A world model for interactive agents"), ["世界模型"])
        self.assertEqual(classify("Scaling text-to-video diffusion"), ["视频生成"])
        self.assertEqual(classify("ControlNet for controllable generation"), ["可控生成"])
        self.assertIn("可控生成", classify("相机控制与视频编辑"))
        self.assertIn("视频生成", classify("文生视频模型"))

    def test_queries_merge_versions_and_reject_stale_or_future_records(self):
        def feed(entries):
            return ('<feed xmlns="http://www.w3.org/2005/Atom">' + ''.join(
                '<entry><id>http://arxiv.org/abs/' + pid + '</id><title>' + title
                + '</title><summary>Research abstract</summary><published>' + date
                + '</published></entry>' for pid, title, date in entries) + '</feed>').encode()
        feeds = [feed([
            ("2611.00001v1", "Video generation", "2026-11-13T00:00:00Z"),
            ("2611.00002v1", "Video generation", "2026-11-01T00:00:00Z"),
            ("2611.00003v1", "Video generation", "2026-11-15T00:00:00Z"),
        ]), feed([("2611.00001v2", "Video generation with a world model", "2026-11-13T00:00:00Z")]), feed([]), feed([])]
        with patch.object(generate, "request_data", side_effect=feeds) as request, patch.object(generate.time, "sleep"):
            papers = generate.collect_papers(datetime(2026, 11, 14, tzinfo=timezone.utc))
        self.assertEqual(len(papers), 1)
        self.assertEqual(next(iter(papers.values()))["topics"], ["视频生成", "世界模型"])
        queries = [parse_qs(urlsplit(call.args[0].full_url).query)["search_query"][0] for call in request.call_args_list]
        self.assertEqual(len(queries), len(ARXIV_QUERIES))
        self.assertTrue(any('"world model"' in query and '"3D"' not in query for query in queries))

    def test_partial_query_failure_is_not_reported_as_empty_success(self):
        with patch.object(generate, "request_data", side_effect=[b'<feed/>', TimeoutError()]), patch.object(generate.time, "sleep"):
            with self.assertRaises(TimeoutError):
                generate.collect_papers(datetime(2026, 11, 14, tzinfo=timezone.utc))
