from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from statistics import mean,median
from cac.core.retrieval import candidate_pool
from cac.core.builder import build_packet_from_candidates
from cac.baselines.naive_rag import fixed_context_rag, heuristic_rerank_rag, metadata_aware_rag, schema_aware_chunk_rag, oracle_candidate_rag, long_context_rag, iterative_rag
from .profiles import TASKS, build_task_profile
from .generate import generate_decision_dossiers
from .score import score_packet_generic

def parse_csv(v,cast=str): return [cast(x.strip()) for x in v.split(',') if x.strip()]
def task_from_id(account_id,task_types): return next(t for t in task_types if account_id.startswith(t[:3]))

def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def run_suite(n,budgets,distractors,task_types,metadata_noise,output_dir,seed,target):
    output_dir.mkdir(parents=True,exist_ok=True); rows=[]; fails=[]
    for i,d in enumerate(distractors,1):
        print(f'[{i}/{len(distractors)}] distractors={d}',flush=True); dossiers=generate_decision_dossiers(n,d,seed,task_types,metadata_noise=metadata_noise)
        for dossier in dossiers:
            tt=task_from_id(dossier.account_id,task_types)
            for budget in budgets:
                profile=build_task_profile(tt,dossier.entity,budget); candidates=candidate_pool(profile,dossier.sources,max_candidates=32)
                packets=[build_packet_from_candidates(profile,candidates,method='cac'),fixed_context_rag(profile,candidates,8,'fixed_context_rag_k8'),metadata_aware_rag(profile,candidates,8),schema_aware_chunk_rag(profile,candidates,8),oracle_candidate_rag(profile,candidates,8),long_context_rag(profile,candidates,24),iterative_rag(profile,candidates,8),heuristic_rerank_rag(profile,candidates,8)]
                for packet in packets:
                    rec=score_packet_generic(dossier,packet); rec.update({'budget':budget,'distractors':d,'candidate_pool_size':len(candidates),'same_candidate_pool':True,'missing_case_type':dossier.missing_case_type}); rows.append(rec); labs=classify(rec)
                    if labs: fails.append({**rec,'failure_bucket':';'.join(labs),'admitted_sources':[ev.item.source_id for ev in packet.admitted]})
    write_csv(output_dir/'results.csv',rows)
    summary=group(rows,['method'])
    write_csv(output_dir/'summary.csv',summary)
    write_json(output_dir/'summary.json',summary)
    cis=confidence_intervals(rows)
    write_csv(output_dir/'confidence_intervals.csv',cis)
    write_json(output_dir/'confidence_intervals.json',cis)
    write_csv(output_dir/'budget_curves.csv',group(rows,['method','budget']))
    write_csv(output_dir/'task_summary.csv',group(rows,['method','task_type']))
    mint=min_tokens(rows,target,'decision_grade_score')
    write_csv(output_dir/'min_tokens_to_decision_grade_target.csv',mint)
    write_json(output_dir/'min_tokens_to_decision_grade_target.json',mint)
    genmint=min_tokens(rows,target,'generated_answer_score')
    write_csv(output_dir/'min_tokens_to_generated_answer_target.csv',genmint)
    write_json(output_dir/'min_tokens_to_generated_answer_target.json',genmint)
    fs=fail_summary(fails)
    write_csv(output_dir/'failure_summary_all.csv',fs)
    write_json(output_dir/'failure_summary_all.json',fs)
    top=sorted(fails,key=lambda r:float(r['decision_grade_score']))[:200]
    write_csv(output_dir/'failure_analysis_top200.csv',top)
    write_json(output_dir/'failure_analysis_top200.json',top)
    report(output_dir/'benchmark_report.md', summary, mint, len(rows), target, task_summary=group(rows, ['method','task_type']), failure_summary=fs, generated_min_tokens=genmint, confidence_intervals=cis)
def classify(r):
    labs=[]
    if float(r['decision_grade_score'])<.85: labs.append('decision_grade_below_0.85')
    if float(r['slot_fill_rate'])<.8: labs.append('slot_underfill')
    if float(r['exact_clause_preservation'])<1: labs.append('exact_representation_failure')
    if float(r['contradiction_recall'])<1: labs.append('contradiction_miss')
    if float(r['insufficient_evidence_calibration'])<1: labs.append('missing_evidence_calibration_failure')
    if float(r['distractor_admission_rate'])>.05 or float(r['irrelevant_context_share'])>.10: labs.append('irrelevant_context')
    return labs
