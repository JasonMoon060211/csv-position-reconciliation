import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from report_html import write_html

BASE = Path(__file__).resolve().parent


def now():
    return datetime.now(timezone.utc).isoformat()


def execute(args):
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    batch = Path(tempfile.mkdtemp(prefix="workflow_", dir=root))
    print(f"Run folder: {batch}", flush=True)

    manifest = {
        "started_at": now(),
        "python": sys.version,
        "status": "FAILED",
        "exit_code": 2,
        "inputs": {},
    }
    code = 2
    html = None

    try:
        inputs = batch / "inputs"
        inputs.mkdir()
        command = [sys.executable, str(BASE / "reconcile_cli.py")]

        for name in ("trades", "opening", "reference"):
            source = getattr(args, name).resolve()
            snapshot = inputs / f"{name}.csv"

            # Read once: the fingerprint and snapshot use identical bytes.
            data = source.read_bytes()
            snapshot.write_bytes(data)
            manifest["inputs"][name] = {
                "source": str(source),
                "snapshot": str(snapshot.relative_to(batch)),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            command.extend([f"--{name}", str(snapshot)])

        # INPUT_VALIDATION_V1
        from validate_inputs import validate_bundle
        manifest["input_rows"] = validate_bundle(inputs)
        manifest["validation"] = "PASSED"

        command.extend(["--output-dir", str(batch / "results")])
        result = subprocess.run(
            command,
            cwd=BASE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        (batch / "stdout.log").write_text(
            result.stdout, encoding="utf-8"
        )
        (batch / "stderr.log").write_text(
            result.stderr, encoding="utf-8"
        )
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        manifest["cli_exit_code"] = result.returncode

        if result.returncode not in (0, 1):
            raise ValueError("Reconciliation failed; see stderr.log.")

        reports = list((batch / "results").glob("run_*/report.csv"))
        if len(reports) != 1:
            raise ValueError("Expected exactly one report for this run.")

        html = write_html(reports[0])
        code = result.returncode
        manifest.update({
            "status": "MATCH" if code == 0 else "EXCEPTIONS",
            "exit_code": code,
            "report_csv": str(reports[0].relative_to(batch)),
            "report_html": str(html.relative_to(batch)),
        })

    except Exception as error:
        # Boundary handler: retain the failure reason for this batch.
        manifest["error"] = f"{type(error).__name__}: {error}"
        print(f"Workflow failed: {error}", file=sys.stderr)

    finally:
        manifest["finished_at"] = now()
        staging = batch / "manifest.json.tmp"
        staging.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        staging.replace(batch / "manifest.json")

    print(f"Manifest: {batch / 'manifest.json'}", flush=True)

    if html is not None and code in (0, 1):
        print(f"HTML report: {html}", flush=True)
        if args.open:
            try:
                if not webbrowser.open(html.resolve().as_uri()):
                    print("Open the HTML file manually.")
            except Exception as error:
                print(f"Browser unavailable: {error}", file=sys.stderr)

    return code


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Reconciliation with input snapshots and run manifest."
    )
    parser.add_argument("--open", action="store_true")
    parser.add_argument(
        "--trades", type=Path, default=BASE / "trades.csv"
    )
    parser.add_argument(
        "--opening", type=Path, default=BASE / "opening_positions.csv"
    )
    parser.add_argument(
        "--reference", type=Path, default=BASE / "positions.csv"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=BASE / "outputs"
    )
    args = parser.parse_args(argv)

    try:
        return execute(args)
    except OSError as error:
        print(f"Cannot create/save run files: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
