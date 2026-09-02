# ETH London -> New York M11 Deep-Breach Secondary F90 Reclaim — Result

Execution basis: **deterministic reconstruction from the persisted M10 95-row cohort**. M10 already persisted the first F80/F75 breach timestamps, first later F90 reclaim timestamps, strict-breakout timestamps, terminal completion, partition, and outcome for every executed F90 EARLY_RECLAIM trade. No trading semantics were changed.

- M10 cohort parity: **95 rows / 77 breakout winners**.
- Deep-breach event counts reproduce M10 exactly: **F80 41 = 24 winners + 17 non-winners; F75 32 = 17 winners + 15 non-winners**.
- M10 source raw-5m coverage: **100.0000%**.
- Timestamp chronology audit: **PASS**.

## Secondary F90 reclaim signature — pooled major

| Boundary | Deep N | Winners | Non-winners | Winner reclaim | Before BO | On BO bar | Non-winner reclaim | Separation | BO if reclaim | BO if no reclaim | Signature |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| F80 | 41 | 24 | 17 | 100.0% | 70.8% | 29.2% | 11.8% | 88.2 pp | 92.3% | 0.0% | PASS |
| F75 | 32 | 17 | 15 | 100.0% | 64.7% | 35.3% | 6.7% | 93.3 pp | 94.4% | 0.0% | PASS |

## Major-partition detail

| Partition | Boundary | Deep N | Winner N | Non-winner N | Winner reclaim | Before BO | On BO bar | Non-winner reclaim | Median breach->reclaim |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | F80 | 16 | 9 | 7 | 100.0% | 88.9% | 11.1% | 14.3% | 15.0m |
| external | F75 | 10 | 5 | 5 | 100.0% | 80.0% | 20.0% | 0.0% | 20.0m |
| development | F80 | 21 | 13 | 8 | 100.0% | 53.8% | 46.2% | 12.5% | 32.5m |
| development | F75 | 18 | 10 | 8 | 100.0% | 50.0% | 50.0% | 12.5% | 90.0m |
| reference_validation | F80 | 4 | 2 | 2 | 100.0% | 100.0% | 0.0% | 0.0% | 92.5m |
| reference_validation | F75 | 4 | 2 | 2 | 100.0% | 100.0% | 0.0% | 0.0% | 85.0m |

## No-reclaim recovery deadlines — pooled major

| Boundary | Checkpoint | No-reclaim N | Eventual BO | Winner protected by deadline | Candidate |
|---|---:|---:|---:|---:|---|
| F80 | 15m | 29 | 44.8% | 45.8% | NO |
| F80 | 30m | 23 | 39.1% | 62.5% | NO |
| F80 | 45m | 17 | 29.4% | 79.2% | NO |
| F80 | 60m | 17 | 29.4% | 79.2% | NO |
| F75 | 15m | 29 | 48.3% | 17.6% | NO |
| F75 | 30m | 21 | 42.9% | 47.1% | NO |
| F75 | 45m | 18 | 33.3% | 64.7% | NO |
| F75 | 60m | 18 | 33.3% | 64.7% | NO |

## Development-specific recovery

The secondary-reclaim event is much slower / later in Development:
- F80 deep-breach winners: **13**; only **7/13 (53.8%)** reclaim F90 before the breakout candle, while **6/13 (46.2%)** first reclaim F90 on the breakout candle itself.
- F75 deep-breach winners: **10**; **5/10 (50.0%)** reclaim before breakout and **5/10 (50.0%)** only on the breakout candle.
- Development non-winner reclaim rate is only **12.5%** at both F80 and F75.
- However, at F80 +45m without reclaim, Development still has **40.0% eventual breakout**; F75 +45m still has **45.5% eventual breakout**. A hard no-reclaim deadline would therefore kill too many eventual winners.

## Decision

**Status: ETH_LONDON_NY_M11_SECONDARY_RECLAIM_SIGNATURE_SUPPORTED**

- Supported structural secondary-reclaim boundaries: **F80, F75**.
- Recovery-deadline candidates: **none**.
- Important qualification: the supported signature is descriptive structural separation, not yet an actionable pre-breakout filter. A material share of winners—especially Development—first reclaim F90 on the breakout bar itself, so “wait for secondary reclaim” often provides no earlier decision point.
- No economic rule, stop, timeout, target, runner, leverage, or portfolio lock is authorized by M11.
