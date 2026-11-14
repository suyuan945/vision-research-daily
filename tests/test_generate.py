import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate


PAPER_URL = "https://arxiv.org/abs/2611.12345"
PAPER = {"id": "2611.12345", "title": "Test paper", "url": PAPER_URL}


def response(content, reason="stop"):
    return json.dumps({
        "choices": [{"finish_reason": reason, "message": {"content": content}}],
    }).encode()


class GenerateDigestTests(unittest.TestCase):
    def test_truncated_json_is_retried_then_archived(self):
        digest = {
            "title": "研究日报",
            "summary": "测试摘要",
            "tags": ["4DGS"],
            "highlights": ["测试论文"],
            "markdown": f"## 论文\n[arXiv]({PAPER_URL})\n" + "测试正文" * 100,
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with (
                patch.object(generate, "CONTENT", output),
                patch.object(generate, "collect_papers", return_value={PAPER_URL: PAPER}),
                patch.dict(generate.os.environ, {"DEEPSEEK_API_KEY": "test-key"}),
                patch.object(generate, "request_data", side_effect=[
                    response('{"markdown":"unfinished', "length"),
                    response(json.dumps(digest)),
                ]) as send,
            ):
                generate.main()
                generate.main()
            files = list(output.glob("*.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(send.call_count, 2)
            issue = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertEqual(issue["papers"], [PAPER])
            self.assertEqual(issue["title"], digest["title"])

    def test_unclosed_json_and_unknown_source_are_rejected(self):
        invalid_source = {
            "title": "研究日报",
            "summary": "测试摘要",
            "tags": [],
            "highlights": [],
            "markdown": "https://arxiv.org/abs/2611.99999\n" + "测试正文" * 100,
        }
        with patch.object(generate, "request_data", side_effect=[
            response('{"markdown":"unfinished'),
            response(json.dumps(invalid_source)),
        ]) as send:
            with self.assertRaisesRegex(RuntimeError, "No valid DeepSeek digest"):
                generate.generate_digest("test-key", {PAPER_URL: PAPER})
        self.assertEqual(send.call_count, 2)
