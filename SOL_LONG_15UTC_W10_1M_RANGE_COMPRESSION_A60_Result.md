# SOL LONG 15:00 UTC W10 1m Range Compression Revalidation — A60 Result

A60 tests one locked continuous candidate from A58: K3 latest completed 1m range normalized by R. The threshold is derived from Development only and then frozen before scoring External or Reference Validation.

## Frozen threshold derivation

- Development FAILED_BREAK median: **0.070956R**
- Development RECOVER_E40 median: **0.085308R**
- Frozen midpoint threshold T: **0.078132R**
- Compression rule: `latest_range_R <= 0.078131796` at **K3 only**.

## Partition discrimination

| Partition | Fail N | Target N | Time N | Fail hit | Target hit | Gap | Ratio | Compressed | Time hit | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| development | 233 | 63 | 4 | 55.8% | 41.3% | 14.5pp | 1.35x | 159 (53.0%) | 75.0% | PASS |
| external | 133 | 54 | 5 | 72.9% | 70.4% | 2.6pp | 1.04x | 139 (72.4%) | 80.0% | fail |
| reference_validation | 134 | 48 | 2 | 56.0% | 47.9% | 8.1pp | 1.17x | 99 (53.8%) | 50.0% | PASS |

## Development six-block direction

| Block | Fail N | Target N | Fail hit | Target hit | Gap | Ratio | Eligible | Bad direction |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 40 | 8 | 67.5% | 37.5% | 30.0pp | 1.80x | True | True |
| 1 | 37 | 16 | 48.6% | 43.8% | 4.9pp | 1.11x | True | True |
| 2 | 41 | 9 | 43.9% | 55.6% | -11.7pp | 0.79x | True | False |
| 3 | 30 | 8 | 40.0% | 50.0% | -10.0pp | 0.80x | True | False |
| 4 | 46 | 10 | 58.7% | 20.0% | 38.7pp | 2.93x | True | True |
| 5 | 39 | 12 | 71.8% | 41.7% | 30.1pp | 1.72x | True | True |

Bad direction in eligible Development blocks: **4/6**.

## Frozen gate details

Development: fail_gt_target=PASS, gap_ge_10pp=PASS, ratio_ge_1p25=PASS, fail_hit_ge_45pct=PASS, blocks_ge_4of6=PASS

External: support=PASS, fail_gt_target=PASS, gap_ge_5pp=fail, ratio_ge_1p15=fail, fail_hit_ge_40pct=PASS

Reference Validation: support=PASS, fail_gt_target=PASS, gap_ge_5pp=PASS, ratio_ge_1p15=PASS, fail_hit_ge_40pct=PASS

## Decision

**Status: SOL_LONG_15UTC_W10_1M_RANGE_COMPRESSION_A60_DEVELOPMENT_ONLY**

A60 remains conditional on the completed first-W10 cohort and is therefore anatomy/revalidation only. A supported result authorizes only a later replay across all live-causal post-breakout opportunities; it does not authorize an exit or position-management rule.

Research only. Live Baba Bot remains unchanged.
