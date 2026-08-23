# B27BT — BTC 24H Age-2 Causal Failed-Reclaim Anatomy — Result

**Audit status: PASS.** All path classes use only the age-2 raw 5m source interval; the containing 4H final close is diagnostic-only and is not used to classify FAILED_RECLAIM.

Parent identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**

## Pooled OOS primary readout

| Origin | Age-2 cohort N | Baseline P(T) | FAILED_RECLAIM N | P(T|FR) | non-FR P(T) | FR lift | FR final-4H beyond diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 180 | 52.2% | 38 | 60.5% | 50.0% | +10.5pp | 63.2% |
| BEAR | 131 | 61.8% | 14 | 78.6% | 59.8% | +18.7pp | 85.7% |

## Pooled OOS path anatomy

| Origin | Path | N | Share | P(TRANSITION) |
|---|---|---:|---:|---:|
| BULL | NO_BREAK | 98 | 54.4% | 45.9% |
| BULL | BREAK_NO_RECLAIM | 37 | 20.6% | 64.9% |
| BULL | BREAK_RECLAIM_NO_REBREAK | 7 | 3.9% | 28.6% |
| BULL | FAILED_RECLAIM | 38 | 21.1% | 60.5% |
| BEAR | NO_BREAK | 93 | 71.0% | 57.0% |
| BEAR | BREAK_NO_RECLAIM | 20 | 15.3% | 70.0% |
| BEAR | BREAK_RECLAIM_NO_REBREAK | 4 | 3.1% | 75.0% |
| BEAR | FAILED_RECLAIM | 14 | 10.7% | 78.6% |

## OOS partition stability

| Partition | Origin | Cohort N | FR N | P(T|FR) | P(T|non-FR) | Lift |
|---|---|---:|---:|---:|---:|---:|
| external | BULL | 106 | 20 | 45.0% | 41.9% | +3.1pp |
| external | BEAR | 66 | 6 | 83.3% | 50.0% | +33.3pp |
| reference_validation | BULL | 74 | 18 | 77.8% | 62.5% | +15.3pp |
| reference_validation | BEAR | 65 | 8 | 75.0% | 70.2% | +4.8pp |

## Causal FAILED_RECLAIM timing — pooled OOS

| Origin | Break->reclaim min median [P25,P75] | Reclaim->rebreak min median [P25,P75] | Confirmation->regime-exit h median [P25,P75] |
|---|---|---|---|
| BULL | 22.5 [5.0,96.2] | 12.5 [5.0,25.0] | 9.75 [6.77,15.67] |
| BEAR | 45.0 [5.0,98.8] | 7.5 [5.0,21.2] | 7.04 [5.60,10.15] |

## Frozen support gate

- Exact raw-data/detector/parent identity: **PASS**.
- Every eligible episode maps to exactly one 48x5m age-2 path class: **PASS**.
- Pooled-OOS FAILED_RECLAIM N >=10/origin: **PASS**.
- Pooled-OOS P(T|FAILED_RECLAIM) >=65% both origins: **FAIL**.
- Pooled-OOS FR-minus-non-FR transition lift >=10pp both origins: **PASS**.
- External + validation positive FR lift with FR N>=3/cell, both origins: **PASS**.
- Causal confirmation and next 5m eligible open before eventual regime exit: **PASS**.
- Containing 4H final-close status excluded from classification/gate: **PASS**.
- No trading/economic/live BBC change: **PASS**.

**Frozen verdict: `B27BT_CAUSAL_FAILED_RECLAIM_NOT_SUPPORTED`.**

A supported result validates only a causal transition discriminator and a post-confirmation observation window. It does not authorize a trade.

Research only. Live BBC unchanged.
