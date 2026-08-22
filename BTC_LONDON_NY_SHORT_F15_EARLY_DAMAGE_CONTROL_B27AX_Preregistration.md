# B27AX — BTC London→NY SHORT F15 Early Damage-Control Threshold Map — Preregistration

## Purpose
Test whether the early path-shape separation localized in B27AW can reduce the PRE_H2 failure loss tail without changing the independently discovered F15 entry, H2 semantics, E20 full-position hybrid, F65 baseline invalidation, session, or regime universe.

## Frozen lineage
- Cohort/economics baseline: B27AT `E20` full-position hybrid only.
- Early path features: B27AW.
- Major partitions: `external`, `development`, `reference_validation`.
- Baseline pooled-major total must reproduce exactly: `-15.05841591698896` USD across 163 trades.
- Baseline E20 activation count must reproduce 92.
- $500 notional; $0.40 round-trip fee, identical to B27AT.

## Causal decision rule
Each candidate is evaluated independently at exactly one frozen decision horizon: **5m, 10m, or 15m** of completed post-fill 5m bars. The fill bar itself remains excluded.

A candidate may early-exit only if, at that decision timestamp:
1. the original B27AT trade is still open;
2. H2 has not occurred before the decision timestamp (equivalently, the B27AW at-risk feature row exists);
3. the candidate feature is greater than or equal to its preregistered threshold.

If triggered, exit the full position at the completed 5m close known at that decision timestamp. If not triggered, preserve the exact original B27AT E20-hybrid path/PnL. No re-entry.

## Frozen rule families and grids
No feature combinations are allowed.

### A. `adverse_close_r`
Maximum completed 5m close above F15 during the frozen observation window, normalized by London range R.

Thresholds: **0.05, 0.10, 0.15, 0.20, 0.25R**.

### B. `wick_imbalance_r`
`adverse_wick_r - favorable_wick_r` over the same frozen observation window.

Thresholds: **0.05, 0.10, 0.15, 0.20, 0.25R**.

Total map: 2 families × 3 horizons × 5 thresholds = **30 candidates**.

## Selection / guardrails
A candidate is promotion-eligible only if all are true:
- pooled-major total PnL is strictly greater than the frozen B27AT baseline;
- pooled-major expectancy is positive;
- each of external/development/reference_validation has expectancy >= 0;
- each major partition has PF >= 1.0.

If multiple candidates pass, select exactly one: the eligible candidate with highest pooled-major total PnL. Ties resolve by earlier horizon, then larger threshold, then family name alphabetically.

If none pass, result is `NONE`. The diagnostic best pooled candidate may still be reported but is not promoted.

## Required diagnostics
For every candidate report N, WR, PF, expectancy, total PnL by partition and pooled-major, number of early cuts, number of cut trades that were baseline winners, number of cut trades that later activated E20 in the frozen baseline, and total PnL delta vs baseline.

## Prohibited
No threshold insertion between grid values; no post-hoc E07/E08/etc.; no regime slice; no candle-pattern rule; no feature combination/classifier; no F15/F65/E20 change; no runner change; no live BBC change.

Research only.