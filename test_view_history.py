import json
import tempfile
import unittest
from pathlib import Path

from view_history import build_history, report_link, write_history


class TestHistory(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def batch(self, name, manifest):
        batch = self.root / name
        batch.mkdir()
        (batch / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return batch

    def test_order_summary_and_link(self):
        older = self.batch("workflow_older", {
            "started_at": "2025-01-01T00:00:00+00:00",
            "status": "MATCH",
            "exit_code": 0,
            "report_html": "report.html",
        })
        (older / "report.html").write_text("OK", encoding="utf-8")
        self.batch("workflow_newer", {
            "started_at": "2025-01-02T00:00:00+00:00",
            "status": "EXCEPTIONS",
            "exit_code": 1,
        })
        output = write_history(self.root)
        document = output.read_text(encoding="utf-8")
        self.assertEqual(
            output.resolve(),
            (self.root / "index.html").resolve(),
        )
        self.assertIn("运行记录：2", document)
        self.assertIn("打开报告", document)
        self.assertLess(
            document.index("workflow_newer"),
            document.index("workflow_older"),
        )

    def test_failure_escape_and_broken_manifest(self):
        self.batch("workflow_failed", {
            "status": "FAILED",
            "error": "<script>alert(1)</script>",
            "report_html": "report.html",
        })
        broken = self.root / "workflow_broken"
        broken.mkdir()
        (broken / "manifest.json").write_text("{", encoding="utf-8")
        document = build_history(self.root)
        self.assertNotIn("<script>", document)
        self.assertIn("&lt;script&gt;", document)
        self.assertIn("清单损坏或缺失：1", document)
        self.assertNotIn("打开报告", document)

    def test_empty_history_and_path_escape(self):
        self.assertIn("暂无运行记录", build_history(self.root))
        batch = self.root / "workflow_test"
        batch.mkdir()
        outside = self.root / "outside.html"
        outside.write_text("outside", encoding="utf-8")
        link = report_link(batch, {
            "status": "MATCH",
            "report_html": "../outside.html",
        })
        self.assertEqual(link, "报告路径被拒绝")


if __name__ == "__main__":
    unittest.main()
