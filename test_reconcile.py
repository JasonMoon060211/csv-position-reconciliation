import unittest

from reconcile import (
    calculate_positions,
    load_reference_positions,
    reconcile,
)


def make_trade(
    trade_id="T001",
    account="ACC001",
    symbol="DEMO",
    side="BUY",
    quantity="100",
):
    """Create synthetic trade data for tests."""
    return {
        "trade_id": trade_id,
        "account": account,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
    }


class TestReconciliation(unittest.TestCase):

    def test_buy_and_sell(self):
        trades = [
            make_trade("T001", quantity="100"),
            make_trade("T002", side="SELL", quantity="30"),
            make_trade("T003", quantity="20"),
        ]

        result = calculate_positions(trades)

        self.assertEqual(result, {("ACC001", "DEMO"): 90})

    def test_multiple_accounts_and_symbols(self):
        trades = [
            make_trade("T001", quantity="100"),
            make_trade("T002", account="ACC002", quantity="10"),
            make_trade("T003", symbol="TEST", quantity="5"),
        ]

        result = calculate_positions(trades)

        self.assertEqual(result, {
            ("ACC001", "DEMO"): 100,
            ("ACC002", "DEMO"): 10,
            ("ACC001", "TEST"): 5,
        })

    def test_duplicate_trade_id(self):
        trades = [
            make_trade("T001"),
            make_trade("T001"),
        ]

        with self.assertRaisesRegex(
            ValueError, "Duplicate trade ID"
        ):
            calculate_positions(trades)

    def test_invalid_trade_inputs(self):
        cases = [
            ("invalid side", {"side": "HOLD"}),
            ("zero quantity", {"quantity": "0"}),
            ("negative quantity", {"quantity": "-10"}),
            ("non-numeric quantity", {"quantity": "abc"}),
        ]

        for name, changes in cases:
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    calculate_positions([make_trade(**changes)])

    def test_duplicate_reference_position(self):
        rows = [
            {"account": "ACC001", "symbol": "DEMO", "quantity": "90"},
            {"account": "ACC001", "symbol": "DEMO", "quantity": "95"},
        ]

        with self.assertRaisesRegex(
            ValueError, "Duplicate reference position"
        ):
            load_reference_positions(rows)

    def test_match_and_mismatch(self):
        calculated = {
            ("ACC001", "DEMO"): 90,
            ("ACC002", "TEST"): 7,
        }
        reference = {
            ("ACC001", "DEMO"): 90,
            ("ACC002", "TEST"): 8,
        }

        rows = reconcile(calculated, reference)
        by_key = {
            (row["account"], row["symbol"]): row
            for row in rows
        }

        self.assertEqual(len(rows), 2)
        self.assertEqual(by_key[("ACC001", "DEMO")]["status"], "MATCH")
        self.assertEqual(by_key[("ACC001", "DEMO")]["difference"], 0)
        self.assertEqual(by_key[("ACC002", "TEST")]["status"], "MISMATCH")
        self.assertEqual(by_key[("ACC002", "TEST")]["difference"], -1)

    def test_missing_reference(self):
        rows = reconcile({("ACC001", "DEMO"): 90}, {})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "MISSING_REFERENCE")
        self.assertIsNone(rows[0]["reference_position"])
        self.assertIsNone(rows[0]["difference"])

    def test_reference_only(self):
        rows = reconcile({}, {("ACC001", "DEMO"): 90})

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "REFERENCE_ONLY")
        self.assertIsNone(rows[0]["calculated_position"])
        self.assertIsNone(rows[0]["difference"])


if __name__ == "__main__":
    unittest.main()
