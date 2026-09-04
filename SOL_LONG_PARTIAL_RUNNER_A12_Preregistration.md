# SOL LONG Partial Profit + Progressive Runner Floor — A12 Preregistration

## Purpose
A12 follows the rejected A11 full-position ratchet experiment on the currently supported SOL stack only:

`A2 E0_RESTING_H -> E40 + A4 REC_H2`.

A11 established a useful fact: progressive floors can raise episode WR and reduce gross-loss dollars, but full-position ratchet exits clip too much continuation payoff and reduce stack PF/net. A12 therefore tests a narrower hybrid hypothesis:

> realize only part of the position at a native extension milestone, keep a runner for E40, and protect only that runner after further favorable progress.

A6, A8, A10, and A11 remain rejected and absent from the supported stack.

## Frozen context
- Parent: A2 `E0_RESTING_H -> E40`.
- Recovery: A4 `REC_H2` only.
- Full target remains `H + 0.40R`.
- Same reference `[L,H]`, clocks, partitions, lifecycle/recovery watch, notional, and 5bps stress conventions.
- No new entry, no H3/H4 retry, no indicator, no regime filter.
- Frozen A4 H2 entry timestamps are retained.
- If an A12-modified parent becomes raw-profitable, its H2 recovery is conservatively suppressed exactly as in A11. A12 does not create a newly eligible H2 from an earlier candidate exit.

## Causal partial semantics
For parent and retained H2 recovery trades:
1. the position begins at 100% of frozen notional;
2. partial target is evaluated only from bars after the frozen entry bar, using observed high;
3. when E20 (`H + 0.20R`) is first touched, the preregistered fraction is realized exactly at E20;
4. the remaining fraction stays active toward the unchanged E40 target;
5. frozen reference invalidation / failed-break / time lifecycle remains active on the remaining fraction;
6. candidate runner floors use completed-bar information only and exit at the next 5m open when triggered;
7. E40 target has priority on each bar over a runner-floor close exit;
8. no future MFE or intrabar floor information is used.

The total candidate return is the notional-weighted sum of realized partial return plus runner return. The existing 5bps stress is applied once to the full weighted trade return, preserving A2/A4 stress convention rather than charging artificial extra full-notional costs for a split exit.

## Preregistered family
E20 and E40 are explicit Stage-11 canonical exit candidates in the pair-native protocol. Partial fractions are intentionally coarse. Runner protection is derived from the looser A11 concept but activates only after the runner has progressed beyond the partial milestone.

### `PP20_25`
- realize 25% at E20;
- keep 75% runner to E40;
- runner otherwise follows frozen lifecycle with no added floor.

### `PP20_50`
- realize 50% at E20;
- keep 50% runner to E40;
- runner otherwise follows frozen lifecycle with no added floor.

### `HY20_25`
- realize 25% at E20;
- keep 75% runner to E40;
- after completed-bar running MFE reaches `0.30R`, runner floor becomes `H + 0.10R`;
- after running MFE reaches `0.35R`, runner floor becomes `H + 0.20R`.

### `HY20_50`
- realize 50% at E20;
- keep 50% runner to E40;
- same runner floors as `HY20_25`.

No nearby partial fractions, milestones, floor levels, or post-result substitutions are allowed.

## Development evaluation
Central Development is the only selection surface.

For each lane report:
- exact parent N parity;
- partial-hit N for parent and retained H2;
- runner-floor trigger N where applicable;
- retained H2 N;
- frozen parent raw-winner preservation;
- episode WR, PF, expectancy, net, and gross loss;
- trade-stack PF/net for modified parent + retained modified H2;
- all corresponding 5bps metrics;
- stack improvement versus frozen A2+A4 H2;
- six Development half-year block stack-net improvements.

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
3. highest 5bps stack PF;
4. highest episode WR;
5. simpler partial-only lane before hybrid runner-floor lane when otherwise tied;
6. smaller partial fraction when otherwise tied.

If no lane passes, A12 fails and OOS cannot provide a substitute.

## Frozen OOS validation
Only the frozen Development winner may be evaluated on:
- Central External;
- Central Reference Validation;
- 240m/17:00 support External and Reference Validation;
- 180m/18:00 support External and Reference Validation.

A12 is supported only if:
- Central External and Central Reference Validation both have positive raw and 5bps stack-net improvement;
- raw and 5bps stack PF do not decrease in either central OOS cell;
- episode gross loss does not increase in either central OOS cell;
- parent raw-winner preservation >= 97% in both central OOS cells;
- at least 3 of 4 support OOS cells have positive raw stack-net improvement;
- at least 3 of 4 support OOS cells have positive 5bps stack-net improvement.

OOS cannot alter the lane.

## Interpretation
A12 succeeds only if partial monetization preserves enough E40 continuation payoff to outperform the frozen A2+A4 stack after stress and across OOS. A WR increase by itself is not sufficient.

Research only. Live Baba Bot remains unchanged.
