"""China healthcare geography records for the RQ3 case study (unit S12).

The bounded case: when a provincial medical-insurance platform suspends
settlement, the exposure is geographic - every designated hospital and
pharmacy in the province loses networked payment at once. This module
holds the officially verified resource records that quantify that
exposure, and makes the missingness explicit: the registry records only
what was directly verified from official documents; every other
provincial region is named NOT recorded, never imputed.

Records (all verified live 2026-08-29; verbatim quotes and PDF-extraction
output in ``evidence/S12/live-verification.md``):

- CHN national 2023 (National Health Commission 2023 statistical
  bulletin, machine-extracted from the official PDF)
- Beijing 2023 (Beijing 2023 health development statistical bulletin,
  machine-extracted from the official PDF)
- Yunnan 2023 (Yunnan Daily reporting provincial health-commission
  statistics; the commission's own 2024 bulletin PDF was unreachable -
  SSL handshake failure - so the newspaper-of-record citation is used)

Comparability caveats (recorded per record, never smoothed over):

- Beijing reports AUTHORIZED beds (编制床位) and beds per 1,000 as
  authorized; the national bulletin reports total institutions' beds.
  These are different measures and are NOT pooled into one comparison.
- Yunnan's latest verified record year (2023) PREDATES the registry's
  episodes (2024+): the exposure report states the record year next to
  the numbers rather than implying they are at-episode-year figures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macropulse.case_study.episodes import Episode
from macropulse.scope import EVIDENCE_LABELS

RECORD_EVIDENCE_LABEL = "external"

# Closed metric vocabulary. Each metric's measure is pinned so records
# with different underlying measures cannot be silently pooled.
PROVINCIAL_METRICS = (
    "institutions",  # medical & health institutions (count)
    "beds",  # total institution beds (count); see notes for authorized vs actual
    "beds_per_1000",  # beds per 1,000 population; see notes for the measure
)

# China's 31 provincial-level divisions (NHC bulletin coverage; HK/MO/TW
# are reported separately in source publications and are out of scope).
# This is the closed region vocabulary for named missingness.
PROVINCES = (
    "Beijing",
    "Tianjin",
    "Hebei",
    "Shanxi",
    "Inner Mongolia",
    "Liaoning",
    "Jilin",
    "Heilongjiang",
    "Shanghai",
    "Jiangsu",
    "Zhejiang",
    "Anhui",
    "Fujian",
    "Jiangxi",
    "Shandong",
    "Henan",
    "Hubei",
    "Hunan",
    "Guangdong",
    "Guangxi",
    "Hainan",
    "Chongqing",
    "Sichuan",
    "Guizhou",
    "Yunnan",
    "Shaanxi",
    "Gansu",
    "Qinghai",
    "Ningxia",
    "Xinjiang",
    "Tibet",
)

# Case-study subset of the panel (RQ3 scope: a bounded case, not the
# whole panel).
CASE_STUDY_COUNTRIES = ("CHN",)


@dataclass(frozen=True)
class ResourceRecord:
    """One officially verified healthcare-resource figure for one region.

    Citation fields (source_name, source_title, source_url, published)
    are mandatory, same rule as episodes: a number without a source is a
    fabrication. ``notes`` records measure-definition caveats.
    """

    region: str  # province name, or "CHN" for the national record
    metric: str  # PROVINCIAL_METRICS
    value: float
    year: int
    source_name: str
    source_title: str
    source_url: str
    published: date
    notes: str = ""
    evidence_label: str = RECORD_EVIDENCE_LABEL

    def __post_init__(self) -> None:
        if self.metric not in PROVINCIAL_METRICS:
            raise ValueError(f"metric {self.metric!r} not in {PROVINCIAL_METRICS}")
        if self.region != "CHN" and self.region not in PROVINCES:
            raise ValueError(f"unknown region: {self.region!r}")
        if self.value <= 0:
            raise ValueError(f"{self.region} {self.metric}: value must be positive")
        if not (2010 <= self.year <= 2030):
            raise ValueError(
                f"{self.region} {self.metric}: implausible year {self.year}"
            )
        for field_name in ("source_name", "source_title", "source_url"):
            value = getattr(self, field_name)
            if not value or not value.strip():
                raise ValueError(
                    f"{self.region} {self.metric}: {field_name} citation is "
                    "mandatory - an uncited figure is a fabrication"
                )
        if self.source_url and not self.source_url.startswith(("http://", "https://")):
            raise ValueError(f"{self.region} {self.metric}: source_url must be http(s)")
        if self.evidence_label not in EVIDENCE_LABELS:
            raise ValueError(
                f"{self.region} {self.metric}: evidence_label "
                f"{self.evidence_label!r} not in the S01 vocabulary"
            )
        if self.evidence_label != RECORD_EVIDENCE_LABEL:
            raise ValueError(
                f"{self.region} {self.metric}: case-study records are external "
                f"documents - label must be {RECORD_EVIDENCE_LABEL!r}"
            )


# --- verified records (live, 2026-08-29) --------------------------------------

_NHC_2023_URL = (
    "https://www.nhc.gov.cn/wjw/c100178/202408/"
    "1de460738f81464280e9ed3277630e33/files/1734002454304_67772.pdf"
)
_BJ_2023_URL = "http://www.phic.org.cn/tjsj/wstjgb/202408/P020240819586687344254.pdf"
_YNDAILY_URL = "https://www.yndaily.com/html/2024/yaowenyunnan_0925/129208.html"

VERIFIED_RECORDS: tuple[ResourceRecord, ...] = (
    # National 2023, NHC 2023 statistical bulletin (PDF text extraction):
    # "2023年末，全国医疗卫生机构总数 1070785 个" / "全国医疗卫生机构床位
    # 1017.4 万张" / "每千人口医疗卫生机构床位数由 2022 年 6.92 张增加到
    # 2023 年 7.23 张"
    ResourceRecord(
        region="CHN",
        metric="institutions",
        value=1_070_785,
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="National total, all medical & health institutions.",
    ),
    ResourceRecord(
        region="CHN",
        metric="beds",
        value=10_174_000,  # 1017.4 万张
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="National total institution beds (床位), not authorized beds.",
    ),
    ResourceRecord(
        region="CHN",
        metric="beds_per_1000",
        value=7.23,
        year=2023,
        source_name="National Health Commission (China)",
        source_title="2023年我国卫生健康事业发展统计公报",
        source_url=_NHC_2023_URL,
        published=date(2024, 8, 26),
        notes="Beds per 1,000 population, total institution beds (2022: 6.92).",
    ),
    # Beijing 2023, Beijing 2023 health development statistical bulletin
    # (PDF text extraction): "机构数达 12518 家" / "全市医疗机构编制床位总数达
    # 149971 张" / "每千常住人口医疗机构编制床位 6.87 张"
    ResourceRecord(
        region="Beijing",
        metric="institutions",
        value=12_518,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes="Medical & health institutions incl. 12,298 medical institutions.",
    ),
    ResourceRecord(
        region="Beijing",
        metric="beds",
        value=149_971,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes="AUTHORIZED beds (编制床位); actual beds (实有) 138,825.",
    ),
    ResourceRecord(
        region="Beijing",
        metric="beds_per_1000",
        value=6.87,
        year=2023,
        source_name="Beijing Municipal Health Commission",
        source_title="2023年北京市卫生健康事业发展统计公报",
        source_url=_BJ_2023_URL,
        published=date(2024, 8, 19),
        notes=(
            "AUTHORIZED beds per 1,000 permanent residents (编制); actual "
            "(实有) 6.35. Not comparable to the national total-bed rate."
        ),
    ),
    # Yunnan 2023, Yunnan Daily (2024-09-25) reporting provincial health
    # statistics: "截至2023年，全省共有医疗卫生机构28765个、医疗卫生机构
    # 拥有床位数35.99万张"
    ResourceRecord(
        region="Yunnan",
        metric="institutions",
        value=28_765,
        year=2023,
        source_name="Yunnan Daily (reporting provincial health-commission data)",
        source_title="筑基强本守护人民健康",
        source_url=_YNDAILY_URL,
        published=date(2024, 9, 25),
        notes=(
            "Province-wide institutions. The commission's own 2024 bulletin "
            "PDF was unreachable (SSL handshake failure) - not recorded."
        ),
    ),
    ResourceRecord(
        region="Yunnan",
        metric="beds",
        value=359_900,  # 35.99 万张
        year=2023,
        source_name="Yunnan Daily (reporting provincial health-commission data)",
        source_title="筑基强本守护人民健康",
        source_url=_YNDAILY_URL,
        published=date(2024, 9, 25),
        notes="Province-wide institution beds; includes 275,778 hospital beds.",
    ),
)


def recorded_regions(records: tuple[ResourceRecord, ...]) -> list[str]:
    """Regions with at least one verified record (national excluded)."""
    return sorted({r.region for r in records if r.region in PROVINCES})


def unrecorded_provinces(records: tuple[ResourceRecord, ...]) -> list[str]:
    """Provinces with NO verified record - named missingness.

    The registry records only what was directly verified; every other
    province is explicitly listed here rather than imputed, estimated,
    or silently omitted.
    """
    recorded = set(recorded_regions(records))
    return [p for p in PROVINCES if p not in recorded]


@dataclass(frozen=True)
class ExposureReport:
    """What one episode window suspends, per the verified records.

    ``record_year`` is carried alongside the figures so the report never
    implies the exposure numbers are at-episode-year values.
    """

    episode_id: str
    region: str
    institutions: int | None
    beds: int | None
    record_year: int | None
    record_sources: tuple[str, ...]


def exposure_report(
    episode: Episode,
    records: tuple[ResourceRecord, ...] = VERIFIED_RECORDS,
) -> ExposureReport:
    """Resource exposure of an episode: the latest verified records for
    the episode's region, explicitly dated (record year vs episode year).

    The episode's region is matched against provincial records only; a
    region with no verified records returns None values with the sources
    that were searched - missingness named, never guessed.
    """
    matching = [r for r in records if r.region == episode.region]
    latest_year = max((r.year for r in matching), default=None)
    latest = [r for r in matching if r.year == latest_year] if latest_year else []

    def metric_value(metric: str) -> int | None:
        for record in latest:
            if record.metric == metric:
                return int(record.value)
        return None

    sources = tuple(
        sorted({f"{r.source_name} ({r.source_title}, {r.year})" for r in latest})
    )
    return ExposureReport(
        episode_id=episode.episode_id,
        region=episode.region,
        institutions=metric_value("institutions"),
        beds=metric_value("beds"),
        record_year=latest_year,
        record_sources=sources,
    )


__all__ = [
    "CASE_STUDY_COUNTRIES",
    "PROVINCES",
    "PROVINCIAL_METRICS",
    "RECORD_EVIDENCE_LABEL",
    "VERIFIED_RECORDS",
    "ExposureReport",
    "ResourceRecord",
    "exposure_report",
    "recorded_regions",
    "unrecorded_provinces",
]
