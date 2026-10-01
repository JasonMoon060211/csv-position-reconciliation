import csv
import re
from pathlib import Path

SCHEMAS = {
    "trades": ("trade_id", "account", "symbol", "side", "quantity"),
    "opening": ("account", "symbol", "quantity"),
    "reference": ("account", "symbol", "quantity"),
}


def validate_file(path, kind):
    path = Path(path)
    required = SCHEMAS[kind]
    seen = set()
    count = 0

    def fail(line, message):
        raise ValueError(
            f"Input validation: {path.name}, line {line}: {message}"
        )

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file, strict=True)
        try:
            headers = reader.fieldnames
            if not headers:
                fail(1, "missing header")
            if any(not h or h != h.strip() for h in headers):
                fail(1, "empty header or surrounding whitespace")
            if len(headers) != len(set(headers)):
                fail(1, "duplicate headers")

            missing = set(required) - set(headers)
            if missing:
                fail(1, "missing columns: " + ", ".join(sorted(missing)))

            for row in reader:
                line = reader.line_num
                if None in row or any(v is None for v in row.values()):
                    fail(line, "field count does not match header")

                for key in required:
                    value = row[key]
                    if not value or not value.strip():
                        fail(line, f"{key} is empty")
                    if value != value.strip():
                        fail(line, f"{key} has surrounding whitespace")

                quantity = row["quantity"]
                if not re.fullmatch(r"[+-]?[0-9]+", quantity):
                    fail(line, "quantity must be an integer")

                try:
                    number = int(quantity)
                except ValueError:
                    fail(line, "quantity cannot be parsed")

                if kind == "trades":
                    if row["side"] not in {"BUY", "SELL"}:
                        fail(line, "side must be BUY or SELL")
                    if number <= 0:
                        fail(line, "trade quantity must be positive")
                    key = row["trade_id"]
                    label = "trade_id"
                else:
                    key = (row["account"], row["symbol"])
                    label = "account/symbol"

                if key in seen:
                    fail(line, f"duplicate {label}: {key}")
                seen.add(key)
                count += 1

        except csv.Error as error:
            fail(reader.line_num, f"invalid CSV: {error}")

    return count


def validate_bundle(folder):
    folder = Path(folder)
    counts = {
        kind: validate_file(folder / f"{kind}.csv", kind)
        for kind in SCHEMAS
    }
    if not any(counts.values()):
        raise ValueError("Input validation: all input files are empty")
    return counts
