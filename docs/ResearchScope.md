# Research Scope (locked in S01, 2026-08-19)

This document is the human-readable statement of the locked research scope.
The machine-readable source of truth is `src/macropulse/scope.py`; both were
locked together and must stay in sync.

## Country panel (ten representative economies)

Balanced global set chosen to include the FRED benchmark economy, the major
emerging economies, and coverage across four continents. All ten are covered
by FRED mirrors, the World Bank API, and ILOSTAT.

| ISO3 | Economy | Inclusion rationale |
|---|---|---|
| USA | United States | FRED home turf; benchmark economy |
| CHN | China | Second-largest economy; vintage and methodology breaks |
| JPN | Japan | Developed, aging, deflation case study |
| DEU | Germany | EU anchor; energy-shock episode |
| GBR | United Kingdom | Post-Brexit labor market measurement |
| IND | India | Largest emerging economy; youth transition lens |
| BRA | Brazil | Latin America; commodity-cycle economy |
| KOR | South Korea | Advanced digital economy benchmark |
| ZAF | South Africa | African economy; high structural unemployment |
| MEX | Mexico | Nearshoring and remittances case |

## Research questions

- **RQ1 (labor slack and youth transitions, S10).** How do youth unemployment,
  NEET, and school-to-work transition indicators diverge from headline
  unemployment across the panel, and how does that divergence change across
  data vintages?
- **RQ2 (digital reach and inclusion, S11).** How do internet, mobile, and
  account-ownership rates co-vary with income and gender across the panel, and
  where do measurement gaps hide digital exclusion?
- **RQ3 (payment resilience and healthcare, S12).** What do payment-outage
  episodes reveal about resilience measurement in digitized healthcare systems,
  for the case-study subset of the panel?
- **RQ4 (vintage and revision transparency, S07).** Where do official release
  calendars, revisions, and methodology breaks create systematic blind spots
  in cross-country comparison?

RQ3 is explicitly a case study: it goes deep on a small subset of the panel
rather than all ten economies.

## Non-claims boundary

The project does not make, and its outputs must not imply, any of the
following:

1. No causal claims about macroeconomic outcomes without documented evidence.
2. No investment advice, price targets, or trading signals.
3. No fabricated values, release dates, citations, or test results.
4. No presentation of synthetic, mocked, or cached data as observed data.
5. AI-generated prose derives only from validated structured inputs.
6. No claims of live API, cloud deployment, or production status without evidence.
7. Cross-country comparisons are descriptive, not rankings or scores of merit.

## Modules

`traditional-indicators` (baseline layer), `labor-slack-youth`,
`digital-inclusion`, `payment-resilience-healthcare`, `vintage-transparency`.

## Evidence vocabulary

Every dataset and observation carries exactly one source label:

- `real` - observed values retrieved from an approved official source.
- `synthetic` - generated fixture data used for tests and demos.
- `mocked` - deterministic stand-in for an external service (no-key behavior).
- `cached` - previously retrieved `real` data served from local storage.
- `external` - approved file or third-party source outside the primary APIs.

Every normalized observation preserves the provenance fields required by the
architecture contract: `period`, `release_time`, `retrieval_time`, `vintage`,
`unit`, `frequency`, `seasonal_adjustment`, `source`, `quality_grade`.
