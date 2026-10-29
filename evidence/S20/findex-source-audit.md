# Source audit: account_ownership_pct (Global Findex)

**Date:** 2026-10-29 · **Question:** does the database hold every survey
year the source publishes, or was a fetch omitted?

**Verdict: no fetch omission.** The sparsity is inherent to the source —
Global Findex is a survey series published in waves (2011 / 2014 / 2017 /
2021 / 2024; MEX uniquely has a 2022 wave instead of 2021). Every
survey-year value the World Bank API publishes for the ten panel
economies is present in the database, byte-identical at full float
precision.

## Method

1. Catalog check (`src/macropulse/catalog.py`): primary source
   `world_bank` code `FX.OWN.TOTL.ZS`, role primary, verified confirmed;
   coverage note "Global Findex survey years only (2011/2014/2017/2021/2024
   waves; re-verified live 2026-08-29)". Female variant `FX.OWN.TOTL.FE.ZS`
   is the fallback.
2. Live source fetch (2026-10-29, World Bank API v2,
   `FX.OWN.TOTL.ZS` for the ten panel ISO3 codes, all available years,
   via the local HTTP proxy): 660 records returned, of which **50 carry a
   value** — exactly 5 survey years per economy.
3. Database comparison (dev Postgres, `normalized_observations` where
   `indicator_id='account_ownership_pct'`): per country 5 valued rows +
   61 rows with `value IS NULL AND missing_reason='wb_missing_value'`,
   all vintage `2026-09-10`. Valued years per country match the live
   fetch exactly, including MEX's 2022; all 50 values match at full
   float precision (**0 mismatches**).

## Survey years observed in the live source (identical in the database)

| ISO | Survey years |
|-----|--------------|
| BRA, CHN, DEU, GBR, IND, JPN, KOR, USA, ZAF | 2011, 2014, 2017, 2021, 2024 |
| MEX | 2011, 2014, 2017, **2022**, 2024 |

Values as returned live (and stored), full precision:

| ISO | Year | FX.OWN.TOTL.ZS (% of adults) |
|-----|------|------------------------------|
| BRA | 2011 | 55.860384771673 |
| BRA | 2014 | 68.123158518616 |
| BRA | 2017 | 70.0439481477435 |
| BRA | 2021 | 84.0357458977852 |
| BRA | 2024 | 86.3811782311541 |
| CHN | 2011 | 63.8173128563221 |
| CHN | 2014 | 78.9652608494559 |
| CHN | 2017 | 79.5313410701405 |
| CHN | 2021 | 88.7090216844445 |
| CHN | 2024 | 89.3830319754266 |
| DEU | 2011 | 98.1336173269525 |
| DEU | 2014 | 98.7604066823874 |
| DEU | 2017 | 99.14118600163 |
| DEU | 2021 | 99.9765938161833 |
| DEU | 2024 | 98.2983235670699 |
| GBR | 2011 | 97.201284899645 |
| GBR | 2014 | 98.9310547976756 |
| GBR | 2017 | 96.366318852125 |
| GBR | 2021 | 99.7632738299911 |
| GBR | 2024 | 99.2843092777584 |
| IND | 2011 | 35.2318385316409 |
| IND | 2014 | 53.1415500480136 |
| IND | 2017 | 79.8753284971461 |
| IND | 2021 | 77.5291370626274 |
| IND | 2024 | 89.0248224502547 |
| JPN | 2011 | 96.4220483126666 |
| JPN | 2014 | 96.6455822293813 |
| JPN | 2017 | 98.2433920065994 |
| JPN | 2021 | 98.4894200399726 |
| JPN | 2024 | 98.5235592091779 |
| KOR | 2011 | 93.0468690333371 |
| KOR | 2014 | 94.3608135378731 |
| KOR | 2017 | 94.8510126919781 |
| KOR | 2021 | 98.6713470938187 |
| KOR | 2024 | 96.8949448884961 |
| MEX | 2011 | 27.4293831561048 |
| MEX | 2014 | 39.1408431572041 |
| MEX | 2017 | 36.0417666941178 |
| MEX | 2022 | 48.9714753743921 |
| MEX | 2024 | 53.0320833316729 |
| USA | 2011 | 87.9578658638029 |
| USA | 2014 | 93.5838007921263 |
| USA | 2017 | 93.1221843138765 |
| USA | 2021 | 94.9532296473716 |
| USA | 2024 | 97.0230983290589 |
| ZAF | 2011 | 53.6450756317438 |
| ZAF | 2014 | 70.3174554981439 |
| ZAF | 2017 | 69.2184941645761 |
| ZAF | 2021 | 85.378111952418 |
| ZAF | 2024 | 81.1259662052011 |

