# Contributing

Thanks for improving Context Admission Control and DecisionRiskBench.

## Development Setup

Use Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest -q
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH='.'
C:\Python310\python.exe -m pytest -q
```

## Contribution Rules

- Keep benchmark claims tied to reproducible commands and packaged outputs.
- Do not let CAC core or non-oracle baselines read scorer-only gold labels.
- Keep synthetic/proxy limitations explicit in docs and reports.
- Add focused tests for benchmark, scoring, packaging, or documentation changes.
- Avoid committing generated caches, local verification outputs, or large zip
  archives.

## Pull Request Checklist

- `pytest -q` passes without requiring `PYTHONUTF8=1`.
- `PYTHONPATH=. python tests/run_smoke_tests.py` passes.
- `PYTHONPATH=. python examples/acme_demo.py` passes.
- New benchmark outputs include row counts and enough command context to
  reproduce them.
