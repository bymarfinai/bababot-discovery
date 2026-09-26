# SOL Regime Detector — Stage 4 Hysteresis / Transition Result

Stage 4 used **2023–2024 only**. No forward return, TP/SL, trade outcome, 2025, or 2026 data were used.

## Mandatory audits

| Audit | Pass | Value |
|---|---|---|
| stage3_valid | PASS | True |
| no_2025_2026_rows | PASS | [2023, 2024] |
| final_regime_only_three_classes | PASS | ['BEAR', 'BULL', 'SIDEWAYS'] |
| transition_is_separate_flag | PASS | bool |
| confidence_in_0_1 | PASS | [0.051127676000721295, 0.9821710277592484] |
| prefix_causality_all_checkpoints | PASS | 4/4 |
| all_switches_obey_frozen_rules | PASS | [] |
| no_future_outcome_fields | PASS | [] |
| nondegenerate_final_class_shares | PASS | {'BULL': 0.21448928408572732, 'BEAR': 0.2181372549019608, 'SIDEWAYS': 0.5673734610123119} |
| transition_share_5_to_60pct | PASS | 0.5454286365709075 |
| final_switches_le_70pct_raw | PASS | {'raw': 1778, 'final': 317, 'ratio': 0.1782902137232846} |
| onebar_final_runs_le_10pct | PASS | 0.0 |
| median_duration_not_lower_than_raw | PASS | {'BULL': {'raw': 4.0, 'final': 36.5, 'pass': True}, 'BEAR': {'raw': 4.0, 'final': 32.0, 'pass': True}, 'SIDEWAYS': {'raw': 6.0, 'final': 40.0, 'pass': True}} |

## Raw vs final regime distribution

| Regime | Raw share | Final share | Raw median run | Final median run | Final P90 run |
|---|---:|---:|---:|---:|---:|
| BULL | 30.4% | 21.4% | 4.0h | 36.5h | 81.0h |
| BEAR | 25.4% | 21.8% | 4.0h | 32.0h | 90.2h |
| SIDEWAYS | 44.1% | 56.7% | 6.0h | 40.0h | 205.0h |

## State-machine stability

- Raw provisional switches: **1778**.
- Final regime switches: **317**.
- Switch retention ratio: **17.8%** of raw switching.
- One-bar final runs: **0/318 (0.0%)**.
- Transition-flag share: **54.5%**.
- Confirmed non-startup switches logged: **317**.

## Prefix causality

| Checkpoint | Pass | Max numeric diff | Categorical mismatch |
|---|---|---:|---:|
| 2023-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2023-12-31 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2024-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2024-12-31 22:00:00+00:00 | PASS | 0.0 | 0 |

## Decision

**Status: SOL_REGIME_DETECTOR_STAGE4_STATE_MACHINE_VALID**

The causal hysteresis / transition layer passed all frozen stability and replay audits.
The detector now has a final-form state output suitable for Stage 5 forward-behavior validation.
Stage 5 may test whether BULL / BEAR / SIDEWAYS actually separate subsequent SOL behavior, but may not retroactively change Stage-4 rules.