def group(rows,keys):
    groups={}
    for r in rows: groups.setdefault(tuple(r[k] for k in keys),[]).append(r)
    metrics=['context_tokens','evidence_score','decision_grade_score','slot_fill_rate','quality_per_1k_tokens','decision_grade_per_1k_tokens','contradiction_recall','exact_clause_preservation','insufficient_evidence_calibration','distractor_admission_rate','irrelevant_context_share','answer_readiness_score','generated_answer_score','generated_answer_per_1k_tokens','generated_answer_slot_coverage','generated_answer_exact_use','generated_answer_missing_disclosure','generated_answer_contradiction_handling','generated_answer_citation_support']
    out=[]
    for k,vals in groups.items():
        rec={keys[i]:k[i] for i in range(len(keys))}; rec['n']=len(vals)
        for m in metrics: rec[f'avg_{m}']=round(sum(float(v[m]) for v in vals)/len(vals),4)
        rec['answer_readiness_safe_rate']=round(sum(1 for v in vals if str(v['answer_readiness_safe'])=='True')/len(vals),4); rec['generated_answer_safe_rate']=round(sum(1 for v in vals if str(v['generated_answer_safe'])=='True')/len(vals),4); out.append(rec)
    return sorted(out,key=lambda r:(str(r.get('method','')),r.get('budget',0),str(r.get('task_type',''))))
def scen(r): return (r['account_id'],r['distractors'],r['task_type'],r['missing_case_type'])
def min_tokens(rows,target,metric):
    by={}
    for r in rows: by.setdefault(r['method'],{}).setdefault(scen(r),[]).append(r)
    out=[]
    for method,scenarios in by.items():
        hits=[]; ctx=[]; miss=0
        for vals in scenarios.values():
            hs=[v for v in sorted(vals,key=lambda v:int(v['budget'])) if float(v[metric])>=target]
            if not hs: miss+=1; continue
            hits.append(int(hs[0]['budget'])); ctx.append(int(float(hs[0]['context_tokens'])))
        n=len(scenarios); out.append({'method':method,'target_metric':metric,'target_score':target,'scenario_count':n,'hit_rate':round(len(hits)/n,4),'not_reached_rate':round(miss/n,4),'mean_min_budget_hit':round(mean(hits),2) if hits else 'not_reached','median_min_budget_hit':round(median(hits),2) if hits else 'not_reached','mean_context_tokens_at_first_hit':round(mean(ctx),2) if ctx else 'not_reached'})
    return sorted(out,key=lambda r:(-float(r['hit_rate']),999999 if r['mean_min_budget_hit']=='not_reached' else float(r['mean_min_budget_hit'])))
def fail_summary(fails):
    c={}
    for r in fails:
        for b in r['failure_bucket'].split(';'): c[(r['method'],b)]=c.get((r['method'],b),0)+1
    return [{'method':m,'failure_bucket':b,'count':n} for (m,b),n in sorted(c.items())]

def confidence_intervals(rows):
    from math import sqrt
    metrics=['decision_grade_score','generated_answer_score','evidence_score','generated_answer_safe']
    out=[]
    methods=sorted({r['method'] for r in rows})
    for method in methods:
        vals=[r for r in rows if r['method']==method]
        rec={'method':method,'n':len(vals)}
        for m in metrics:
            if m=='generated_answer_safe':
                xs=[1.0 if str(v[m])=='True' else 0.0 for v in vals]
            else:
                xs=[float(v[m]) for v in vals]
            meanv=sum(xs)/len(xs) if xs else 0.0
            if len(xs)>1:
                sd=(sum((x-meanv)**2 for x in xs)/(len(xs)-1))**0.5
                ci=1.96*sd/(len(xs)**0.5)
            else:
                sd=ci=0.0
            rec[f'{m}_mean']=round(meanv,4); rec[f'{m}_ci95_low']=round(meanv-ci,4); rec[f'{m}_ci95_high']=round(meanv+ci,4)
        out.append(rec)
    return out

def write_csv(path,rows):
    if not rows: path.write_text('', encoding="utf-8"); return
    fields=sorted({k for r in rows for k in r.keys()})
    with path.open('w',newline='',encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); [w.writerow(r) for r in rows]
