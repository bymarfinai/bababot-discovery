# BNB F85/F15 Transfer — M2 Exact Frozen BTC Signal — B27EE Result

Raw 5m coverage: BTC **100.0000%**, BNB **100.0000%**.

Exact frozen BTC raw-5m signal adapters were reused unchanged. No BNB-specific tuning, no new clocks, no PnL optimization.

## Pooled-major exact-signal comparison

| Source | Side | BNB N | BNB H2 Hit | BNB Resolved H2 WR | BTC N | BTC H2 Hit | Gate |
|---|---|---:|---:|---:|---:|---:|---|
| ALT_0330 | LONG | 56 | 91.1% | 96.2% | 62 | 95.2% | PASS |
| RAW_0530 | LONG | 55 | 87.3% | 90.6% | 66 | 86.4% | PASS |
| LONDON | LONG | 60 | 76.7% | 95.8% | 68 | 85.3% | FAIL |
| RAW_2330 | LONG | 42 | 73.8% | 91.2% | 47 | 85.1% | FAIL |
| SHORT_2000 | SHORT | 64 | 85.9% | 93.2% | 56 | 83.9% | PASS |

## Major-partition BNB diagnostics

| Source | Partition | N | H2 Hit | Resolved H2 WR |
|---|---|---:|---:|---:|
| ALT_0330 | external | 13 | 84.6% | 91.7% |
| ALT_0330 | development | 29 | 89.7% | 96.3% |
| ALT_0330 | reference_validation | 14 | 100.0% | 100.0% |
| RAW_0530 | external | 14 | 71.4% | 76.9% |
| RAW_0530 | development | 29 | 89.7% | 92.9% |
| RAW_0530 | reference_validation | 12 | 100.0% | 100.0% |
| LONDON | external | 27 | 51.9% | 87.5% |
| LONDON | development | 20 | 100.0% | 100.0% |
| LONDON | reference_validation | 13 | 92.3% | 100.0% |
| RAW_2330 | external | 15 | 66.7% | 83.3% |
| RAW_2330 | development | 20 | 80.0% | 94.1% |
| RAW_2330 | reference_validation | 7 | 71.4% | 100.0% |
| SHORT_2000 | external | 20 | 85.0% | 94.4% |
| SHORT_2000 | development | 28 | 89.3% | 96.2% |
| SHORT_2000 | reference_validation | 16 | 81.2% | 86.7% |

LONG habitat gates passed: **2/4**.
SHORT_2000 gate: **PASS**.

**Status: B27EE_BNB_M2_EXACT_SIGNAL_TRANSFER_NOT_SUPPORTED**

B27EE stops here. No TP/SL/PnL milestone and no M3 is run automatically.
