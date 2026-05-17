from __future__ import annotations

import argparse
from pathlib import Path
from benchmarks.decision_risk.run import run_suite


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=10)
    p.add_argument('--budgets', default='40,60,80,120,160')
    p.add_argument('--distractors', default='50,100')
    p.add_argument('--metadata-noise', type=float, default=.30)
    p.add_argument('--seed', type=int, default=404)
    p.add_argument('--target-score', type=float, default=.90)
    p.add_argument('--output-dir', default='outputs/decision_risk_v1_4_stress')
    a = p.parse_args()
    out = Path(a.output_dir)
    run_suite(
        n=a.n,
        budgets=[int(x) for x in a.budgets.split(',') if x],
        distractors=[int(x) for x in a.distractors.split(',') if x],
        task_types=['renewal_risk','security_exception','contract_termination','incident_postmortem'],
        metadata_noise=a.metadata_noise,
        output_dir=out,
        seed=a.seed,
        target=a.target_score,
    )
    (out/'STRESS_SUITE_NOTE.md').write_text(
        '# Failure-mode stress suite\n\n'
        'Targets known CAC failure modes: contradiction misses, slot underfill, exact-representation failure, and distractor pressure. '
        'This is still synthetic but uses high distractor counts and harsher metadata noise.\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    main()
