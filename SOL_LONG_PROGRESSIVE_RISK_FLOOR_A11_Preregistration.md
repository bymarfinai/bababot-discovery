# SOL LONG Progressive Risk Floor — A11 Preregistration

## Purpose
A11 tests the user's hybrid exit hypothesis on the **currently supported SOL stack only**:

`A2 E0_RESTING_H -> E40 + A4 REC_H2`.

A6 early invalidation, A8 reclaim re-entry, and A10 persistence re-entry remain rejected and absent.

The hypothesis is not an earlier static stop. The existing lifecycle already exits a confirmed breakout after a completed close `<= H`. A11 therefore asks whether a **ratcheting profit floor above H**, activated only after the trade has already produced meaningful favorable excursion, can improve exit efficiency.

Goal:

> once SOL has paid enough favorable excursion, progressively reduce how much of that progress can be given back, while still leaving E40 continuation room.

## Frozen context
- Parent: A2 `E0_RESTING_H -> E40`.
- Recovery: A4 `REC_H2` only.
- Target remains `H + 0.40R`.
- Same reference `[L,H]`, clocks, partitions, 720-minute lifecycle/recovery watch, notional, and 5bps stress.
- No new entry, no new H visit, no H3/H4 retry, no indicator, no regime filter.
- Frozen A4 H2 entry timestamps are retained. A11 may suppress an H2 recovery only if its parent episode becomes raw-profitable under the ratchet. A11 does **not** create newly eligible H2 entries from an earlier ratchet exit; this is conservative and isolates exit efficiency.

## Causal ratchet semantics
For both the parent trade and a retained H2 recovery trade:
1. target evaluation keeps the frozen baseline priority;
2. running MFE is updated only from completed/observed 5m bars;
3. a ratchet can activate only after at least one completed 5m close `> H` has confirmed the breakout;
4. the current ratchet floor is non-decreasing;
5. if a completed close is `<= active_floor`, exit at the next 5m open when available;
6. frozen reference invalidation / failed-break / time exits remain active and can still exit first;
7. target is never lowered and E40 remains the full target.

Thus A11 never uses future MFE and never credits a floor intrabar.

## Preregistered family
Milestones are canonical fractions of the frozen E40 target; they are not selected from A9/A10 OOS results.

### `RF_LOOSE`
- once running MFE >= `0.20R`: floor = `H + 0.05R`;
- once running MFE >= `0.30R`: floor = `H + 0.15R`.

### `RF_BALANCED`
- once running MFE >= `0.15R`: floor = `H + 0.05R`;
- once running MFE >= `0.25R`: floor = `H + 0.15R`;
- once running MFE >= `0.35R`: floor = `H + 0.25R`.

### `RF_TIGHT`
- once running MFE >= `0.10R`: floor = `H + 0.05R`;
- once running MFE >= `0.20R`: floor = `H + 0.10R`;
- once running MFE >= `0.30R`: floor = `H + 0.20R`.

### `RF_GIVEBACK15`
After running MFE first reaches `0.20R`, use a continuously ratcheting close floor:

`floor_R = max(0.05, running_MFE_R - 0.15)`

so a trade that has reached 0.20R protects at least +0.05R, at 0.30R protects about +0.15R, and the floor continues rising with additional completed-bar MFE. The E40 target still has priority.

No nearby milestones, floor levels, giveback values, or post-result substitutions are allowed.

## Development evaluation
Central Development is the only selection surface.

Report for each lane:
- exact parent N parity;
- parent ratchet triggers;
- retained H2 recovery N;
- original raw winners preserved as raw winners;
- newly negative original winners;
- parent WR;
- episode WR, PF, expectancy, net and gross loss;
- trade-stack PF/net for parent + retained H2;
- all corresponding 5bps metrics;
- improvement versus the frozen A2+A4 H2 stack;
- six Development half-year block improvements.

### Development gate
A lane is eligible only if:
- parent N parity is exact;
- raw and 5bps stack net both improve versus frozen A2+A4 H2;
- raw and 5bps stack PF both improve;
- episode gross-loss dollars do not increase;
- episode raw WR does not decrease;
- at least 98% of frozen raw parent winners remain raw winners;
- at least 4 of 6 adequate Development blocks have positive raw stack-net improvement;
- at least 4 of 6 adequate Development blocks have positive 5bps stack-net improvement.

Among passing lanes choose, in order:
1. highest 5bps stack-net improvement;
2. highest raw stack-net improvement;
3. highest episode WR improvement;
4. highest 5bps stack PF;
5. simpler fixed ladder before continuous giveback when otherwise tied.

If no lane passes, A11 fails and OOS cannot supply a substitute.

## Frozen OOS validation
Only the frozen Development winner may be evaluated on:
- Central External;
- Central Reference Validation;
- 240m/17:00 support External and Reference Validation;
- 180m/18:00 support External and Reference Validation.

A11 is supported only if:
- Central External and Central Reference Validation both have positive raw and 5bps stack-net improvement;
- raw and 5bps stack PF do not decrease in either central OOS cell;
- episode gross loss does not increase in either central OOS cell;
- parent raw-winner preservation >= 97% in both central OOS cells;
- at least 3 of 4 support OOS cells have positive raw stack-net improvement;
- at least 3 of 4 support OOS cells have positive 5bps stack-net improvement.

OOS cannot alter the frozen ratchet.

## Interpretation
A11 is an exit-efficiency experiment, not a new entry system. Success means favorable excursion is harvested more efficiently without materially clipping the SOL continuation edge.

Research only. Live Baba Bot remains unchanged.
