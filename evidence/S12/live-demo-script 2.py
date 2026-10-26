"""S12 live case-study demo - RQ3 payment resilience.

Combines live World Bank data (payment profile half) with the verified
case-study registry (episode half):

  1. payment profiles for the case subset (CHN) plus reference
     economies (KOR, USA) - real data, latest-common-period alignment
     AND the latest-wave profile showing the input asymmetry
  2. the verified Yunnan episode registry
  3. the observation-alignment blind-spot report
  4. the Yunnan resource exposure report

Reproducible: ``PYTHONPATH=src .venv/bin/python evidence/S12/live-demo-script.py``
"""

from datetime import date, datetime

from macropulse.case_study import (
    EPISODES,
    VERIFIED_RECORDS,
    alignment_report,
    exposure_report,
    unrecorded_provinces,
)
from macropulse.case_study.episodes import CHINA_STANDARD_TIME
from macropulse.connectors.worldbank import WorldBankConnector
from macropulse.lenses.payment import Component, build_profile

CASE_SUBSET = ["CHN"]
REFERENCE = ["KOR", "USA"]  # context only, clearly not the case study

SERIES = {
    "digital_payments": "g20.any",
    "health_expenditure": "SH.XPD.CHEX.GD.ZS",
}

wb = WorldBankConnector()

# observed: {country: {key: {year: (value, vintage)}}}
observed: dict[str, dict[str, dict[int, tuple[float, date]]]] = {}
for country in CASE_SUBSET + REFERENCE:
    observed[country] = {}
    for key, code in SERIES.items():
        fetched = wb.fetch_indicator(code, country)
        observed[country][key] = {
            p.period.year: (p.value, p.vintage)
            for p in fetched.points
            if p.value is not None  # drop WB NULL placeholder rows (S11 finding)
        }

print("== payment profiles (real, live WB API, retrieved 2026-08-29) ==")
print(f"{'iso3':5} {'role':10} {'period':7} {'digital_payments':>17} "
      f"{'health_expenditure':>19}  missing")
for country in CASE_SUBSET + REFERENCE:
    role = "case" if country in CASE_SUBSET else "reference"
    waves = observed[country]["digital_payments"]
    # alignment policy 1: latest period where BOTH components are observed
    common = set(waves) & set(observed[country]["health_expenditure"])
    year = max(common)
    profile = build_profile(
        [
            Component(
                key="digital_payments",
                indicator_id="digital_payments_made_pct",
                source_code=SERIES["digital_payments"],
                period=date(year, 1, 1),
                value=waves[year][0],
                missing_reason=None,
                vintage=waves[year][1],
            ),
            Component(
                key="health_expenditure",
                indicator_id="health_expenditure_pct_gdp",
                source_code=SERIES["health_expenditure"],
                period=date(year, 1, 1),
                value=observed[country]["health_expenditure"][year][0],
                missing_reason=None,
                vintage=observed[country]["health_expenditure"][year][1],
            ),
        ],
        country,
    )
    print(f"{country:5} {role:10} {year:<7} {profile.digital_payments!s:>17} "
          f"{profile.health_expenditure!s:>19}  {profile.missing_components or '-'}")

# alignment policy 2: CHN's latest Findex wave (2024) - health expenditure
# has no 2024 observation; the profile must name that, not hide it.
latest_wave = max(observed["CHN"]["digital_payments"])
wave_year = latest_wave
if wave_year not in observed["CHN"]["health_expenditure"]:
    profile = build_profile(
        [
            Component(
                key="digital_payments",
                indicator_id="digital_payments_made_pct",
                source_code=SERIES["digital_payments"],
                period=date(wave_year, 1, 1),
                value=observed["CHN"]["digital_payments"][wave_year][0],
                missing_reason=None,
                vintage=observed["CHN"]["digital_payments"][wave_year][1],
            ),
            Component(
                key="health_expenditure",
                indicator_id="health_expenditure_pct_gdp",
                source_code=SERIES["health_expenditure"],
                period=date(wave_year, 1, 1),
                value=None,
                missing_reason="not_observed_at_period",
                vintage=None,
            ),
        ],
        "CHN",
    )
    print(f"CHN   (wave)    {wave_year:<7} {profile.digital_payments!s:>17} "
          f"{profile.health_expenditure!s:>19}  {profile.missing_components}")

print("\n== verified episode registry (external, citation-backed) ==")
for e in EPISODES:
    print(f"{e.episode_id:26} {e.start:%Y-%m-%d %H:%M} -> {e.end:%m-%d %H:%M} "
          f"{e.duration_hours:>4.0f}h {e.kind}")
    print(f"{'':26} source: {e.source_name} - {e.source_title}")

print("\n== observation alignment (the computed blind spot) ==")
for episode_id, freqs in alignment_report(EPISODES).items():
    for frequency, alignment in freqs.items():
        print(
            f"{episode_id:26} {frequency:10} spanned={str(alignment.periods_spanned):32} "
            f"straddles={str(alignment.boundary_straddled):5} "
            f"share={alignment.duration_share_of_period:.5f} "
            f"resolvable={alignment.resolvable}"
        )

print("\n== resource exposure of the Yunnan episodes (verified records) ==")
for episode in EPISODES:
    report = exposure_report(episode)
    print(
        f"{report.episode_id:26} region={report.region} "
        f"institutions={report.institutions} beds={report.beds} "
        f"(record year {report.record_year}, predates the episode)"
    )

print(f"\nunrecorded provinces (named, never imputed): {len(unrecorded_provinces(VERIFIED_RECORDS))}")
print(f"episode windows are {CHINA_STANDARD_TIME} (China Standard Time, UTC+8, no DST)")
