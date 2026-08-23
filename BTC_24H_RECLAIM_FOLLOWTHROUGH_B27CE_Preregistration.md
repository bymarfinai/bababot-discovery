# B27CE — BTC 24H Direct-Break Reclaim Followthrough Anatomy — Preregistration

## Purpose
B27BZ showed that after a direct Low close-break, the first retest of the broken Low reclaimed above L in 734 pooled-major cases (external 202 / development 336 / reference_validation 196; pooled OOS 398). B27BZ stopped at that reclaim.

B27CE follows only those exact `RETEST_RECLAIMED` rows to determine whether reclaim usually persists upward or fails and re-breaks the Low.

Research/anatomy only. No trade, stop, TP, fee, PF, PnL, expectancy, or live BBC change.

## Frozen source cohort
Source: persisted `BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Events.csv`.

Include only major partitions and rows with `retest_class == RETEST_RECLAIMED`.

Identity must reproduce exactly:
- external 202
- development 336
- reference_validation 196
- pooled major 734
- pooled OOS 398.

No clock/regime/weekday or price filter may be added.

## Causal followthrough window
The reclaim is confirmed only at completion of the B27BZ retest candle (`retest_complete_ts`). Evaluation begins at the next raw 5m bar and ends at the same 4H observation block end.

Let `L` and `H` be the previous completed 4H Low/High and `R4 = H-L`.

If `retest_complete_ts >= obs_end`, classify `NO_FOLLOWTHROUGH_WINDOW`. Such rows remain in the identity count but are excluded from all directional-rate denominators and excursion quantiles because no post-reclaim bar exists.

Otherwise scan completed 5m closes after reclaim confirmation. The first strict boundary close determines the terminal class:
- `REBREAK_LOW`: first `close < L` before any `close > H`;
- `HIGH_BREAK`: first `close > H` before any `close < L`;
- `NO_BOUNDARY_BY_BLOCK_END`: neither strict boundary close occurs before block end.

No bar after the terminal boundary may affect excursion metrics.

## Frozen descriptive excursion metrics
From the first post-reclaim 5m bar through the terminal bar (or block end), report:
- maximum high above L as fraction of R4;
- maximum close above L as fraction of R4;
- whether max close reaches L + 5%, 10%, 15%, 25%, or 50% of R4;
- reclaim-confirmation to rebreak/high-break minutes;
- for `NO_BOUNDARY_BY_BLOCK_END`, final block close relative to L.

These ladders are descriptive only and cannot be selected as a trading threshold inside B27CE.

## Required reporting
Report external, development, reference_validation, pooled OOS, pooled major, every UTC 4H clock block, and regime.

Primary fields per scope:
- cohort N and eligible post-reclaim N;
- REBREAK_LOW N/rate among eligible;
- HIGH_BREAK N/rate among eligible;
- NO_BOUNDARY N/rate among eligible;
- NO_FOLLOWTHROUGH_WINDOW N;
- median reclaim->rebreak minutes among REBREAK_LOW;
- P50/P75 max-close extension above L as %R4;
- +5/+10/+15/+25/+50% R4 close-extension rates.

## Interpretation discipline
This is not trading WR.

A reclaim may be called `mostly temporary within the same 4H block` only if pooled-OOS REBREAK_LOW rate >=60% and both external and validation REBREAK_LOW rates >=55%, using only eligible post-reclaim rows.

A reclaim may be called `mostly persistent/reversal-like within the same 4H block` only if pooled-OOS (HIGH_BREAK + NO_BOUNDARY) rate >=60% and both external and validation >=55%, using only eligible post-reclaim rows.

Otherwise verdict is mixed.

Frozen verdict labels:
- `B27CE_RECLAIM_MOSTLY_TEMPORARY`
- `B27CE_RECLAIM_MOSTLY_PERSISTENT`
- `B27CE_RECLAIM_FOLLOWTHROUGH_MIXED`

No economic or live implication follows automatically.