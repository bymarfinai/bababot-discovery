# BNB B29 A2 — Stop Verdict

## Status

**B29-A2-v1 REJECTED — DO NOT TUNE THIS IDENTITY AGAINST THE SAME WALK-FORWARD RESULTS**

The accepted result is the frozen-identity run `34915709055`, produced only after recovering the exact accepted A1 raw/fingerprint identity.

## Data identity

- BNBUSDT 5m raw rows: 687,936
- Raw start: 2020-02-10 08:00 UTC
- Raw last open timestamp: 2026-08-25 23:55 UTC
- Coverage: 100%
- Frozen A1 fingerprint hash: `2bdb2c99f961942ed48a41d3fa8f6c5a1bd083b280126308f423b98f38ff6ea6`
- Post-2026-08-26 data touched: NO
- Exact A1 identity guard: PASS

## Accepted A2 result

- Evaluable walk-forward queries: 10,185
- Median analog count: 64 in every fold
- Structural coherence: PASS
  - pooled median same `structure_state`: 64.06%
  - pooled median same `path_state`: 70.31%
- Pooled horizon rhos:
  - +15m: 0.0209
  - +30m: 0.0350
  - +60m: 0.0200
  - +120m: 0.0066
  - +360m: 0.0073
- Positive pooled horizons: 5/5
- Median pooled rho: 0.0200, below frozen requirement 0.0300
- Mean pooled sign agreement: 50.74%, above frozen requirement 50.50%
- Positive fold median-rho count: 3/5
- Aggregate character-memory gate: FAIL

Fold median rhos:
- 2022: -0.0016
- 2023: -0.0093
- 2024: +0.0395
- 2025: +0.0352
- 2026-precutoff: +0.0100

## Interpretation

A1 succeeds as a causal structural representation, and A2 confirms that nearest analogs are genuinely coherent in structural labels. However, generic nearest-neighbour similarity across the full A1 fingerprint does not carry enough stable forward-behaviour information to qualify as a reusable predictive character memory under the preregistered gate.

The failure is temporal: 2022 and 2023 are effectively non-predictive while 2024-2026 are weakly positive. Therefore B29 must not proceed to entry/TP/SL construction from A2-v1.

## Stop rule

Do not rescue A2-v1 by changing K, the categorical penalty, the feature list, horizon list, query sampling, fold definitions, or acceptance thresholds after seeing these results.

Any further character-memory work must receive a new experimental identity and must address the observed temporal/regime dependence explicitly rather than optimize A2-v1 until it passes.

No live orders were placed.
