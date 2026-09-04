# SOL LONG 15:00 UTC Confirmed-Recovery Retest Anatomy — A35 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A35 is forensic only. It studies the exact A34 DC10_C12 confirmation cohort and asks whether confirmed E40 continuations offer a cheaper E10/E05 retest before target.

## Summary

| Role | Partition | N | E40 rate | Winner→E10 retest | Winner→E05 retest | All E10 retest | E10 retest→E40 | Median E10 retest | E40 median min-low | Non-E40 median min-low |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | 27 | 59.3% | 6.2% | 6.2% | 44.4% | 8.3% | 10m | 0.154R | -0.045R |
| CENTRAL | external | 19 | 52.6% | 40.0% | 20.0% | 68.4% | 30.8% | 10m | 0.169R | -0.073R |
| CENTRAL | reference_validation | 13 | 61.5% | 37.5% | 25.0% | 61.5% | 37.5% | 8m | 0.121R | -0.070R |
| CLOCK_SUPPORT | development | 34 | 44.1% | 33.3% | 6.7% | 70.6% | 20.8% | 10m | 0.144R | -0.047R |
| CLOCK_SUPPORT | external | 18 | 55.6% | 30.0% | 10.0% | 61.1% | 27.3% | 5m | 0.134R | -0.063R |
| CLOCK_SUPPORT | reference_validation | 21 | 52.4% | 45.5% | 36.4% | 71.4% | 33.3% | 10m | 0.063R | -0.062R |
| REF_SUPPORT | development | 27 | 48.1% | 15.4% | 7.7% | 59.3% | 12.5% | 8m | 0.144R | -0.045R |
| REF_SUPPORT | external | 17 | 52.9% | 33.3% | 22.2% | 64.7% | 27.3% | 10m | 0.148R | -0.090R |
| REF_SUPPORT | reference_validation | 14 | 57.1% | 37.5% | 25.0% | 64.3% | 33.3% | 10m | 0.121R | -0.079R |

## Decision

- Dev winner E10 retest=6.2%, E10->E40=8.3%; Central OOS winner E10 retest=40.0%/37.5%; support nonzero=4/4.

**Status: SOL_LONG_15UTC_CONFIRMED_RETEST_A35_INCONCLUSIVE**

If supported, A36 may test one fixed confirmation-then-E10 resting retest entry. E05 remains diagnostic unless separately authorized by A35 evidence.

Research only. Live Baba Bot remains unchanged.
