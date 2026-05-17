from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_llm_prompt_export_and_answer_eval(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    prompts = tmp_path / "prompts.jsonl"
    subprocess.run([
        sys.executable, "-m", "benchmarks.decision_risk.export_llm_eval_prompts",
        "--n", "1", "--budget", "120", "--distractors", "5", "--output", str(prompts)
    ], cwd=root, check=True)
    records = [json.loads(line) for line in prompts.read_text().splitlines() if line.strip()]
    assert records
    answers = tmp_path / "answers.jsonl"
    with answers.open("w", encoding="utf-8-sig") as f:
        for rec in records:
            f.write(json.dumps({**rec, "answer": "Decision: escalate. Source: [demo]. Missing evidence: none. Conflict noted."}) + "\n")
    out = tmp_path / "eval"
    subprocess.run([
        sys.executable, "-m", "benchmarks.decision_risk.llm_eval",
        "--answers", str(answers), "--output-dir", str(out)
    ], cwd=root, check=True)
    assert (out / "llm_answer_eval.csv").exists()
    assert (out / "llm_answer_summary.csv").exists()
