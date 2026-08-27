# BNB F85 LONG Transfer — M5 Two-Stage Economics — B27EH

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
B27EG showed that BNB F85 LONG signals often reach structural H2 but economic losers usually fail to extend materially beyond H2. B27EH tests whether BNB needs a different payout architecture while keeping the frozen signal architecture unchanged.

This experiment changes **economics only**. No entry, clock, K1/OPP0, leave, F85 confirmation, next-open execution, habitat filter, or candidate identity may change.

## Frozen sample
- Instrument: Binance USD-M BNBUSDT perpetual.
- Raw event clock: 5m.
- Historical partitions remain: external, development, reference_validation, august.
- Primary inference uses pooled-major = external + development + reference_validation.
- LONG sources only: ALT_0330 and RAW_0530.
- Candidate identity and accepted/blocked state are frozen to B27EF. No re-arbitration is allowed in this milestone; this isolates payoff architecture from position-lock effects.
- Expected pooled-major accepted LONG count: 106 = 55 ALT_0330 + 51 RAW_0530.
- SHORT_2000 economics remain exactly B27EF and are reported only as a frozen portfolio control.
- Notional remains $500 per accepted trade; total roundtrip fee remains $0.40. Split exits divide notional proportionally; total fee remains $0.40 because total traded notional is unchanged.

## Frozen pre-H2 failure rule
For all B27EH LONG mechanisms, before H2 is reached:
- completed raw 5m close < F35 invalidates;
- execution occurs at the next raw 5m open, matching the causal completed-close convention;
- if H2 (`high >= H`) and F35 close invalidation occur on the same bar, H2 has priority, matching the frozen B27EF target-before-close-invalidation ordering;
- if no H2 or invalidation occurs by execution-window end, exit at the execution-end raw 5m open.

## Mechanism A — H2_ONLY
This is the direct test of whether the portable edge is primarily return-to-boundary rather than extension.

1. Enter at the exact frozen B27EF next-open price.
2. If H2 is reached, exit 100% at H.
3. Otherwise use the frozen pre-H2 F35 close invalidation / execution-window-end rules above.

No E10/E20 runner exists.

## Mechanism B — H2_50_E10_CONFIRM_E20
This is the preregistered two-stage architecture.

### Stage 1
1. Enter at the exact frozen B27EF next-open price.
2. On first H2 reach, exit 50% of notional at H.
3. The remaining 50% becomes the continuation sleeve.

### Stage 2 — continuation evidence
- No same-H2-bar continuation decision is allowed.
- Starting with the **next completed raw 5m bar after the H2 bar**, the runner is not armed until a completed raw 5m close is at or above `E10 = H + 0.10R`.
- Before E10 confirmation, if a completed raw 5m close is below H, continuation has failed; exit the remaining 50% at the next raw 5m open.
- If E10 confirmation occurs, runner becomes armed only after that bar closes. E20 cannot be credited on the E10-confirmation bar.

### Armed runner
Starting on the bar after E10 confirmation:
- target: `E20 = H + 0.20R` using raw 5m high touch;
- failure floor: completed raw 5m close below H, exit remaining 50% at next raw 5m open;
- if neither occurs by execution-window end, exit remaining 50% at the execution-end raw 5m open;
- if E20 touch and close-below-H occur on the same post-confirmation bar, E20 target has priority, matching the existing target-before-close-invalidation convention.

No alternative split, E-level, stop, time window, or confirmation threshold is swept in B27EH.

## Economics and slippage
For each mechanism report 0, 2, 5 and 10 bps adverse slippage **per fill**:
- LONG entry worsens upward;
- LONG exits worsen downward;
- split-exit PnL is notional-weighted across the two exit legs;
- fee remains $0.40 total per trade.

## Required outputs
For each mechanism, source, partition, and pooled-major report:
- N, wins, WR, PF, expectancy, net, max loss streak;
- H2 exits / pre-H2 invalidations / time exits;
- for two-stage only: E10 confirmed count/rate, E20 runner hits, continuation-failure exits, runner time exits;
- 0/2/5/10 bps stress;
- delta versus frozen B27EF LONG economics;
- frozen-acceptance combined portfolio with unchanged B27EF SHORT_2000.

## Frozen support gate
A LONG mechanism is `SUPPORTED` only if pooled-major:
1. accepted LONG N == 106;
2. WR >= 70%;
3. PF >= 1.50;
4. net > 0;
5. max loss streak <= 4;
6. ALT_0330 net > 0 and RAW_0530 net > 0;
7. external, development, and reference_validation each have net > 0;
8. at 5 bps adverse slippage: PF >= 1.20 and net > 0.

If both mechanisms pass, the preregistered preferred mechanism is the one with higher 5 bps PF; tie-breaker is higher 5 bps net. If neither passes, no architecture is selected.

The frozen-acceptance combined portfolio is diagnostic only in B27EH because changed exit duration would require a separate re-arbitration milestone before any executable portfolio claim.

## Mandatory audits
Execution must abort before persistence if any fail:
1. B27EG status is complete and B27EF status remains frozen NOT_SUPPORTED.
2. B27EF candidate IDs, accepted flags, entry timestamps, entry prices, H/L/R/F35 and source identities are unchanged.
3. Exactly 106 pooled-major accepted LONG trades are evaluated.
4. No BNB signal rule or candidate filter is added.
5. H2/E10/E20 use only raw 5m bars available causally at each decision.
6. E10 continuation cannot be armed on information earlier than the E10 bar close.
7. E20 cannot be credited on the E10-confirmation bar.
8. No parameter sweep or post-result adjustment occurs.
9. Raw BNB 5m coverage >= 99.5%.
10. Outputs persist only to `bnb-transfer-b27ed-b27ef`; `main` is not modified.

**Research only. B27EH stops after this two-stage economics result. No re-arbitration, optimization, forward shadow, or live integration is run automatically.**