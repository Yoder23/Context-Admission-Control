from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from statistics import mean,median
from typing import Any,List
from cac.core.builder import build_profile, build_packet_from_candidates
from cac.core.retrieval import candidate_pool
from cac.baselines.naive_rag import fixed_context_rag, heuristic_rerank_rag, metadata_aware_rag, schema_aware_chunk_rag
from .generate_dossiers import generate_dossiers
from .score import score_packet

def parse_csv_arg(value:str,cast=str): return [cast(x.strip()) for x in value.split(',') if x.strip()]

def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def run_suite(n:int,budgets:List[int],distractors:List[int],metadata_modes:List[str],slot_modes:List[str],output_dir:Path,seed:int,target_score:float)->None:
    output_dir.mkdir(parents=True,exist_ok=True); rows=[]; failure_records=[]
    total_combos=len(metadata_modes)*len(distractors); combo_i=0
    for metadata_mode in metadata_modes:
        for distractor_count in distractors:
            combo_i+=1; print(f"[{combo_i}/{total_combos}] metadata={metadata_mode} distractors={distractor_count}", flush=True)
            dossiers=generate_dossiers(n=n,distractors=distractor_count,metadata_mode=metadata_mode,seed=seed)
            for dossier in dossiers:
                for budget in budgets:
                    base_profile=build_profile("Assess renewal risk and cite evidence. Flag contradictions between CRM, support, billing, executive signals, and contract terms.",dossier.entity,budget,slot_mode="perfect_slots")
                    candidates=candidate_pool(base_profile,dossier.sources,max_candidates=24)
                    methods=[]
                    for slot_mode in slot_modes:
                        profile=build_profile(base_profile.task,dossier.entity,budget,slot_mode=slot_mode)
                        methods.append((slot_mode,build_packet_from_candidates(profile,candidates,method=f"cac_{slot_mode}")))
                    methods.extend([("not_applicable",fixed_context_rag(base_profile,candidates,k=5,method="fixed_context_rag_k5")),("not_applicable",fixed_context_rag(base_profile,candidates,k=6,method="fixed_context_rag_k6")),("not_applicable",fixed_context_rag(base_profile,candidates,k=8,method="fixed_context_rag_k8")),("not_applicable",heuristic_rerank_rag(base_profile,candidates,k=8)),("not_applicable",metadata_aware_rag(base_profile,candidates,k=8)),("not_applicable",schema_aware_chunk_rag(base_profile,candidates,k=8))])
                    for slot_mode,packet in methods:
                        rec=score_packet(dossier,packet); rec.update({"budget":budget,"distractors":distractor_count,"metadata_mode":metadata_mode,"slot_mode":slot_mode,"missing_case":dossier.missing_case,"missing_case_type":dossier.missing_case_type,"candidate_pool_size":len(candidates),"same_candidate_pool":True}); rows.append(rec)
                        if rec["evidence_score"]<0.85:
                            labels=classify_failures(rec)
                            failure_records.append({**rec,"admitted_sources":[ev.item.source_id for ev in packet.admitted],"failure_bucket":";".join(labels)})
    print(f'writing {len(rows)} result rows to {output_dir}', flush=True)
    write_csv(output_dir/'results.csv',rows)
    summary=summarize(rows)
    write_csv(output_dir/'summary.csv',summary)
    write_json(output_dir/'summary.json',summary)
    budget_curves=group_summary(rows,['method','budget'])
    write_csv(output_dir/'budget_curves.csv',budget_curves)
    min_tokens=min_tokens_to_target(rows,target_score,metric='evidence_score')
    write_csv(output_dir/'min_tokens_to_target.csv',min_tokens)
    write_json(output_dir/'min_tokens_to_target.json',min_tokens)
    min_decision=min_tokens_to_target(rows,target_score,metric='decision_grade_score')
    write_csv(output_dir/'min_tokens_to_decision_grade_target.csv',min_decision)
    write_json(output_dir/'min_tokens_to_decision_grade_target.json',min_decision)
    failure_summary=all_failure_summary(failure_records)
    write_csv(output_dir/'failure_summary_all.csv',failure_summary)
    write_json(output_dir/'failure_summary_all.json',failure_summary)
    top_failures=sorted(failure_records,key=lambda r:r['evidence_score'])[:200]
    write_csv(output_dir/'failure_analysis_top200.csv',top_failures)
    write_json(output_dir/'failure_analysis_top200.json',top_failures)
    write_report(output_dir/'benchmark_report.md',summary,min_tokens,budget_curves,len(rows),target_score,min_decision)

