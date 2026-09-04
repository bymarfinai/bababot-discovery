# SOL LONG E10-Fail Trigger Anatomy — A15 Preregistration

## Purpose
A14 found the first post-A4 exit intervention with positive Development economics: `CP_E10_5_FULL` improved raw and 5bps stack PF/net, but failed the frozen Development gate because parent winner preservation was 97.5% (<98%) and block stability was only 3/6.

A15 is forensic only. It studies **only trades on which A14 `CP_E10_5_FULL` would actually intervene**.

Question:

> At the exact causal moment an E20 trade collapses to `<= E10` on the next 5m completed close, what observable state separates genuine E40 continuations from true stallers?

A15 does not change any trade, threshold, target, entry, recovery, or lifecycle.

## Frozen context
- Supported stack remains A2 `E0_RESTING_H -> E40` + A4 `REC_H2`.
- A6/A8/A10/A11/A12/A14 remain rejected and absent from the supported stack.
- A14 `CP_E10_5_FULL` is used only to define the trigger cohort; it is not adopted.
- Same `[L,H]`, `R`, E40 target, partitions, clocks, raw SOLUSDT 5m data, notional and 5bps stress.

## Exact trigger cohort
For each frozen parent trade and persisted A4 H2 trade:
1. find the first causal E20 touch (`high >= H + 0.20R`) inside the frozen baseline trade;
2. inspect only the next completed 5m bar;
3. require that bar close `<= H + 0.10R`;
4. require that the A14 next-open intervention would occur strictly before the frozen baseline exit.

Only those actual A14 interventions enter A15.

## Outcome labels
Outcome labels are forensic future information only:
- `TRIGGERED_E40_RECOVERY`: frozen baseline trade later exits at E40 target;
- `TRIGGERED_TRUE_STALLER`: frozen baseline trade does not reach E40 before its frozen exit.

Labels may never be used as causal inputs.

## Causal features frozen before run
All features are known no later than the trigger bar close:

### Before / at E20
- entry -> E20 minutes;
- frozen break -> E20 minutes when defined;
- E20-touch-bar close in R;
- E20-touch-bar close minus E20 in R;
- running MAE from entry through E20 touch in R;
- number of completed closes > H through E20 touch.

### On the +5m E10-failure trigger bar
- trigger close in R;
- trigger close minus E10 in R;
- trigger high in R;
- trigger low in R;
- absolute candle body in R;
- upper wick in R;
- lower wick in R;
- whether trigger bar itself traded E25;
- whether trigger bar itself traded E30.

### Progress/giveback through trigger close
- peak favorable excursion from E20 touch through trigger bar in R;
- giveback from that peak to trigger close in R;
- total running MFE from entry through trigger bar in R.

No EMA, RSI, regime filter, new clock, or threshold scan is allowed.

## Reporting
Report separately for Parent, REC_H2, and POOLED when sample size permits:
- N by outcome;
- median and Q25/Q75 for each continuous feature;
- rates for binary features;
- Development recovery-vs-staller gaps;
- Central External and Central Reference Validation direction replication;
- four support OOS direction counts.

## Support gate for A16
A15 may authorize a small A16 false-positive guard only if:
1. Central Development has at least 5 `TRIGGERED_E40_RECOVERY` and at least 30 `TRIGGERED_TRUE_STALLER` pooled observations;
2. at least one preregistered causal feature shows a material Development separation;
3. the same direction is present in both Central External and Central Reference Validation when each has at least 3 recovery and 10 staller observations;
4. the feature is not broadly contradicted by support cells (same direction in at least 3 of 4 support OOS cells with both classes present).

Because the recovery cohort is expected to be small, A15 is explicitly allowed to conclude `INCONCLUSIVE` rather than manufacture a threshold.

If supported, A16 may preregister only a tiny guard family derived from rounded Central Development quantiles/state values. OOS cannot choose or retune the guard.

Research only. Live Baba Bot remains unchanged.
