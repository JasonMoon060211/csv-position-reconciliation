import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from validate_inputs import validate_file
from view_history import build_history

BASE = Path(__file__).resolve().parent


class TestReleaseRegressions(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_invalid_manifest_status_is_unreadable(self):
        batch = self.root / "workflow_broken"
        batch.mkdir()

        for status in ([], {}, None, 123, "UNKNOWN"):
            with self.subTest(status=status):
                (batch / "manifest.json").write_text(
                    json.dumps({"status": status}),
                    encoding="utf-8",
                )
                document = build_history(self.root)
                self.assertIn("清单损坏或缺失：1", document)
                self.assertNotIn("打开报告", document)

    def test_validator_accepts_utf8_bom(self):
        path = self.root / "trades.csv"
        path.write_text(
            "trade_id,account,symbol,side,quantity\n"
            "T1,DEMO_ACCOUNT,DEMO,BUY,10\n",
            encoding="utf-8-sig",
        )
        self.assertEqual(validate_file(path, "trades"), 1)

    def test_cli_rejects_malformed_csv(self):
        cases = {
            "duplicate_header": (
                "trade_id,account,symbol,side,quantity,quantity\n"
                "T1,DEMO_ACCOUNT,DEMO,BUY,10,10\n"
            ),
            "extra_field": (
                "trade_id,account,symbol,side,quantity\n"
                "T1,DEMO_ACCOUNT,DEMO,BUY,10,EXTRA\n"
            ),
            "surrounding_whitespace": (
                "trade_id,account,symbol,side,quantity\n"
                "T1, DEMO_ACCOUNT,DEMO,BUY,10\n"
            ),
        }

        for name, content in cases.items():
            with self.subTest(case=name):
                folder = self.root / name
                folder.mkdir()

                (folder / "trades.csv").write_text(
                    content, encoding="utf-8"
                )
                (folder / "opening.csv").write_text(
                    "account,symbol,quantity\n"
                    "DEMO_ACCOUNT,DEMO,50\n",
                    encoding="utf-8",
                )
                (folder / "reference.csv").write_text(
                    "account,symbol,quantity\n"
                    "DEMO_ACCOUNT,DEMO,60\n",
                    encoding="utf-8",
                )

                result = subprocess.run(
                    [
                        sys.executable,
                        str(BASE / "reconcile_cli.py"),
                        "--trades", str(folder / "trades.csv"),
                        "--opening", str(folder / "opening.csv"),
                        "--reference", str(folder / "reference.csv"),
                        "--output-dir", str(folder / "outputs"),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )

                self.assertEqual(
                    result.returncode, 2, result.stderr
                )
                self.assertIn("Input validation", result.stderr)
                self.assertEqual(
                    list((folder / "outputs").rglob("report.csv")),
                    [],
                )


if __name__ == "__main__":
    unittest.main()
