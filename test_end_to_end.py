import csv
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

        for name in ("reconcile.py", "reconcile_daily.py"):
            shutil.copy2(SOURCE / name, self.folder / name)

        self.write(
            "opening_positions.csv",
            "account,symbol,quantity\n"
            "ACC001,DEMO,50\n"
            "ACC002,TEST,20\n"
            "ACC003,OTHER,12\n",
        )
        self.write(
            "trades.csv",
            "trade_id,account,symbol,side,quantity\n"
            "T001,ACC001,DEMO,BUY,90\n"
            "T002,ACC002,TEST,BUY,7\n",
        )
        self.write(
            "positions.csv",
            "account,symbol,quantity\n"
            "ACC001,DEMO,140\n"
            "ACC002,TEST,28\n"
            "ACC003,OTHER,12\n",
        )

    def write(self, name, text):
        (self.folder / name).write_text(text, encoding="utf-8")

    def run_program(self):
        return subprocess.run(
            [sys.executable, str(self.folder / "reconcile_daily.py")],
            cwd=self.folder,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_report_contents(self):
        result = self.run_program()
        self.assertEqual(result.returncode, 0, result.stderr)

        with (self.folder / "daily_report.csv").open(
            newline="", encoding="utf-8"
        ) as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [row["status"] for row in rows],
            ["MATCH", "MISMATCH", "MATCH"],
        )
        self.assertEqual(
            [row["calculated_position"] for row in rows],
            ["140", "27", "12"],
        )
        self.assertEqual(
            [row["difference"] for row in rows],
            ["0", "-1", "0"],
        )

    def test_duplicate_trade_blocks_report(self):
        with (self.folder / "trades.csv").open(
            "a", encoding="utf-8"
        ) as file:
            file.write("T001,ACC001,DEMO,BUY,90\n")

        result = self.run_program()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate trade ID", result.stderr)
        self.assertFalse((self.folder / "daily_report.csv").exists())

    def test_missing_column_blocks_report(self):
        self.write(
            "trades.csv",
            "trade_id,account,symbol,quantity\n"
            "T001,ACC001,DEMO,90\n",
        )

        result = self.run_program()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing columns", result.stderr)
        self.assertFalse((self.folder / "daily_report.csv").exists())


if __name__ == "__main__":
    unittest.main()
