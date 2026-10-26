"""On-demand AI briefing endpoints (the S16 pipeline behind the service).

``POST /briefing`` generates one country's briefing from that country's
latest-vintage observations: the deterministic S16 pipeline runs first
(facts -> claims -> adjudication), the LLM prose source is tried on top
of the validated claims, and the deterministic template document is the
guaranteed fallback (``briefing/generate.py``). Every attempt appends a
``briefing_runs`` audit row; ``GET /briefing/{run_id}`` reads one back.

The dashboard never touches the database or the LLM directly (S14
invariant) - it is a thin client of these endpoints. The LLM prose
source is injected via ``app.state.llm_source_factory`` (set by
``create_app``); when unset, the generator resolves ``LLM_*`` from the
environment at call time and falls back, honestly, when absent.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session, selectinload

from macropulse.api.deps import DbSession
from macropulse.api.routes import (
    _observation_out,
    latest_vintage_condition,
    latest_vintage_subquery,
)
from macropulse.api.schemas import (
    BriefingClaimOut,
    BriefingGenerateOut,
    BriefingGenerateRequest,
    BriefingOut,
    FactRefOut,
)
from macropulse.briefing import generate_briefing
from macropulse.db.models import (
    BriefingRun,
    Country,
    Indicator,
    NormalizedObservation,
    SourceCatalogEntry,
)

router = APIRouter(prefix="/briefing", tags=["briefing"])


def latest_observation_rows(
    db: Session, country_iso3: str
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """One country's latest-vintage observations in the wire shape.

    Rows are serialized through the pinned ``ObservationOut`` schema
    (``model_dump(mode="json")``) - exactly the contract shape
    ``BriefingFacts.from_observations`` consumes - so the briefing is
    built from what the service serves, never from a private read path.
    Also returns ``{indicator_id: name}`` for human-readable claims.
    """
    filters = [NormalizedObservation.country_iso3 == country_iso3]
    latest_sq = latest_vintage_subquery(db, filters)
    query = (
        db.query(NormalizedObservation, SourceCatalogEntry)
        .join(
            SourceCatalogEntry,
            NormalizedObservation.source_id == SourceCatalogEntry.id,
        )
        .filter(*filters)
        .join(latest_sq, latest_vintage_condition(latest_sq))
        .order_by(
            NormalizedObservation.indicator_id,
            NormalizedObservation.period,
            NormalizedObservation.id,
        )
    )
    rows = [
        _observation_out(obs, src).model_dump(mode="json") for obs, src in query
    ]
    names = dict(db.query(Indicator.indicator_id, Indicator.name).all())
    return rows, names


def _briefing_out(run: BriefingRun) -> BriefingOut:
    """Serialize one run with its claims in insertion order."""
    claims = sorted(run.claims, key=lambda c: c.id)
    return BriefingOut(
        id=run.id,
        created_at=run.created_at,
        model=run.model,
        prompt_version=run.prompt_version,
        status=run.status,
        claims=[
            BriefingClaimOut(
                claim_text=claim.claim_text,
                evidence_refs=[FactRefOut(**ref) for ref in claim.evidence_refs],
                validated=claim.validated,
            )
            for claim in claims
        ],
    )


def _load_run(db: Session, run_id: int) -> BriefingRun:
    run = (
        db.query(BriefingRun)
        .options(selectinload(BriefingRun.claims))
        .filter(BriefingRun.id == run_id)
        .one_or_none()
    )
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown briefing run: {run_id}")
    return run


@router.post("", response_model=BriefingGenerateOut)
def generate_briefing_endpoint(
    payload: BriefingGenerateRequest,
    db: DbSession,
    request: Request,
) -> BriefingGenerateOut:
    """Generate one country's briefing on demand; always answers.

    Unknown countries are 404 (house convention). A facts-contract
    violation (duplicate observation identity, out-of-vocabulary label)
    surfaces as 422 - an ambiguous fact is not a fact. LLM failures are
    NOT errors: the deterministic document returns with ``status``
    ``"fallback"`` and a ``warning`` naming the reason.
    """
    country = db.get(Country, payload.country_iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"unknown country: {payload.country_iso3}",
        )

    rows, names = latest_observation_rows(db, payload.country_iso3)
    db.commit()  # end the read transaction BEFORE the (slow) LLM call

    factory = getattr(request.app.state, "llm_source_factory", None)
    llm_source = factory() if factory is not None else None

    try:
        outcome = generate_briefing(
            db,
            payload.country_iso3,
            rows,
            indicator_names=names,
            llm_source=llm_source,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    assert outcome.run_id is not None  # record_run defaults to True
    run = _load_run(db, outcome.run_id)
    return BriefingGenerateOut(
        **_briefing_out(run).model_dump(),
        country_iso3=payload.country_iso3,
        prose=outcome.prose,
        used_llm=outcome.used_llm,
        warning=outcome.warning,
    )


@router.get("/{run_id}", response_model=BriefingOut)
def get_briefing_run(run_id: int, db: DbSession) -> BriefingOut:
    """Read one persisted run: identity, status, and adjudicated claims."""
    return _briefing_out(_load_run(db, run_id))
