# SOL LONG E20 Continuation vs Staller Anatomy — A13 Preregistration

## Purpose
A11 and A12 showed the same structural trade-off on the currently supported SOL stack:

`A2 E0_RESTING_H -> E40 + A4 REC_H2`.

Universal profit protection raises WR and reduces gross loss, but reduces expectancy/net by clipping continuation payoff. A13 therefore does **not** test another exit rule.

A13 asks:

> once a frozen trade has causally reached E20 (`H + 0.20R`), what observable path characteristics distinguish an E20 trade that continues to E40 from one that later stalls and exits by the frozen non-target lifecycle?

The objective is to determine whether a later A14 conditional protection rule is justified. A13 is forensic only.

## Frozen context
- Parent remains frozen A2 `E0_RESTING_H -> E40`.
- Recovery remains frozen A4 `REC_H2` only.
- A6, A8, A10, A11 and A12 are rejected and absent from the strategy.
- Same `[L,H]`, `R`, clocks, partitions, lifecycle/recovery horizons, target E40, notional and 5bps conventions.
- A13 never changes an entry, exit, recovery eligibility, target or position size.

## Cohort
Analyze every frozen parent or frozen H2 recovery trade that **causally reaches E20 before its frozen exit**.

Anchor:
- `e20_ts` = first 5m bar whose observed high reaches `H + 0.20R` while the frozen trade is active.

Outcome label, for forensic comparison only:
- `E20_TO_E40_CONTINUATION`: frozen trade subsequently exits at E40 target;
- `E20_STALLER`: frozen trade reaches E20 but its frozen exit is not TARGET.

The future outcome label is never an input to any candidate rule.

A13 reports:
- pooled stack (`PARENT + REC_H2`) in normalized R;
- parent separately;
- H2 separately;
- Development and all frozen OOS/support partitions.

## Pre-E20 anatomy
At the E20 anchor report:
- minutes entry -> E20;
- minutes confirmed breakout -> E20 when available;
- close displacement vs H in R on E20 bar;
- E20-bar close relative to E20 in R;
- running MFE at E20;
- running MAE from entry through E20;
- number of completed closes > H before/through E20;
- number of completed closes >= E10 before/through E20.

## Fixed causal post-E20 snapshots
At `+5m, +10m, +15m, +30m, +60m` after the E20 anchor, record only information observable by that timestamp.

If the frozen trade has already exited before a snapshot, record `baseline_exited_by_snapshot = true`, its frozen exit reason and elapsed exit time. Do not drop it silently.

For trades still active at the snapshot, measure:
- current close vs H in R;
- current close vs E20 in R;
- running MFE since E20, expressed as extension above H in R;
- peak extension achieved since E20;
- maximum giveback from post-E20 peak to a completed close, in R;
- running MAE below E20 in R;
- number/fraction of completed post-E20 closes >= E20;
- number/fraction of completed post-E20 closes > H;
- consecutive closes >= E20 ending at snapshot;
- whether E25 (`H+0.25R`) has been reached;
- whether E30 (`H+0.30R`) has been reached;
- whether price has closed back <= E10;
- whether price has closed back <= H.

No optimized threshold search is allowed in A13.

## Quantile/state reporting
For continuous features report Development Q25/Q50/Q75 by outcome class.
For binary features report rates by outcome class.

A13 may rank fixed feature/snapshot separations by absolute Development gap for readability, but may not convert those gaps into a trading threshold.

## Support gate for A14
A13 is supported for a small conditional-protection experiment only if:
1. Central Development pooled E20 cohort contains at least 80 continuations and at least 40 stallers;
2. at least one simple causal post-E20 dimension shows a meaningful Development separation, such as:
   - E25/E30 progress;
   - fraction closes >= E20;
   - close vs E20;
   - giveback from peak;
   - closed back <= E10;
   - time-to-E20;
3. the same directional separation is present in both Central External and Central Reference Validation at the same fixed snapshot/state definition;
4. the corresponding central OOS comparison has at least 20 continuations and 15 stallers per cell;
5. direction is not obviously contradicted across both support clocks/reference cells.

OOS is replication-only and cannot choose a threshold or snapshot.

## Interpretation
If supported, A14 may preregister only a very small conditional exit/protection family derived from rounded Central Development quantiles or discrete state counts. Clean E20 continuations must remain eligible for full E40 payoff; protection may target only observable stalling paths.

If unsupported, do not scan partial percentages or ratchet thresholds to rescue the concept.

Research only. Live Baba Bot remains unchanged.
