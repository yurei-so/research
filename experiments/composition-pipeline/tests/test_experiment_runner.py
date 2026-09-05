import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run-experiment"


class ExperimentRunnerTest(unittest.TestCase):
    def test_contract_smoke_emits_bounded_result(self) -> None:
        result = subprocess.run(
            [RUNNER, "contract_smoke"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), {
            "format": "composition-pipeline.experiment-result",
            "version": 1,
            "experiment": "contract_smoke",
            "status": "ok",
        })

    def test_runner_rejects_path_traversal(self) -> None:
        result = subprocess.run(
            [RUNNER, "../contract_smoke"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("invalid experiment identifier", result.stderr)


if __name__ == "__main__":
    unittest.main()
