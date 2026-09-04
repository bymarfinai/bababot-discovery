# SOL LONG Additional Untouched Clocks — A20 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A20 continues Stage 12 using only untouched clock candidates derived from the old A1 anatomy atlas. Supported 18:00 and 03:00 clusters remain frozen; A17-tested 08:00 and 13:00 are not retuned.

## Frozen untouched candidates

| Candidate | Ref | Clock UTC | Distance to supported clock | Stable blocks | Break conversion | Median extension | Clock support | Ref support |
|---|---:|---:|---:|---:|---:|---:|---|---|
| A20_Z1_R360_H15 | 360m | 15:00 | 3h | 5/6 | 69.2% | 0.211R | R360/16 | R300/15 |
| A20_Z2_R120_H12 | 120m | 12:00 | 6h | 5/6 | 71.9% | 0.368R | R120/11 | R180/12 |

## Central Development economics

| Candidate | N | Trades/wk | WR | PF | Net | 5bps PF | 5bps Net | +blocks raw/stress | Existing-portfolio overlap | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| A20_Z1_R360_H15 | 601 | 3.84 | 40.6% | 1.28 | $338.91 | 1.14 | $188.66 | 5/5 | 38.9% | YES |
| A20_Z2_R120_H12 | 832 | 5.31 | 52.5% | 0.95 | $-71.46 | 0.83 | $-279.46 | 3/1 | 21.0% | NO |

Frozen Development winner: **A20_Z1_R360_H15**.

## Frozen OOS

| Role | Partition | Cell | N | WR | PF | Net | 5bps PF | 5bps Net |
|---|---|---|---:|---:|---:|---:|---:|---:|
| CANDIDATE | external | R360/15 | 281 | 40.9% | 1.55 | $419.82 | 1.43 | $349.57 |
| CANDIDATE | reference_validation | R360/15 | 337 | 44.5% | 1.57 | $263.33 | 1.35 | $179.08 |
| CLOCK_SUPPORT | external | R360/16 | 273 | 38.5% | 1.49 | $371.81 | 1.38 | $303.56 |
| CLOCK_SUPPORT | reference_validation | R360/16 | 309 | 37.5% | 1.55 | $228.12 | 1.33 | $150.87 |
| REF_SUPPORT | external | R300/15 | 288 | 45.8% | 1.82 | $593.37 | 1.69 | $521.37 |
| REF_SUPPORT | reference_validation | R300/15 | 344 | 43.9% | 1.63 | $276.93 | 1.39 | $190.93 |

Validation: **central_ok=True; support positive raw=4/4; support positive 5bps=4/4**.

## Decision

**Status: SOL_LONG_ADDITIONAL_CLOCKS_A20_SUPPORTED**

A20 promotes only a supported parent habitat. Recovery is not inherited; any recovery transfer requires a separate preregistered test.

Research only. Live Baba Bot remains unchanged.