def classify_failures(rec:dict[str,Any])->list[str]:
    labels=[]
    if float(rec.get('slot_fill_rate',1.0))<0.8: labels.append('slot_underfill')
    if float(rec.get('decision_grade_score',1.0))<0.85: labels.append('decision_grade_gate')
    if float(rec.get('exact_clause_preservation',1.0))<1.0: labels.append('exact_clause_failure')
    if float(rec.get('contradiction_recall',1.0))<1.0: labels.append('contradiction_miss')
    if float(rec.get('insufficient_evidence_calibration',1.0))<1.0: labels.append('missing_evidence_calibration_failure')
    if float(rec.get('distractor_admission_rate',0.0))>0.0 or float(rec.get('irrelevant_context_share',0.0))>0.10: labels.append('distractor_or_irrelevant_context')
    if float(rec.get('spurious_uncertainty_rate',0.0))>0.0: labels.append('spurious_uncertainty')
    return labels or ['low_composite_score']

def summarize(rows): return group_summary(rows,['method'])

def group_summary(rows,keys):
    groups={}
    for r in rows: groups.setdefault(tuple(r[x] for x in keys),[]).append(r)
    out=[]; metrics=['context_tokens','evidence_score','decision_grade_score','slot_fill_rate','quality_per_1k_tokens','decision_grade_per_1k_tokens','contradiction_recall','exact_clause_preservation','insufficient_evidence_calibration','unsupported_claim_rate','distractor_admission_rate','irrelevant_context_tokens','irrelevant_context_share','spurious_uncertainty_rate','over_budget_tokens']
    for k,vals in groups.items():
        rec={keys[i]:k[i] for i in range(len(keys))}; rec['n']=len(vals)
        nvals=len(vals)
        for m in metrics:
            rec[f'avg_{m}']=round(sum(float(v[m]) for v in vals)/nvals,4)
        rec['over_budget_rate']=round(sum(1.0 if str(v.get('over_budget')).lower()=='true' else 0.0 for v in vals)/nvals,4); out.append(rec)
    out.sort(key=lambda r:(str(r.get('method','')),r.get('budget',0))); return out

def scenario_key(r): return (r['account_id'],r['distractors'],r['metadata_mode'],r.get('slot_mode','not_applicable'),r.get('missing_case_type','none'))

def min_tokens_to_target(rows,target,metric='evidence_score'):
    by_method={}
    for r in rows: by_method.setdefault(r['method'],{}).setdefault(scenario_key(r),[]).append(r)
    out=[]
    for method,scenarios in by_method.items():
        hit_budgets=[]; hit_context_tokens=[]; not_reached=0
        for vals in scenarios.values():
            vals=sorted(vals,key=lambda v:int(v['budget'])); hits=[v for v in vals if float(v[metric])>=target]
            if not hits: not_reached+=1; continue
            first=hits[0]; hit_budgets.append(int(first['budget'])); hit_context_tokens.append(int(float(first['context_tokens'])))
        scenario_count=len(scenarios)
        if hit_budgets: out.append({'method':method,'target_metric': metric, 'target_score':target,'scenario_count':scenario_count,'hit_rate':round(len(hit_budgets)/scenario_count,4),'not_reached_rate':round(not_reached/scenario_count,4),'mean_min_budget_hit':round(mean(hit_budgets),2),'median_min_budget_hit':round(median(hit_budgets),2),'mean_context_tokens_at_first_hit':round(mean(hit_context_tokens),2),'median_context_tokens_at_first_hit':round(median(hit_context_tokens),2)})
        else: out.append({'method':method,'target_metric': metric, 'target_score':target,'scenario_count':scenario_count,'hit_rate':0.0,'not_reached_rate':1.0,'mean_min_budget_hit':'not_reached','median_min_budget_hit':'not_reached','mean_context_tokens_at_first_hit':'not_reached','median_context_tokens_at_first_hit':'not_reached'})
    out.sort(key=lambda r:(1.0-float(r['hit_rate']),999999 if r['mean_min_budget_hit']=='not_reached' else float(r['mean_min_budget_hit']))); return out

