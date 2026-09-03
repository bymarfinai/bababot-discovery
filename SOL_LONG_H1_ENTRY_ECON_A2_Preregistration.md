# SOL LONG H1 Entry Economics — A2 Preregistration

**Status:** PREREGISTERED after A1B established H1 as modal first-break visit and before A2 result-bearing execution.

## Objective
Answer the user's second question: **given that the first upside breakout most often occurs at H1, where should a causal LONG entry be placed to monetize that breakout?**

A2 evaluates actual trade economics. H1 rate is not an optimization target.

## Frozen structural parent
From A1/A1B, without retuning:
- LONG only;
- central habitat: reference R240, execution start 18:00 UTC;
- topology controls: R240 / 17:00 UTC and R180 / 18:00 UTC;
- observation horizon: 720 minutes;
- H/L/R definition unchanged;
- H1 = first distinct contiguous visit episode with `high >= H`;
- H1 breakout confirmation = first completed raw 5m close strictly above H during H1;
- A1B established H1 as modal first-break visit in 9/9 frozen role × partition combinations.

No alternate reference, clock, visit number, or session is searched in A2.

## Entry timing families
Four causal entry families are frozen before results:

### E0 — RESTING_H
A buy order at the already-known completed reference High `H` is active from execution start. It fills at H on the first H1 touch. Exit evaluation begins on the following raw 5m bar, so same-bar post-fill target path is never assumed.

### E1 — H1_TOUCH_NEXT_OPEN
Observe the completed first bar of H1 (`high >= H`), then enter at the next raw 5m open if it remains inside the 720m window.

### E2 — H1_BREAK_NEXT_OPEN
Observe the first completed 5m H1 candle with `close > H`, then enter at the next raw 5m open.

### E3 — H1_RETEST_RECLAIM_NEXT_OPEN
After completed H1 breakout confirmation, wait for the first later completed raw 5m candle whose `low <= H` and `close > H`; enter at the next raw 5m open. If no such retest/reclaim occurs, no trade.

These candidates intentionally cover pre-confirmation, touch-confirmation, breakout-confirmation, and post-break-retest timing. No F-level grid is introduced.

## Native target family
Targets are not copied from BTC/ETH.

Using **Development central H1 first-break events only**, calculate `extension_before_reclaim_R` exactly as A1. Derive three target candidates from Q35, Q50, Q65 of that distribution, rounded **down** to the nearest 0.05R, minimum 0.05R. Duplicate rounded levels are deduplicated.

Target price = `H + E*R`.

No alternative target may be substituted after this family is printed.

## Frozen lifecycle / invalidation
For every entry family and target:
1. Before an H1 breakout has been confirmed, structural invalidation occurs on the first completed 5m close strictly below `L`; exit at next raw 5m open.
2. Once H1 breakout has been confirmed, failed-break invalidation occurs on the first later completed 5m close `<= H`; exit at next raw 5m open.
3. Profit target uses intrabar high `>= H + E*R` starting from the first bar **after entry**. Fill is at the target price.
4. If neither target nor invalidation exits before the frozen 720m window ends, exit at the final completed 5m close.
5. If an invalidation close occurs on the final bar with no next open available, use the final close as time exit; do not fabricate a next bar.
6. One trade maximum per session per candidate. No re-entry.

For E2/E3 the H1 breakout is already confirmed at entry. For E0/E1 the state changes to confirmed only when a later completed H1 bar closes >H.

## Causality / ambiguous-bar rule
- Entries after observations always execute at the next raw 5m open.
- RESTING_H fills at H on first touch but target/exit evaluation begins only on the next bar.
- Completed-close invalidations execute next-open.
- If target is hit on a bar whose close also creates an invalidation, target is considered hit intrabar before a close-based invalidation can execute; this is live-reproducible because invalidation is not actionable until close.

## Economics
- Fixed notional: $500 per accepted trade.
- Gross return = `(exit_price / entry_price) - 1` for LONG.
- Gross PnL = gross return × $500.
- 5 bps stress subtracts 0.0005 from return per trade, matching the existing benchmark stress convention.
- Report N, trades/week, WR, PF, expectancy, net PnL, max loss streak, and 5bps PF/expectancy/net.

## Development selection
A candidate entry × target can be eligible only if:
- Development N >= 120;
- at least 5 of 6 half-year blocks have N >= 15;
- gross PF > 1.15 and expectancy > 0;
- 5bps PF > 1.00 and 5bps expectancy > 0;
- at least 4 of 6 adequately sampled blocks have gross PF > 1 and net > 0;
- no adequately sampled block has gross PF < 0.70.

Among eligible candidates choose, in order:
1. most profitable adequately sampled Development blocks;
2. highest minimum adequate-block PF;
3. highest Development 5bps PF;
4. highest Development gross PF;
5. highest Development expectancy;
6. higher N;
7. earlier entry-family order E0, E1, E2, E3;
8. smaller target.

If no candidate passes, A2 fails without OOS and without retuning.

## OOS gates
Only the frozen Development winner is evaluated on External and Reference Validation, first on central habitat and then the two frozen topology controls.

Central OOS requires in **each** partition:
- N >= 40;
- gross PF > 1.00;
- gross expectancy > 0;
- 5bps PF > 0.90;
- 5bps net PnL > -$10.

Topology support requires at least one of the two frozen support habitats to have gross PF >1 and net >0 in **both** OOS partitions using the exact frozen entry family and target.

No posthoc target, entry, clock, reference, or stop substitution is allowed.

## Required outputs
- `SOL_LONG_H1_ENTRY_ECON_A2_Result.md`
- `SOL_LONG_H1_ENTRY_ECON_A2_CANDIDATES.csv`
- `SOL_LONG_H1_ENTRY_ECON_A2_SELECTED.csv`
- `SOL_LONG_H1_ENTRY_ECON_A2_TRADES.csv`
- `SOL_LONG_H1_ENTRY_ECON_A2_Status.txt`

## Interpretation
A2 may identify a profitable H1 entry timing or fail. A structural H1 result is **not** sufficient for success; the winner must be selected and replicated on economic metrics.

Research only. Live Baba Bot remains unchanged.
