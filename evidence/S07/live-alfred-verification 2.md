# S07 live ALFRED verification (2026-08-29)

Evidence that the realtime-query path works against the live FRED API.
The API key was loaded from gitignored `.env.local` into the process env
for the run only; it is never printed or committed.

## Realtime windows produce distinct vintages (UNRATE)

Two fetches of the same observation window with different realtime windows:

```
live mode: True
label: real
retrieval: 2026-08-29
period=2023-01-01 vintage=2023-04-01 value=3.4 missing=None
period=2023-02-01 vintage=2023-04-01 value=3.6 missing=None
period=2023-03-01 vintage=2023-04-01* value=3.5 missing=None  (*2023-04-07)
later-window vintages: ['2024-04-01', '2024-04-01', '2024-04-01']
later-window values: [3.4, 3.6, 3.5]
```

The vintage stamps track the realtime window, proving the ALFRED
restriction is honored. UNRATE values did not change between these two
windows (honest observation - no revision for these months across these
windows).

## A genuine revision chain (PAYEMS, Jan 2023)

Nonfarm payrolls revise substantially; the same identity
(period=2023-01-01) fetched under two realtime windows:

```
early-window: period=2023-01-01 vintage=2023-02-03 value=155073.0
late-window:  period=2023-01-01 vintage=2024-04-01 value=154773.0
revision: period=2023-01-01 2023-02-03->2024-04-01
          155073.0->154773.0 abs=-300.0 rel=-0.001934572749608249
```

January 2023 payrolls (thousands) were first reported at 155,073 in the
Feb 2023 release and revised to 154,773 by the April 2024 vintage
(-300K, the annual benchmark revision). This is exactly the
revision-transparency evidence RQ4 requires: the two vintages are distinct
stored identities, and `revision_deltas()` computes the change without
fabrication (both values present, non-zero base -> relative is computable).

All points above carry evidence_label=real (live API, external source).
