"""S16 live demo: a structured briefing over the live service and DB.

Fetches latest-vintage observations from the running S13 query service
(real WB data: 10 economies x 11 years, evidence_label=real), builds
claims, adjudicates them against the validated facts JSON, renders the
document, runs the banned-phrase rejection check on the rendered
output, demonstrates the rejection machinery on deliberately bad
input (a tampered value and a causal sentence), and persists the run
(briefing_runs + briefing_claims) to the dev database, then re-reads
the rows.

Run (service must be up on :8000):

    PYTHONPATH=src .venv/bin/python evidence/S16/live-demo-script.py
"""

from __future__ import annotations

from macropulse.briefing import (
    DETERMINISTIC_MODEL,
    DETERMINISTIC_PROMPT_VERSION,
    BriefingFacts,
    adjudicate,
    adjudicate_all,
    build_claims,
    check_prose,
    record_briefing_run,
    render_briefing,
    render_rejection_report,
)
from macropulse.db.base import make_engine, make_session_factory
from macropulse.db.models import BriefingClaim, BriefingRun
from macropulse.views.client import QueryServiceClient


def step(msg: str) -> None:
    print(f"\n=== {msg} ===")


def main() -> None:
    step("fetch validated facts from the running query service")
    client = QueryServiceClient.from_env()
    health = client.health()
    print("service health:", health)
    assert health.get("status") == "ok" and health.get("data_mode") == "database"

    observations = client.observations(latest_vintage=True)
    indicators = client.indicators()
    names = {i["indicator_id"]: i["name"] for i in indicators}
    print(f"observations served: {len(observations)}; indicators: {sorted(names)}")

    facts = BriefingFacts.from_observations(observations, names)
    print(
        f"facts: {len(facts.facts)} real observations, "
        f"{len(facts.missing)} missing, {len(facts.excluded)} excluded"
    )

    step("build claims and adjudicate against the validated JSON")
    claims = build_claims(facts)
    adjudicated = adjudicate_all(claims, facts)
    kinds = {}
    for c, _ in adjudicated:
        kinds[c.kind] = kinds.get(c.kind, 0) + 1
    print("claims built:", kinds)
    n_valid = sum(1 for _, a in adjudicated if a.validated)
    print(f"validated: {n_valid}/{len(adjudicated)}")

    step("rejection demonstrations (deliberately bad input, clearly labelled)")
    # (a) A tampered level claim: value changed to something not in the JSON.
    level = next(c for c, _ in adjudicated if c.kind == "level")
    tampered_value = level.value + 0.5
    tampered = level.model_copy(
        update={
            "value": tampered_value,
            "text": level.text.replace(repr(level.value), repr(tampered_value)),
        }
    )
    verdict = adjudicate(tampered, facts)
    print(
        f"tampered value claim -> validated={verdict.validated}, reason={verdict.reason}"
    )
    assert verdict.reason == "value_mismatch"

    # (b) A causal sentence attached to an otherwise validated statement.
    causal_sentence = f"{level.text} This happened because growth was broad-based."
    print("causal sentence -> banned:", check_prose(causal_sentence))
    assert check_prose(causal_sentence) == ["causal_phrase"]

    step("render the document and run the banned-phrase check on it")
    document = render_briefing(facts, adjudicated)
    print(document)
    banned = check_prose(document)
    print("\nbanned phrases in rendered document:", banned)
    assert banned == []
    print(render_rejection_report(adjudicated))

    step("persist the run (incl. the rejected tampered claim) and re-read")
    persisted = adjudicated + [(tampered, verdict)]
    factory = make_session_factory(make_engine())
    with factory() as session:
        run_id = record_briefing_run(
            session,
            model=DETERMINISTIC_MODEL,
            prompt_version=DETERMINISTIC_PROMPT_VERSION,
            adjudicated=persisted,
        )
        run = session.get(BriefingRun, run_id)
        assert run is not None
        print(
            f"run {run_id}: model={run.model!r}, "
            f"prompt_version={run.prompt_version!r}, status={run.status!r}"
        )
        rows = (
            session.query(BriefingClaim)
            .filter(BriefingClaim.briefing_run_id == run_id)
            .all()
        )
        n_stored_valid = sum(1 for r in rows if r.validated)
        print(
            f"claims stored: {len(rows)} "
            f"({n_stored_valid} validated, {len(rows) - n_stored_valid} rejected)"
        )
        rejected_row = next(r for r in rows if not r.validated)
        print("a rejected row's evidence_refs:", rejected_row.evidence_refs)
        assert len(rows) == len(persisted)
        assert len(rows) - n_stored_valid == 1

    step("demo complete - prose derived only from validated JSON, with citations")


if __name__ == "__main__":
    main()
