import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "run_workflow.py"


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

        self.write(
            "opening.csv",
            "account,symbol,quantity\nACC001,DEMO,50\n",
        )
        self.write(
            "trades.csv",
            "trade_id,account,symbol,side,quantity\n"
            "T001,ACC001,DEMO,BUY,10\n",
        )
        self.write(
            "reference.csv",
            "account,symbol,quantity\nACC001,DEMO,60\n",
        )

    def write(self, name, content):
        (self.root / name).write_text(content, encoding="utf-8")

    def run_workflow(self):
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT),
                "--trades", str(self.root / "trades.csv"),
                "--opening", str(self.root / "opening.csv"),
                "--reference", str(self.root / "reference.csv"),
                "--output-dir", str(self.root / "outputs"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        manifests = list(
            self.root.glob("outputs/workflow_*/manifest.json")
        )
        self.assertEqual(
            len(manifests), 1, result.stdout + result.stderr
        )
        path = manifests[0]
        return (
            result,
            path.parent,
            json.loads(path.read_text(encoding="utf-8")),
        )

    def test_success_preserves_snapshot_and_hash(self):
        original = (self.root / "trades.csv").read_bytes()
        result, batch, manifest = self.run_workflow()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(manifest["status"], "MATCH")
        self.assertTrue((batch / manifest["report_html"]).exists())
        self.assertTrue((batch / "stdout.log").exists())
        self.assertTrue((batch / "stderr.log").exists())

        record = manifest["inputs"]["trades"]
        snapshot = batch / record["snapshot"]
        self.assertEqual(snapshot.read_bytes(), original)
        self.assertEqual(
            record["sha256"], hashlib.sha256(original).hexdigest()
        )

        # Editing the original after the run must not alter its snapshot.
        self.write("trades.csv", "changed after run\n")
        self.assertEqual(snapshot.read_bytes(), original)

    def test_mismatch_still_generates_html(self):
        self.write(
            "reference.csv",
            "account,symbol,quantity\nACC001,DEMO,61\n",
        )
        result, batch, manifest = self.run_workflow()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(manifest["exit_code"], 1)
        self.assertEqual(manifest["status"], "EXCEPTIONS")
        self.assertTrue((batch / manifest["report_csv"]).exists())
        self.assertTrue((batch / manifest["report_html"]).exists())

    def test_missing_input_leaves_failure_manifest(self):
        (self.root / "trades.csv").unlink()
        result, batch, manifest = self.run_workflow()

        self.assertEqual(result.returncode, 2)
        self.assertEqual(manifest["status"], "FAILED")
        self.assertIn("error", manifest)
        self.assertNotIn("report_html", manifest)
        self.assertEqual(list(batch.rglob("report.html")), [])


if __name__ == "__main__":
    unittest.main()
