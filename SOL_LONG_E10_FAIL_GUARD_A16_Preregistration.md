# SOL LONG E10-Fail False-Positive Guard — A16 Preregistration

## Purpose
A15 found two trigger-time dimensions that separate `CP_E10_5_FULL` true stallers from genuine E40 recoveries and replicate in both Central OOS cells plus all four support cells:
- `entry_to_e20_min`: E40 recoveries are slower to reach E20;
- `running_mae_R_to_e20`: E40 recoveries have deeper pre-E20 adverse excursion.

A16 tests whether these dimensions can act as a **guard around the rejected A14 `CP_E10_5_FULL` signal**, preserving genuine continuation while retaining A14's positive Development PF/net direction.

A16 does not change the A2 entry, A4 H2 recovery, E40 target, or the E10-failure signal itself.

## Frozen context
- Supported stack remains A2 `E0_RESTING_H -> E40` + A4 `REC_H2`.
- A14 core signal remains exactly: first E20 touch, then next completed 5m close `<= E10`, with next-open action strictly before frozen baseline exit.
- Same `[L,H]`, `R`, partitions, clocks, notional, lifecycle and 5bps stress.
- No OOS threshold selection or retuning.

## Development-derived guard values
From A15 Central Development trigger anatomy:
- true-staller median `entry_to_e20_min` = approximately 10m;
- true-staller median pre-E20 MAE = approximately 0.23R, rounded conservatively to 0.25R.

These values are frozen before A16.

## Preregistered family
All lanes perform a full next-open exit only when the frozen A14 E10-fail signal occurs **and** the guard allows intervention.

### `G_FAST10`
Intervene only when:
- `entry_to_e20_min <= 10m`.

### `G_SHALLOW25`
Intervene only when:
- `running_mae_R_to_e20 <= 0.25R`.

### `G_FAST10_SHALLOW25`
Intervene only when both:
- `entry_to_e20_min <= 10m`;
- `running_mae_R_to_e20 <= 0.25R`.

### `G_FAST10_OR_SHALLOW25`
Intervene when either:
- `entry_to_e20_min <= 10m`; or
- `running_mae_R_to_e20 <= 0.25R`.

No nearby time or MAE thresholds are allowed.

## Development selection
Central Development only.

Report:
- parent intervention N;
- retained H2 N and H2 intervention N;
- parent raw-winner preservation;
- episode WR and gross loss;
- stack PF/net;
- 5bps stack PF/net;
- six Development block net improvements.

A lane passes Development only if:
- raw stack net improves vs frozen A2+A4;
- 5bps stack net improves;
- raw stack PF improves;
- 5bps stack PF improves;
- episode gross loss does not increase;
- episode WR does not decrease;
- parent winner preservation >= 98%;
- at least 4/6 adequate blocks have positive raw stack-net improvement;
- at least 4/6 adequate blocks have positive 5bps stack-net improvement.

Among passing lanes choose by:
1. highest 5bps stack-net improvement;
2. highest raw stack-net improvement;
3. highest winner preservation;
4. highest 5bps PF;
5. simpler single-feature guard before conjunction/disjunction if otherwise tied.

If none pass, A16 is rejected and OOS cannot supply a substitute.

## Frozen OOS validation
Only the frozen Development winner may be tested on:
- Central External;
- Central Reference Validation;
- CLOCK_SUPPORT External / Reference Validation;
- REF_SUPPORT External / Reference Validation.

A16 is supported only if:
- both Central OOS cells have positive raw and 5bps stack-net improvement;
- raw and 5bps stack PF do not decrease in either Central OOS cell;
- parent winner preservation >= 98% in both Central OOS cells;
- episode gross loss does not increase in either Central OOS cell;
- at least 3/4 support cells have positive raw stack-net improvement;
- at least 3/4 support cells have positive 5bps stack-net improvement.

OOS cannot alter the frozen guard.

Research only. Live Baba Bot remains unchanged.
