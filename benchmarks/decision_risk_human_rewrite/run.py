from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.decision_risk.generate import generate_decision_dossiers
from benchmarks.decision_risk.run import run_suite
from benchmarks.decision_risk_human_rewrite.rewrite import rewrite_dossiers

# This runner reuses the main DecisionRiskBench suite but evaluates rewritten dossiers
# by monkey-patching the generation function at module boundary. It writes a clear
# README note that this is semi-synthetic surface variation, not human-audited data.


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=10)
    p.add_argument('--budgets', default='40,60,80,120,160,240,500')
    p.add_argument('--distractors', default='25,50')
    p.add_argument('--task-types', default='renewal_risk,security_exception,contract_termination,incident_postmortem')
    p.add_argument('--metadata-noise', type=float, default=.18)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--target-score', type=float, default=.90)
    p.add_argument('--output-dir', default='outputs/decision_risk_v1_4_rewrite')
    a = p.parse_args()

    # Implement a small local copy of run_suite's first generation step by wrapping
    # generate_decision_dossiers. To avoid invasive changes, replace the function in
    # benchmarks.decision_risk.run at runtime.
    import benchmarks.decision_risk.run as base_run
    original = base_run.generate_decision_dossiers

    def rewritten_generator(n, distractors, seed, task_types, metadata_noise=.1):
        base = generate_decision_dossiers(n, distractors, seed, task_types, metadata_noise=metadata_noise)
        return rewrite_dossiers(base, seed=seed + distractors * 17 + n)

    base_run.generate_decision_dossiers = rewritten_generator
    try:
        run_suite(
            n=a.n,
            budgets=[int(x) for x in a.budgets.split(',') if x],
            distractors=[int(x) for x in a.distractors.split(',') if x],
            task_types=[x for x in a.task_types.split(',') if x],
            metadata_noise=a.metadata_noise,
            output_dir=Path(a.output_dir),
            seed=a.seed,
            target=a.target_score,
        )
        Path(a.output_dir, 'SEMI_SYNTHETIC_NOTE.md').write_text(
            '# Semi-synthetic rewrite note\n\n'
            'This suite uses the synthetic DecisionRiskBench generator, then rewrites source surface text and perturbs observable metadata. '
            'Gold labels remain benchmark-only scoring labels. This is not human-audited data, but it reduces template phrase matching.\n',
            encoding='utf-8',
        )
    finally:
        base_run.generate_decision_dossiers = original


if __name__ == '__main__':
    main()
