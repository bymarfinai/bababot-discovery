# ETH London -> New York M14 F75 H2-State Conditional Exit — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
M13 showed that unconditional F75 de-risk reduces Development losses but sacrifices too much win rate. M14 tests one natural lifecycle state only: **whether H2 has already occurred when the first completed-close F75 breach is observed**.

The goal is to determine whether one side of that binary structural state can support a conditional full exit while preserving the high-WR F90 EARLY_RECLAIM setup.

## Frozen setup
- ETHUSDT perpetual, raw 5m.
- Exact M5 F90 EARLY_RECLAIM executed cohort: 95 setups.
- Original entry unchanged.
- Target: E15 = H + 0.15R.
- Hard invalidation: first completed 5m close < F50.
- Session time exit unchanged.
- $500 notional; $0.40 round-trip fee model; 5bps stress unchanged.
- Baseline economics must reproduce M8 E15/F50 exactly.

## Frozen F75 event
- F75 = L + 0.75R.
- Candidate event = first completed 5m candle with close < F75, provided E15 has not already traded and that candle has not already closed below F50.
- H2 is the frozen lifecycle event `high >= H` after the causal leave; exact persisted M5/M10 H2 identity is used.
- At the completion of the F75-breach candle, classify exactly one state:
  1. `PRE_H2`: no H2 bar has occurred yet (`h2_bar_start` missing or strictly later than the F75-breach bar).
  2. `H2_SEEN`: H2 occurred on an earlier bar or on the same F75-breach bar (`h2_bar_start <= breach_bar_start`).
- Same-bar H2 + F75 close is therefore causally known only after the candle completes and belongs to `H2_SEEN`.

## Frozen execution
A conditional exit is never filled on the F75-breach candle itself. It executes at the **next raw 5m open** after the qualifying completed candle. If no next bar exists before session end, no special exit occurs and baseline lifecycle continues to time exit.

No re-entry, partial cut, add-back, trailing stop, post-breakout floor, additional level, timeout, or indicator is allowed.

## Frozen variants
1. `BASE_F50`: unchanged E15/F50 benchmark.
2. `F75_PRE_H2_EXIT`: full exit at next 5m open only when first F75 breach state = `PRE_H2`; H2_SEEN breaches remain on baseline E15/F50 lifecycle.
3. `F75_POST_H2_EXIT`: full exit at next 5m open only when first F75 breach state = `H2_SEEN`; PRE_H2 breaches remain on baseline E15/F50 lifecycle.

These are exhaustive complementary states of one preregistered structural variable. No additional state split may be added after inspection.

## Same-bar precedence
Within each raw 5m bar:
1. resting E15 target hit (`high >= E15`) wins first;
2. completed-close F50 invalidation (`close < F50`) applies next;
3. only otherwise can a completed-close F75 conditional-exit event arm for the next bar open.

## Required telemetry
By external / development / reference_validation / pooled-major, report:
- N, WR, PF, expectancy, net, max loss streak;
- 5bps WR/PF/expectancy/net;
- F75 breach count;
- PRE_H2 vs H2_SEEN breach count;
- conditional exit count;
- conditional-exit winner/loser count under baseline identity;
- average PnL delta versus baseline on baseline winners and baseline losers.

## Frozen promotion screen
A conditional candidate is supported only if all are true:
1. Audit PASS and pooled N = 95.
2. Every major partition N >= 15.
3. Every major partition WR >= 70% at 0bps.
4. Development PF >= 1.00, expectancy > 0, net > 0 at 0bps.
5. External and reference-validation PF > 1.00 and net > 0 at 0bps.
6. Pooled WR >= 72%, PF >= 1.30, expectancy > 0, net > 0 at 0bps.
7. Pooled 5bps PF > 1.00 and net > 0.

If both complementary candidates pass, rank by Development PF, then Development WR, pooled WR, pooled 5bps PF.

## Mandatory audits
- Exact M8 E15/F50 baseline parity: exit reason/timestamp/price/PnL.
- Exact M5/M10 95-row cohort identity.
- H2-state assignment uses only persisted causal H2 timestamps.
- Conditional exit is strictly after F75 breach completion.
- At most one conditional exit per setup.
- Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.
