"""S11 live lens demo - RQ2 digital reach & inclusion.

Fetches internet / mobile / account / female-account / GDP-per-capita-PPP
from the live World Bank API for a 10-economy panel, builds one
DigitalProfile per country at the latest period where all four lens
dimensions are OBSERVED (NULL placeholder rows dropped), then reports:

  1. the panel (levels + both documented relationships)
  2. Spearman rank covariation of reach vs income per adult GDP
  3. measurement gaps per dimension (as_of 2026)

Reproducible: ``PYTHONPATH=src .venv/bin/python evidence/S11/live-demo-script.py``
"""

from datetime import date

from macropulse.connectors.worldbank import WorldBankConnector
from macropulse.lenses.digital import (
    Component,
    LENS_INDICATORS,
    build_profile,
    measurement_gap,
    rank_covariation,
)

COUNTRIES = ["USA", "CHN", "JPN", "DEU", "GBR", "IND", "BRA", "KOR", "ZAF", "MEX"]
SERIES = {
    "internet": "IT.NET.USER.ZS",
    "mobile": "IT.CEL.SETS.P2",
    "account": "FX.OWN.TOTL.ZS",
    "account_female": "FX.OWN.TOTL.FE.ZS",
}
INCOME = "NY.GDP.PCAP.PP.KD"

wb = WorldBankConnector()

# observed: {(country, key): {year: (value, vintage)}}
observed: dict[tuple[str, str], dict[int, tuple[float, date]]] = {}
for country in COUNTRIES:
    for key, code in SERIES.items():
        fetched = wb.fetch_indicator(code, country)
        points = sorted(fetched.points, key=lambda p: p.period)
        years = {
            p.period.year: (p.value, p.vintage)
            for p in points
            if p.value is not None
        }
        observed[(country, key)] = years
        null_rows = sum(1 for p in points if p.value is None)
        if null_rows and country == "USA":
            print(f"[note] {code} USA: {null_rows} NULL placeholder rows dropped")

gdp: dict[str, float] = {}
for country in COUNTRIES:
    fetched = wb.fetch_indicator(INCOME, country)
    by_year = {p.period.year: p.value for p in fetched.points if p.value is not None}
    gdp[country] = by_year

print("\n== panel (aligned to latest period with all four dimensions observed) ==")
print(f"{'iso3':4} {'period':7} {'internet':>9} {'mobile':>7} {'account':>8} "
      f"{'female':>7} {'acct-int':>8} {'gender':>7}")
panel_rows = []
for country in COUNTRIES:
    year_sets = [set(observed[(country, k)].keys()) for k in SERIES]
    common = set.intersection(*year_sets)
    period_year = max(common)
    comps = []
    for ind_id, key in LENS_INDICATORS.items():
        value, vintage = observed[(country, key)][period_year]
        comps.append(Component(
            key=key, indicator_id=ind_id, source_code=SERIES[key],
            period=date(period_year, 1, 1), value=value,
            missing_reason=None, vintage=vintage,
        ))
    value, vintage = observed[(country, "account_female")][period_year]
    comps.append(Component(
        key="account_female", indicator_id=None, source_code=SERIES["account_female"],
        period=date(period_year, 1, 1), value=value,
        missing_reason=None, vintage=vintage,
    ))
    profile = build_profile(comps, country)
    income = gdp[country].get(period_year)
    panel_rows.append((country, profile, income))
    print(f"{country:4} {period_year:<7} {profile.internet!s:>9} "
          f"{profile.mobile!s:>7} {profile.account!s:>8} {profile.account_female!s:>7} "
          f"{profile.account_internet_gap!s:>8} {profile.gender_account_gap!s:>7}")

complete = [r for r in panel_rows if r[2] is not None]
print("\n== rank covariation vs GDP per capita PPP (same aligned year) ==")
accounts = [r[1].account for r in complete]
internets = [r[1].internet for r in complete]
incomes = [r[2] for r in complete]
rho_account, n_a = rank_covariation(accounts, incomes)
rho_internet, n_i = rank_covariation(internets, incomes)
print(f"account   vs gdp_pc: rho={rho_account:+.2f} (n={n_a})")
print(f"internet  vs gdp_pc: rho={rho_internet:+.2f} (n={n_i})")

print("\n== measurement gaps (panel-union observed years, as_of 2026) ==")
observed_years = {key: set() for key in SERIES}
for (country, key), years in observed.items():
    observed_years[key] |= set(years.keys())
gaps = measurement_gap(
    {k: sorted(v) for k, v in observed_years.items()}, as_of=2026
)
for key in SERIES:
    g = gaps[key]
    print(f"{key:16} last_observed={g.last_observed} years_since={g.years_since}")
