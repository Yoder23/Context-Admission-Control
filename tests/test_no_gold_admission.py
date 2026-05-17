from __future__ import annotations

from pathlib import Path

BANNED = ("gold_slots", "gold_negative", "gold_positive", "gold_exact_required", "is_distractor")


def _strip_oracle_function(text: str) -> str:
    marker = "def oracle_candidate_rag"
    idx = text.find(marker)
    if idx == -1:
        return text
    # Keep code before oracle and code after the next top-level function following oracle.
    before = text[:idx]
    rest = text[idx:]
    next_def = rest.find("\ndef long_context_rag")
    if next_def == -1:
        return before
    return before + rest[next_def:]


def test_cac_core_does_not_read_scorer_gold_labels() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in (root / "cac" / "core").glob("*.py"):
        if path.name == "schemas.py":
            continue
        text = path.read_text()
        for token in BANNED:
            assert token not in text, f"{path} contains scorer-only label {token}"


def test_non_oracle_rag_baselines_do_not_read_scorer_gold_labels() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "cac" / "baselines" / "naive_rag.py"
    text = _strip_oracle_function(path.read_text())
    for token in BANNED:
        assert token not in text, f"non-oracle baseline path contains scorer-only label {token}"
