# SOL LONG E20 Conditional Protection — A14 Preregistration

## Purpose
A13 showed that, after a frozen SOL trade first reaches E20, continuation and stalling paths are observably different very early and that these differences replicate across Central External, Central Reference Validation, and support cells.

A14 converts only the strongest **discrete native states** into a small economic intervention family. It does not lower E40 universally and does not reintroduce A11/A12 universal profit protection.

Supported stack remains:

`A2 E0_RESTING_H -> E40 + A4 REC_H2`.

## Frozen context
- Parent: frozen A2.
- Recovery: frozen A4 `REC_H2` only.
- Rejected A6/A8/A10/A11/A12 remain absent.
- E40 stays the full continuation target.
- Same `[L,H]`, R, clocks, partitions, lifecycle/recovery windows, notional and 5bps stress.
- Persisted A4 H2 entries are retained only for candidate parent episodes that remain raw non-positive. No new H2 entry may be created by A14.

## A13 facts used
A14 uses only fixed, replicated A13 states:
- at the E20-touch anchor, continuations close materially stronger relative to E20 than stallers;
- within +5m and +10m, stallers are much more likely to close back to E10 or lower;
- these directions replicate in both Central OOS cells and broadly across support cells.

No A13 OOS value is used to choose a numerical threshold. Thresholds are the already-defined structural levels E20 and E10 and fixed 5m/10m clocks.

## Causal semantics
For parent and retained H2 trades:
1. frozen E40 target keeps priority if reached before a conditional signal can be acted upon;
2. `e20_i` is the first active 5m bar whose observed high reaches `H+0.20R`;
3. a signal based on a bar close can only execute at the **next 5m open**;
4. if the frozen trade would already exit at or before that next open, A14 cannot claim an earlier fill;
5. if no A14 signal occurs, the frozen exit and PnL are reproduced exactly;
6. no future MFE/outcome label is used.

## Preregistered family

### `CP_ANCHOR_FULL`
If the first E20-touch bar completes with `close < E20`, exit the full position at the next 5m open.

Interpretation: E20 was touched intrabar but not accepted on close.

### `CP_ANCHOR_HALF`
If the first E20-touch bar completes with `close < E20`, realize 50% at the next 5m open. The remaining 50% keeps the frozen lifecycle and full E40 target.

Interpretation: weaker intervention for the same immediately observable weak-E20 state.

### `CP_E10_5_FULL`
After first E20 touch, inspect only the next completed 5m bar. If that bar closes `<= E10` (`H+0.10R`), exit the full position at the following 5m open.

### `CP_E10_10_FULL`
After first E20 touch, inspect only the next two completed 5m bars (+5m and +10m). On the first completed close `<= E10`, exit the full position at the following 5m open.

No neighboring levels (E15/E12.5/etc.), alternative fractions, or alternative clocks may be substituted after seeing results.

## Development selection
Central Development is the only selection surface.

For each lane report:
- parent N parity;
- parent intervention count;
- retained H2 N and H2 intervention count;
- original raw winner preservation;
- episode WR, PF, expectancy, net and gross loss;
- parent+retained-H2 trade-stack PF/net;
- all 5bps metrics;
- improvement versus frozen A2+A4;
- six Development block improvements.

### Development gate
A lane is eligible only if:
- parent N parity exact;
- raw and 5bps stack net both improve;
- raw and 5bps stack PF both improve;
- episode gross-loss dollars do not increase;
- episode raw WR does not decrease;
- at least 98% of frozen raw parent winners remain raw winners;
- at least 4 of 6 adequate Development blocks have positive raw stack-net improvement;
- at least 4 of 6 adequate Development blocks have positive 5bps stack-net improvement.

Choose among passing lanes by:
1. highest 5bps stack-net improvement;
2. highest raw stack-net improvement;
3. highest episode WR improvement;
4. highest 5bps stack PF;
5. simpler full-state intervention before half-size tie-break only if economics are otherwise tied.

If none passes, A14 is rejected and OOS cannot supply a substitute.

## Frozen OOS validation
Only the frozen Development winner may be evaluated on:
- Central External;
- Central Reference Validation;
- CLOCK_SUPPORT External/Reference Validation;
- REF_SUPPORT External/Reference Validation.

Supported only if:
- both Central OOS cells have positive raw and 5bps stack-net improvement;
- raw and 5bps stack PF do not decrease in either Central OOS cell;
- episode gross loss does not increase in either Central OOS cell;
- raw parent-winner preservation >=97% in both Central OOS cells;
- at least 3/4 support cells have positive raw stack-net improvement;
- at least 3/4 support cells have positive 5bps stack-net improvement.

OOS cannot alter the frozen rule.

Research only. Live Baba Bot remains unchanged.
