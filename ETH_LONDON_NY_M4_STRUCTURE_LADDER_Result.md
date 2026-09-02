# ETH London -> New York M4 Structure Ladder — Result

Raw 5m coverage: ETH **100.0000%**, BTC **100.0000%**.

Frozen causal ladder: **fill -> H2 arrival -> strict close breakout > H -> post-confirmation E10/E20 extension**. H2 is not TP.

- ETH filled entries audited: **703**.
- BTC control filled entries audited: **660**.
- Entry identity / chronology audit: **PASS**.

## ETH pooled-major structure

| Entry | N | H2/fill | Breakout/fill | Breakout/H2 | Immediate BO/H2 | Later BO after H2 reject | E10 after confirmed BO | E20 after confirmed BO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F95 | 98 | 87.8% | 78.6% | 89.5% | 53.5% | 77.5% | 90.9% | 81.8% |
| F90 | 151 | 83.4% | 77.5% | 92.9% | 55.6% | 83.9% | 93.2% | 83.8% |
| F85 | 160 | 81.2% | 74.4% | 91.5% | 52.3% | 82.3% | 92.4% | 84.0% |
| F80 | 149 | 76.5% | 69.8% | 91.2% | 52.6% | 81.5% | 94.2% | 86.5% |
| F75 | 138 | 73.2% | 68.1% | 93.1% | 56.4% | 84.1% | 93.6% | 86.2% |

## BTC pooled-major structure

| Entry | N | H2/fill | Breakout/fill | Breakout/H2 | Immediate BO/H2 | Later BO after H2 reject | E10 after confirmed BO | E20 after confirmed BO |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F95 | 89 | 92.1% | 87.6% | 95.1% | 53.7% | 89.5% | 94.9% | 84.6% |
| F90 | 132 | 85.6% | 81.1% | 94.7% | 52.2% | 88.9% | 96.3% | 86.0% |
| F85 | 149 | 81.2% | 76.5% | 94.2% | 53.7% | 87.5% | 96.5% | 89.5% |
| F80 | 143 | 76.2% | 72.0% | 94.5% | 52.3% | 88.5% | 96.1% | 90.3% |
| F75 | 134 | 70.9% | 67.2% | 94.7% | 47.4% | 90.0% | 95.6% | 88.9% |

## ETH major-partition breakout calibration

| Partition | Entry | N | H2/fill | Breakout/fill | Breakout/H2 | Immediate BO/H2 | Later BO after reject |
|---|---|---:|---:|---:|---:|---:|---:|
| external | F95 | 36 | 94.4% | 91.7% | 97.1% | 61.8% | 92.3% |
| external | F90 | 56 | 83.9% | 78.6% | 93.6% | 57.4% | 85.0% |
| external | F85 | 56 | 82.1% | 76.8% | 93.5% | 56.5% | 85.0% |
| external | F80 | 45 | 75.6% | 68.9% | 91.2% | 58.8% | 78.6% |
| external | F75 | 42 | 73.8% | 71.4% | 96.8% | 64.5% | 90.9% |
| development | F95 | 43 | 86.0% | 69.8% | 81.1% | 51.4% | 61.1% |
| development | F90 | 65 | 84.6% | 75.4% | 89.1% | 50.9% | 77.8% |
| development | F85 | 70 | 82.9% | 72.9% | 87.9% | 44.8% | 78.1% |
| development | F80 | 69 | 78.3% | 69.6% | 88.9% | 44.4% | 80.0% |
| development | F75 | 65 | 73.8% | 66.2% | 89.6% | 50.0% | 79.2% |
| reference_validation | F95 | 19 | 78.9% | 73.7% | 93.3% | 40.0% | 88.9% |
| reference_validation | F90 | 30 | 80.0% | 80.0% | 100.0% | 62.5% | 100.0% |
| reference_validation | F85 | 34 | 76.5% | 73.5% | 96.2% | 61.5% | 90.0% |
| reference_validation | F80 | 35 | 74.3% | 71.4% | 96.2% | 61.5% | 90.0% |
| reference_validation | F75 | 31 | 71.0% | 67.7% | 95.5% | 59.1% | 88.9% |

## Decision

**Status: ETH_LONDON_NY_M4_STRUCTURE_LADDER_CALIBRATED**

M4 is descriptive structural calibration only. No entry level, TP, stop, runner, or economic configuration is promoted by this result.