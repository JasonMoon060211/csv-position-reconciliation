import unittest

from reconcile_daily import calculate_closing_positions


class TestOpeningPositions(unittest.TestCase):

    def test_opening_plus_trades(self):
        opening = [
            {"account": "ACC001", "symbol": "DEMO", "quantity": "50"},
        ]
        trades = [
            {
                "trade_id": "T001",
                "account": "ACC001",
                "symbol": "DEMO",
                "side": "BUY",
                "quantity": "100",
            },
            {
                "trade_id": "T002",
                "account": "ACC001",
                "symbol": "DEMO",
                "side": "SELL",
                "quantity": "30",
            },
        ]

        result = calculate_closing_positions(trades, opening)

        self.assertEqual(result, {("ACC001", "DEMO"): 120})

    def test_position_without_trades_is_preserved(self):
        opening = [
            {"account": "ACC003", "symbol": "OTHER", "quantity": "12"},
        ]

        result = calculate_closing_positions([], opening)

        self.assertEqual(result, {("ACC003", "OTHER"): 12})

    def test_new_position_starts_from_zero(self):
        trades = [
            {
                "trade_id": "T001",
                "account": "ACC001",
                "symbol": "DEMO",
                "side": "BUY",
                "quantity": "10",
            },
        ]

        result = calculate_closing_positions(trades, [])

        self.assertEqual(result, {("ACC001", "DEMO"): 10})

    def test_duplicate_opening_position_is_rejected(self):
        row = {
            "account": "ACC001",
            "symbol": "DEMO",
            "quantity": "50",
        }

        with self.assertRaisesRegex(
            ValueError, "Duplicate reference position"
        ):
            calculate_closing_positions([], [row, row])


if __name__ == "__main__":
    unittest.main()