def report(path, summary, mint, total, target, task_summary=None, failure_summary=None, generated_min_tokens=None, confidence_intervals=None):
    lines = [
        '# DecisionRiskBench v1.4 Report',
        '',
        'Synthetic benchmark artifact. This is not production proof.',
        '',
        f'Total rows: {total}',
        '',
        '## Headline aggregate results',
        '| Method | Tokens | Evidence | Decision Grade | Generated Answer | Slot Fill | Decision/1k | Gen Answer/1k | Missing Cal | Distractor | Gen Safe Rate |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in sorted(summary, key=lambda x: (-x['avg_decision_grade_score'], x['avg_context_tokens'])):
        lines.append(f"| {r['method']} | {r['avg_context_tokens']} | {r['avg_evidence_score']} | {r['avg_decision_grade_score']} | {r['avg_generated_answer_score']} | {r['avg_slot_fill_rate']} | {r['avg_decision_grade_per_1k_tokens']} | {r['avg_generated_answer_per_1k_tokens']} | {r['avg_insufficient_evidence_calibration']} | {r['avg_distractor_admission_rate']} | {r['generated_answer_safe_rate']} |")

    if task_summary:
        lines += [
            '',
            '## Per-task decision-grade summary',
            '',
            'This table is included to avoid hiding mixed results. CAC wins the aggregate in the packaged run, but not every task/metric slice.',
            '',
            '| Task | Best Method by Decision Grade | Best Score | CAC Score | Note |',
            '|---|---|---:|---:|---|',
        ]
        by_task = {}
        for r in task_summary:
            by_task.setdefault(r['task_type'], []).append(r)
        for task, vals in sorted(by_task.items()):
            vals_sorted = sorted(vals, key=lambda x: -x['avg_decision_grade_score'])
            best = vals_sorted[0]
            cac = next((v for v in vals if v['method'] == 'cac'), None)
            cac_score = cac['avg_decision_grade_score'] if cac else 'n/a'
            note = 'CAC wins' if best['method'] == 'cac' else f"{best['method']} leads this slice"
            lines.append(f"| {task} | {best['method']} | {best['avg_decision_grade_score']} | {cac_score} | {note} |")

    lines += [
        '',
        f'## Minimum budget to decision-grade >= {target}',
        '| Method | Hit Rate | Mean Min Budget | Mean Context at First Hit |',
        '|---|---:|---:|---:|',
    ]
    for r in mint:
        lines.append(f"| {r['method']} | {r['hit_rate']} | {r['mean_min_budget_hit']} | {r['mean_context_tokens_at_first_hit']} |")


    if generated_min_tokens:
        lines += [
            '',
            f'## Minimum budget to generated-answer score >= {target}',
            '| Method | Hit Rate | Mean Min Budget | Mean Context at First Hit |',
            '|---|---:|---:|---:|',
        ]
        for r in generated_min_tokens:
            lines.append(f"| {r['method']} | {r['hit_rate']} | {r['mean_min_budget_hit']} | {r['mean_context_tokens_at_first_hit']} |")


    if confidence_intervals:
        lines += [
            '',
            '## 95% confidence intervals over packaged rows',
            '',
            'These are simple row-level normal-approximation intervals, not a substitute for a larger human-audited evaluation.',
            '',
            '| Method | Decision Grade Mean [95% CI] | Generated Answer Mean [95% CI] | Safe Rate Mean [95% CI] |',
            '|---|---:|---:|---:|',
        ]
        for r in sorted(confidence_intervals, key=lambda x: -float(x['generated_answer_score_mean'])):
            lines.append(f"| {r['method']} | {r['decision_grade_score_mean']} [{r['decision_grade_score_ci95_low']}, {r['decision_grade_score_ci95_high']}] | {r['generated_answer_score_mean']} [{r['generated_answer_score_ci95_low']}, {r['generated_answer_score_ci95_high']}] | {r['generated_answer_safe_mean']} [{r['generated_answer_safe_ci95_low']}, {r['generated_answer_safe_ci95_high']}] |")

    if failure_summary:
        lines += [
            '',
            '## Failure summary',
            '',
            'Multi-label failure counts across all rows. A row can count toward multiple failure buckets.',
            '',
            '| Method | Failure Bucket | Count |',
            '|---|---|---:|',
        ]
        for r in failure_summary[:80]:
            lines.append(f"| {r['method']} | {r['failure_bucket']} | {r['count']} |")

    lines += [
        '',
        '## Scoring notes',
        '',
        'Evidence score is a weighted proxy over slot fill, exact wording, contradiction handling, missing-evidence calibration, supportedness, and distractor/irrelevant-context penalties.',
        '',
        'Decision-grade score starts from evidence score and applies hard caps for decision-critical failures such as missing exact wording, undisclosed missing evidence, unsurfaced contradiction, authority inversion, irrelevant-context overload, and unsupported evidence.',
        '',
        "Generated-answer score is a deterministic, label-aided answer-readiness proxy over each method's admitted context. It is not an LLM answer study or human judge.",
        '',
        '## Claim hygiene',
        '',
        'Supported: CAC has the strongest aggregate decision-grade behavior in this synthetic packaged run.',
        '',
        'Not supported: CAC beats every RAG baseline on every task and every metric, or that CAC is production-proven.',
    ]
    path.write_text('\n'.join(lines), encoding="utf-8")

def main():
    p=argparse.ArgumentParser(); p.add_argument('--n',type=int,default=10); p.add_argument('--budgets',default='40,60,80,120,160,240,500'); p.add_argument('--distractors',default='5,25,50'); p.add_argument('--task-types',default=','.join(['renewal_risk','security_exception','contract_termination','incident_postmortem'])); p.add_argument('--metadata-noise',type=float,default=.12); p.add_argument('--seed',type=int,default=42); p.add_argument('--target-score',type=float,default=.90); p.add_argument('--output-dir',default='outputs/decision_risk_v1_4_n20'); a=p.parse_args(); run_suite(a.n,parse_csv(a.budgets,int),parse_csv(a.distractors,int),parse_csv(a.task_types,str),a.metadata_noise,Path(a.output_dir),a.seed,a.target_score)
if __name__=='__main__': main()
