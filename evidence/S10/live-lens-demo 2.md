# S10 live lens demonstration (2026-08-29)

Real data (WB + ILOSTAT live APIs, evidence_label `real`, external
sources) assembled into full-component RQ1 profiles. The script aligned
each country to the latest period covered by all three series (WB
unemployment runs one year ahead of ILOSTAT NEET - 2025 vs 2024; live
finding, not an assumption).

```
USA 2025-01-01: headline=4.198 youth=9.34 neet=11.59 gap=5.1pp
     neet-unemp=7.4pp missing=['enrollment']
ZAF 2024-01-01: headline=32.279 youth=60.248 neet=34.61 gap=28.0pp
     neet-unemp=2.3pp missing=['enrollment']
BRA 2025-01-01: headline=5.97 youth=13.981 neet=18.703 gap=8.0pp
     neet-unemp=12.7pp missing=['enrollment']
```

Manual inspection notes (provenance / labels / claims boundaries):

- **Provenance preserved**: each component carries its own source and
  vintage (WB: unemployment/youth from SL.UEM.TOTL.ZS / SL.UEM.1524.ZS;
  ILOSTAT: NEET from DF_EIP_NEET_SEX_RT). Mixed sources in one profile
  are legitimate - identities are per component, never blended.
- **Alignment is honest**: ZAF shows 2024 (ILOSTAT's latest), not a
  blended 2024/2025 view. USA and BRA show 2025 only because their NEET
  runs to 2025.
- **Missingness named, not hidden**: enrollment is unfetched in this
  demo (`component_not_fetched`); the profile reports it rather than
  degrading silently.
- **Reading the numbers (descriptive only)**: the USA gap (5.1pp) vs the
  ZAF gap (28.0pp) at very different levels is exactly why gap AND ratio
  are both reported. ZAF's small `neet_minus_unemployed` (2.3pp) says
  ZAF youth disengagement is mostly *unemployed* (actively seeking), not
  withdrawn - a different labor market than the headline-adjacent gap
  suggests. BRA's 12.7pp excess points the other way. No causal or
  welfare claim is made; these are arithmetic relationships on observed
  values, per the S01 non-claims boundary.
- A live boundary case surfaced during the demo: misaligned periods
  (fetching each series' LATEST point, then keeping only those at the
  common period) produced `headline=None` for ZAF and the profile
  correctly returned no relationships rather than fabricating any - the
  lens rules held on real data.