## What changed in the chart layer (this audit's fix)

With `connectgaps=False`, a line-only Plotly trace draws **nothing** for
a series whose every observed point is isolated by gaps — the Findex
shape rendered as a blank chart despite 5 real observations. Fix (no
data touched, presentation only):

- `isolated_point_indices` (pure, `src/macropulse/views/assembly.py`):
  an observed point whose grid neighbours are both missing is isolated;
  isolated points additionally render as markers in the series color.
  Gaps stay gaps — nothing interpolated, nothing zero-filled.
- `missingness_note` (pure, `src/macropulse/views/labels.py`): caption
  under every chart separating **source-confirmed gaps** (row exists,
  value NULL, `missing_reason` named — the non-survey years) from
  **unrecorded grid periods** (no row at all — expected but missing).
  For this indicator every panel country reads: 5 observed periods,
  61 source-confirmed `wb_missing_value` gaps, 0 unrecorded periods.
- `coverage_counts` splits `missing` into `source_no_data` + `no_record`
  (sums back to `missing`); the comparison view shows the split.

Live-verified via AppTest on the served figure JSON: BRA country view
carries modes `['lines','markers']` with marker xs exactly
`2011/2014/2017/2021/2024` at the values above; MEX markers include
`2022-01-01` and exclude `2021-01-01`; dense series (e.g.
internet_users_pct) stay `['lines']` only.

## Cloud confirmation (2026-10-29, after push of this fix)

Push: `ecdbc31..e15bc62` on `main` (remote HEAD verified via
`git ls-remote`); the live SCC app tracks `main` and redeploys
automatically. Verified from the CLI:

- **Production data (Neon, `neondb`)** — queried live via the Neon API:
  `account_ownership_pct` carries exactly 5 valued survey-year rows per
  economy (2011/2014/2017/2021/2024; MEX 2011/2014/2017/**2022**/2024)
  plus 61 `wb_missing_value` rows each, all vintage `2026-09-10` — the
  exact points the new marker traces render, identical to the dev DB and
  the live WB fetch above.
- **App reachable** — `GET https://macro-pulse-hl.streamlit.app/` → 200
  serving the Streamlit shell (9782 bytes, same as the 2026-10-16
  verification); the `/_stcore/stream` endpoint answers upgrade requests.
- **Rendering path** — the cloud runs the same `app/dashboard.py`
  against the same Neon data whose output was asserted byte-level via
  AppTest above (marker xs/values, missingness note, coverage split);
  690 tests green excluding the macOS duplicate copies, ruff clean.

What the CLI cannot do (documented so the gap is explicit, not
implied): SCC now fronts anonymous sessions with the share.streamlit.io
browser flow — health returns the static shell instead of `ok` for
non-browser clients, and the websocket upgrade never completes
(`101` without `Sec-WebSocket-Accept`, HTML body instead of frames; the
official public 30-days app behaves identically from this network, so
this is edge behavior, not app state). The final human-eye confirmation
is opening the app in a browser: Country view defaults to BRA +
account_ownership_pct — the chart must show five markers at the survey
years listed above, with the missingness note beneath.
