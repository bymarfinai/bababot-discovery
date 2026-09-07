# SOL LONG 15UTC Native Entry + Target Calibration — A46 Preregistration

## Checkpoint
A46 continues the supported SOL `R360/15` habitat from A20. It does **not** reopen clock, reference duration, regime, recovery, or portfolio-state discovery.

Frozen baseline: `R360/15`, `E0_RESTING_H`, target `E40`, $500 notional, 5 bps stress.

A45 found no replicated pre-placement range-shape separator. Therefore A46 does not add a filter. It asks whether the **execution rule itself** for the already-supported 15UTC habitat should be calibrated natively rather than inherited from the earlier 18UTC lineage.

## Data partitions
Unchanged from the SOL lineage:
- Development: 2022-01-01 to 2025-01-01
- External: before 2022-01-01 within available SOL data
- Reference validation: 2025-01-01 to 2026-07-30

Only Development may select the challenger. External/reference are opened only after one challenger is frozen.

## Frozen habitat
- reference range: 360 minutes ending 15:00 UTC (`09:00–15:00 UTC`)
- execution horizon: existing A1/A20 720-minute horizon
- long-only
- no calendar/month/day filter
- no portfolio-state filter
- no recovery overlay

## Native target derivation
Using Development `R360/15` sessions only, measure post-break extension above H before the first reclaim close `<= H` (or execution-horizon end if no reclaim), normalized by R.

Take Q35/Q50/Q65 of positive extensions. Each is rounded **down** to the nearest 0.05R, minimum 0.05R, then deduplicated. No target level is hand-added after seeing economics.

## Frozen entry families
Test exactly the existing causal execution families, now inside `R360/15`:
1. `E0_RESTING_H`
2. `E1_H1_TOUCH_NEXT_OPEN`
3. `E2_H1_BREAK_NEXT_OPEN`
4. `E3_H1_RETEST_RECLAIM_NEXT_OPEN`

Candidate grid = 4 entry families × native target levels. Baseline E0/E40 is reported separately even if E40 is not one of the native target levels.

## Development eligibility
A challenger is eligible only if all are true:
- N >= 200;
- raw PF > 1.15 and raw net > 0;
- 5bps PF >= baseline Development 5bps PF + 0.10;
- 5bps expectancy >= baseline Development 5bps expectancy + $0.10/trade;
- 5bps net >= 80% of baseline Development 5bps net;
- at least 4 Development half-year blocks have >=15 trades;
- at least 4 adequate blocks are positive under 5bps stress;
- minimum adequate-block 5bps PF >= 0.70.

If no candidate is eligible, verdict is `REJECTED_DEVELOPMENT` and OOS is not used for selection.

If multiple are eligible, freeze one challenger by: highest positive stress blocks, then highest minimum adequate-block stress PF, then highest 5bps PF, then 5bps expectancy, then 5bps net, then N; ties resolve by entry-family order E0→E1→E2→E3 and lower target.

## OOS support gate
For the frozen challenger, compare candidate vs frozen E0/E40 baseline independently in external and reference_validation.

Candidate must have in **both** partitions:
- raw PF > 1 and raw net > 0;
- 5bps PF > 1 and 5bps net > 0.

Then pooled external+reference stress economics must satisfy at least one preregistered route:

**QUALITY route**
- pooled challenger 5bps PF >= pooled baseline 5bps PF + 0.10;
- pooled challenger 5bps expectancy >= 1.20 × pooled baseline 5bps expectancy;
- pooled challenger 5bps net >= 0.70 × pooled baseline 5bps net.

**RETURN route**
- pooled challenger 5bps net >= pooled baseline 5bps net;
- pooled challenger 5bps PF >= pooled baseline 5bps PF - 0.05.

If either route passes, A46 is supported. Otherwise baseline E0/E40 remains frozen.

## Outputs
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_TARGETS.csv`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_DEVELOPMENT.csv`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_OOS.csv`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_TRADES.csv`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_Result.md`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_Status.txt`

## Verdict labels
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_SUPPORTED`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_REJECTED_DEVELOPMENT`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_REJECTED_OOS`
- `SOL_LONG_15UTC_NATIVE_ENTRY_TARGET_A46_RECONCILIATION_FAIL`

Research only. Live Baba Bot remains unchanged.