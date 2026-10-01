import argparse
import csv
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from reconcile import read_csv, load_reference_positions, reconcile
from reconcile_daily import calculate_closing_positions
from validate_inputs import validate_file

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Position reconciliation")
    parser.add_argument("--trades", type=Path, default=BASE / "trades.csv")
    parser.add_argument(
        "--opening", type=Path, default=BASE / "opening_positions.csv"
    )
    parser.add_argument(
        "--reference", type=Path, default=BASE / "positions.csv"
    )
    parser.add_argument("--output-dir", type=Path, default=BASE / "outputs")
    args = parser.parse_args()

    logger = logging.getLogger("reconciliation")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handlers = []

    try:
        output = args.output_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        prefix = datetime.now().strftime("run_%Y%m%d_%H%M%S_")
        run_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=output))
        print(f"Run folder: {run_dir}", flush=True)

        handlers.append(logging.FileHandler(
            run_dir / "run.log", encoding="utf-8"
        ))
        handlers.append(logging.StreamHandler())

        for handler in handlers:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"
            ))
            logger.addHandler(handler)

        logger.info("Started")
        for name in ("trades", "opening", "reference"):
            logger.info("%s: %s", name, getattr(args, name).resolve())

        for name in ("trades", "opening", "reference"):
            validate_file(getattr(args, name).resolve(), name)

        trades = read_csv(
            args.trades.resolve(),
            ["trade_id", "account", "symbol", "side", "quantity"],
        )
        opening = read_csv(
            args.opening.resolve(), ["account", "symbol", "quantity"]
        )
        reference = read_csv(
            args.reference.resolve(), ["account", "symbol", "quantity"]
        )

        closing = calculate_closing_positions(trades, opening)
        results = reconcile(closing, load_reference_positions(reference))

        # Reject completely empty inputs rather than reporting success.
        if not results:
            raise ValueError("No positions to reconcile.")

        columns = [
            "account", "symbol", "calculated_position",
            "reference_position", "difference", "status",
        ]

        # Only publish report.csv after writing completes.
        staging = run_dir / "report.csv.tmp"
        report = run_dir / "report.csv"
        with staging.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(results)
        staging.replace(report)

        exceptions = sum(row["status"] != "MATCH" for row in results)
        exit_code = 1 if exceptions else 0

        logger.info(
            "Completed: trades=%s positions=%s exceptions=%s exit_code=%s",
            len(trades), len(results), exceptions, exit_code,
        )
        print(f"Report: {report}")
        print(f"Positions: {len(results)} | Exceptions: {exceptions}")
        print(f"Exit code: {exit_code}")
        return exit_code

    except (OSError, ValueError, csv.Error) as error:
        if logger.handlers:
            logger.error("Failed: %s", error)
        else:
            print(f"Failed: {error}", file=sys.stderr)
        return 2

    finally:
        for handler in handlers:
            logger.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    sys.exit(main())
