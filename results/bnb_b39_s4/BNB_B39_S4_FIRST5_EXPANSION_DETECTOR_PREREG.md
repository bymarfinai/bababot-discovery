# BNB B39-S4 — Frozen First-5m Expansion Detector Validation Preregistration

## Objective
Validate one frozen early-reaction detector from B39-S3 without searching any new feature, threshold, combination, entry, SL, or TP.

S4 asks:
"Does the first-5m displacement character robustly identify a useful subset of real >=1R expansion events across DEV, REF, and years?"

## Frozen parent
Use the exact persisted B39-S3 ledger, itself parity-locked to B39-S1:
- DEV normalizable = 785
- REF normalizable = 463
- DEV GE1R = 375
- REF GE1R = 241

## Frozen causal decision
Decision point:
- close of the first raw 5m bar strictly after the completed first-touch 15m bar.

Same B39-S3 resolution discipline:
- if +1.00 event-R is already touched before/on that 5m decision bar: TOO_FAST_WIN, not detector-eligible;
- if demand_low is touched before/on decision: TOO_FAST_FAIL, not detector-eligible;
- same-bar target+floor: AMBIGUOUS_RESOLUTION;
- only `PLUS5_CLOSE / ELIGIBLE` events can receive a detector signal.

## Frozen primary detector D1
No threshold search in S4.

`D1_FIRST5_DISPLACEMENT` is TRUE when:

`p5_close_r > 0.20335748322474653`

where:
`p5_close_r = (first_post_touch_5m_close - anchor_price) / event_risk`

This is exactly the B39-S3 DEV Q75 cut.

No additional candle-quality or pre-touch filter is allowed.

## Frozen benchmark only
For timing comparison, report but do not promote:

`B15_DISPLACEMENT = p15_close_r > 0.2591007864238388`

on the B39-S3 PLUS15 unresolved cohort.

B15 is a latency benchmark only. It is not a competing detector eligible for promotion in S4.

## Validation outcomes
Primary:
- GE1R

Secondary:
- GE1_5R
- CLEAN1R
- CLEAN1_5R
- GE2R, reconstructed with the unchanged B39-S1 event-risk/path definition.

## Required detector metrics
For DEV, REF, and each year:
- eligible events
- signal count and signal rate
- GE1R precision / hit rate
- GE1_5R rate
- GE2R rate
- CLEAN1R and CLEAN1_5R rates
- GE1R true positives, false positives
- unresolved GE1R winner retention = signal GE1R / eligible GE1R
- whole-universe GE1R capture = signal GE1R / all frozen GE1R
- too-fast GE1R count lost before decision

## Robustness checks
- exact same threshold DEV -> REF
- year-by-year rate and signal count
- compare D1 signal cohort against its contemporaneous eligible base rate
- uplift in percentage points and relative lift
- Wilson 95% interval for GE1R signal rate
- do not select or tune from confidence intervals

## Entry-lateness diagnostic
S4 may report, but must NOT optimize:
- market-at-signal price distance from anchor in event-R
- remaining reward to anchor +1R
- structural risk from signal close to demand_low
- implied target-to-floor reward/risk at the signal close

This is a diagnostic only. It does not define final entry economics.

## Stop / advance rule
D1 can advance as the frozen B39 expansion detector character only if:
1. GE1R signal rate is materially above the eligible base rate in both DEV and REF;
2. REF does not collapse relative to DEV;
3. year-by-year results are not driven by one isolated year;
4. retained signal count remains useful;
5. late confirmation does not consume most of the remaining +1R reward.

If D1 passes, the next stage must be entry discovery around this frozen character. The detector threshold itself stays frozen.
