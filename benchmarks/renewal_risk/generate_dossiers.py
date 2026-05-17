from __future__ import annotations
from typing import List
import random
from cac.core.schemas import AccountDossier, SourceItem, SourceType
from cac.core.slots import CANONICAL_SLOT_NAMES

METADATA_MODE_OFFSETS = {"clean_metadata":0,"missing_20_percent_tags":101,"wrong_10_percent_tags":202,"stale_freshness_metadata":303}
MISSING_CASE_TYPES = ("missing_executive_sponsor","missing_contract_clause","missing_billing_status","missing_support_trend","missing_crm_status","missing_recent_negative_signal","none")

def generate_dossiers(n:int,distractors:int,metadata_mode:str,seed:int=17)->List[AccountDossier]:
    if metadata_mode not in METADATA_MODE_OFFSETS: raise ValueError(f"unknown metadata_mode: {metadata_mode}")
    rng=random.Random(seed+n*13+distractors*7+METADATA_MODE_OFFSETS[metadata_mode])
    dossiers=[]
    for i in range(n):
        account=f"acct_{i:04d}"; entity=f"Acme-{i:04d} Corp"; missing_case_type=MISSING_CASE_TYPES[i%len(MISSING_CASE_TYPES)]
        sources=base_sources(account,entity,i,missing_case_type)+distractor_sources(account,entity,i,distractors,rng)
        apply_metadata_noise(sources,metadata_mode,rng)
        present=sorted({s for item in sources for s in item.gold_slots})
        missing=[s for s in CANONICAL_SLOT_NAMES if s not in present]
        has_positive=any(s.gold_positive for s in sources); has_negative=any(s.gold_negative for s in sources)
        dossiers.append(AccountDossier(account_id=account,entity=entity,sources=sources,present_gold_slots=present,missing_gold_slots=missing,has_contradiction=has_positive and has_negative,metadata_mode=metadata_mode,distractors=distractors,missing_case=missing_case_type!="none",missing_case_type=missing_case_type))
    return dossiers

def base_sources(account:str,entity:str,i:int,missing_case_type:str)->List[SourceItem]:
    freshness=(i*3)%35+2; out=[]
    if missing_case_type!="missing_crm_status": out.append(SourceItem(source_id=f"{account}_crm_health",account_id=account,entity=entity,source_type=SourceType.CRM,title="CRM renewal health note",text=f"Account owner marked {entity} green and healthy. Renewal is expected to be on track and low risk.",freshness_days=12,authority=0.55,topics=["crm","health","renewal","forecast"],risk_tags=["subjective_status"],structured={"crm_status":"healthy","forecast":"on_track"},gold_slots=["crm_health_status"],gold_positive=True))
    if missing_case_type not in {"missing_billing_status","missing_recent_negative_signal"}: out.append(SourceItem(source_id=f"{account}_billing_overdue",account_id=account,entity=entity,source_type=SourceType.BILLING,title="Billing status row",text=f"Most recent invoice for {entity} is 47 days overdue. Two prior invoices were also paid late. Outstanding balance is 184000.",freshness_days=freshness,authority=0.97,topics=["billing","payment","overdue","invoice","renewal"],risk_tags=["payment_default","operational_signal"],structured={"invoice_status":"47_days_overdue","prior_late_payments":2,"outstanding_balance":184000},gold_slots=["billing_status","recent_negative_signal"],gold_negative=True))
    if missing_case_type not in {"missing_support_trend","missing_recent_negative_signal"}: out.append(SourceItem(source_id=f"{account}_support_p1_cluster",account_id=account,entity=entity,source_type=SourceType.SUPPORT,title="Support escalation cluster",text=f"{entity} has three unresolved P1 escalations related to SSO downtime and data export failures. Two tickets mention renewal risk.",freshness_days=7,authority=0.90,topics=["support","escalation","p1","renewal","outage"],risk_tags=["operational_signal","customer_unhappy"],gold_slots=["support_trend","recent_negative_signal"],gold_negative=True))
    out.append(SourceItem(source_id=f"{account}_contract_dpa_distractor",account_id=account,entity=entity,source_type=SourceType.CONTRACT,title="MSA Section 4.1 Data Processing Addendum",text="The parties agree to maintain commercially reasonable administrative, physical, and technical safeguards for personal data. This section does not modify payment obligations, renewal timing, termination rights, or cure periods.",freshness_days=220,authority=0.95,topics=["contract","data processing","security"],risk_tags=["legal","distractor","generic_contract"],is_distractor=True))
    if missing_case_type not in {"missing_contract_clause","missing_recent_negative_signal"}: out.append(SourceItem(source_id=f"{account}_contract_termination_payment",account_id=account,entity=entity,source_type=SourceType.CONTRACT,title="MSA Section 12.2 Termination for Cause",text="If either party materially breaches this Agreement and fails to cure such breach within thirty (30) days after written notice, the non-breaching party may terminate the Agreement. Non-payment of undisputed fees for more than forty-five (45) days constitutes material breach after notice.",freshness_days=220,authority=0.99,topics=["contract","termination","payment","breach","renewal","cure"],risk_tags=["legal","obligation","exact_wording_required","termination","payment_default","cure"],gold_slots=["contract_renewal_or_termination_terms","recent_negative_signal"],gold_negative=True,gold_exact_required=True))
    out.append(SourceItem(source_id=f"{account}_old_call_positive",account_id=account,entity=entity,source_type=SourceType.CALL_NOTE,title="Old positive call note",text=f"Six months ago, {entity} said the platform was strategic and renewal seemed likely. They praised the roadmap but asked for export reliability improvements.",freshness_days=190,authority=0.50,topics=["call","renewal","roadmap"],risk_tags=["stale_positive_signal"],gold_positive=True))
    out.append(SourceItem(source_id=f"{account}_slack_speculation",account_id=account,entity=entity,source_type=SourceType.SLACK,title="Internal Slack speculation",text=f"Someone in sales said {entity} is probably fine and the billing issue is just procurement being slow. No source attached.",freshness_days=75,authority=0.25,topics=["slack","billing","speculation"],risk_tags=["low_authority","speculation"],is_distractor=True,gold_positive=True))
    if missing_case_type not in {"missing_executive_sponsor","missing_recent_negative_signal"}: out.append(SourceItem(source_id=f"{account}_exec_email_blocked",account_id=account,entity=entity,source_type=SourceType.EMAIL,title="Executive sponsor renewal email",text=f"{entity} VP Operations wrote: We cannot recommend renewal unless the SSO outages are resolved and export reliability is materially improved before the renewal review.",freshness_days=9,authority=0.86,topics=["email","executive sponsor","renewal","support"],risk_tags=["executive_commitment","customer_unhappy","exact_wording_required"],gold_slots=["executive_sponsor_signal","recent_negative_signal"],gold_negative=True,gold_exact_required=False))
    return out

