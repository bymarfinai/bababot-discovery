# SOL LONG 15:00 UTC L0 Early Progress Specificity — A63 Scientific Verdict

## Verdict

**`SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED`**

A63 supports a narrow mechanistic conclusion: among the three early-progress feature families carried forward from A62, **`running_mae_R` is specifically associated with frozen L0/M0 reference-invalidation losses relative to frozen M1 time/no-structural-fail losses at both 60 and 120 minutes**.

This is a mechanism-specificity result, not an economic-intervention result.

## Frozen reconciliation

The execution parent remained:

`R360 / 15UTC / E0_RESTING_H -> E40`

The mature loss universe reconciled exactly:

| Partition | Parent | CENTRAL losses | L0/M0 | M1 |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 |
| External Validation | 281 | 166 | 13 | 16 |
| Reference Validation | 337 | 187 | 26 | 21 |
| **Pooled** | **1,219** | **710** | **76** | **95** |

Raw SOLUSDT 5m market coverage was **99.7671%**.

## Specificity result

A63 tested only the three A62-supported feature families and only the two A62-supported early ages. No new feature or age sweep was allowed.

### `running_mae_R` — L0-specific

This family passed the preregistered full Development + External Validation + Reference Validation replication gates at **both** fixed ages.

- **60m**
  - Development: median gap `+0.222R`, effect `1.219`, Development blocks `4/4` in the preregistered direction.
  - External Validation: median gap `+0.114R`, effect `0.545`.
  - Reference Validation: median gap `+0.320R`, effect `0.798`.
- **120m**
  - Development: median gap `+0.216R`, effect `1.235`, Development blocks `3/3` in the preregistered direction.
  - External Validation: median gap `+0.206R`, effect `0.969`.
  - Reference Validation: median gap `+0.240R`, effect `0.655`.

Therefore `running_mae_R` passes the strict **2-of-2 specificity rule**.

### `close_H_R` — not established as 2-of-2 L0-specific

`close_H_R` replicated fully at 60m, but failed the preregistered Development block-direction rule at 120m (`2/3` adequate blocks in the expected direction). It therefore does not pass the strict 2-of-2 specificity rule.

It must not be promoted as an independently established L0-specific mechanism on the basis of A63.

### `drawdown_from_best_R` — not L0-specific under A63

`drawdown_from_best_R` did not achieve full specificity replication at either fixed age. Its A62 separation versus eventual winners does not survive as a robust L0-versus-M1 mechanism-specific signature.

## Scientific interpretation

A62 showed that L0/M0 losses differ from eventual winners by approximately 60–120 minutes through deeper adverse excursion, weaker location relative to H, and larger giveback.

A63 narrows that broader anatomy. When the comparator is changed from eventual winners to another never-break loss mechanism, the durable distinction is:

> **L0/M0 reference-invalidation losses experience systematically deeper adverse excursion than M1 time/no-structural-fail losses by 60 minutes, and that distinction persists at 120 minutes across Development and both OOS partitions.**

The evidence therefore supports **adverse-excursion depth** as the current mechanism-specific early-progress axis for L0/M0. It does not support treating the full A62 three-feature pattern as uniquely L0-specific.

## Interpretation boundary

A63 authorizes **no** live trading action.

In particular, A63 does not authorize:

- an MAE threshold;
- a stop-loss change;
- an emergency exit;
- partial derisking;
- position-size reduction;
- an entry filter;
- a composite score;
- any change to live Baba Bot.

The observed medians and effects are descriptive statistics, not executable thresholds.

A future economic-feasibility experiment is now scientifically justified, but it must be separately preregistered and must explicitly measure winner damage, non-L0 damage, total PnL, drawdown, trade retention, and OOS economics before any intervention can be considered deployable.

## Lineage consequence

- Preserve `running_mae_R` as the only A63-established L0-specific early-progress feature family.
- Do not rescue `close_H_R` by changing the 120m block rule, snapshot, threshold, or comparator.
- Do not rescue `drawdown_from_best_R` through a composite or alternate threshold inside the A63 lineage.
- Do not convert the A63 result directly into execution.
- Preserve the frozen parent, mature loss taxonomy, and partition semantics.

A64 remains an unused experiment identifier until a separate hypothesis is explicitly preregistered.

Research only. Live Baba Bot remains unchanged.
