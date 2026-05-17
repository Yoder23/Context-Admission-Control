
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .schemas import EvidencePacket


def packet_brief(packet: EvidencePacket) -> Dict[str, Any]:
    return {
        "method": packet.method,
        "tokens": packet.budget_used.get("context_tokens", 0),
        "sources_admitted": packet.budget_used.get("sources_admitted", 0),
        "structured_facts": len(packet.structured_facts),
        "summaries": len(packet.summaries),
        "exact_evidence": len(packet.exact_evidence),
        "conflicts": len(packet.conflicts),
        "uncertainties": len(packet.uncertainties),
        "filled_slots": packet.filled_slots,
        "missing_slots": packet.missing_slots,
    }
