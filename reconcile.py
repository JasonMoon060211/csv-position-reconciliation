import csv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def read_csv(filename, required_columns):
    """Read a CSV file and check its column names."""
    with open(
        PROJECT_DIR / filename,
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        missing = set(required_columns) - columns

        if missing:
            raise ValueError(
                f"{filename}: missing columns {sorted(missing)}"
            )

        rows = []
        for line_number, row in enumerate(reader, start=2):
            for column in required_columns:
                value = row.get(column)
                if value is None or not value.strip():
                    raise ValueError(
                        f"{filename}, line {line_number}: "
                        f"empty field {column}"
                    )
                row[column] = value.strip()
            rows.append(row)

        return rows


def calculate_positions(trades):
    """Calculate positions and reject duplicate trade IDs."""
    positions = {}
    seen_ids = set()

    for trade in trades:
        trade_id = trade["trade_id"]

        if trade_id in seen_ids:
            raise ValueError(f"Duplicate trade ID: {trade_id}")
        seen_ids.add(trade_id)

        quantity = int(trade["quantity"])
        if quantity <= 0:
            raise ValueError(
                f"{trade_id}: quantity must be positive"
            )

        side = trade["side"]
        if side not in ("BUY", "SELL"):
            raise ValueError(
                f"{trade_id}: invalid trade side {side}"
            )

        key = (trade["account"], trade["symbol"])
        change = quantity if side == "BUY" else -quantity
        positions[key] = positions.get(key, 0) + change

    return positions


def load_reference_positions(rows):
    """Read one reference quantity per account and symbol."""
    positions = {}

    for row in rows:
        key = (row["account"], row["symbol"])

        if key in positions:
            raise ValueError(
                f"Duplicate reference position: {key}"
            )

        positions[key] = int(row["quantity"])

    return positions


def reconcile(calculated, reference):
    """Compare all account-symbol pairs in either dataset."""
    results = []

    for account, symbol in sorted(calculated.keys() | reference.keys()):
        key = (account, symbol)
        actual = calculated.get(key)
        expected = reference.get(key)
        difference = None

        if actual is None:
            status = "REFERENCE_ONLY"
        elif expected is None:
            status = "MISSING_REFERENCE"
        else:
            difference = actual - expected
            status = "MATCH" if difference == 0 else "MISMATCH"

        results.append({
            "account": account,
            "symbol": symbol,
            "calculated_position": actual,
            "reference_position": expected,
            "difference": difference,
            "status": status,
        })

    return results


def main():
    trades = read_csv(
        "trades.csv",
        ["trade_id", "account", "symbol", "side", "quantity"],
    )
    reference_rows = read_csv(
        "positions.csv",
        ["account", "symbol", "quantity"],
    )

    calculated = calculate_positions(trades)
    reference = load_reference_positions(reference_rows)
    results = reconcile(calculated, reference)

    output_file = PROJECT_DIR / "report.csv"
    columns = [
        "account",
        "symbol",
        "calculated_position",
        "reference_position",
        "difference",
        "status",
    ]

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    print("=== Trade Reconciliation Report ===")
    print(f"Trades processed: {len(trades)}")

    for row in results:
        print(
            f"{row['account']} / {row['symbol']} | "
            f"Calculated: {row['calculated_position']} | "
            f"Reference: {row['reference_position']} | "
            f"Difference: {row['difference']} | "
            f"{row['status']}"
        )

    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    main()
