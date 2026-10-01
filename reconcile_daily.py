import csv

from reconcile import (
    PROJECT_DIR,
    read_csv,
    calculate_positions,
    load_reference_positions,
    reconcile,
)


def calculate_closing_positions(trades, opening_rows):
    """Add period trade changes to opening positions."""
    closing = load_reference_positions(opening_rows)
    changes = calculate_positions(trades)

    for key, change in changes.items():
        closing[key] = closing.get(key, 0) + change

    return closing


def main():
    trades = read_csv(
        "trades.csv",
        ["trade_id", "account", "symbol", "side", "quantity"],
    )
    opening_rows = read_csv(
        "opening_positions.csv",
        ["account", "symbol", "quantity"],
    )
    reference_rows = read_csv(
        "positions.csv",
        ["account", "symbol", "quantity"],
    )

    closing = calculate_closing_positions(trades, opening_rows)
    reference = load_reference_positions(reference_rows)
    results = reconcile(closing, reference)

    columns = [
        "account",
        "symbol",
        "calculated_position",
        "reference_position",
        "difference",
        "status",
    ]
    output_file = PROJECT_DIR / "daily_report.csv"

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    print("=== Daily Position Reconciliation ===")
    print(f"Trades processed: {len(trades)}")

    for row in results:
        print(
            f"{row['account']} / {row['symbol']} | "
            f"Calculated: {row['calculated_position']} | "
            f"Reference: {row['reference_position']} | "
            f"Difference: {row['difference']} | "
            f"{row['status']}"
        )

    exceptions = sum(row["status"] != "MATCH" for row in results)
    print(f"Positions checked: {len(results)}")
    print(f"Exceptions: {exceptions}")
    print(f"Report saved to: {output_file}")


if __name__ == "__main__":
    main()
