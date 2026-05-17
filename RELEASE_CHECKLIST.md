# Release Checklist

Run these gates before publishing a public release.

## Required

```bash
pytest -q
PYTHONPATH=. python tests/run_smoke_tests.py
PYTHONPATH=. python examples/acme_demo.py
```

## Benchmark Smoke Runs

```bash
PYTHONPATH=. python -m benchmarks.decision_risk.run \
  --n 1 \
  --budgets 40 \
  --distractors 5 \
  --output-dir outputs/release_verify_decision

PYTHONPATH=. python -m benchmarks.decision_risk_human_rewrite.run \
  --n 1 \
  --budgets 40 \
  --distractors 5 \
  --metadata-noise 0.18 \
  --output-dir outputs/release_verify_rewrite

PYTHONPATH=. python -m benchmarks.decision_risk_stress.run \
  --n 1 \
  --budgets 40 \
  --distractors 50 \
  --metadata-noise 0.30 \
  --output-dir outputs/release_verify_stress
```

## Claim Hygiene

- README says the benchmark is synthetic.
- README says generated-answer scoring is deterministic and label-aided.
- README does not claim production proof or real LLM preference wins.
- CAC core and non-oracle baselines do not read gold scorer labels.
- Large archive zips are published as release assets, not committed to git.
