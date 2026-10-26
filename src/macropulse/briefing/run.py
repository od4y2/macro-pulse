"""Persistence of briefing runs and their claims (unit S16).

One ``briefing_runs`` row per generation attempt (S03 schema): the
generator identity (``model``) and ``prompt_version`` are recorded so
provenance of the prose survives the run. Rejected claims are persisted
with ``validated=False`` - the audit trail of what was attempted and
refused, not just what passed.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from macropulse.briefing.claims import Adjudication, Claim
from macropulse.db.models import BriefingClaim, BriefingRun

# Recorded generator identities. The S16 generator is deterministic
# templates - the row says so honestly. An LLM prose source (briefing/
# llm.py) records its own identifier under the same schema; when the LLM
# path fails its gates, the run falls back to the deterministic document
# and records that identity with status "fallback".
DETERMINISTIC_MODEL = "deterministic-template"
DETERMINISTIC_PROMPT_VERSION = "s16-v1"

# Closed vocabulary for the status column (String(16)): "completed" is a
# successful run of whatever generator the model column names;
# "fallback" marks a run whose document came from the deterministic
# templates because the requested generator could not be used or failed.
BRIEFING_STATUSES = ("completed", "fallback")


def record_briefing_run(
    session: Session,
    *,
    model: str,
    prompt_version: str,
    adjudicated: list[tuple[Claim, Adjudication]],
    status: str = "completed",
) -> int:
    """Persist one run and all its claims; return the run id.

    ``model`` and ``prompt_version`` must fit their schema columns
    (128 / 32 chars) - a truncated generator identity would be a
    corrupted audit record, so over-long values raise instead.
    ``status`` comes from the closed ``BRIEFING_STATUSES`` vocabulary.
    """
    if len(model) > 128:
        raise ValueError(f"model {model!r} exceeds the 128-char column")
    if len(prompt_version) > 32:
        raise ValueError(
            f"prompt_version {prompt_version!r} exceeds the 32-char column"
        )
    if status not in BRIEFING_STATUSES:
        raise ValueError(f"status {status!r} outside {BRIEFING_STATUSES}")

    run = BriefingRun(model=model, prompt_version=prompt_version, status=status)
    session.add(run)
    session.flush()  # allocate run.id before the claims reference it
    for claim, adjudication in adjudicated:
        session.add(
            BriefingClaim(
                briefing_run_id=run.id,
                claim_text=claim.text,
                evidence_refs=[ref.model_dump() for ref in claim.refs],
                validated=adjudication.validated,
            )
        )
    session.commit()
    return run.id
