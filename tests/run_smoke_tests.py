from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tiny_v1_4_verify"
if OUT.exists():
    shutil.rmtree(OUT)
cmd = [
    sys.executable,
    "-m",
    "benchmarks.decision_risk.run",
    "--n",
    "1",
    "--budgets",
    "40",
    "--distractors",
    "5",
    "--output-dir",
    str(OUT),
]
subprocess.run(cmd, cwd=ROOT, check=True)
with (OUT / "results.csv").open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 32, len(rows)  # 1 account x 4 tasks x 1 budget x 1 distractor x 8 methods
print("decision-risk smoke tests ok")
