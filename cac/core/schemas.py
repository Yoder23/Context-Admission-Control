
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple
import math
import re


class SourceType(str, Enum):
    CONTRACT = "contract"
    BILLING = "billing"
    SUPPORT = "support"
    CRM = "crm"
    EMAIL = "email"
    CALL_NOTE = "call_note"
    SLACK = "slack"
    SECURITY = "security"
    INTERNAL_NOTE = "internal_note"


class Representation(str, Enum):
    IGNORE = "ignore"
    METADATA_ONLY = "metadata_only"
    STRUCTURED_FACT = "structured_fact"
    SUMMARY = "summary"
    EXACT_EXCERPT = "exact_excerpt"
    FULL_SOURCE_SPAN = "full_source_span"


EXACT_REPRESENTATIONS = {Representation.EXACT_EXCERPT, Representation.FULL_SOURCE_SPAN}


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text.split()) * 1.25))


def normalize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class SourceItem:
    source_id: str
    account_id: str
    entity: str
    source_type: SourceType
    title: str
    text: str
    freshness_days: int
    authority: float
    topics: List[str]
    risk_tags: List[str]
    structured: Dict[str, Any] = field(default_factory=dict)
    token_cost: int = 0
    # Benchmark gold labels. Non-oracle methods must not read these fields; they are scorer/oracle-only.
    gold_slots: List[str] = field(default_factory=list)
    gold_negative: bool = False
    gold_positive: bool = False
    gold_exact_required: bool = False
    is_distractor: bool = False

    def __post_init__(self) -> None:
        if self.token_cost <= 0:
            self.token_cost = estimate_tokens(self.text)


@dataclass(frozen=True)
class RequiredEvidenceSlot:
    name: str
    source_types: Tuple[SourceType, ...]
    any_risk_tags: Tuple[str, ...] = ()
    all_risk_tags: Tuple[str, ...] = ()
    any_topics: Tuple[str, ...] = ()
    all_topics: Tuple[str, ...] = ()
    exact_wording_required: bool = False
    description: str = ""


@dataclass
class TaskProfile:
    task: str
    entity: str
    answer_target: str = "renewal_risk_assessment"
    token_budget: int = 2000
    risk_profile: str = "commercial_contract"
    required_slots: Tuple[RequiredEvidenceSlot, ...] = ()
    slot_mode: str = "perfect_slots"


@dataclass
class Candidate:
    item: SourceItem
    candidate_score: float


@dataclass
class CandidateValuation:
    item: SourceItem
    relevance: float
    authority: float
    freshness: float
    novelty: float
    contradiction_potential: float
    task_criticality: float
    redundancy: float
    token_cost_penalty: float
    slot_fill_bonus: float
    admission_score: float
    representation: Representation
    admission_reason: str
    representation_reason: str
    slot_matches: List[str]


@dataclass
class AdmittedEvidence:
    item: SourceItem
    representation: Representation
    slot_matches: List[str]
    token_cost: int


@dataclass
class EvidencePacket:
    answer_target: str
    entity: str
    method: str
    budget_used: Dict[str, Any]
    structured_facts: List[Dict[str, Any]] = field(default_factory=list)
    summaries: List[Dict[str, Any]] = field(default_factory=list)
    exact_evidence: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    excluded_evidence: List[Dict[str, Any]] = field(default_factory=list)
    audit_trace: List[Dict[str, Any]] = field(default_factory=list)
    filled_slots: List[str] = field(default_factory=list)
    missing_slots: List[str] = field(default_factory=list)
    admitted: List[AdmittedEvidence] = field(default_factory=list)


@dataclass
class AccountDossier:
    account_id: str
    entity: str
    sources: List[SourceItem]
    present_gold_slots: List[str]
    missing_gold_slots: List[str]
    has_contradiction: bool
    metadata_mode: str
    distractors: int
    missing_case: bool
    missing_case_type: str = "none"
