import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parent / "reconcile_cli.py"


class TestCLI(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

        self.write(
            "opening.csv",
            "account,symbol,quantity\nACC001,DEMO,50\n",
        )
        self.write(
            "trades.csv",
            "trade_id,account,symbol,side,quantity\n"
            "T001,ACC001,DEMO,BUY,10\n",
        )
        self.write(
            "reference.csv",
            "account,symbol,quantity\nACC001,DEMO,60\n",
        )

    def write(self, name, content):
        (self.folder / name).write_text(content, encoding="utf-8")

    def run_cli(self):
        return subprocess.run(
            [
                sys.executable, str(CLI),
                "--trades", str(self.folder / "trades.csv"),
                "--opening", str(self.folder / "opening.csv"),
                "--reference", str(self.folder / "reference.csv"),
                "--output-dir", str(self.folder / "outputs"),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_match_returns_zero_and_writes_log(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)

        reports = list(self.folder.glob("outputs/*/report.csv"))
        self.assertEqual(len(reports), 1)
        self.assertIn("MATCH", reports[0].read_text(encoding="utf-8"))
        log = reports[0].parent / "run.log"
        self.assertIn("Completed", log.read_text(encoding="utf-8"))

    def test_mismatch_returns_one(self):
        self.write(
            "reference.csv",
            "account,symbol,quantity\nACC001,DEMO,61\n",
        )
        result = self.run_cli()

        self.assertEqual(result.returncode, 1, result.stderr)
        reports = list(self.folder.glob("outputs/*/report.csv"))
        self.assertEqual(len(reports), 1)
        self.assertIn("MISMATCH", reports[0].read_text(encoding="utf-8"))

    def test_missing_file_returns_two(self):
        (self.folder / "trades.csv").unlink()
        result = self.run_cli()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Failed", result.stderr)
        self.assertEqual(
            list(self.folder.glob("outputs/*/report.csv")), []
        )

    def test_rerun_preserves_previous_report(self):
        first = self.run_cli()
        second = self.run_cli()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(
            len(list(self.folder.glob("outputs/*/report.csv"))), 2
        )


if __name__ == "__main__":
    unittest.main()
