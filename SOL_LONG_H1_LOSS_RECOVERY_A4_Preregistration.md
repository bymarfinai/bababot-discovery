# SOL LONG H1 Loss Recovery — A4 Preregistration

## Purpose
A4 asks whether a frozen A2 loser can be converted into a profitable **combined episode** by a causal second-chance LONG entry on a later distinct visit to the same reference High.

This stage does **not** change the A2 parent trade. The A2 `E0_RESTING_H -> E40` outcome remains frozen. A4 adds at most one recovery trade after the parent loss has already been realized.

The objective is actual economics, not H-visit rate.

## Frozen parent
- Branch: `research/sol-long-structure-a1-run`.
- Parent: A2 `E0_RESTING_H -> E40`.
- Central habitat: reference 240m, execution 18:00 UTC.
- Support habitats remain 240m/17:00 and 180m/18:00.
- Reference levels `[L,H]`, `R = H-L` stay exactly the parent levels.
- Parent entry and exit are not rescored or modified.
- Parent loser cohort: frozen A2 trades with `pnl <= 0`.
- Target remains exactly `H + 0.40R`.
- Notional and 5bps stress remain exactly A2 conventions.

## Recovery watch
Recovery observation begins at the **parent exit timestamp**, when the parent position is flat.

A fixed recovery watch horizon of **720 minutes after the parent exit** is used. This mirrors the frozen A1/A2 720-minute lifecycle and is not selected from A4 results.

The same reference `[L,H]` remains active only for this recovery watch. A4 does not roll or rebuild the reference.

## Distinct visit numbering
Starting from the original A2 H1 episode, visits to `H` are counted as distinct episodes:
- a visit episode contains one or more contiguous 5m bars with `high >= H`;
- a new visit can begin only after at least one completed 5m bar with `high < H`;
- original A2 fill episode is `H1`;
- subsequent episodes are `H2`, `H3`, `H4`, ... chronologically.

A recovery entry on visit `Hj` is eligible only if the first bar of that visit starts at or after the parent exit timestamp. Visits that occurred while the parent position was still open cannot be used as recovery entries.

## Preregistered recovery entry family
Only three canonical second-chance entries are tested:
1. `REC_H2`: resting LONG at `H` on eligible H2.
2. `REC_H3`: resting LONG at `H` on eligible H3.
3. `REC_H4`: resting LONG at `H` on eligible H4.

There are no nearby fractional entries, no extra visit numbers, and no post-result substitution.

If a visit bar opens above `H`, the recovery stop-market fill is conservatively modeled at that bar's open; otherwise a touch `high >= H` fills at `H`.

## Recovery trade lifecycle
From recovery entry until the fixed recovery-watch end:
- Target: `H + 0.40R`.
- Before any completed 5m close `> H`, a completed close `< L` is `REFERENCE_INVALIDATION`; exit next 5m open when available.
- After the first completed 5m close `> H`, the breakout is confirmed; a later completed close `<= H` is `FAILED_BREAK`; exit next 5m open when available.
- If neither target nor invalidation occurs by the recovery-watch end, exit at the final completed close (`TIME`).
- As in A2, target is not credited on the recovery entry bar; target evaluation begins on the following 5m bar.
- One recovery trade maximum per parent loser per tested visit lane.

## Economics and definitions
For each recovery lane report:
- eligible parent losers;
- recovery trade N;
- recovery WR, PF, expectancy, net;
- 5bps WR, PF, expectancy, net;
- parent-loss dollars represented by the recovery cohort;
- combined episode PnL = `parent_pnl + recovery_pnl`;
- **episode rescue rate** = share with combined episode PnL `> 0`;
- combined episode PF/expectancy/net within the eligible loser cohort;
- overall strategy net/PF if the recovery overlay is added to the frozen A2 parent trades.

A recovery trade that is green but leaves `parent_pnl + recovery_pnl <= 0` is **not** counted as a rescued loss.

## Development selection
The Development central cohort is the only selection surface.

A lane is eligible only if:
- recovery N >= 40;
- recovery PF > 1.15;
- recovery expectancy > 0;
- 5bps recovery PF > 1.00;
- 5bps recovery expectancy > 0;
- episode rescue rate >= 25%;
- recovery net > 0;
- at least 4 of 6 Development half-year blocks with adequate N >= 5 have positive recovery net.

Among passing lanes choose, in order:
1. highest 5bps combined-episode net improvement;
2. highest episode rescue rate;
3. highest 5bps recovery PF;
4. highest recovery PF;
5. lower visit number.

If no lane passes, A4 fails and OOS recovery economics are not used to select a substitute.

## OOS
Only the frozen Development winner may be evaluated on:
- Central External;
- Central Reference Validation;
- 240m/17:00 support External and Reference Validation;
- 180m/18:00 support External and Reference Validation.

Support/OOS is diagnostic validation only; it cannot change the selected visit.

## A4 support gate
A4 is supported only if the frozen lane has:
- positive recovery net on Central External and Central Reference Validation;
- positive 5bps recovery net on Central External and Central Reference Validation;
- positive overall-strategy net improvement in both central OOS partitions;
- episode rescue rate > 0 in both central OOS partitions;
- positive recovery net in at least 3 of 4 topology-support OOS cells.

## Forensic recovery anatomy
Regardless of economic pass/fail, report for each parent loss class:
- share that later reaches `H + 0.40R` within 720m after parent exit;
- median minutes from parent exit to target;
- first post-parent canonical visit associated with the recovery path when observable;
- original parent loss magnitude distribution.

This anatomy is descriptive and cannot authorize post-hoc entry changes.

Research only. Live Baba Bot remains unchanged.
