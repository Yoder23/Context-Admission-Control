from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


def _rows(path: Path) -> int:
    with path.open(encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def test_human_rewrite_smoke(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "rewrite"
    subprocess.run([
        sys.executable, "-m", "benchmarks.decision_risk_human_rewrite.run",
        "--n", "1", "--budgets", "40", "--distractors", "5", "--metadata-noise", "0.18", "--output-dir", str(out)
    ], cwd=root, check=True)
    assert _rows(out / "results.csv") == 32
    assert (out / "SEMI_SYNTHETIC_NOTE.md").exists()


def test_stress_smoke(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "stress"
    subprocess.run([
        sys.executable, "-m", "benchmarks.decision_risk_stress.run",
        "--n", "1", "--budgets", "40", "--distractors", "50", "--metadata-noise", "0.30", "--output-dir", str(out)
    ], cwd=root, check=True)
    assert _rows(out / "results.csv") == 32
    assert (out / "STRESS_SUITE_NOTE.md").exists()
