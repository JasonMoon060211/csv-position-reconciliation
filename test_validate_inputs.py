import tempfile
import unittest
from pathlib import Path

from validate_inputs import validate_file, validate_bundle

TRADE_HEADER = "trade_id,account,symbol,side,quantity\n"
POSITION_HEADER = "account,symbol,quantity\n"


class TestInputValidation(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def reject_trade(self, rows):
        path = self.write("trades.csv", TRADE_HEADER + rows)
        with self.assertRaisesRegex(ValueError, "Input validation"):
            validate_file(path, "trades")

    def test_valid_bundle_with_negative_opening(self):
        self.write(
            "trades.csv",
            TRADE_HEADER + "T1,A,DEMO,SELL,5\n",
        )
        self.write(
            "opening.csv",
            POSITION_HEADER + "A,DEMO,-10\n",
        )
        self.write(
            "reference.csv",
            POSITION_HEADER + "A,DEMO,-15\n",
        )
        self.assertEqual(
            validate_bundle(self.root),
            {"trades": 1, "opening": 1, "reference": 1},
        )

    def test_duplicate_trade_id(self):
        self.reject_trade(
            "T1,A,DEMO,BUY,10\n"
            "T1,B,OTHER,SELL,5\n"
        )

    def test_bad_quantity_side_and_required_fields(self):
        for quantity in ("0", "-1", "1.5", "NaN", "inf", "1e3", ""):
            with self.subTest(quantity=quantity):
                self.reject_trade(f"T1,A,DEMO,BUY,{quantity}\n")

        for row in (
            "T1,A,DEMO,HOLD,10\n",
            "T1,,DEMO,BUY,10\n",
            "T1, A,DEMO,BUY,10\n",
        ):
            with self.subTest(row=row):
                self.reject_trade(row)

    def test_bad_csv_schema(self):
        cases = (
            "account,symbol\nA,DEMO\n",
            "account,symbol,quantity,quantity\nA,DEMO,1,2\n",
            POSITION_HEADER + "A,DEMO\n",
            POSITION_HEADER + "A,DEMO,1,EXTRA\n",
            "",
        )
        for content in cases:
            with self.subTest(content=content):
                path = self.write("opening.csv", content)
                with self.assertRaises(ValueError):
                    validate_file(path, "opening")

    def test_duplicate_positions_and_empty_bundle(self):
        for kind in ("opening", "reference"):
            with self.subTest(kind=kind):
                path = self.write(
                    f"{kind}.csv",
                    POSITION_HEADER + "A,DEMO,1\nA,DEMO,2\n",
                )
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    validate_file(path, kind)

        self.write("trades.csv", TRADE_HEADER)
        self.write("opening.csv", POSITION_HEADER)
        self.write("reference.csv", POSITION_HEADER)
        with self.assertRaisesRegex(ValueError, "all input files"):
            validate_bundle(self.root)


if __name__ == "__main__":
    unittest.main()
