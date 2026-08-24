# B27DL — F85 LONG E20 Armed Range-Trailing Exit — Preregistration

## Purpose
Test the user-proposed exit-only change on the exact B27DK 4-zone operating portfolio. Entry logic, zone filters, reference geometry, notional and fee remain unchanged.

## Frozen operating zones
- ALT_0330: frozen TOUCH_FIRST_HALF eligibility.
- RAW_0530: B27DJ RANGE_COMPLETED_SECOND_HALF.
- LONDON 08:00: frozen Same-Bar F85 eligibility.
- RAW_2330: B27DJ RANGE_COMPLETED_SECOND_HALF.

## Baseline
Current exit is fixed `E20 = H + 0.20R`, where `R = H-L`. A high touch of E20 exits immediately at E20. Before E20, completed 5m close below F35 invalidates. Otherwise time exit at execution end.

## Single frozen runner variant
Name: `E20_ARMED_STEP10_RUNNER`.

1. Before E20, management is identical to baseline.
2. The first 5m bar whose high reaches E20 arms the runner. The baseline TP is NOT taken.
3. Protective floor becomes E20 starting from the next 5m bar. The arming bar itself cannot be stopped by the newly armed floor, removing intrabar path ambiguity.
4. The floor is a hard protective price floor on subsequent bars:
   - if bar open <= floor, exit at bar open (gap-safe assumption);
   - else if bar low <= floor, exit at the floor;
   - for portfolio locking, the exit becomes available after that completed 5m bar.
5. Floor ratchets only from completed 5m closes, in structural 0.10R milestones:
   - completed close >= E30 keeps floor at E20;
   - completed close >= E40 raises floor to E30;
   - completed close >= E50 raises floor to E40;
   - completed close >= E60 raises floor to E50;
   - and so on indefinitely in 0.10R steps.
   Equivalently, after a completed close at milestone En (n >= 30, multiples of 10), floor = max(previous floor, E(n-10)).
6. Floor never decreases.
7. If no protective-floor exit occurs, use the same execution-end time exit.
8. No alternate step size, arm level, floor offset, candle timeframe or threshold is tested inside B27DL.

## Execution / causality rules
- Raw completed Binance Futures BTCUSDT 5m bars from the same B21 data source.
- Same baseline priority on the pre-arm bar: E20 high-touch arms before any F35 close invalidation is interpreted.
- Ratchet information uses only completed 5m closes and becomes effective on the next bar.
- No post-hoc intrabar ordering assumptions.

## Exact portfolio rescore
Runner exits can keep positions open longer, so B27DL MUST rerun the same global one-BTC-position chronological lock. It is invalid to simply replace PnL on the 228 B27DK accepted trades without rescoring blocked entries.

## Frozen comparison
Report baseline versus runner for every partition and pooled-major, plus per-zone contribution after the global lock. Also report runner-armed count, protective-floor exits, time exits after arm, milestone reach rates, and blocked-trade change.

## Decision label
`B27DL_RUNNER_SUPPORTED` only if pooled-major:
- total net PnL > B27DK baseline;
- PF >= 1.80;
- WR >= 70%;
- accepted N >= 80% of B27DK baseline accepted N;
- every major partition remains net positive.
Otherwise label `B27DL_RUNNER_NOT_SUPPORTED`.

This is a research/operating exit experiment only. No live BBC change is authorized.