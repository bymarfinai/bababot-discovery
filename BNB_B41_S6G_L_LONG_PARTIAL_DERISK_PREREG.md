# BNB B41-S6G-L — LONG Partial De-Risk Preregistration

## Objective

Test whether the frozen B41 LONG failure alarm is more useful as a **partial de-risk signal** than as a full exit.

This stage does not search for a new alarm, stop level, EMA/Fibonacci condition, TP, or bounce timing.

## Frozen parents

- S6C-L signature: `75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f`
- S6E-L signature: `953f2a9a1a721fbe0c8fcefcaa73feb4470ae72e7407b9e4cb14aab4f4b7a5e8`
- S6F-L signature: `d62c788c66afee53a9c6d09fb0fb9e4b5f00d96caa22bafc5c3a34b53e0d2ed4`
- Setup: LOWER Q80 + TF60 C2 reclaim -> MARKET LONG.
- Alarm: frozen `R4_60_2OF3_Q85` at detector+60m.
- Baseline: hold 100% position to detector+180m.

## Frozen policies

All fractions refer to original position size.

1. `P25_ALARM`
   - If alarm fires at +60m, realize 25% at the completed +60m close.
   - Hold remaining 75% to +180m.

2. `P50_ALARM`
   - If alarm fires, realize 50% at +60m.
   - Hold remaining 50% to +180m.

3. `P75_ALARM`
   - If alarm fires, realize 75% at +60m.
   - Hold remaining 25% to +180m.

4. `P25_ALARM_P25_FAILREC`
   - Realize 25% at alarm.
   - On remaining position, apply frozen E1 recovery test at detector+105m.
   - If E1 fails (close < Q80 wall), realize another 25% of original size at +105m.
   - Hold final 50% to +180m.
   - If E1 passes, hold remaining 75% to +180m.

No other fraction is searched.

## Managed outcome

For each realized fraction:
`fraction * aligned_outcome_at_that_exit`.

Unrealized remainder at +180m:
`remaining_fraction * baseline_aligned180`.

Total managed outcome is the sum.

## Metrics

Report:
- mean / median / q10 managed outcome;
- positive-outcome rate;
- baseline-winner mean and median retention;
- baseline-loser mean and median improvement;
- alarm-winner mean retention;
- alarm-loser mean improvement;
- mean cost vs baseline;
- q10 improvement vs baseline;
- tail-efficiency ratio = q10 improvement / abs(mean cost), when mean cost <0.

## DEV eligibility

A policy is DEV_ELIGIBLE if:
- n180 >=30;
- managed mean >= 95% of baseline mean;
- baseline-winner mean outcome >=95% of baseline-winner mean outcome;
- positive-outcome rate >= baseline positive rate - 2 percentage points;
- q10 managed outcome > baseline q10;
- baseline-loser mean outcome > baseline-loser mean outcome;
- if managed mean is below baseline mean, tail-efficiency ratio >=1.0.

## DEV nomination

Choose the smallest de-risk action among eligible policies in fixed order:
`P25_ALARM` -> `P50_ALARM` -> `P75_ALARM` -> `P25_ALARM_P25_FAILREC`.

This is a conservatism/simplicity rule, not a performance ranking.

If none qualifies -> NO_NOMINATION.

## REF validation

The single DEV nominee validates if:
- n180 >=20;
- managed mean >=95% of REF baseline mean;
- baseline-winner mean retention >=95%;
- positive rate >= REF baseline positive rate -2pp;
- q10 improves;
- baseline-loser mean improves;
- if mean cost is negative, tail-efficiency ratio >=1.0.

No alternative may replace a failed nominee after REF.

## Gate

Validated nominee -> `LONG_PARTIAL_DERISK_READY`.

Otherwise -> `LONG_PARTIAL_DERISK_NOT_READY`.

No TP, PF, expectancy, leverage, fee/slippage optimization, or PnL optimization.