def distractor_sources(account:str,entity:str,i:int,count:int,rng:random.Random)->List[SourceItem]:
    templates=[(SourceType.CONTRACT,"Generic liability clause","The aggregate liability of each party shall not exceed fees paid in the prior twelve months. This clause does not address payment default or termination cure periods.",["contract","liability"],["legal","generic_contract"]),(SourceType.SECURITY,"Security review note","Security review completed with medium findings unrelated to renewal risk. No active blocker identified.",["security","review"],["noise"]),(SourceType.INTERNAL_NOTE,"Enablement note","Customer requested enablement materials for a new admin training session next quarter.",["training","admin"],["noise"]),(SourceType.CALL_NOTE,"Paraphrased optimism","The account team believes the customer may still renew if roadmap messaging lands well.",["call","renewal"],["stale_positive_signal"]),(SourceType.SUPPORT,"Minor ticket","A low-priority UI ticket was closed successfully. No escalation or renewal risk mentioned.",["support","ticket"],["distractor"]),(SourceType.BILLING,"Procurement note","Procurement asked for invoice formatting changes. No updated payment status was provided.",["billing","invoice"],["distractor"])]
    return [SourceItem(source_id=f"{account}_distractor_{j:03d}",account_id=account,entity=entity,source_type=st,title=title,text=text,freshness_days=rng.randint(10,260),authority=rng.choice([0.35,0.50,0.65,0.80]),topics=list(topics),risk_tags=list(tags),is_distractor=True) for j,(st,title,text,topics,tags) in ((j,templates[j%len(templates)]) for j in range(count))]

def apply_metadata_noise(sources:List[SourceItem],metadata_mode:str,rng:random.Random)->None:
    if metadata_mode=="clean_metadata": return
    if metadata_mode=="missing_20_percent_tags":
        for s in sources:
            if rng.random()<0.20 and s.risk_tags: s.risk_tags=s.risk_tags[:-1]
            if rng.random()<0.20 and s.topics: s.topics=s.topics[:-1]
    elif metadata_mode=="wrong_10_percent_tags":
        for s in sources:
            if rng.random()<0.10: s.risk_tags.append(rng.choice(["renewal","termination","noise","payment_default","customer_unhappy"]))
            if rng.random()<0.10: s.topics.append(rng.choice(["renewal","billing","support","contract","security"]))
    elif metadata_mode=="stale_freshness_metadata":
        for s in sources:
            if rng.random()<0.30: s.freshness_days+=rng.randint(120,300)
    else: raise ValueError(f"unknown metadata_mode: {metadata_mode}")
