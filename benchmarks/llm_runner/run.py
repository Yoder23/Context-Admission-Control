from __future__ import annotations

"""Real-model LLM evaluation pipeline for CAC vs RAG baselines.

Wires together:
  1. Prompt export  (same logic as export_llm_eval_prompts.py)
  2. Local LLM call (caller.py)
  3. Answer scoring (decision_risk/llm_eval.py)
  4. Markdown report

Usage
-----
Full pipeline (export + call + score):

    python -m benchmarks.llm_runner.run \\
        --n 5 \\
        --budget 160 \\
        --distractors 25 \\
        --model microsoft/phi-3-mini-4k-instruct \\
        --output-dir outputs/llm_eval_real

Resume from existing prompts (skip re-generation):

    python -m benchmarks.llm_runner.run \\
        --prompts outputs/llm_eval_real/prompts.jsonl \\
        --model microsoft/phi-3-mini-4k-instruct \\
        --output-dir outputs/llm_eval_real

Smoke test with GPT-2 (not for publication):

    python -m benchmarks.llm_runner.run \\
        --n 1 --budget 80 --distractors 5 \\
        --model gpt2 \\
        --max-new-tokens 64 \\
        --output-dir outputs/llm_eval_gpt2_smoke
"""

import argparse
import csv
import json
import textwrap
from collections import defaultdict
from pathlib import Path

from benchmarks.decision_risk.export_llm_eval_prompts import (
    make_prompt,
    packet_context,
)
from benchmarks.decision_risk.generate import generate_decision_dossiers
from benchmarks.decision_risk.llm_eval import score_answer, summarize, write_csv
from benchmarks.decision_risk.profiles import TASKS, build_task_profile
from benchmarks.llm_runner.caller import load_caller
from benchmarks.llm_runner.judge import judge_answers, _summarize as judge_summarize, _write_csv as judge_write_csv, _write_report as judge_write_report
from cac.baselines.naive_rag import (
    fixed_context_rag,
    iterative_rag,
    oracle_candidate_rag,
    schema_aware_chunk_rag,
)
from cac.core.builder import build_packet_from_candidates
from cac.core.retrieval import candidate_pool


_METHODS = {
    "cac": lambda profile, cands: build_packet_from_candidates(profile, cands, method="cac"),
    "fixed_context_rag_k8": lambda profile, cands: fixed_context_rag(profile, cands, 8, "fixed_context_rag_k8"),
    "schema_aware_chunk_rag_k8": lambda profile, cands: schema_aware_chunk_rag(profile, cands, 8),
    "oracle_candidate_rag_k8": lambda profile, cands: oracle_candidate_rag(profile, cands, 8),
    "iterative_rag_k8": lambda profile, cands: iterative_rag(profile, cands, 8),
}


# ---------------------------------------------------------------------------
# Prompt export
# ---------------------------------------------------------------------------

def export_prompts(
    n: int,
    budget: int,
    distractors: int,
    seed: int,
    output: Path,
    metadata_noise: float = 0.1,
) -> None:
    """Generate decision dossiers and write prompts JSONL."""
    dossiers = generate_decision_dossiers(n, distractors, seed, list(TASKS), metadata_noise=metadata_noise)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for dossier in dossiers:
            task_type = next(t for t in TASKS if dossier.account_id.startswith(t[:3]))
            profile = build_task_profile(task_type, dossier.entity, budget)
            candidates = candidate_pool(profile, dossier.sources, max_candidates=32)
            for method, fn in _METHODS.items():
                packet = fn(profile, candidates)
                rec = {
                    "account_id": dossier.account_id,
                    "task_type": task_type,
                    "method": method,
                    "budget": budget,
                    "distractors": distractors,
                    "metadata_noise": metadata_noise,
                    "prompt": make_prompt(task_type, dossier.entity, packet_context(packet)),
                    "gold_present_slots": dossier.present_gold_slots,
                    "gold_missing_slots": dossier.missing_gold_slots,
                    "has_contradiction": dossier.has_contradiction,
                }
                f.write(json.dumps(rec) + "\n")
    print(f"[llm_runner] Exported {output}")


