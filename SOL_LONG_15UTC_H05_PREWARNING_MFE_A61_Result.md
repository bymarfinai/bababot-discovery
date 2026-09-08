# SOL LONG 15:00 UTC H05 Pre-warning MFE — A61 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A61 evaluates one causal feature only: maximum favorable high extension from breakout confirmation (or entry if later) through the completed first POST_H05 warning bar.

## Frozen threshold

- Development FAILED_BREAK median MFE: **0.0875R**
- Development RECOVER_E40 median MFE: **0.0925R**
- Frozen midpoint threshold T: **0.0900R**
- LOW_MFE = prewarning_mfe_R <= T

## Partition replication

| Partition | Fail N | Target N | Fail median | Target median | Fail LOW_MFE | Target LOW_MFE | Gap | Ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 184 | 31 | 0.0875R | 0.0925R | 51.1% | 48.4% | 2.7% | 1.06x |
| external | 113 | 32 | 0.0585R | 0.0734R | 70.8% | 56.2% | 14.5% | 1.26x |
| reference_validation | 107 | 29 | 0.0843R | 0.0610R | 53.3% | 65.5% | -12.2% | 0.81x |

## Development block consistency

| Block | Fail N | Target N | Fail hit | Target hit | Adequate | Same bad direction |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 31 | 4 | 51.6% | 100.0% | yes | no |
| 1 | 30 | 7 | 46.7% | 57.1% | yes | no |
| 2 | 33 | 5 | 51.5% | 40.0% | yes | yes |
| 3 | 25 | 5 | 48.0% | 20.0% | yes | yes |
| 4 | 37 | 4 | 45.9% | 50.0% | yes | no |
| 5 | 28 | 6 | 64.3% | 33.3% | yes | yes |

Adequate Development blocks with same bad direction: **3/6**.

## Frozen gate decision

- Development: **FAIL**
- External: **PASS**
- Reference Validation: **FAIL**

## Decision

**Status: SOL_LONG_15UTC_H05_PREWARNING_MFE_A61_INCONCLUSIVE**

The preregistered Development gate failed. Do not rescue the hypothesis by moving T or changing the MFE window.

Research only. Live Baba Bot remains unchanged.
