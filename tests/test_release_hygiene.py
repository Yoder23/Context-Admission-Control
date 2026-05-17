from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_release_files_and_version_are_consistent() -> None:
    required = [
        "LICENSE",
        ".gitignore",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CITATION.cff",
        "CHANGELOG.md",
        "RELEASE_CHECKLIST.md",
        "README.md",
        "pyproject.toml",
        "VERSION",
    ]
    for name in required:
        assert (ROOT / name).exists(), f"missing release file: {name}"

    version = _read("VERSION").strip()
    pyproject = _read("pyproject.toml")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, flags=re.M)
    assert match, "pyproject.toml has no project version"
    assert match.group(1) == version


def test_readme_keeps_claim_boundaries_explicit() -> None:
    readme = _read("README.md").lower()
    assert "synthetic benchmark" in readme
    assert "not supported" in readme
    assert "real llm answers" in readme
    assert "not an llm answer study" in readme
    assert "production proof" in readme


def test_public_source_files_are_ascii() -> None:
    paths = [
        *ROOT.glob("*.md"),
        *ROOT.glob("*.toml"),
        *ROOT.glob("*.cff"),
        *ROOT.glob("cac/**/*.py"),
        *ROOT.glob("benchmarks/**/*.py"),
        *ROOT.glob("tests/**/*.py"),
        *ROOT.glob("examples/**/*.py"),
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        bad = [ch for ch in text if ord(ch) > 127]
        assert not bad, f"{path.relative_to(ROOT)} contains non-ASCII text"


def test_legacy_renewal_benchmark_smoke(tmp_path: Path) -> None:
    out = tmp_path / "renewal"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks.renewal_risk.run",
            "--n",
            "1",
            "--budgets",
            "40",
            "--distractors",
            "5",
            "--metadata-modes",
            "clean_metadata",
            "--slot-modes",
            "perfect_slots",
            "--output-dir",
            str(out),
        ],
        cwd=ROOT,
        check=True,
    )
    with (out / "results.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 7
    assert (out / "benchmark_report.md").exists()
