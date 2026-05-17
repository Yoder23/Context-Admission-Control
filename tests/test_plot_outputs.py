from __future__ import annotations

from pathlib import Path


def test_packaged_v14_plots_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "outputs" / "decision_risk_v1_4_n20"
    for name in [
        "decision_grade_vs_budget.svg",
        "generated_answer_score_vs_budget.svg",
        "generated_answer_per_1k_vs_budget.svg",
        "distractor_rate_vs_budget.svg",
    ]:
        p = out / name
        assert p.exists(), f"missing plot {name}"
        assert p.stat().st_size > 100, f"plot {name} looks empty"
