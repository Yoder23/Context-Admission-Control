from __future__ import annotations

"""External LLM answer evaluation harness.

This module does not call an LLM. It scores JSONL answers produced from
export_llm_eval_prompts.py. It is the bridge from deterministic proxy evaluation
to same-model LLM answer evaluation.

Expected input JSONL fields:
- account_id
- task_type
- method
- answer
- gold_present_slots
- gold_missing_slots
- has_contradiction

The scorer is intentionally simple and auditable; human/LLM-judge scoring can be
added alongside it without changing prompt export.
"""

import argparse, csv, json, re
from pathlib import Path
from collections import defaultdict


def mentions_slot(answer: str, slot: str) -> bool:
    t = answer.lower()
    variants = {slot.lower(), slot.replace('_', ' ').lower(), slot.replace('_', '-').lower()}
    return any(v in t for v in variants)


def score_answer(rec: dict) -> dict:
    answer = rec.get('answer', '') or rec.get('model_answer', '')
    text = answer.lower()
    present = rec.get('gold_present_slots') or []
    missing = rec.get('gold_missing_slots') or []
    has_contradiction = bool(rec.get('has_contradiction'))

    slot_coverage = sum(1 for s in present if mentions_slot(text, s)) / max(1, len(present))
    if missing:
        missing_disclosure = sum(1 for s in missing if mentions_slot(text, s) or 'missing evidence' in text or 'insufficient evidence' in text) / len(missing)
    else:
        missing_disclosure = 1.0
    contradiction = 1.0 if not has_contradiction else (1.0 if ('contradict' in text or 'conflict' in text or 'tension' in text) else 0.0)
    citation_support = 1.0 if re.search(r'\[[^\]]+\]|source[_ -]?id|source:', answer, flags=re.I) else 0.0
    unsupported_penalty = 1.0 if any(x in text for x in ['probably', 'must be', 'definitely', 'guaranteed']) and citation_support < 1.0 else 0.0
    exact_use = 1.0 if ('"' in answer or 'exact' in text or 'clause' in text or 'wrote:' in text) else 0.75
    score = .28*slot_coverage + .20*exact_use + .18*missing_disclosure + .18*contradiction + .10*citation_support + .06*(1-unsupported_penalty)
    caps=[]
    if missing and missing_disclosure < 1.0:
        score = min(score, .70); caps.append('missing_not_disclosed')
    if has_contradiction and contradiction < 1.0:
        score = min(score, .75); caps.append('contradiction_not_handled')
    if unsupported_penalty:
        score = min(score, .85); caps.append('unsupported_uncited_claim')
    return {
        'account_id': rec.get('account_id'),
        'task_type': rec.get('task_type'),
        'method': rec.get('method'),
        'llm_answer_score': round(score,4),
        'llm_answer_safe': score >= .80,
        'llm_slot_coverage': round(slot_coverage,4),
        'llm_missing_disclosure': round(missing_disclosure,4),
        'llm_contradiction_handling': round(contradiction,4),
        'llm_citation_support': round(citation_support,4),
        'llm_caps': ';'.join(caps) if caps else 'none',
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fields = sorted({k for r in rows for k in r})
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)


def summarize(rows: list[dict]) -> list[dict]:
    by=defaultdict(list)
    for r in rows: by[r['method']].append(r)
    out=[]
    for method, vals in by.items():
        out.append({
            'method': method,
            'n': len(vals),
            'avg_llm_answer_score': round(sum(float(v['llm_answer_score']) for v in vals)/len(vals),4),
            'llm_answer_safe_rate': round(sum(1 for v in vals if v['llm_answer_safe'])/len(vals),4),
            'avg_llm_missing_disclosure': round(sum(float(v['llm_missing_disclosure']) for v in vals)/len(vals),4),
            'avg_llm_contradiction_handling': round(sum(float(v['llm_contradiction_handling']) for v in vals)/len(vals),4),
        })
    return sorted(out, key=lambda r: -r['avg_llm_answer_score'])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--answers', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, default=Path('outputs/llm_answer_eval'))
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows=[]
    with args.answers.open(encoding='utf-8-sig') as f:
        for line in f:
            if line.strip(): rows.append(score_answer(json.loads(line)))
    write_csv(args.output_dir/'llm_answer_eval.csv', rows)
    write_csv(args.output_dir/'llm_answer_summary.csv', summarize(rows))
    print(f'wrote {args.output_dir}')


if __name__ == '__main__':
    main()
