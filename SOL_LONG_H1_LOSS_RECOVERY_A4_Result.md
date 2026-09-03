# SOL LONG H1 Loss Recovery — A4 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A4 keeps every frozen A2 parent loss unchanged and asks whether one later resting-H recovery entry can make the combined episode profitable.

## Central Development latent recovery anatomy

| Parent loss class | N | Target eventually hit after exit | Median time to E40 | Modal target visit | Target visit entry-eligible | Median original loss |
|---|---:|---:|---:|---:|---:|---:|
| L2_BREAK_FAST_FAIL_5M | 116 | 65.5% | 160m | H2 | 78.9% | $0.84 |
| L1_NEVER_BREAK_TIME | 59 | 39.0% | 290m | H4 | 95.7% | $6.17 |
| L4_BREAK_FAIL_30M | 56 | 66.1% | 120m | H2 | 78.4% | $0.63 |
| L3_BREAK_FAST_FAIL_10M | 41 | 51.2% | 120m | H2 | 76.2% | $0.62 |
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | 37 | 18.9% | 360m | H2 | 100.0% | $14.00 |
| L5_BREAK_FAIL_LATE | 32 | 56.2% | 255m | H2 | 88.9% | $0.47 |

## Development recovery-lane economics

| Lane | N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | Rescue rate | 5bps rescue | Overlay PF | Overlay net | +blocks | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| REC_H2 | 216 | 26.9% | 1.58 | $0.62 | $134.76 | 1.30 | $0.37 | 25.0% | 24.5% | 1.31 | $448.82 | 5/6 | YES |
| REC_H3 | 166 | 25.9% | 1.21 | $0.24 | $40.54 | 1.00 | $-0.01 | 21.7% | 21.7% | 1.25 | $354.60 | 3/6 | NO |
| REC_H4 | 128 | 23.4% | 0.72 | $-0.42 | $-54.33 | 0.61 | $-0.67 | 20.3% | 19.5% | 1.18 | $259.73 | 2/6 | NO |

## Frozen Development recovery lane

- Lane: **REC_H2**.
- Recovery N: **216**; WR **26.9%**; PF **1.58**; expectancy **$0.62**; net **$134.76**.
- 5bps PF **1.30**; expectancy **$0.37**.
- Episode rescue rate: **25.0%**; 5bps **24.5%**.
- Frozen A2 Central Development PF/net becomes **1.31 / $448.82** when the recovery overlay is added as an extra trade.

## OOS recovery economics

| Role | Partition | N | WR | PF | Exp | Net | 5bps PF | 5bps Net | Rescue rate | Overlay PF | Overlay net |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | external | 125 | 27.2% | 1.44 | $0.90 | $112.87 | 1.29 | $81.62 | 24.0% | 1.46 | $460.40 |
| CENTRAL | reference_validation | 139 | 30.2% | 1.34 | $0.33 | $45.96 | 1.07 | $11.21 | 25.2% | 1.20 | $127.92 |
| CLOCK_SUPPORT | external | 134 | 30.6% | 1.33 | $0.68 | $91.16 | 1.19 | $57.66 | 26.1% | 1.47 | $476.21 |
| CLOCK_SUPPORT | reference_validation | 129 | 22.5% | 1.48 | $0.37 | $47.85 | 1.13 | $15.60 | 20.9% | 1.56 | $280.37 |
| REF_SUPPORT | external | 127 | 28.3% | 0.99 | $-0.02 | $-2.82 | 0.88 | $-34.57 | 24.4% | 1.31 | $335.46 |
| REF_SUPPORT | reference_validation | 150 | 35.3% | 1.41 | $0.38 | $57.21 | 1.12 | $19.71 | 30.0% | 1.27 | $166.05 |

## Decision

**Status: SOL_LONG_H1_LOSS_RECOVERY_A4_SUPPORTED**

A later canonical H-visit can be used as a supported second-chance recovery overlay under the preregistered gates. This is still research-only and is not promoted to the live bot.

Research only. Live Baba Bot remains unchanged.
