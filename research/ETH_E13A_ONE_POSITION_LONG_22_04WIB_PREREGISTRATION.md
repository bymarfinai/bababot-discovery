# ETH E13A — One-Position Sequential LONG Execution Discovery Preregistration

## Purpose
Move from E12 opportunity-level character discovery to a causal execution simulation that matches the intended live constraint: **only one ETH LONG position may be active at a time**. Once a position is opened, every later qualifying signal is ignored until that position is closed; only then may the executor re-arm.

This is a new execution-discovery experiment. It does not retroactively promote any E12 near-miss and does not change any E12 verdict.

## Frozen research scope
- Pair: ETHUSDT.
- Direction: LONG only.
- Partition: Development only. OOS / external / reference-validation remain unopened.
- Search window: **22:00–04:00 WIB**, i.e. quarter-hour clocks from 15:00 through 20:45 UTC.
- Entry price: open of the causal 5-minute bar at the qualifying quarter-hour timestamp, identical to the E12 entry convention.
- Only one position active at a time.
- While a position is active, all qualifying later signals are skipped and recorded as busy-position skips.
- Re-arm only after the prior position has causally closed.
- Fee model remains E12: $500 notional and $0.75 round-trip fee per accepted trade.
- No SHORT.
- No stop-loss search in E13A.
- No TP percentage optimization in E13A.
- No post-result coordinate rescue.

## Frozen E12-derived entry characters
E13A transfers only the already-observed hour-native entry characters. Their E12 statuses remain unchanged.

### Formal-only policy
Use only the four E12 full-gate LONG hours in this range:
1. 23:00–00:00 WIB: `DRIVE_UP__STR_B60_80`, LB60 (E12K formal winner).
2. 00:00–01:00 WIB: `EFF_LOW__RANGE_HIGH`, LB30 (E12L formal winner).
3. 01:00–02:00 WIB: `EFF_HIGH__RV_LOW`, LB240 (E12M formal winner).
4. 03:00–04:00 WIB: `RV_HIGH__RANGE_MID`, LB360 (E12O formal winner).

### Formal-plus-near-miss policy
Use the same four formal winners plus two preregistered descriptive near-miss entry characters:
5. 22:00–23:00 WIB: `RV_MID__RANGE_HIGH`, LB120 (E12J high-WR cross-era clue; still formally FAIL in E12).
6. 02:00–03:00 WIB: `EFF_HIGH__RV_HIGH`, LB360 (E12N strongest robust near-miss; still formally FAIL in E12).

Including these two rows in E13A is a new, explicitly preregistered execution experiment; it must not be described as changing their E12 status.

## Exit semantics: first causal net-positive close
The intended live behavior is "one trade until it becomes profitable, then close." To make that testable without an infinite-hold backtest:

1. After entry, inspect only **completed 5-minute closes** in chronological order.
2. Compute LONG gross PnL on $500 notional from the frozen entry price to that completed close.
3. Subtract the frozen $0.75 round-trip fee.
4. Exit at the **first completed 5-minute close whose net PnL is strictly > $0**.
5. If no such close occurs before the preregistered maximum holding horizon, force-close at the completed 5-minute close exactly at the maximum horizon and record `TIMEOUT`.
6. No wick/intrabar TP assumption is permitted in E13A.
7. A signal whose timestamp occurs while the prior position is still active is skipped; it cannot be backfilled later.

## Maximum-hold discovery grid
Test exactly:
- 240m (4h)
- 480m (8h)
- 720m (12h)
- 960m (16h)
- 1440m (24h)
- 2160m (36h)
- 2880m (48h)

Cross with the two entry policies above for exactly **14 execution candidates**.

## Boundary integrity
For a candidate maximum hold H, accept an entry only when the full H-minute observable path remains inside the Development partition. This prevents a Development-selected candidate from borrowing future prices outside Development even if the realized trade would have closed earlier.

## Metrics
For each of the 14 candidates persist at least:
- candidate signals;
- accepted sequential trades;
- busy-position skipped signals;
- acceptance rate;
- net-positive exits / win rate;
- timeout trades / timeout rate;
- net PnL;
- expectancy;
- PF;
- max drawdown;
- max loss streak;
- mean / median / p75 / p90 trade duration;
- mean timeout PnL;
- 2022 / 2023 / 2024 N, WR, net, expectancy, PF;
- accepted trade count by source hour/character.

Persist the exact accepted trade ledger for the Development-selected candidate.

## Frozen E13A promotion gate
An E13A candidate is a formal execution passer only if all are true:

### Pooled sequential gate
- accepted trades >= 150;
- WR >= 80%;
- net PnL > 0;
- expectancy >= $0.50/trade;
- PF >= 1.50;
- max DD <= $125;
- max loss streak <= 4;
- timeout rate <= 20%.

### Cross-era gate
For each of 2022, 2023, 2024:
- accepted trades >= 40;
- WR >= 75%;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.30.

And at least two of the three years must have WR >= 80%.

## Frozen ranking among formal passers
Rank by, in order:
1. highest minimum yearly expectancy;
2. lowest timeout rate;
3. lowest max DD;
4. highest PF;
5. highest pooled expectancy;
6. highest WR;
7. lower p90 duration;
8. lower maximum hold;
9. `FORMAL_ONLY` before `FORMAL_PLUS_NEARMISS` only as the final deterministic tie-break.

If no candidate passes, report the strongest near-miss descriptively without relaxing any threshold.

## Interpretation boundary
E13A answers whether the E12-derived 22:00–04:00 LONG habitat can be converted into a sequential one-position executor when positions close at the first causal net-positive 5-minute close subject to a finite timeout.

It does **not** answer:
- optimal SHORT behavior;
- production TP/SL;
- leverage or sizing;
- OOS validity;
- live readiness;
- whether a near-miss entry character should be promoted at the E12 character-discovery layer.

Research/shadow only.