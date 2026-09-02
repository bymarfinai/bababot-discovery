# ETH London -> New York M13 F75 Partial De-risk — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Test whether the M12 finding at F75 can improve Development economics **without sacrificing the baseline win rate through a full exit**. M13 reduces only part of the open position after a completed-close F75 breach and leaves the remainder on the frozen E15/F50 lifecycle.

## Frozen setup
- ETHUSDT perpetual, raw 5m.
- Exact M5 F90 EARLY_RECLAIM executed cohort: 95 setups.
- Original entry unchanged.
- Target: E15 = H + 0.15R.
- Hard invalidation: first completed 5m close < F50.
- Session time exit unchanged.
- $500 initial notional.
- Baseline economics must reproduce M8 E15/F50 exactly.

## F75 de-risk event
- F75 = L + 0.75R.
- A de-risk event occurs on the first completed 5m candle with close < F75, provided E15 has not already traded and the same completed candle has not closed below F50.
- The event becomes actionable only after that 5m candle completes.
- Partial reduction executes at the **next raw 5m open**.
- Only one F75 reduction is allowed per setup.
- The residual position remains open with the original E15 target, completed-close F50 invalidation, and session-end exit.
- No re-entry, add-back, trailing stop, post-breakout floor, or second reduction is allowed.

## Frozen variants
1. `BASE_F50`: no F75 reduction.
2. `F75_CUT25`: close 25% of original notional at the causal next-open after F75 breach; retain 75%.
3. `F75_CUT50`: close 50%; retain 50%.
4. `F75_CUT75`: close 75%; retain 25%.

No other fractions may be added after result inspection.

## Cost semantics
- Base fee model remains $0.40 per full $500 round trip.
- For split position accounting, fee is allocated proportionally by notional fraction so the fractions sum to the same $0.40 total fee; M13 introduces no extra re-entry turnover.
- 5bps stress is applied independently to each executed entry/exit price on the corresponding position fraction.

## Outcome and metrics
A setup is a win only when its **combined setup-level PnL** across the reduced piece and residual piece is > 0.

Report by external / development / reference_validation / pooled-major:
- N, WR, PF, expectancy, net, max loss streak;
- 5bps WR/PF/expectancy/net;
- number of F75 de-risk events;
- average realized loss saved on baseline losers;
- average profit surrendered on baseline winners.

## Frozen promotion screen
A partial de-risk variant is supported only if all are true:
1. Audit PASS and N parity = 95 pooled.
2. Every major partition N >= 15.
3. Every major partition WR >= 70% at 0bps.
4. Development PF >= 1.00, expectancy > 0, and net > 0 at 0bps.
5. External and reference-validation PF > 1.00 and net > 0 at 0bps.
6. Pooled WR >= 72%, PF >= 1.30, expectancy > 0, and net > 0 at 0bps.
7. Pooled 5bps PF > 1.00 and net > 0.

If multiple variants pass, rank by Development PF, then Development WR, then pooled WR, then pooled 5bps PF.

## Mandatory audits
- Exact M8 E15/F50 baseline exit reason/timestamp/price/PnL parity.
- F75 reduction occurs only after completed-close F75 breach and before residual exit.
- At most one reduction per setup.
- Reduced fraction + residual fraction = 1.0.
- Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.