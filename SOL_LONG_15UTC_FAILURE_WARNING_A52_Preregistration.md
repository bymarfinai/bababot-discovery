# SOL LONG 15:00 UTC Failure Early-Warning Validation — A52 Preregistration

## Purpose

A51 established the frozen 15UTC/R360/E0→E40 failure state machine. A52 now asks whether the fixed **pre-terminal warnings already defined in A51** are actually discriminative against trades that reach E40.

A52 does not scan new price thresholds, does not optimize exits, and does not modify the live Baba Bot.

## Frozen parent and source

- Pair: SOLUSDT
- Clock: 15:00 UTC
- Reference: R360
- Entry: `E0_RESTING_H`
- Target: E40
- Parent trade counts: Development 601, External 281, Reference Validation 337, total 1219
- Raw winners: Development 244, External 115, Reference Validation 150, total 509
- Raw losses: Development 357, External 166, Reference Validation 187, total 710
- Source rows: `SOL_LONG_15UTC_LOSS_TRIGGER_A51_EVENTS.csv`
- Existing A51 warning definitions are frozen; A52 may not introduce neighboring thresholds.

## Frozen mechanism cohorts

- `WIN`: raw parent trades with `outcome == WIN`.
- `M0_REFERENCE_INVALIDATION`: no confirmed breakout, then completed close `< L`.
- `M1_TIME_NO_STRUCTURAL_FAIL`: no target and no structural invalidation before horizon.
- `M2_FAILED_BREAK`: confirmed breakout, then first completed close `<= H`.

Legacy L2/L3/L4/L5 remain latency subgroups inside M2 and are reported diagnostically only.

## Fixed warning families

### M2 failed-break warnings — primary

1. `POST_H10`: after breakout confirmation and before terminal failure/target, a completed close satisfies `H < close <= H + 0.10R`.
2. `POST_H05`: after breakout confirmation and before terminal failure/target, a completed close satisfies `H < close <= H + 0.05R`.
3. `NO_EXT_005R_BY_5M`: exact frozen A51 boolean.
4. `NO_EXT_010R_BY_10M`: exact frozen A51 boolean.

The primary A52 question is whether `POST_H10` and/or `POST_H05` catch a large fraction of M2 losses while touching materially fewer winners.

### M0 reference-failure warnings

1. `PRE_L25`: before breakout/target, completed close `<= L + 0.25R`.
2. `PRE_L10`: before breakout/target, completed close `<= L + 0.10R`.
3. Frozen A51 `NO_BREAK_{30,60,120,180,240,360}M` states.

### M1 timeout warnings

The same pre-break/no-break warnings are measured versus winners, but M1 is treated as an expiry problem rather than a structural-failure trigger.

## Denominator rule

Coverage is measured over the **entire outcome cohort**, not only trades that survive long enough to create a warning opportunity.

This answers the live-relevant question directly:

> If this warning were later used as a guard, what fraction of bad trades could it catch, and what fraction of actual E40 winners could it sacrifice?

A winner that reaches target before a warning can physically occur is therefore correctly counted as `warning = false`.

## Development-only discovery gate

For each fixed warning and its matching loss mechanism, compute:

- loss hit rate
- winner hit rate
- absolute separation = loss hit rate − winner hit rate
- hit-rate ratio = loss hit rate / winner hit rate (infinite if winner rate is zero)
- Development block direction consistency across six fixed blocks
- median warning lead to terminal trigger for structural losses where A51 has a timestamp lead

A fixed warning becomes an **A52 Development candidate** only if all are true:

1. loss hit rate >= 50%
2. absolute separation >= 25 percentage points
3. hit-rate ratio >= 1.50
4. loss hit rate > winner hit rate in at least 5 of 6 Development blocks with both cohorts present

For M2 `POST_H10` / `POST_H05`, median structural lead must additionally be >= 5 minutes.

No candidate may be created by combining warnings in A52.

## OOS confirmation gate

Only Development candidates are eligible for confirmation.

A Development candidate is `REPLICATED` only if, independently in both External and Reference Validation:

- loss hit rate > winner hit rate
- absolute separation >= 15 percentage points
- hit-rate ratio >= 1.25

No OOS threshold adjustment is permitted.

## Required diagnostics

For M2 primary warnings, report:

- pooled and partition-specific loss/winner rates
- L2/L3/L4/L5 hit rates
- Development six-block direction consistency
- median lead to terminal failed-break trigger
- first warning timing relative to breakout where available

For M0/M1, report the same mechanism-level discrimination where applicable.

## Reconciliation gates

A52 is invalid unless A51 source rows reconcile exactly:

- Development 601 / 244 winners / 357 losses
- External 281 / 115 winners / 166 losses
- Reference Validation 337 / 150 winners / 187 losses
- Total 1219 / 509 winners / 710 losses
- M0 total 76, M1 total 95, M2 total 539

## Decision

Possible statuses:

- `SOL_LONG_15UTC_FAILURE_WARNING_A52_SUPPORTED_FOR_A53`
- `SOL_LONG_15UTC_FAILURE_WARNING_A52_INCONCLUSIVE`

A52 itself cannot change exits. If supported, A53 must separately preregister a small executable guard simulation using only replicated A52 warnings and must quantify WR, PF, expectancy, net, DD, winner sacrifice, and 5bps stress.

Research only. Live Baba Bot remains unchanged.
