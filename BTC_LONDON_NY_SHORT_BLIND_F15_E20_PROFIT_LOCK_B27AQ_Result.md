# B27AQ — BTC London->NY SHORT BLIND_F15 E20 Profit-Lock Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27AK F15 identities and B27AN E20/D50 fixed baseline reproduced before the post-E20 runner was interpreted.

Fixed pooled-major E20/D50 total: **$-11.666**.

| Partition | N | WR | PF | Exp/trade $ | Total $ | E20 reach | Ceiling hits | Gap exits | Time exits | Med ratchets | Med trough ext | Med exit ext | Med capture | Med giveback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 50 | 54.0% | 1.593 | 0.908 | 45.389 | 56.0% | 8 | 20 | 15 | 0.000 | 0.585 | 0.175 | 0.283 | 0.410 |
| development | 79 | 54.4% | 0.842 | -0.272 | -21.484 | 59.5% | 14 | 33 | 10 | 0.000 | 0.640 | 0.132 | 0.168 | 0.586 |
| reference_validation | 34 | 50.0% | 0.433 | -1.146 | -38.964 | 50.0% | 8 | 9 | 4 | 0.000 | 0.834 | 0.182 | 0.218 | 0.665 |
| august | 1 | 0.0% | 0.000 | -2.420 | -2.420 | 0.0% | 0 | 0 | 0 | 0.000 | - | - | - | - |
| POOLED_MAJOR | 163 | 53.4% | 0.946 | -0.092 | -15.058 | 56.4% | 30 | 62 | 29 | 0.000 | 0.643 | 0.165 | 0.213 | 0.528 |

## Frozen support gate

**Status: B27AQ_NOT_SUPPORTED.**

No alternate target, stop, regime gate, confirmation, or runner parameter was introduced.

Research only; live BBC unchanged.
