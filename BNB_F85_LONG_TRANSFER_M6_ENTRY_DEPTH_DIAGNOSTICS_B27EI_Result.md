# BNB F85 LONG Transfer — M6 Entry Depth Diagnostics — B27EI Result

Raw BNB 5m coverage: **100.0000%**. Frozen accepted LONG identity: **PASS (106 = 55 ALT_0330 + 51 RAW_0530)**.

B27EI is diagnostic only: no alternative-entry PnL, no stop change, no candidate filtering, and no level selection by economics.

## Current F85 next-open geometry

| Cohort | N | Confirm close depth med | Entry depth med | Premium vs F85 med | Reward→H med | Risk→F35 med | H2 reward/risk med |
|---|---:|---:|---:|---:|---:|---:|---:|
| ALL | 106 | 0.878R | 0.878R | 0.028R | 0.122R | 0.528R | 0.231 |
| WIN | 61 | 0.878R | 0.877R | 0.027R | 0.123R | 0.527R | 0.233 |
| LOSS | 45 | 0.880R | 0.880R | 0.030R | 0.120R | 0.530R | 0.227 |

## Deeper-entry causal opportunity atlas

| Level | Clean fills | Fill rate | Ambiguous same-bar | No fill | H2 after clean fill | Median fill→H2 | Reward→H | Future MAE | Diagnostic label |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| F80 | 92 | 86.8% | 8 | 6 | 68.5% | 50.0m | 0.200R | 0.482R | - |
| F75 | 91 | 85.8% | 7 | 8 | 62.6% | 60.0m | 0.250R | 0.450R | - |
| F70 | 87 | 82.1% | 5 | 14 | 59.8% | 60.0m | 0.300R | 0.484R | - |
| F65 | 87 | 82.1% | 3 | 16 | 54.0% | 65.0m | 0.350R | 0.447R | - |

## Source stability for deeper fills

| Level | Source | Clean fills | H2 after fill | Reward→H | Future MAE |
|---|---|---:|---:|---:|---:|
| F80 | ALT_0330 | 54 | 77.8% | 0.200R | 0.502R |
| F80 | RAW_0530 | 38 | 55.3% | 0.200R | 0.440R |
| F75 | ALT_0330 | 53 | 69.8% | 0.250R | 0.451R |
| F75 | RAW_0530 | 38 | 52.6% | 0.250R | 0.444R |
| F70 | ALT_0330 | 49 | 67.3% | 0.300R | 0.451R |
| F70 | RAW_0530 | 38 | 50.0% | 0.300R | 0.545R |
| F65 | ALT_0330 | 49 | 61.2% | 0.350R | 0.401R |
| F65 | RAW_0530 | 38 | 44.7% | 0.350R | 0.535R |

## Interpretation

No deeper level satisfies the frozen diagnostic gate. Entry depth alone is not yet supported as the next strategy change.

**Status: B27EI_BNB_ENTRY_DEPTH_DIAGNOSTICS_COMPLETE**

B27EI stops here. No alternative-entry economics or strategy selection is run automatically.
