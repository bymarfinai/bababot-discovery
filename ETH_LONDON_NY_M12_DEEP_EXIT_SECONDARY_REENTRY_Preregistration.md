# ETH London -> New York M12 Deep-Breach Exit + Secondary F90 Re-entry — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Test whether the M11-supported deep-breach recovery structure can improve the actual economics of the frozen ETH London->New York F90 EARLY_RECLAIM setup without retuning entry or target geometry.

M12 directly addresses the M8/M9 bottleneck: pooled E15/F50 economics were positive, but Development remained PF < 1 because a small number of failed pre-breakout paths carried large losses.

## Frozen cohort and baseline
- ETHUSDT perpetual, raw 5m.
- Exact 95 M5 F90 EARLY_RECLAIM executed identities.
- Entry price/timestamp remain exact M5 actual next-open entries.
- Baseline target: `E15 = H + 0.15R`.
- Baseline completed-close invalidation: `F50 = L + 0.50R`.
- Session time exit: 20:00 UTC.
- Baseline execution/economic semantics must reproduce M8 `E15/F50` exactly.
- Notional: $500 per active leg.
- Fee convention: $0.40 per completed leg, matching the prior M8 convention for one entry/exit trade.
- 5bps stress: entry pays +5bps; market/close/time exits pay -5bps; limit TP remains at the target price, matching M8.

## Frozen variants
Only five variants are allowed:
1. `BASE_F50` — exact M8 E15/F50 benchmark.
2. `F80_EXIT_ONLY` — exit current position on first completed 5m close < F80, then remain flat.
3. `F80_EXIT_REENTRY` — same F80 exit, then allow one secondary F90-reclaim re-entry.
4. `F75_EXIT_ONLY` — exit current position on first completed 5m close < F75, then remain flat.
5. `F75_EXIT_REENTRY` — same F75 exit, then allow one secondary F90-reclaim re-entry.

No F85/F70/intermediate fractions, no timing filter, and no post-result level sweep are allowed.

## Deep-exit execution semantics
For F80/F75 variants:
1. From the original M5 entry, E15 TP is active immediately.
2. On every completed bar, intrabar E15 target touch has precedence over any same-bar completed-close deep breach, consistent with M8 TP-before-close-invalidation semantics.
3. If target has not already executed, first completed 5m `close < deep boundary` exits the first leg at that completed close.
4. If no deep exit occurs first, F50 remains the fallback completed-close invalidation.
5. If neither target nor invalidation occurs, exit at 20:00 UTC open.

## Secondary F90 re-entry semantics
Applies only to `*_EXIT_REENTRY` after a deep exit:
1. Search only after the completed deep-breach candle.
2. `secondary reclaim` = first later completed 5m candle with `close > F90`.
3. Re-entry is the next raw 5m bar open after that reclaim candle completes.
4. Maximum one re-entry per original setup.
5. Re-entry is valid only if `F50 < next_open < E15`.
6. If next open >= E15, classify `MISSED_TARGET_AT_OPEN` and remain flat.
7. If next open <= F50, classify `INVALID_BELOW_F50` and remain flat.
8. If there is no next bar before 20:00 UTC, remain flat.
9. Re-entry can follow a reclaim that occurs on the eventual strict-breakout bar; no future breakout knowledge is used.
10. After valid re-entry, target remains E15, completed-close stop remains F50, and time exit remains 20:00 UTC.
11. TP intrabar has precedence over same-bar completed-close F50 invalidation.

## Setup-level economics and WR
The unit of analysis remains the original 95 setup identities.
- `BASE_F50`: one leg.
- `EXIT_ONLY`: one leg ending at deep exit when triggered.
- `EXIT_REENTRY`: total setup PnL = first-leg PnL + second-leg PnL when re-entry occurs.
- Setup WIN = total setup PnL > 0.
- Setup LOSS = total setup PnL < 0.
- WR, PF, expectancy, net, and max loss streak are calculated at setup level, not leg level.

## Required diagnostics
For every variant and major partition plus pooled major:
- N, WR, PF, expectancy, net, max loss streak;
- 5bps WR/PF/expectancy/net;
- deep-exit count;
- re-entry count;
- no-reclaim count;
- missed-target-at-open / invalid-below-F50 counts;
- number of deep-exit setups salvaged back to positive total PnL after re-entry.

## Frozen formal economic screen
Only `F80_EXIT_REENTRY` and `F75_EXIT_REENTRY` may promote.
A variant passes only if:
1. audit PASS and exact M8 BASE_F50 parity;
2. each external/development/reference_validation N >= 15;
3. each major partition nominal WR >= 70%;
4. each major partition nominal PF >= 1.20;
5. each major partition nominal expectancy > 0 and net > 0;
6. pooled-major nominal WR >= 70%, PF >= 1.20, expectancy > 0, net > 0;
7. pooled-major 5bps PF > 1.00 and net > 0.

Ranking among formal passes is WR-first, then PF, expectancy, 5bps PF.

## Mandatory assertions
1. Exact 95 M5/M10 cohort identities.
2. BASE_F50 reproduces M8 E15/F50 partition and pooled metrics within numerical tolerance.
3. Deep exit is never known before the breach candle completes.
4. Re-entry bar is strictly after reclaim bar.
5. No more than one re-entry per setup.
6. No data after 20:00 UTC are used.
7. Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.