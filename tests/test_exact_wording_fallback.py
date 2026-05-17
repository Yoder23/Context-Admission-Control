from __future__ import annotations

from cac.core.schemas import SourceItem, SourceType, RequiredEvidenceSlot
from cac.core.slots import item_matches_slot


def test_no_gold_exact_wording_fallback_uses_text_cues() -> None:
    item = SourceItem(
        source_id="email_1",
        account_id="acct",
        entity="Acme",
        source_type=SourceType.EMAIL,
        title="Executive renewal email",
        text="VP Operations wrote: We cannot recommend renewal unless the outage is resolved.",
        freshness_days=2,
        authority=0.88,
        topics=["executive", "renewal"],
        risk_tags=["customer_unhappy"],
        # Gold labels intentionally set to misleading values; slot matching must not depend on them.
        gold_exact_required=False,
        gold_slots=[],
    )
    slot = RequiredEvidenceSlot(
        name="executive_signal",
        source_types=(SourceType.EMAIL,),
        all_topics=("executive", "renewal"),
        exact_wording_required=True,
        description="Executive wording required.",
    )
    assert item_matches_slot(item, slot)
