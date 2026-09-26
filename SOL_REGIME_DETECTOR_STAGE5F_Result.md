# SOL Regime Detector — Stage 5F Failure Forensics

Stage 5F used **2023-2024 only** and did not modify the frozen detector.

Raw SOLUSDT 5m coverage: **100.0000%**.

## Edge decay by causal milestone

| Milestone | Events | 24H resolved aligned hit | Median pre-6H aligned move | Median future-6H aligned ret | Median future-24H aligned ret |
|---|---:|---:|---:|---:|---:|
| M0_IMPULSE_START | 1775 | 51.4% | 1.813% | -0.160% | -0.252% |
| M1_STRUCTURE_BREAK | 5179 | 51.7% | 2.125% | -0.118% | -0.122% |
| M2_STRUCTURE_CONFIRM | 492 | 47.4% | 0.045% | -0.135% | -0.340% |
| M3_RAW_SCORE_SWITCH | 944 | 50.1% | 0.736% | -0.105% | -0.145% |
| M4_FINAL_SWITCH | 182 | 46.4% | 1.264% | -0.270% | -0.451% |

## 24H aligned hit-rate by half-year

| Milestone | 2023-H1 | 2023-H2 | 2024-H1 | 2024-H2 |
|---|---:|---:|---:|---:|
| M0_IMPULSE_START | 53.1% | 52.0% | 51.1% | 49.7% |
| M1_STRUCTURE_BREAK | 51.5% | 53.3% | 50.7% | 51.5% |
| M2_STRUCTURE_CONFIRM | 46.1% | 45.2% | 55.8% | 42.7% |
| M3_RAW_SCORE_SWITCH | 56.8% | 43.7% | 48.5% | 50.6% |
| M4_FINAL_SWITCH | 33.3% | 39.1% | 58.7% | 56.1% |

## Same-side latency into FINAL_SWITCH

| Earlier milestone | Found within 72H | Median delay to M4 |
|---|---:|---:|
| M0_IMPULSE_START | 98.9% | 3.5h |
| M1_STRUCTURE_BREAK | 96.7% | 2.0h |
| M2_STRUCTURE_CONFIRM | 95.1% | 1.0h |
| M3_RAW_SCORE_SWITCH | 100.0% | 1.0h |

## Consecutive edge changes

| Step | Change in combined aligned hit |
|---|---:|
| M0_IMPULSE_START → M1_STRUCTURE_BREAK | +0.3% |
| M1_STRUCTURE_BREAK → M2_STRUCTURE_CONFIRM | -4.3% |
| M2_STRUCTURE_CONFIRM → M3_RAW_SCORE_SWITCH | +2.6% |
| M3_RAW_SCORE_SWITCH → M4_FINAL_SWITCH | -3.6% |

## Frozen forensic verdict

- Verdict: **MIXED_FORENSIC_RESULT**
- Localization: **LARGEST_DECLINE_M1_STRUCTURE_BREAK→M2_STRUCTURE_CONFIRM**
- Largest consecutive aligned-hit change: **-4.3%** at **M1_STRUCTURE_BREAK→M2_STRUCTURE_CONFIRM**.
- Best milestone combined aligned 24H hit: **51.7%**.

## Technical audits

| Audit | Pass | Value |
|---|---|---|
| stage5_failed_status_present | PASS | True |
| raw_5m_coverage_ge_99_5 | PASS | 1.0 |
| no_24h_window_crosses_2025 | PASS | 2024-12-30 21:00:00+00:00 |
| milestone_source_has_no_future_fields | PASS | [] |
| ambiguous_le_2pct_all | PASS | {'M0_IMPULSE_START:BULL': 0.0010905125408942203, 'M0_IMPULSE_START:BEAR': 0.0011682242990654205, 'M1_STRUCTURE_BREAK:BULL': 0.0007064641469445425, 'M1_STRUCTURE_BREAK:BEAR': 0.003837953091684435, 'M2_STRUCTURE_CONFIRM:BULL': 0.0, 'M2_STRUCTURE_CONFIRM:BEAR': 0.004048582995951417, 'M3_RAW_SCORE_SWITCH:BULL': 0.0, 'M3_RAW_SCORE_SWITCH:BEAR': 0.0, 'M4_FINAL_SWITCH:BULL': 0.0, 'M4_FINAL_SWITCH:BEAR': 0.0} |
| each_milestone_ge_200_eligible24 | FAIL | {'M0_IMPULSE_START': 1773, 'M1_STRUCTURE_BREAK': 5176, 'M2_STRUCTURE_CONFIRM': 491, 'M3_RAW_SCORE_SWITCH': 942, 'M4_FINAL_SWITCH': 181} |

## Decision

**Status: SOL_REGIME_DETECTOR_STAGE5F_FORENSICS_INVALID**

Failed technical audits: **['each_milestone_ge_200_eligible24']**.
