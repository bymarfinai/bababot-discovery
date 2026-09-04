# SOL LONG H1 Early Invalidation — A6 Preregistration

## Purpose
A6 is the first trading intervention after A5. It targets the largest remaining damage source: **parent H1 attempts that have not established a breakout and are deteriorating inside the range**.

A5 showed that in Central Development, after the frozen H2 overlay:
- residual N = 287;
- true-failure proxy N = 157;
- true-failure proxy = 73.5% of residual gross-loss dollars;
- never-break classes L0/L1 = 70.3% of residual gross-loss dollars.

Therefore A6 does **not** add another retry. It asks whether a causal stale-parent failure boundary can cut loss dollars earlier while preserving the original winners.

## Frozen parent
- Parent remains A2 `E0_RESTING_H -> E40`.
- Reference, clock, entry, target `H + 0.40R`, partitioning, notional, and 5bps stress remain unchanged.
- A6 changes only the parent exit when a preregistered early-invalidation rule fires.
- A4 H2 recovery is **not recomputed or used for A6 selection**. This isolates whether parent loss can be improved causally. Integration with H2, if A6 is supported, is a later stage.

## Why these candidates
Only Central Development A5 fixed snapshots were used to define the family.

At +30m while observable:
- good-union median close = `H - 0.060R`;
- true-failure proxy median close = `H - 0.120R`;
- good-union median running MFE = `0.116R`;
- true-failure proxy median running MFE = `0.065R`.

At +60m:
- good-union median close = `H - 0.108R`;
- true-failure proxy median close = `H - 0.216R`;
- good-union median running MFE = `0.095R`;
- true-failure proxy median running MFE = `0.057R`.

Thresholds below are rounded from those Development medians. OOS was not used to choose them.

## Preregistered candidate family
A rule can fire only if the parent position is still open after the snapshot close and **no completed 5m close > H has occurred** from entry through that snapshot.

1. `P30_D12`
   - snapshot +30m;
   - close `<= H - 0.12R`.

2. `P30_D12_M07`
   - same as `P30_D12`;
   - running MFE through +30m `<= 0.07R`.

3. `P60_D22`
   - snapshot +60m;
   - close `<= H - 0.22R`.

4. `P60_D22_M06`
   - same as `P60_D22`;
   - running MFE through +60m `<= 0.06R`.

No nearby thresholds, no additional times, and no OOS retuning are allowed.

## Causal execution
When a candidate fires on the completed snapshot bar:
- exit the parent at the **next 5m open** when available;
- do not credit intrabar information after the snapshot close;
- if the frozen parent already exited before or on the snapshot bar, the candidate cannot act;
- all non-triggered trades retain their frozen A2 outcome exactly.

## Development metrics
For each lane report:
- parent N (must equal baseline);
- triggered N and trigger rate;
- original winners triggered;
- original losers triggered;
- winner preservation rate = share of frozen raw parent winners that remain raw winners after intervention;
- gross-loss dollars and gross-loss reduction;
- PF, expectancy, net;
- 5bps PF, expectancy, net;
- net improvement vs frozen parent;
- 5bps net improvement vs frozen parent;
- six Development half-year block net improvements.

## Development gate
A lane is eligible only if:
- N parity is exact;
- raw net improvement > 0;
- 5bps net improvement > 0;
- PF improves vs frozen parent;
- 5bps PF improves vs frozen parent;
- gross-loss dollars decrease;
- winner preservation >= 95%;
- at least 4 of 6 Development blocks with adequate sample have non-negative net improvement;
- no single Development block loses more than $25 versus baseline due to the intervention.

Among eligible lanes choose in order:
1. highest 5bps net improvement;
2. highest raw net improvement;
3. highest winner preservation;
4. largest gross-loss reduction;
5. simpler rule (depth-only before depth+MFE);
6. later snapshot if otherwise tied.

If no lane passes, A6 fails and OOS cannot supply a substitute.

## Frozen OOS validation
Only the frozen Development winner is then evaluated on:
- Central External;
- Central Reference Validation;
- 240m/17:00 support External and Reference Validation;
- 180m/18:00 support External and Reference Validation.

A6 is supported only if:
- Central External and Central Reference Validation both have positive raw and 5bps net improvement vs their frozen parent baselines;
- winner preservation >= 93% in both central OOS cells;
- gross-loss dollars decrease in both central OOS cells;
- at least 3 of 4 support OOS cells have non-negative raw net improvement;
- at least 3 of 4 support OOS cells have non-negative 5bps net improvement.

OOS cannot alter the rule.

## Interpretation
A6 is a **loss-shrinking** experiment. It is successful if true failures become cheaper without destroying the continuation winners. It is not expected to turn every loser into a winner.

Research only. Live Baba Bot remains unchanged.
