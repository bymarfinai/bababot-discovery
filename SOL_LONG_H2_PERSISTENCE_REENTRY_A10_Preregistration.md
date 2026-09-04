# SOL LONG H2 Persistence-Confirmed Re-entry — A10 Preregistration

## Purpose
A10 is the economic intervention authorized by supported A9. A8 showed that the first reclaim close alone is too weak. A9 showed that genuine latent continuation is distinguished by **persistence above H after reclaim**, with the same direction replicated in Central External and Central Reference Validation.

A10 asks whether waiting for a small, preregistered acceptance state before re-entry can convert additional residual losers without the OOS collapse seen in A8.

## Frozen ancestry
- Parent remains A2 `E0_RESTING_H -> E40`.
- Frozen recovery remains A4 `REC_H2`.
- A6 early invalidation is rejected and absent.
- A8 RC30 is rejected and absent; it is not retuned.
- A9 is forensic only and supplies the acceptance state family below.
- Reference `[L,H]`, `R = H-L`, target `H + 0.40R`, partitions, recovery-watch end, notional, and 5bps stress remain unchanged.

## Eligible residual episode
A10 can act only when:
1. A2 parent is a loser (`parent_pnl <= 0`);
2. frozen A4 H2 recovery is eligible;
3. H2 did not end at `TARGET`;
4. combined A2 + H2 episode remains `<= 0`;
5. the first completed post-H2-exit reclaim close `> H` occurs inside the frozen A4 recovery watch.

The first reclaim is used. A10 cannot skip a false first reclaim and search for a later prettier reclaim.

## Why these state counts
A9 Central Development fixed snapshots showed:
- +10m: median closes `>H` = 3 for latent vs 2 for true failure;
- +15m: median closes `>H` = 4 vs 2;
- +30m: median closes `>H` = 7 vs 3;
- +15m E10 reached rate = 83.9% vs 43.9%.

The same latent>true direction replicated in both Central OOS cells. The family below uses only these rounded state counts and the preregistered E10 level. No OOS threshold was used.

## Preregistered acceptance family
The reclaim signal close counts as the first accepted close above H.

1. `AC10_C3`
   - observe through +10m after the reclaim signal;
   - require all 3 completed closes from signal through +10m to be `> H`.

2. `AC15_C4`
   - observe through +15m;
   - require all 4 completed closes from signal through +15m to be `> H`.

3. `AC15_C4_E10`
   - same 4/4 closes `> H` through +15m;
   - additionally require price to have reached `H + 0.10R` by that snapshot.

4. `AC30_C7`
   - observe through +30m;
   - require all 7 completed closes from signal through +30m to be `> H`.

No nearby close counts, no alternative time windows, no E05/E15/E20 substitution, and no post-result threshold edits are allowed.

## Causal entry
For a lane that satisfies its acceptance state:
- if E40 has already been touched at or before the acceptance snapshot, no A10 trade is allowed because the opportunity has already occurred;
- otherwise enter LONG at the **next 5m open** after the completed acceptance snapshot;
- one A10 trade maximum per residual episode per tested lane.

## A10 lifecycle
After A10 entry:
- target remains `H + 0.40R`;
- target is not credited on the entry bar; target evaluation begins on the following 5m bar;
- the first completed close `<= H` is `FAILED_ACCEPTANCE`; exit at the next 5m open when available;
- if neither target nor failed acceptance occurs by the frozen A4 recovery-watch end, exit at the final completed close (`TIME`).

There is no H3/H4 resting entry and no averaging.

## Development economics
Central Development is the only selection surface.

For each lane report:
- eligible A10 N;
- A10 WR, PF, expectancy, net;
- 5bps WR, PF, expectancy, net;
- combined episode rescue rate for `A2 + H2 + A10`;
- frozen baseline overlay PF/net for `A2 + H2`;
- candidate overlay PF/net after adding A10;
- raw and 5bps overlay net improvement;
- six half-year Development block results.

## Development gate
A lane passes only if:
- A10 N >= 30;
- A10 PF > 1.15;
- A10 expectancy > 0;
- 5bps A10 PF > 1.00;
- 5bps A10 expectancy > 0;
- raw A10 net > 0;
- raw overlay net improvement > 0;
- 5bps overlay net improvement > 0;
- combined episode rescue rate >= 20%;
- at least 4 of 6 Development blocks with N >= 4 have positive raw A10 net.

Among passing lanes choose in order:
1. highest 5bps overlay net improvement;
2. highest 5bps A10 net;
3. highest combined episode rescue rate;
4. highest 5bps PF;
5. fewer confirmation minutes;
6. simpler rule before E10 hybrid if otherwise tied.

If no lane passes, A10 fails and OOS cannot select a substitute.

## Frozen OOS validation
Only the frozen Development winner may be evaluated on:
- Central External;
- Central Reference Validation;
- CLOCK_SUPPORT External / Reference Validation;
- REF_SUPPORT External / Reference Validation.

A10 is supported only if:
- Central External and Central Reference Validation both have positive raw A10 net;
- both central OOS cells have positive 5bps A10 net;
- both central OOS cells improve the A2+H2 overlay net raw and at 5bps;
- rescue rate is >0 in both central OOS cells;
- at least 3 of 4 topology-support cells have positive raw A10 net;
- at least 3 of 4 topology-support cells have positive 5bps A10 net.

OOS cannot change the frozen lane.

## Interpretation
A10 succeeds only if **acceptance confirmation is economically robust**, not merely if it predicts future E40. A9 association alone is insufficient.

Research only. Live Baba Bot remains unchanged.
