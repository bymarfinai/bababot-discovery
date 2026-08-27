# BNB F85 LONG Transfer — M8 ENTRY2 Economics — B27EK

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
B27EJ found that current execution is ENTRY1 immediately after the first F85 reclaim, while a causal ENTRY2 exists after the dominant retest / re-reclaim sequence. B27EK tests whether waiting for that second confirmation improves BNB LONG economics without changing the underlying signal, H2 objective, or F35 failure rule.

This milestone changes **entry timing only**. It does not change K1/OPP0, clocks, F85, H/L/R, habitat filters, target, stop/invalidation, notional, fee, or source selection.

## Frozen sample
- Instrument: Binance USD-M BNBUSDT perpetual, raw 5m.
- Sources: ALT_0330 LONG and RAW_0530 LONG only.
- Parent signal universe: exact B27EF accepted pooled-major LONG set, N=106 = 55 ALT_0330 + 51 RAW_0530.
- Partitions: external, development, reference_validation.
- ENTRY2 identity/timestamp/price comes exactly from B27EJ and must be reproduced causally from raw 5m.
- B27EJ found 45 descriptive ENTRY2 signals; B27EK does not assume all are tradable until the frozen geometry audit below passes.

## Frozen ENTRY2 rule
For each frozen parent signal:
1. Initial reclaim remains the frozen first F85 touch whose completed raw5m bar closes >F85.
2. ENTRY1 remains the next raw5m open after that initial reclaim; ENTRY1 is the baseline only.
3. Starting at ENTRY1 and strictly before H2 / execution-window end, wait for the B27EJ-defined second confirmation:
   - if a completed close <F85 occurs, `second_reclaim` is the first later completed raw5m close >=F85;
   - otherwise, if the first F85 retest contact closes >=F85, that completed bar is `second_reclaim`.
4. ENTRY2 is the next raw5m open after `second_reclaim`.
5. ENTRY2 is executable only if its raw open satisfies the same geometric admissibility as ENTRY1: `F35 < ENTRY2 < H` and ENTRY2 occurs before the original execution-window end and before frozen H2.
6. Signals without an executable ENTRY2 are skipped. There is **no fallback to ENTRY1** in the ENTRY2 strategy being tested.

No alternative retest count, delay, F-level, candle filter, source-specific condition, or threshold is swept.

## Frozen economics
To isolate entry timing, both ENTRY1 baseline and ENTRY2 use the exact B27EH `H2_ONLY` economics:
- $500 notional;
- $0.40 total roundtrip fee;
- target: first raw5m `high >= H`, filled at H;
- before H2, completed raw5m close <F35 invalidates, exit at the next raw5m open;
- if H2 touch and F35 close invalidation occur on the same bar, H2 has priority;
- unresolved trades exit at the original execution-window-end raw5m open.

ENTRY1 comparison is computed only on the **same executable-ENTRY2 parent signals**. This is the primary apples-to-apples timing comparison and prevents apparent improvement caused merely by excluding signals that never formed ENTRY2.

## Slippage
Report adverse symmetric fill stress at 0, 2, 5, and 10 bps:
- LONG entry worsens upward;
- LONG exit worsens downward;
- trade identity and exit reason remain frozen for each strategy at each entry timing.

## Required outputs
For ENTRY1 same-signal baseline and ENTRY2, report pooled-major and by source / major partition:
- N, wins, WR, PF, expectancy, net, max loss streak;
- H2 exits, F35 invalidations, time exits;
- median entry depth in R, reward-to-H in R, risk-to-F35 in R;
- delta ENTRY2 minus ENTRY1 same-signal for WR, PF, expectancy, net;
- 0/2/5/10 bps stress;
- descriptive cohorts `FIRST_HOLD` versus `ACCEPT_BELOW_RERECLAIM` only, with no post-result selection.

## Frozen support gate
`B27EK_ENTRY2_SUPPORTED` only if ENTRY2 pooled-major satisfies all:
1. executable ENTRY2 N >= 30;
2. WR >= 70%;
3. PF >= 1.50;
4. net > 0;
5. max loss streak <= 4;
6. PF is at least 0.25 higher than same-signal ENTRY1 baseline **or** net improves by at least $15;
7. ALT_0330 and RAW_0530 each have >=10 ENTRY2 trades and net >0;
8. external, development, and reference_validation each have >=5 ENTRY2 trades and net >0;
9. at 5 bps adverse slippage: PF >=1.20 and net >0.

Otherwise status is `B27EK_BNB_ENTRY2_ECONOMICS_NOT_SUPPORTED`.

The source/cohort tables are diagnostic. B27EK cannot choose a source-specific or hold-vs-rereclaim filter after seeing results.

## Mandatory audits
Execution aborts before persistence if any fail:
1. B27EJ status is not `B27EJ_BNB_RETEST_SEQUENCE_DIAGNOSTICS_COMPLETE`.
2. Exact 106 frozen accepted parent LONG IDs are not preserved.
3. B27EJ ENTRY2 existence, timestamps and prices are not reproduced one-to-one from raw 5m.
4. raw ENTRY1 and ENTRY2 prices do not equal exact raw5m opens.
5. ENTRY2 uses information earlier than a completed second-confirmation bar + next-open.
6. H/L/R/F85/F35 or execution-window end drift from frozen lineage.
7. same-signal ENTRY1 baseline does not reproduce B27EH H2_ONLY economics for the same candidate IDs.
8. no fallback ENTRY1, PnL-based filtering, parameter sweep, source-specific tuning, or exit modification occurs.
9. raw BNB 5m coverage >=99.5%.
10. outputs persist only to `bnb-transfer-b27ed-b27ef`; `main` is untouched.

**Research only. Stop after B27EK ENTRY2 economics. No re-arbitration, portfolio integration, forward shadow, or live integration is run automatically.**
