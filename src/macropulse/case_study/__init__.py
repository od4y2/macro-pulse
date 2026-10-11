"""Bounded case-study machinery for RQ3 (unit S12).

The payment-resilience case study: verified payment-outage episodes and
healthcare-resource records, citation-mandatory, external-labelled.
The lens profile itself is in ``macropulse.lenses.payment``.
"""

from macropulse.case_study.china_health import (
    CASE_STUDY_COUNTRIES,
    PROVINCES,
    PROVINCIAL_METRICS,
    VERIFIED_RECORDS,
    ExposureReport,
    ResourceRecord,
    exposure_report,
    recorded_regions,
    unrecorded_provinces,
)
from macropulse.case_study.episodes import (
    EPISODE_EVIDENCE_LABEL,
    EPISODE_KINDS,
    EPISODES,
    Episode,
    ObservationAlignment,
    alignment_report,
    episodes_in_window,
    observation_alignment,
    outage_hours_by_year,
    validate_registry,
)

__all__ = [
    "CASE_STUDY_COUNTRIES",
    "EPISODES",
    "EPISODE_EVIDENCE_LABEL",
    "EPISODE_KINDS",
    "PROVINCES",
    "PROVINCIAL_METRICS",
    "VERIFIED_RECORDS",
    "Episode",
    "ExposureReport",
    "ObservationAlignment",
    "ResourceRecord",
    "alignment_report",
    "episodes_in_window",
    "exposure_report",
    "observation_alignment",
    "outage_hours_by_year",
    "recorded_regions",
    "unrecorded_provinces",
    "validate_registry",
]
