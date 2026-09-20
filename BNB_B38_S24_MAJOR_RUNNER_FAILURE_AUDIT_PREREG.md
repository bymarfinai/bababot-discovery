# BNB B38-S24 — Major Runner Failure Character Audit Preregistration

## Objective
Explain why the frozen S23 Major runner adds value overall but loses value in 2026, without tuning directly to 2026.

S24 is diagnostic only.

## Frozen upstream
- E2 signature:
  `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- S20 failure layer unchanged.
- S23 eligibility unchanged:
  `major_room_from_tp2_r <= 0.30105633802816506`
- S23 split unchanged:
  50% TP1 / 50% Major runner.
- Runner BE begins on first 5m bar strictly after TP1-touch bar.

## Audit population
Only S23 trades that:
- are Major-runner eligible,
- are not cut by S20 before TP1,
- reach TP1,
- enter runner state.

Outcome labels:
- HIT = MAJOR_SAME_TP1_BAR or MAJOR_HIT
- BE = BE_EXIT
- AMBIGUOUS kept separate and excluded from separator scoring.

## Decision time
All candidate skip features must be known no later than TP1-touch bar close, before BE protection activates.

## Causal feature families

### Geometry
- major_room_from_tp2_r
- tp1_r
- tp2_r
- tp1_to_tp2_gap_r
- room_tp1_to_major_r
- known_target_count

### Journey to TP1
- minutes_entry_to_tp1
- pre_tp1_path_efficiency
- pre_tp1_green_rate
- pre_tp1_max_pullback_r
- pre_tp1_mae_r
- last1_progress_r
- last3_progress_r
- last3_green_rate

### TP1 completion bar
- tp1_accept = close >= TP1
- tp1_close_above_r
- tp1_bar_body_r
- tp1_bar_range_r
- tp1_close_location

### Structural context
- baseline_sl_pct
- is_wide_q4

## Analysis discipline
- DEV and REF scored separately.
- 2026 is NOT used to derive thresholds.
- Numeric cuts come only from DEV 2022-2024 quartiles.
- Frozen cuts are applied unchanged to REF 2025-2026.
- Report 2025 and 2026 separately after the frozen DEV cuts are fixed.
- No combined skip rule is created in S24.

## Required outputs
- runner HIT/BE/AMBIG counts by period and year
- feature medians HIT vs BE
- robust effect DEV vs REF
- DEV quartile cuts applied unchanged to REF and yearly subsets
- identify whether 2026 weakness is explained by a pre-runner structural state that is also supported by DEV/REF

## Stop rule
Do not create a live skip filter in S24.
If no causal feature is directionally consistent across DEV and REF, keep S23 unchanged.
If a feature is consistent, preregister one S25 skip-policy validation separately.
