
from __future__ import annotations

from typing import Tuple

from .schemas import RequiredEvidenceSlot, SourceType, SourceItem, TaskProfile, Representation, EXACT_REPRESENTATIONS


CANONICAL_SLOT_NAMES = (
    "billing_status",
    "support_trend",
    "crm_health_status",
    "contract_renewal_or_termination_terms",
    "executive_sponsor_signal",
    "recent_negative_signal",
)


def renewal_risk_slots(slot_mode: str = "perfect_slots") -> Tuple[RequiredEvidenceSlot, ...]:
    perfect = (
        RequiredEvidenceSlot(
            name="billing_status",
            source_types=(SourceType.BILLING,),
            all_topics=("billing",),
            any_topics=("payment", "overdue", "invoice"),
            description="Current payment status and late-payment pattern.",
        ),
        RequiredEvidenceSlot(
            name="support_trend",
            source_types=(SourceType.SUPPORT,),
            all_topics=("support",),
            any_topics=("escalation", "p1", "renewal", "outage"),
            description="Recent support escalations or negative operational trend.",
        ),
        RequiredEvidenceSlot(
            name="crm_health_status",
            source_types=(SourceType.CRM,),
            all_topics=("crm",),
            any_topics=("health", "renewal", "forecast"),
            description="Account-team stated health status.",
        ),
        RequiredEvidenceSlot(
            name="contract_renewal_or_termination_terms",
            source_types=(SourceType.CONTRACT,),
            any_risk_tags=("termination", "payment_default", "obligation", "cure"),
            exact_wording_required=True,
            description="Contract terms affecting renewal, termination, cure, or payment default.",
        ),
        RequiredEvidenceSlot(
            name="executive_sponsor_signal",
            source_types=(SourceType.EMAIL, SourceType.CALL_NOTE),
            all_topics=("executive sponsor", "renewal"),
            description="Named or implied executive-sponsor sentiment or commitment.",
        ),
        RequiredEvidenceSlot(
            name="recent_negative_signal",
            source_types=(SourceType.BILLING, SourceType.SUPPORT, SourceType.EMAIL, SourceType.CONTRACT),
            any_risk_tags=("operational_signal", "payment_default", "customer_unhappy", "termination"),
            description="Recent high-authority negative signal.",
        ),
    )

    if slot_mode == "perfect_slots":
        return perfect
    if slot_mode == "partial_slots":
        # Missing executive sponsor as an explicit requirement, but other requirements can still pull it in
        # through contradiction/negative-signal checks.
        return tuple(slot for slot in perfect if slot.name != "executive_sponsor_signal")
    if slot_mode == "noisy_slots":
        # Adds noisy optional-ish slot and weakens one topic constraint.
        return perfect + (
            RequiredEvidenceSlot(
                name="security_review_noise",
                source_types=(SourceType.SECURITY, SourceType.INTERNAL_NOTE),
                any_topics=("security", "review"),
                description="Noisy extra requirement that may or may not be relevant.",
            ),
        )
    if slot_mode == "minimal_slots":
        return (
            perfect[0],  # billing
            perfect[2],  # crm
            perfect[3],  # contract exact
        )
    raise ValueError(f"Unknown slot_mode: {slot_mode}")


def item_matches_slot(item: SourceItem, slot: RequiredEvidenceSlot) -> bool:
    if item.source_type not in slot.source_types:
        return False
    item_tags = set(tag.lower() for tag in item.risk_tags)
    item_topics = set(topic.lower() for topic in item.topics)
    any_risk_tags = set(tag.lower() for tag in slot.any_risk_tags)
    all_risk_tags = set(tag.lower() for tag in slot.all_risk_tags)
    any_topics = set(topic.lower() for topic in slot.any_topics)
    all_topics = set(topic.lower() for topic in slot.all_topics)
    # Primary path: metadata matching.
    metadata_ok = (
        (not any_risk_tags or bool(item_tags & any_risk_tags))
        and (not all_risk_tags or all_risk_tags.issubset(item_tags))
        and (not any_topics or bool(item_topics & any_topics))
        and (not all_topics or all_topics.issubset(item_topics))
    )
    if not metadata_ok:
        # Content-based fallback: apply_noise may corrupt topics/risk_tags but
        # never modifies document title or text, so they are noise-immune.
        # Normalize underscores to spaces so compound tags (e.g. "payment_default")
        # match their natural representation in prose ("payment default").
        hay = " ".join([item.title, item.text]).lower()
        norm = lambda kw: kw.lower().replace("_", " ")
        content_ok = (
            (any_risk_tags and any(norm(t) in hay for t in any_risk_tags))
            or (any_topics and any(norm(t) in hay for t in any_topics))
            or (all_topics and any(norm(t) in hay for t in all_topics))
            or (not any_risk_tags and not any_topics and not all_topics)
        )
        if not content_ok:
            return False
    if slot.exact_wording_required:
        if item.source_type != SourceType.CONTRACT and "exact_wording_required" not in item_tags:
            # No-gold fallback for wording-sensitive emails/notes when noisy metadata
            # strips the exact tag. This uses only source text/title/tags.
            hay = " ".join([item.title, item.text, " ".join(item.topics), " ".join(item.risk_tags)]).lower()
            exact_language_cues = (
                "wrote:", "i approve", "approve this", "only until",
                "we cannot recommend", "customer counsel", "we dispute",
                "we will", "commit", "complete owner review",
            )
            if not any(cue in hay for cue in exact_language_cues):
                return False
    return True


def matched_slots(item: SourceItem, profile: TaskProfile) -> list[str]:
    return [slot.name for slot in profile.required_slots if item_matches_slot(item, slot)]


def slot_requires_exact(profile: TaskProfile, slot_name: str) -> bool:
    return any(slot.name == slot_name and slot.exact_wording_required for slot in profile.required_slots)


def representation_satisfies_slot(profile: TaskProfile, slot_name: str, representation: Representation) -> bool:
    if slot_requires_exact(profile, slot_name):
        return representation in EXACT_REPRESENTATIONS
    return True
