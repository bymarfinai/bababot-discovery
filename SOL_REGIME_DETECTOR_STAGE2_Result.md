# SOL Regime Detector — Stage 2 Feature Engine Result

Raw SOLUSDT 5m coverage: **100.0000%**.
Exported 1H feature rows: **32,136**.
Raw confirmed 1H pivots: **4,739** ({'H': 2373, 'L': 2366}).
Raw confirmed 4H pivots: **1,847** ({'L': 925, 'H': 922}).

## Feature-engine descriptive structure only

1H causal structure-state counts: **{'MIXED': 11771, 'BULL_SEQ': 10420, 'BEAR_SEQ': 9945}**.
4H causal structure-state counts: **{'MIXED': 12800, 'BULL_SEQ': 10240, 'BEAR_SEQ': 9096}**.
These are structural feature states, **not** Bull/Bear/Sideways regime labels.

## Mandatory audits

| Audit | Pass | Value |
|---|---|---|
| raw_5m_coverage | PASS | 1.0 |
| all_exported_1h_complete | PASS | 0 |
| all_used_4h_complete | PASS | 0 |
| 1h_accepted_sequence_alternates | PASS | 3753 |
| 4h_accepted_sequence_alternates | PASS | 1441 |
| 1h_raw_event_identity_unique | PASS | 0 |
| 4h_raw_event_identity_unique | PASS | 0 |
| 1h_confirmation_delay_exact | PASS | [5] |
| 4h_confirmation_delay_exact | PASS | [3] |
| 4h_context_fully_closed | PASS | 0 |
| no_future_label_fields | PASS | [] |
| prefix_causality_all_checkpoints | PASS | 4/4 checkpoints |

## Prefix causality checkpoints

| Checkpoint | Pass | Max numeric diff | String mismatch |
|---|---|---:|---:|
| 2023-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2024-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2025-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2026-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |

## Decision

**Status: SOL_REGIME_DETECTOR_STAGE2_FEATURE_ENGINE_VALID**

Stage 2 feature engine passed every frozen causality / completeness / swing-sequence audit.
No Bull/Bear/Sideways threshold or score has been selected yet.
Stage 3 is authorized to build competing BullScore / BearScore / SidewaysScore using Development data only.
