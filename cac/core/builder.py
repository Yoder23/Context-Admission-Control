
from __future__ import annotations

from typing import List

from .schemas import TaskProfile, SourceItem, EvidencePacket, Candidate
from .slots import renewal_risk_slots
from .retrieval import candidate_pool
from .valuation import value_candidates
from .packet import assemble_packet
from .expansion import expansion_loop


def build_profile(task: str, entity: str, token_budget: int, slot_mode: str = "perfect_slots") -> TaskProfile:
    return TaskProfile(task=task, entity=entity, token_budget=token_budget, required_slots=renewal_risk_slots(slot_mode), slot_mode=slot_mode)


def build_packet_from_candidates(profile: TaskProfile, candidates: List[Candidate], method: str | None = None) -> EvidencePacket:
    vals = value_candidates(profile, candidates)
    packet, admitted = assemble_packet(profile, vals, method=method or f"cac_{profile.slot_mode}")
    return expansion_loop(profile, candidates, packet, admitted)


def build_packet(profile: TaskProfile, sources: List[SourceItem], max_candidates: int = 20) -> EvidencePacket:
    candidates = candidate_pool(profile, sources, max_candidates=max_candidates)
    return build_packet_from_candidates(profile, candidates)
