
from __future__ import annotations

from typing import List

from .schemas import SourceItem, TaskProfile, Candidate, normalize


def keyword_overlap_score(query: str, item: SourceItem) -> float:
    q = set(normalize(query))
    d = set(normalize(" ".join([item.title, item.text, " ".join(item.topics), " ".join(item.risk_tags)])))
    if not q:
        return 0.0
    overlap = len(q & d) / len(q)
    entity_boost = 0.15 if item.entity.lower() in query.lower() else 0.0
    return min(1.0, overlap + entity_boost)


def candidate_pool(profile: TaskProfile, sources: List[SourceItem], max_candidates: int = 20) -> List[Candidate]:
    query = (
        f"{profile.task} {profile.entity} renewal risk billing support CRM contract termination "
        f"payment overdue escalation executive sponsor discount health"
    )
    candidates: list[Candidate] = []
    for item in sources:
        if item.entity.lower() != profile.entity.lower():
            continue
        score = keyword_overlap_score(query, item)
        # Include weak near-matches too; this is important for distractor pressure.
        if score > 0.02:
            candidates.append(Candidate(item=item, candidate_score=round(score, 4)))
    candidates.sort(key=lambda c: c.candidate_score, reverse=True)
    return candidates[:max_candidates]
