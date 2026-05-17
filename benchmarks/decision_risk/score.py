from __future__ import annotations
from typing import Any, Dict
from cac.core.schemas import AccountDossier, EvidencePacket, EXACT_REPRESENTATIONS
from .answers import generate_decision_answer, score_generated_answer

def score_packet_generic(dossier: AccountDossier, packet: EvidencePacket) -> Dict[str, Any]:
    present=set(dossier.present_gold_slots); missing=set(dossier.missing_gold_slots); exact_slots={slot for s in dossier.sources for slot in s.gold_slots if s.gold_exact_required}
    filled=set(); exact_filled=set(); pos=False; neg=False; unsupported=0; distractors=0; irrelevant_tokens=0; low_pos=False; high_neg=False
    for ev in packet.admitted:
        item=ev.item
        if item.gold_positive:
            pos=True; low_pos = low_pos or item.authority<.65
        if item.gold_negative:
            neg=True; high_neg = high_neg or item.authority>=.85
        if item.is_distractor: distractors+=1
        if not item.gold_slots: unsupported+=1; irrelevant_tokens+=ev.token_cost
        for slot in item.gold_slots:
            if slot in exact_slots:
                if ev.representation in EXACT_REPRESENTATIONS: filled.add(slot); exact_filled.add(slot)
            else: filled.add(slot)
    slot_fill=len(filled & present)/max(1,len(present)); exact=1.0 if not exact_slots else len(exact_filled & exact_slots)/max(1,len(exact_slots)); contra=1.0 if not dossier.has_contradiction else (1.0 if pos and neg and packet.conflicts else 0.0)
    if missing:
        reported=set(packet.missing_slots); text=' '.join(packet.uncertainties).lower(); reported|={s for s in missing if s in text or s.replace('_',' ') in text}; miss_cal=len(reported&missing)/len(missing)
    else: miss_cal=1.0
    n=max(1,len(packet.admitted)); tokens=packet.budget_used.get('context_tokens',0); unsupported_rate=min(1,unsupported/n); distractor_rate=min(1,distractors/n); irrelevant_share=irrelevant_tokens/max(1,tokens); rel_penalty=.5*distractor_rate+.5*irrelevant_share
    evidence=.30*slot_fill+.22*exact+.20*contra+.18*miss_cal+.04*(1-unsupported_rate)+.04*(1-min(1,rel_penalty))+.02
    decision,gates=decision_grade(evidence,present,missing,slot_fill,exact,contra,miss_cal,distractor_rate,irrelevant_share,unsupported_rate,low_pos,high_neg,dossier.has_contradiction)
    answer=answer_readiness_score(dossier, packet, decision, miss_cal, contra)
    generated_answer = generate_decision_answer(packet)
    generated_scores = score_generated_answer(dossier, packet, generated_answer)
    rec = {'account_id':dossier.account_id,'task_type':packet.answer_target,'method':packet.method,'context_tokens':tokens,'sources_admitted':packet.budget_used.get('sources_admitted',len(packet.admitted)),'evidence_score':round(evidence,4),'decision_grade_score':round(decision,4),'decision_grade_gate_reasons':';'.join(gates) if gates else 'none','slot_fill_rate':round(slot_fill,4),'exact_clause_preservation':round(exact,4),'contradiction_recall':round(contra,4),'insufficient_evidence_calibration':round(miss_cal,4),'unsupported_claim_rate':round(unsupported_rate,4),'distractor_admission_rate':round(distractor_rate,4),'irrelevant_context_share':round(irrelevant_share,4),'irrelevant_context_tokens':irrelevant_tokens,'over_budget_tokens':packet.budget_used.get('over_budget_tokens',0),'over_budget':packet.budget_used.get('over_budget',False),'quality_per_1k_tokens':round(evidence/max(1,tokens)*1000,4),'decision_grade_per_1k_tokens':round(decision/max(1,tokens)*1000,4),'answer_readiness_score': round(answer, 4), 'answer_readiness_safe': answer >= .80,'filled_gold_slots':sorted(filled&present),'missing_gold_slots':sorted(missing),'packet_missing_slots':packet.missing_slots}
    rec.update(generated_scores)
    rec['generated_answer_per_1k_tokens'] = round(rec['generated_answer_score']/max(1,tokens)*1000,4)
    return rec
def decision_grade(evidence,present,missing,slot_fill,exact,contra,miss_cal,distractor,irrelevant,unsupported,low_pos,high_neg,has_contra):
    score=evidence; reasons=[]
    def cap(v,r):
        nonlocal score
        if score>v: score=v
        reasons.append(r)
    if slot_fill<.80: cap(.72,'slot_underfill')
    if exact<1: cap(.65,'exact_required_missing')
    if missing and miss_cal<1: cap(.70,'missing_evidence_not_disclosed')
    if has_contra and contra<1: cap(.75,'contradiction_not_surfaced')
    if low_pos and high_neg and contra<1: cap(.60,'authority_inversion')
    if distractor>.25 or irrelevant>.30: cap(.80,'irrelevant_context_overload')
    if unsupported>0: cap(.85,'unsupported_evidence')
    return score, sorted(set(reasons))
def answer_readiness_score(dossier, packet, decision, missing_cal, contra):
    # Deterministic answer-readiness proxy. This does not score generated prose;
    # it estimates whether the admitted context/packet is sufficient for a safe answer.
    cites = bool([ev for ev in packet.admitted if ev.item.gold_slots])
    return .60 * decision + .15 * cites + .15 * missing_cal + .10 * contra
