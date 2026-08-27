# ETH Post-Breakout Retest — M1 Structural Atlas

**PREREGISTERED before result-bearing execution.**

Purpose: test a distinct LONG structure after corrected ETH K1 OPP0 reaches H2 and then produces a completed 5m close above frozen H. Compare immediate next-open after breakout versus waiting for the first retest of H from above that closes back at/above H, then taking the next 5m open.

Frozen upstream gate: `ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt` must equal `ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY`.

Universe: all clean LONG H2 windows from ALT_0330, RAW_0530, LONDON, RAW_2330. Pre-H2 F-levels do not qualify or filter this experiment. Frozen 6h30 execution window remains unchanged.

Confirmed breakout: starting on the H2 bar, first completed raw 5m `close > H`. H2 bar may itself qualify. Wick-only breaks do not. A completed `close < L` before breakout gives `PRE_BREAKOUT_COLLAPSE`; no later breakout is used.

Immediate comparator A: next raw 5m open after confirmed breakout, if inside execution window.

Retest: search begins strictly after breakout bar. The first later bar with `low <= H` is the only retest attempt. `close >= H` = `RETEST_HOLD`; `close < H` = `RETEST_FAIL`. No second chance after a failed first retest. No touch before session end = `NO_RETEST`.

Retest execution B: next raw 5m open after `RETEST_HOLD`, only if that open exists inside execution window and is `>= H`. The retest bar itself is never an execution bar.

Structural continuation diagnostics after each executable A/B:
- E05 = H + 0.05R
- E10 = H + 0.10R
- E20 = H + 0.20R
- E30 = H + 0.30R

For each target, scan causally from execution bar onward. First completed `close < H` is structural failure. If a raw 5m bar both reaches target by high and closes < H, outcome is `AMBIGUOUS` because intrabar order is unknown; it is not credited as target success. Otherwise first target hit = `TARGET`; first close < H = `FAIL`; neither = `SESSION_END`.

Report by habitat x partition and pooled-major: clean H2 N; breakout N/rate; H2-bar breakout rate; H2→breakout minutes; A N; retest-attempt/hold/fail/no-retest counts; B N/rate among breakouts; breakout→retest minutes; retest penetration below H in R; B execution fraction; A and B E05/E10/E20/E30 target/fail/ambiguous/session-end counts and target rates; entry→target minutes; maximum extension before first close < H/session end; and B-minus-A target-rate deltas.

No PnL, PF, fees, leverage, TP/SL optimization, EMA/volume/body/regime filters, new clocks, execution-window extension, SHORT testing, or automatic next milestone. M1 is an atlas and does not promote a winner.

Mandatory assertions: corrected M2 gate; exact all-four-habitat clean LONG H2 cohort; close>H breakout only; retest strictly after breakout; first retest only; completed close>=H hold; next-open causality; B open>=H; close<H failure; same-bar target+failure ambiguous; raw 5m coverage>=99.5%; synthetic tests for H2-bar breakout, wick-only non-breakout, retest hold/fail, and same-bar ambiguity.

**Stop after M1 result.**
