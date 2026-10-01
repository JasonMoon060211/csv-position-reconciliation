import csv
import tempfile
import unittest
from pathlib import Path

from report_html import COLUMNS, build_html, write_html


def make_row(account="ACC001", status="MATCH"):
    return {
        "account": account,
        "symbol": "DEMO",
        "calculated_position": "60",
        "reference_position": "60" if status == "MATCH" else "61",
        "difference": "0" if status == "MATCH" else "-1",
        "status": status,
    }


class TestHTMLReport(unittest.TestCase):
    def test_summary_and_exception_order(self):
        document = build_html([
            make_row("MATCH_ACCOUNT"),
            make_row("EXCEPTION_ACCOUNT", "MISMATCH"),
        ])
        self.assertIn("持仓：2", document)
        self.assertIn("异常：1", document)
        self.assertLess(
            document.index("EXCEPTION_ACCOUNT"),
            document.index("MATCH_ACCOUNT"),
        )

    def test_html_is_escaped(self):
        document = build_html([
            make_row("<script>alert(1)</script>"),
        ])
        self.assertNotIn("<script>", document)
        self.assertIn("&lt;script&gt;", document)

    def test_invalid_reports_are_rejected(self):
        for rows in ([], [{}], [make_row(status="UNKNOWN")]):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    build_html(rows)

    def test_csv_to_html(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "report.csv"
            with source.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerow(make_row())

            output = write_html(source)

            self.assertEqual(output, source.with_suffix(".html"))
            self.assertIn(
                "全部一致", output.read_text(encoding="utf-8")
            )
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
