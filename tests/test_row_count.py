from __future__ import annotations

import csv
from pathlib import Path


def test_packaged_v14_n20_row_count() -> None:
    root = Path(__file__).resolve().parents[1]
    results = root / "outputs" / "decision_risk_v1_4_n20" / "results.csv"
    assert results.exists(), "packaged n=20 results.csv is missing"
    with results.open(encoding="utf-8") as f:
        rows = sum(1 for _ in f) - 1
    assert rows == 13440


def test_packaged_v14_has_all_methods_and_tasks() -> None:
    root = Path(__file__).resolve().parents[1]
    results = root / "outputs" / "decision_risk_v1_4_n20" / "results.csv"
    with results.open(encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    methods = {r["method"] for r in records}
    tasks = {r["task_type"] for r in records}
    assert methods == {
        "cac",
        "fixed_context_rag_k8",
        "metadata_aware_rag_k8",
        "schema_aware_chunk_rag_k8",
        "oracle_candidate_rag_k8",
        "long_context_rag_k24",
        "iterative_rag_k8",
        "heuristic_rerank_rag_k8",
    }
    assert tasks == {"renewal_risk", "security_exception", "contract_termination", "incident_postmortem"}