def write_csv(path,rows):
    if not rows: path.write_text('', encoding="utf-8"); return
    fieldnames=sorted({k for r in rows for k in r.keys()})
    with path.open('w',newline='',encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); [w.writerow(r) for r in rows]

def all_failure_summary(failure_records:list[dict[str,Any]])->list[dict[str,Any]]:
    counts={}
    for r in failure_records:
        method=r.get('method','unknown')
        for label in str(r.get('failure_bucket','unknown')).split(';'):
            key=(method,label)
            counts[key]=counts.get(key,0)+1
    return [{'method':m,'failure_bucket':b,'count':c} for (m,b),c in sorted(counts.items())]

def failure_bucket_counts_from_file(output_dir:Path)->list[dict[str,Any]]:
    path=output_dir/'failure_summary_all.csv'
    if not path.exists() or path.stat().st_size==0: return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_report(path,summary,min_tokens,budget_curves,total_rows,target,min_decision=None):
    output_dir=path.parent
    failure_counts=failure_bucket_counts_from_file(output_dir)
    lines=['# RenewalRiskBench v0.5.4 Report','','Synthetic benchmark for CAC vs fixed-context RAG under same-candidate-pool conditions.','',f'Total result rows: {total_rows}','','## Summary','| Method | Tokens | Evidence | Decision Grade | Slot Fill | Q/1k | Decision/1k | Contradiction | Exact Clause | Missing Evidence | Distractor Rate | Irrelevant Share | Spurious Uncertainty |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sorted(summary,key=lambda x:(-x['avg_evidence_score'],x['avg_context_tokens'])): lines.append(f"| {r['method']} | {r['avg_context_tokens']} | {r['avg_evidence_score']} | {r['avg_decision_grade_score']} | {r['avg_slot_fill_rate']} | {r['avg_quality_per_1k_tokens']} | {r['avg_decision_grade_per_1k_tokens']} | {r['avg_contradiction_recall']} | {r['avg_exact_clause_preservation']} | {r['avg_insufficient_evidence_calibration']} | {r['avg_distractor_admission_rate']} | {r['avg_irrelevant_context_share']} | {r.get('avg_spurious_uncertainty_rate',0)} |")
    lines+=['',f'## Minimum budget/context to evidence score >= {target}','| Method | Hit Rate | Not Reached | Mean Min Budget | Median Min Budget | Mean Context Tokens at First Hit |','|---|---:|---:|---:|---:|---:|']
    for r in min_tokens: lines.append(f"| {r['method']} | {r['hit_rate']} | {r['not_reached_rate']} | {r['mean_min_budget_hit']} | {r['median_min_budget_hit']} | {r['mean_context_tokens_at_first_hit']} |")
    if min_decision:
        lines += ['', f'## Minimum budget/context to decision-grade score >= {target}', '| Method | Hit Rate | Not Reached | Mean Min Budget | Median Min Budget | Mean Context Tokens at First Hit |', '|---|---:|---:|---:|---:|---:|']
        for r in min_decision:
            lines.append(f"| {r['method']} | {r['hit_rate']} | {r['not_reached_rate']} | {r['mean_min_budget_hit']} | {r['median_min_budget_hit']} | {r['mean_context_tokens_at_first_hit']} |")
    lines+=['','## Scoring formula','Composite evidence score is disclosed so readers can interpret the benchmark:','','```text','evidence_score =','  0.34 * slot_fill_rate','+ 0.20 * exact_clause_preservation','+ 0.19 * contradiction_recall','+ 0.19 * insufficient_evidence_calibration','+ 0.03 * (1 - unsupported_claim_rate)','+ 0.03 * (1 - relevance_penalty)','+ 0.02 * (1 - spurious_uncertainty_rate)','','relevance_penalty = 0.5 * distractor_admission_rate + 0.5 * irrelevant_context_share','```','','Decision-grade score starts from `evidence_score` and applies caps: exact-clause missing (0.65), undisclosed missing evidence (0.70), unsurfaced contradiction (0.75), authority inversion (0.60), irrelevant-context overload (0.80), or unsupported evidence (0.85).','','Quality per 1k tokens is useful only alongside absolute evidence score and slot fill; minimal slot profiles can look efficient while under-specifying the task.','','## Contradiction caveat','Fixed-context RAG can remain competitive on raw contradiction recall because stuffing more chunks may admit both CRM optimism and operational negatives. CAC is evaluated as an evidence-sufficiency controller: it should surface contradictions deliberately, not by over-admitting context.','','## Failure taxonomy','- slot_underfill: packet did not fill enough gold evidence slots.','- exact_clause_failure: contract clause was not preserved with an exact/full representation.','- contradiction_miss: packet admitted only one side of a known contradiction or failed to mark it.','- missing_evidence_calibration_failure: required missing evidence was not surfaced.','- distractor_or_irrelevant_context: admitted irrelevant/distractor evidence hurt the composite score.']
    if failure_counts:
        lines+=['','## All failure bucket counts from packaged run' ,'| Method | Failure Bucket | Count |','|---|---|---:|']
        for r in failure_counts:
            lines.append(f"| {r['method']} | {r['failure_bucket']} | {r['count']} |")
    lines+=['','## Reproducibility','Smoke run:','','```bash','PYTHONPATH=. python -m benchmarks.renewal_risk.run \\','  --n 2 \\','  --budgets 60,120 \\','  --distractors 5 \\','  --metadata-modes clean_metadata,wrong_10_percent_tags \\','  --slot-modes perfect_slots,partial_slots \\','  --output-dir outputs/smoke','```','','Full packaged run:','','```bash','PYTHONPATH=. python -m benchmarks.renewal_risk.run \\','  --n 20 \\','  --budgets 60,80,120,160,240,500 \\','  --distractors 5,10,25,50 \\','  --metadata-modes clean_metadata,missing_20_percent_tags,wrong_10_percent_tags,stale_freshness_metadata \\','  --slot-modes perfect_slots,partial_slots,noisy_slots,minimal_slots \\','  --output-dir outputs/renewal_risk_v053','```','','## Limitations','- Synthetic benchmark, not production proof.','- The task remains renewal-risk-specific.','- Source metadata is synthetic even in noisy modes.','- Heuristic and metadata-aware RAG baselines are not production cross-encoders or proprietary enterprise RAG stacks.','- Final answer generation is not LLM-judged in this harness; scoring is evidence-packet based.']
    path.write_text('\n'.join(lines), encoding="utf-8")

def main():
    p=argparse.ArgumentParser(); p.add_argument('--n',type=int,default=20); p.add_argument('--budgets',default='60,80,120,160,240,500'); p.add_argument('--distractors',default='5,10,25,50'); p.add_argument('--metadata-modes',default='clean_metadata,missing_20_percent_tags,wrong_10_percent_tags,stale_freshness_metadata'); p.add_argument('--slot-modes',default='perfect_slots,partial_slots,noisy_slots,minimal_slots'); p.add_argument('--output-dir',default='outputs/renewal_risk_v053'); p.add_argument('--seed',type=int,default=17); p.add_argument('--target-score',type=float,default=0.90); args=p.parse_args(); run_suite(n=args.n,budgets=parse_csv_arg(args.budgets,int),distractors=parse_csv_arg(args.distractors,int),metadata_modes=parse_csv_arg(args.metadata_modes,str),slot_modes=parse_csv_arg(args.slot_modes,str),output_dir=Path(args.output_dir),seed=args.seed,target_score=args.target_score)
if __name__=='__main__': main()
