# BTC Weekly Value-Area Breakout B15 — Preregistration

## Question
Can a causal breakout of transaction-memory value-area boundaries provide a robust BTC setup: **VAH break -> LONG** and **VAL break -> SHORT**?

This study is intentionally different from B13, which treated VAH/VAL primarily as support/resistance reaction levels. B15 tests continuation through the boundary.

## Data and partitions
- Instrument: Binance USD-M BTCUSDT perpetual.
- Source data: official Binance futures 15m klines, aggregated to H1 for execution.
- Load range: 2019-09-01 through 2026-08-19/20 as available.
- External untouched test: 2020-01-01 through 2021-12-31 complete ISO weeks.
- Development: 2022-01-01 through 2024-12-31 complete ISO weeks.
- Reference validation untouched test: 2025-01-01 through 2026-07-29 complete ISO weeks.
- August 2026 is diagnostic only.

## Causal value-area construction
For completed source periods on H1, H4, D1, and W1:
- Build a 24-bin volume profile from underlying 15m typical prices weighted by volume.
- POC is the highest-volume bin.
- Value area expands from POC toward the larger adjacent-volume bin until 70% of period volume is included.
- VAL and VAH are the resulting value-area boundaries.
- A level becomes usable only after its source period is complete.
- No future bars may affect a level used by a signal.

## Frozen breakout setup
Execution timeframe is H1.

For each source timeframe TF in {H1,H4,D1,W1}:

### VAH_BREAK_LONG
At completed H1 signal bar i:
1. the active causal VAH(TF) exists at the start of bar i;
2. H1 open_i <= VAH;
3. H1 close_i > VAH.

Then enter LONG at H1 open_(i+1).

### VAL_BREAK_SHORT
At completed H1 signal bar i:
1. the active causal VAL(TF) exists at the start of bar i;
2. H1 open_i >= VAL;
3. H1 close_i < VAL.

Then enter SHORT at H1 open_(i+1).

No post-hoc minimum breakout-distance filter, retest requirement, wick filter, EMA filter, or volume filter is allowed in B15 V1.

## First-break semantics
For each active source-period level instance and side, keep only the **first qualifying H1 breakout** while that level instance is active. This avoids repeatedly trading the same boundary after it has already been broken.

## Weekly routing
- Scan from Monday 00:00 UTC through Saturday 12:00 UTC.
- Maximum one trade per ISO week.
- Each atomic rule is evaluated by taking its first qualifying breakout that week.
- Development ranks atomic rules using: full weekly coverage first, then WR, Wilson lower bound, PF, N.
- Freeze the top development atomic rule as PRIMARY_RULE.
- Also freeze a TOP4_ROUTER using up to four development-ranked rules with distinct (source_tf, boundary) pairs; the chronologically first qualifying signal wins, ties by frozen rank.
- **No forced fallback**. Missing weeks remain missing and reduce coverage.

Atomic rule universe is fixed before results:
- H1|VAH_BREAK_LONG
- H1|VAL_BREAK_SHORT
- H4|VAH_BREAK_LONG
- H4|VAL_BREAK_SHORT
- D1|VAH_BREAK_LONG
- D1|VAL_BREAK_SHORT
- W1|VAH_BREAK_LONG
- W1|VAL_BREAK_SHORT

## Execution economics
- Entry: next H1 open after completed breakout signal.
- Fee model: 0.15% round-trip.
- Net TP target: +1.00%.
- Net loss target: -1.00%.
- Therefore price barriers are +1.15% favorable and -0.85% adverse (mirrored for short).
- Same-bar TP+SL ambiguity: adverse-first.
- Exit horizon: end of same ISO week.
- No overlapping second weekly trade.

## Acceptance gates
### B15_ROBUST_WEEKLY_100
Must pass on BOTH external and reference-validation:
- coverage = 100%;
- exactly one selected trade per complete week;
- TP WR = 100%;
- zero losing weeks / max losing streak 0;
- positive expectancy;
- PF > 1;
- all four chronological blocks positive.

### B15_HIGH_PRECISION_WEEKLY
Secondary diagnostic only, BOTH external and validation:
- coverage = 100%;
- TP WR >= 80%;
- positive expectancy;
- PF > 1;
- max losing streak <= 2;
- at least 3 of 4 chronological blocks positive.

## Research discipline
- Development only selects/fixes PRIMARY_RULE and TOP4_ROUTER.
- No OOS retuning or post-hoc rescue belongs to B15 V1.
- If B15 fails, any retest/acceptance/breakout-strength extension must be a separately preregistered experiment.
- Live BBC remains untouched.
