# B27AY — BTC London→NY SHORT F15 Entry Between Retest #2 and #3 — Preregistration

## Question
Does moving the frozen SHORT F15 entry window from between Low retest #1→#2 to between Low retest #2→#3 improve structural conversion and E20 full-hybrid economics without changing entry depth, stop, target, runner, regime, or source-session levels?

## Frozen source universe
- BTCUSDT 5m, identical 698,112-row source used by B27Q/B27AK/B27AT.
- London→New York only.
- Frozen B27Q SHORT K1 / OPP0 opportunities only.
- Frozen London High/Low and partitions unchanged.

## Visit semantics
- A valid Low retest bar satisfies `low <= L` AND `close >= L`.
- Consecutive valid Low-touch bars are one visit episode.
- Strict completed 5m `close < L` is a breakdown, not a valid retest.
- Strict completed 5m `close > H` is an opposite break.

## New chronology
1. Reproduce K1 Low visit #1 exactly.
2. Require a causal leave from visit #1.
3. Require a distinct valid Low retest #2 before strict breakdown `<L`, opposite break `>H`, or session end.
4. Collapse consecutive retest-#2 bars into one episode.
5. Require a causal leave from retest #2; eligibility begins on the next 5m bar after the leave bar completes.
6. Frozen entry remains `F15 = L + 0.15R`, R=H-L.
7. F15 must fill strictly after second-visit leave eligibility and strictly before retest #3, strict breakdown `<L`, opposite break `>H`, or session end.
8. Retest #3 is a milestone only. It is a distinct valid Low retest (`low<=L`, `close>=L`).
9. After entry, economics remain frozen B27AT E20 full-position hybrid: pre-activation completed-close invalidation at `F65=L+0.65R`; activation at intrabar `E20=L-0.20R`; after E20 full position remains open with frozen 3-bar pivot-high profit ceiling ratchet; session-end behavior and $500 notional/$0.40 fee unchanged.

## Causal ordering guards
- Entry cannot occur on retest #2 episode bars.
- Leave from retest #2 is known only at leave-bar close; entry eligibility starts next bar.
- F15 fill bar must be strictly before retest #3 / breakdown / opposite-break terminal bar.
- If strict breakdown occurs before a valid retest #3, that path is `BREAKDOWN_BEFORE_H3`, not H3 success.
- Fill bar cannot activate E20; B27AT activation chronology remains unchanged.

## Outputs
Per partition and pooled-major report:
- K1 opportunities.
- Valid retest #2 opportunities.
- Clean post-H2 leave windows.
- F15 fills between #2 and #3.
- H3 hit count/rate among fills.
- Strict breakdown after H3 and E20 activation diagnostics.
- Frozen E20 full-hybrid N, WR, PF, expectancy, total PnL.
- Compare with frozen original #1→#2 F15 E20-hybrid baseline (pooled-major N=163, total=-15.05841591698896).

## Interpretation rule
This is a timing-shift test, not a parameter search. No alternative entry fraction, stop, activation level, confirmation, regime filter, candle threshold, or runner parameter may be introduced after seeing results.

Research only. Live BBC unchanged.
