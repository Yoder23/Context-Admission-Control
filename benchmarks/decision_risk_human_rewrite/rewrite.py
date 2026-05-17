from __future__ import annotations

import random
from dataclasses import replace
from typing import Iterable, List

from cac.core.schemas import AccountDossier, SourceItem

PHRASE_REWRITES = [
    ("green and on track", "stable according to the account owner"),
    ("Invoice is", "The most recent undisputed invoice sits at"),
    ("days overdue", "days past the due date"),
    ("unresolved P1 escalations", "open priority-one incidents"),
    ("termination", "ending the agreement"),
    ("material breach", "material non-compliance"),
    ("approve this exception only until", "grant time-limited approval through"),
    ("daily access review", "daily access evidence review"),
    ("Root cause was", "The underlying cause appears to be"),
    ("customer impact", "customer-facing impact"),
    ("cannot recommend renewal", "will not support renewal"),
    ("no source attached", "without citing a system of record"),
]

TOPIC_DROPS = {"renewal", "status", "risk", "contract", "support", "security"}


def rewrite_text(text: str, rng: random.Random) -> str:
    out = text
    for old, new in PHRASE_REWRITES:
        if old.lower() in out.lower() and rng.random() < 0.75:
            # case-insensitive-ish simple replacement for synthetic text
            out = out.replace(old, new)
            out = out.replace(old.capitalize(), new.capitalize())
    # Add surface variation that should not alter the gold labels.
    if rng.random() < 0.5:
        out = out + " The note is written in abbreviated operational language."
    if rng.random() < 0.35:
        out = "Reviewer note: " + out
    return out


def rewrite_source(item: SourceItem, rng: random.Random) -> SourceItem:
    # Keep gold labels for scoring only, but perturb the observable text/metadata.
    topics = list(item.topics)
    risk_tags = list(item.risk_tags)
    if topics and rng.random() < 0.35:
        topics = [t for t in topics if t not in TOPIC_DROPS] or topics[:1]
    if risk_tags and rng.random() < 0.25:
        risk_tags = risk_tags[:-1]
    return replace(
        item,
        title=rewrite_text(item.title, rng),
        text=rewrite_text(item.text, rng),
        topics=topics,
        risk_tags=risk_tags,
        freshness_days=item.freshness_days + (rng.randint(0, 90) if rng.random() < 0.25 else 0),
    )


def rewrite_dossiers(dossiers: Iterable[AccountDossier], seed: int = 991) -> List[AccountDossier]:
    rng = random.Random(seed)
    rewritten = []
    for dossier in dossiers:
        rewritten.append(
            replace(
                dossier,
                account_id=dossier.account_id + "_rewrite",
                sources=[rewrite_source(src, rng) for src in dossier.sources],
                metadata_mode=dossier.metadata_mode + "+human_rewrite_surface_noise",
            )
        )
    return rewritten
