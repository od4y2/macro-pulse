"""Validated facts JSON for the structured AI briefing (unit S16).

``BriefingFacts`` is the ONLY input prose may derive from (S01 non-claim:
"AI-generated prose derives only from validated structured inputs"). It is
built from observation dicts exactly as served by the S13 query service
(the ``ObservationOut`` shape) and partitions them so a statement can
never present non-real evidence as observed:

- ``facts``: real-evidence observations with a value - the only things a
  briefing may state;
- ``missing``: real-evidence observations whose value is NULL
  (missingness is surfaced as availability statements, never hidden);
- ``excluded``: observations whose evidence label is not ``real``
  (mocked/synthetic/cached/external) - counted and named in the
  limitations section, never stated as observed.

Construction is itself a rejection gate: duplicate (indicator, country,
period) rows (multiple vintages passed by mistake) and evidence labels
outside the locked vocabulary raise - the caller must pass latest-vintage,
contract-shaped observations.

Everything here is pure: no clock reads, no I/O. The run row records
time; the document does not.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, field_validator

from macropulse.scope import EVIDENCE_LABELS


class BriefingFact(BaseModel):
    """One observed fact with the provenance the service serves."""

    indicator_id: str
    country_iso3: str
    period: str
    value: float
    unit: str
    frequency: str
    vintage: str
    evidence_label: str
    quality_grade: str
    source_system: str
    source_code: str

    @field_validator("period")
    @classmethod
    def _period_is_iso(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"period {v!r} is not an ISO date") from exc
        return v


class MissingObservation(BaseModel):
    """A real-evidence observation whose value is NULL (reason recorded)."""

    indicator_id: str
    country_iso3: str
    period: str
    vintage: str
    missing_reason: str | None
    source_system: str
    source_code: str


class ExcludedObservation(BaseModel):
    """An observation kept out of statements because it is not real."""

    indicator_id: str
    country_iso3: str
    period: str
    evidence_label: str
    vintage: str
    source_system: str
    source_code: str


class BriefingFacts(BaseModel):
    """The validated JSON contract prose derives from."""

    facts: list[BriefingFact]
    missing: list[MissingObservation]
    excluded: list[ExcludedObservation]
    indicator_names: dict[str, str] = {}

    @classmethod
    def from_observations(
        cls,
        observations: list[dict[str, Any]],
        indicator_names: dict[str, str] | None = None,
    ) -> BriefingFacts:
        """Partition served observation dicts into facts/missing/excluded.

        Raises ``ValueError`` on evidence labels outside the locked
        vocabulary or on duplicate (indicator, country, period) rows -
        the briefing needs the latest-vintage view, and a duplicate would
        make the fact ambiguous.
        """
        seen: dict[tuple[str, str, str], str] = {}
        facts: list[BriefingFact] = []
        missing: list[MissingObservation] = []
        excluded: list[ExcludedObservation] = []
        for o in observations:
            label = o["evidence_label"]
            if label not in EVIDENCE_LABELS:
                raise ValueError(
                    f"evidence label {label!r} is outside the locked "
                    f"vocabulary {sorted(EVIDENCE_LABELS)}"
                )
            key = (o["indicator_id"], o["country_iso3"], o["period"])
            if key in seen:
                raise ValueError(
                    f"duplicate (indicator, country, period) {key}: vintages "
                    f"{seen[key]!r} and {o['vintage']!r} - pass latest-vintage "
                    "observations only"
                )
            seen[key] = o["vintage"]
            source = o["source"]
            if label != "real":
                excluded.append(
                    ExcludedObservation(
                        indicator_id=o["indicator_id"],
                        country_iso3=o["country_iso3"],
                        period=o["period"],
                        evidence_label=label,
                        vintage=o["vintage"],
                        source_system=source["system"],
                        source_code=source["code"],
                    )
                )
            elif o["value"] is None:
                missing.append(
                    MissingObservation(
                        indicator_id=o["indicator_id"],
                        country_iso3=o["country_iso3"],
                        period=o["period"],
                        vintage=o["vintage"],
                        missing_reason=o.get("missing_reason"),
                        source_system=source["system"],
                        source_code=source["code"],
                    )
                )
            else:
                facts.append(
                    BriefingFact(
                        indicator_id=o["indicator_id"],
                        country_iso3=o["country_iso3"],
                        period=o["period"],
                        value=o["value"],
                        unit=o["unit"],
                        frequency=o["frequency"],
                        vintage=o["vintage"],
                        evidence_label=label,
                        quality_grade=o["quality_grade"],
                        source_system=source["system"],
                        source_code=source["code"],
                    )
                )
        return cls(
            facts=facts,
            missing=missing,
            excluded=excluded,
            indicator_names=indicator_names or {},
        )

    def indicator_label(self, indicator_id: str) -> str:
        """Human-readable indicator name, falling back to the id."""
        return self.indicator_names.get(indicator_id, indicator_id)