# ---------------------------------------------------------------------------
# LLM call pass
# ---------------------------------------------------------------------------

def call_llm(
    prompts_path: Path,
    answers_path: Path,
    model_name: str,
    device: str,
    max_new_tokens: int,
    trust_remote_code: bool,
) -> None:
    """Read prompts JSONL, call LLM for each, write augmented answers JSONL."""
    with prompts_path.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    call = load_caller(model_name, device=device, max_new_tokens=max_new_tokens, trust_remote_code=trust_remote_code)

    answers_path.parent.mkdir(parents=True, exist_ok=True)
    total = len(records)
    with answers_path.open("w", encoding="utf-8") as f:
        for i, rec in enumerate(records, 1):
            print(f"[llm_runner] {i}/{total}  {rec['method']:35s} {rec['account_id']}", flush=True)
            answer = call(rec["prompt"])
            rec["model_answer"] = answer
            f.write(json.dumps(rec) + "\n")

    print(f"[llm_runner] Answers written -> {answers_path}")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def write_report(
    path: Path,
    summary: list[dict],
    model_name: str,
    n_prompts: int,
) -> None:
    lines = [
        f"# Real-model LLM eval - `{model_name}`",
        "",
        f"Prompts evaluated: **{n_prompts}**",
        "",
        "## Summary",
        "",
        "| Method | n | LLM Score | Safe Rate | Missing Disclosure | Contradiction Handling |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['method']} "
            f"| {row['n']} "
            f"| {row['avg_llm_answer_score']:.4f} "
            f"| {row['llm_answer_safe_rate']:.4f} "
            f"| {row['avg_llm_missing_disclosure']:.4f} "
            f"| {row['avg_llm_contradiction_handling']:.4f} |"
        )

    cac_row = next((r for r in summary if r["method"] == "cac"), None)
    best_rag = next((r for r in summary if r["method"] != "cac"), None)

    lines += ["", "## Interpretation", ""]

    if cac_row and best_rag:
        delta = cac_row["avg_llm_answer_score"] - best_rag["avg_llm_answer_score"]
        if delta > 0:
            lines.append(
                f"CAC scores **{delta:+.4f}** vs the best RAG baseline "
                f"({best_rag['method']}) on LLM answer quality."
            )
        else:
            lines.append(
                f"Best RAG baseline ({best_rag['method']}) scores "
                f"**{-delta:+.4f}** above CAC on LLM answer quality."
            )

    lines += [
        "",
        "### Boundaries",
        "",
        "- LLM answer score is a lexical proxy (slot mentions, citation markers, hedging).",
        "- For authoritative results, replace or supplement with a human or LLM judge.",
        "- The same synthetic candidate pool is used; retriever quality is not tested.",
        "",
        f"Model: `{model_name}`",
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[llm_runner] Report -> {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="CAC vs RAG real-model LLM eval pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              # Full run
              python -m benchmarks.llm_runner.run --n 5 --budget 160 \\
                  --model microsoft/phi-3-mini-4k-instruct \\
                  --output-dir outputs/llm_eval_real

              # Smoke test (GPT-2, incoherent answers - harness test only)
              python -m benchmarks.llm_runner.run --n 1 --budget 80 \\
                  --model gpt2 --max-new-tokens 64 \\
                  --output-dir outputs/llm_eval_smoke
        """),
    )

    # Prompt export options (skip if --prompts is given)
    ap.add_argument("--n", type=int, default=5, help="Number of accounts to generate.")
    ap.add_argument("--budget", type=int, default=160, help="Token budget for context.")
    ap.add_argument("--distractors", type=int, default=25, help="Distractor items per dossier.")
    ap.add_argument("--metadata-noise", type=float, default=0.1, help="Fraction of metadata fields to corrupt (0.0-1.0). Default 0.1.")
    ap.add_argument("--seed", type=int, default=42)

    # Resume options
    ap.add_argument(
        "--prompts",
        type=Path,
        default=None,
        help="Path to existing prompts JSONL to skip re-generation.",
    )
    ap.add_argument(
        "--answers",
        type=Path,
        default=None,
        help="Path to existing answers JSONL to skip LLM call (score-only mode).",
    )

    # LLM options
    ap.add_argument(
        "--model",
        default="microsoft/phi-3-mini-4k-instruct",
        help="HuggingFace model ID. Default: microsoft/phi-3-mini-4k-instruct.",
    )
    ap.add_argument(
        "--max-new-tokens",
        type=int,
        default=300,
        help="Maximum tokens to generate per answer.",
    )
    ap.add_argument(
        "--device",
        default="auto",
        choices=["cpu", "cuda", "auto"],
        help="Device for model inference.",
    )
    ap.add_argument(
        "--trust-remote-code",
        action="store_true",
        help="Pass trust_remote_code=True to HuggingFace loaders (only for models that require it).",
    )

    # Output
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/llm_eval_real"),
    )
    ap.add_argument(
        "--judge",
        action="store_true",
        help="After scoring, run an LLM-as-judge pass on the answers using the same model.",
    )
    ap.add_argument(
        "--judge-max-new-tokens",
        type=int,
        default=80,
        help="Max tokens for judge responses (default 80 -- only needs JSON).",
    )

    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: prompts ---
    if args.prompts:
        prompts_path = args.prompts
        print(f"[llm_runner] Using existing prompts: {prompts_path}")
    else:
        prompts_path = args.output_dir / "prompts.jsonl"
        export_prompts(args.n, args.budget, args.distractors, args.seed, prompts_path, metadata_noise=args.metadata_noise)

    # --- Step 2: LLM call ---
    if args.answers:
        answers_path = args.answers
        print(f"[llm_runner] Using existing answers: {answers_path}")
    else:
        answers_path = args.output_dir / "model_answers.jsonl"
        call_llm(
            prompts_path=prompts_path,
            answers_path=answers_path,
            model_name=args.model,
            device=args.device,
            max_new_tokens=args.max_new_tokens,
            trust_remote_code=args.trust_remote_code,
        )

    # --- Step 3: score ---
    scored_rows = []
    with answers_path.open(encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                scored_rows.append(score_answer(json.loads(line)))

    write_csv(args.output_dir / "llm_answer_eval.csv", scored_rows)

    summary = summarize(scored_rows)
    write_csv(args.output_dir / "llm_answer_summary.csv", summary)

    # --- Step 4: report ---
    with answers_path.open(encoding="utf-8-sig") as f:
        n_prompts = sum(1 for line in f if line.strip())

    write_report(
        path=args.output_dir / "llm_eval_report.md",
        summary=summary,
        model_name=args.model,
        n_prompts=n_prompts,
    )

    print(f"\n[llm_runner] Done. Results in {args.output_dir}/")
    print("\nSummary:")
    for row in summary:
        print(
            f"  {row['method']:35s}  score={row['avg_llm_answer_score']:.4f}"
            f"  safe={row['llm_answer_safe_rate']:.2f}"
        )

    # --- Step 5 (optional): LLM-as-judge pass ---
    if args.judge:
        print("\n[llm_runner] Running LLM-as-judge pass ...")
        call_judge = load_caller(
            args.model,
            device=args.device,
            max_new_tokens=args.judge_max_new_tokens,
            trust_remote_code=args.trust_remote_code,
        )
        judge_rows = judge_answers(answers_path, call_judge)
        judge_summary = judge_summarize(judge_rows)
        judge_write_csv(args.output_dir / "judge_eval.csv", judge_rows)
        judge_write_csv(args.output_dir / "judge_summary.csv",
                        [{k: v for k, v in r.items()} for r in judge_summary])
        judge_write_report(args.output_dir / "judge_report.md",
                           judge_summary, answers_path, args.model)
        print("\n[judge] Summary:")
        for row in judge_summary:
            print(
                f"  {row['method']:35s}  overall={row['avg_overall']:.2f}"
                f"  safe={row['judge_safe_rate']:.0%}"
            )


if __name__ == "__main__":
    main()
