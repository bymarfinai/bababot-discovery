# BNB F85 LONG Transfer — M7 Retest Sequence Diagnostics — B27EJ

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
B27EI showed that the frozen F85 next-open entry is geometrically expensive, but blindly waiting for deeper F80/F75/F70/F65 fills reduces subsequent H2 probability. B27EJ diagnoses whether the missing information is **sequence/timing** rather than depth: how many F85 retests occur after the initial reclaim, whether a second confirmation/re-reclaim exists, and what price usually does after a strict H breakout.

This milestone is diagnostic only. No PnL, new entry rule, stop, target, filter, or strategy selection is allowed.

## Frozen sample
- BNBUSDT Binance USD-M perpetual, raw 5m.
- Exact B27EF accepted pooled-major LONG set only: N=106 = 55 ALT_0330 + 51 RAW_0530.
- Existing signal remains first pre-H2 F85 touch + same-bar close >F85 + next raw5m open.
- B27EG economic label / structural outcome and B27EI geometry must join one-to-one.

## Terminology
- `initial_reclaim`: frozen confirmation bar close > F85.
- `ENTRY1`: frozen next-open entry immediately after initial reclaim.
- `F85_retest_bar`: after ENTRY1 and before first H2, a raw5m bar with low <= F85.
- Consecutive F85_retest_bars are one retest episode.
- `F85_hold_retest`: retest episode whose first contact bar closes >= F85.
- `F85_accept_below`: any completed raw5m close < F85 after initial reclaim and before H2.
- `second_reclaim`: first completed raw5m close >= F85 after a prior completed close <F85, or the first F85 hold-retest if no close-below occurred. Its next raw5m open is the descriptive `ENTRY2` timestamp/price. B27EJ does not trade ENTRY2.
- `H2`: first later bar with high >= H, frozen structural boundary return.
- `strict_H_breakout`: first completed raw5m close > H after H2.

## Pre-H2 sequence diagnostics
For each signal, using only raw5m bars from ENTRY1 to first H2 / execution-window end:
1. Count F85 retest episodes: 0, 1, 2, 3+.
2. Record first retest time, whether first contact holds F85 or closes below it, deepest low in R, and whether/when F85 is re-reclaimed.
3. Record whether a descriptive ENTRY2 exists, its next-open depth `(entry2-L)/R`, reward to H, and minutes from ENTRY1.
4. Classify path: `DIRECT_H2_NO_RETEST`, `RETEST_THEN_H2`, `ACCEPT_BELOW_RERECLAIM_THEN_H2`, `RETEST_NO_H2`, `NO_RETEST_NO_H2`.
5. Report H2 probability conditional on retest count and first-retest behavior, pooled and by source.
6. Compare B27EF WIN vs LOSS only descriptively; no filter may be selected from outcome differences.

## Post-H breakout diagnostics
For trades that reach H2:
1. Record whether H2 bar itself closes >H.
2. Locate first strict_H_breakout (completed close >H), if any.
3. Starting only after that breakout bar closes, classify the first causal event among:
   - `E10_CONTINUATION`: high >= H+0.10R before H retest/failure;
   - `H_HOLD_RETEST`: low <= H and close >= H before E10;
   - `H_FAIL_ACCEPT_BELOW`: completed close < H before E10;
   - `TIMEOUT`.
4. Count H retest episodes before first E10 and before E20.
5. If an H hold-retest occurs, record whether E10/E20 is subsequently reached.

## Frozen interpretation labels
Pre-H2 pattern label:
- `DIRECT_CONTINUATION_DOMINANT` if >=60% of H2 trades have 0 F85 retests.
- `ONE_RETEST_DOMINANT` if >=50% of H2 trades have exactly 1 retest episode.
- `MULTI_RETEST_DOMINANT` if >=50% of H2 trades have >=2 retest episodes.
- otherwise `MIXED_PRE_H2_SEQUENCE`.

Post-breakout label among strict H breakouts:
- `DIRECT_EXTENSION_DOMINANT` if >=50% first event is E10_CONTINUATION.
- `H_RETEST_DOMINANT` if >=50% first event is H_HOLD_RETEST.
- `FAILED_BREAKOUT_DOMINANT` if >=50% first event is H_FAIL_ACCEPT_BELOW.
- otherwise `MIXED_POST_BREAKOUT_SEQUENCE`.

These labels are descriptive only and do not authorize a strategy change.

## Mandatory audits
Execution aborts if:
1. B27EI status is not `B27EI_BNB_ENTRY_DEPTH_DIAGNOSTICS_COMPLETE`.
2. Exact 106 accepted pooled-major LONG IDs are not preserved.
3. raw entry open / F85 / H / L / R / confirmation timestamps drift from frozen lineage.
4. Retest counting begins before ENTRY1 or uses future knowledge.
5. second_reclaim ENTRY2 uses anything earlier than a completed bar close + next-open.
6. post-H analysis credits information from the strict-breakout bar before that bar closes.
7. no PnL or parameter optimization is performed.
8. raw BNB 5m coverage <99.5%.
9. outputs persist only to `bnb-transfer-b27ed-b27ef`; `main` remains untouched.

**Research only. Stop after B27EJ sequence diagnosis. Any ENTRY2 economics must be a separate preregistered milestone.**