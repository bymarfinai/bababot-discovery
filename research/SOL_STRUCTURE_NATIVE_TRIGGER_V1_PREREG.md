# SOL Structure-Specific Native Trigger V1 — Preregistration

## Purpose
Separate **market structure** from **entry**. A structure is context only. Each structure receives one trigger that is native to its own market logic. This experiment does not retune the structures and does not use a universal trigger matrix.

## Data / execution freeze
- Symbol: SOLUSDT Futures 5m repository data.
- Research/evaluation universe: 2020-01-01 through 2024-12-31.
- **2025+ remains CLOSED.**
- Causal pivots: same 2-left / 2-right confirmation semantics as Structural Library V1 and Structure × Trigger Matrix V1.
- Structure definitions: reuse exactly `detect_setups()` from `sol_structure_trigger_matrix_v1.py` for:
  1. `SWEEP_RECLAIM`
  2. `HL_SETUP`
  3. `BREAKOUT_PULLBACK_SETUP`
  4. `FAILED_BREAKDOWN_RECLAIM`
- Structure completion is **not an entry**.
- A trigger may occur only after setup completion and within the next **12 completed 5m bars (60 minutes)**.
- Entry: next 5m open after the trigger bar.
- Diagnostic exit: fixed +60m from entry.
- Round-trip cost: 0.15%.
- Notional: $500.
- No hour filter, indicator filter, regime filter, ML model, TP/SL optimization, or post-result rescue.

## Frozen native triggers

### A. SWEEP_RECLAIM → RETEST_HOLD_BREAK
Setup is the frozen `SWEEP_RECLAIM` context.
1. After setup completion, wait for the first bar whose low touches/breaches the swept level while its close is at/above that level (`low <= anchor_level` and `close >= anchor_level`). This is the retest/hold bar.
2. Structure invalidates if any completed close falls below the anchor level before entry.
3. After a valid retest/hold, trigger on the first later completed bar whose close is above the **high of the retest/hold bar**.
4. No entry if trigger does not occur within 12 bars after setup.

### B. HL_SETUP → BREAK_INTERVENING_HIGH
Setup is the frozen `HL_SETUP` context, where `secondary_level` is the confirmed HL and `anchor_level` is the intervening H1.
1. Structure invalidates on a completed close below the confirmed HL (`secondary_level`).
2. Trigger on the first completed bar after setup whose close is above H1 (`anchor_level`).
3. No entry if trigger does not occur within 12 bars after setup.

### C. BREAKOUT_PULLBACK_SETUP → RECOVERY_HIGH_BREAK
Setup is the frozen `BREAKOUT_PULLBACK_SETUP` context.
1. At setup completion, define `recovery_high` once as the maximum high from the known pullback pivot-low bar (`secondary_pivot_i`) through the setup-confirmation bar inclusive. This level is fully causal and frozen at setup time.
2. Structure invalidates on a completed close below the original breakout level (`anchor_level`).
3. Trigger on the first later completed bar whose close is above the frozen `recovery_high`.
4. No entry if trigger does not occur within 12 bars after setup.

### D. FAILED_BREAKDOWN_RECLAIM → RETEST_RECLAIM_HIGH_BREAK
Setup is the frozen `FAILED_BREAKDOWN_RECLAIM` context.
1. Freeze `reclaim_high` as the high of the setup/reclaim bar.
2. After setup, wait for the first retest/hold bar with `low <= anchor_level` and `close >= anchor_level`.
3. Structure invalidates if any completed close falls below the reclaimed level before entry.
4. After a valid retest/hold, trigger on the first later completed bar whose close is above frozen `reclaim_high`.
5. No entry if trigger does not occur within 12 bars after setup.

## Measurements per structure-native-trigger detector
Report independently:
- setup count
- triggered entry count and trigger rate
- median trigger delay
- WR at fixed +60m net of cost
- net expectancy
- PF
- PnL on $500 notional
- max drawdown
- max loss streak
- clean-up-impulse incidence using the existing adaptive diagnostic barrier
- median MFE60, MAE60, and MFE/|MAE|
- yearly 2020/2021/2022/2023/2024 economics

## Frozen promotion gates
A detector advances to structure-specific execution / TP / SL characterization only if **all** hold:
1. triggered N >= 100
2. pooled fixed +60m net expectancy > 0
3. pooled PF >= 1.15
4. positive PnL in at least 4 of 5 years
5. pooled median MFE/|MAE| >= 1.20

## Stop rule
If a detector fails, do not rescue it on 2020-2024 by changing its trigger window, pivot order, structural levels, hours, indicators, regime filters, TP, or SL. The result rejects only this exact **structure + native trigger** pair; the underlying structure remains available for testing a genuinely different preregistered entry trigger later.
