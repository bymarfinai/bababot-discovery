# B27BR — BTC 24H SIDEWAYS Age × Frozen-Boundary Combination — Result

**Audit status: PASS.** Combined regime-state anatomy only; no trading/economic rule or live change was used.

Frozen parent identity reproduced from the exact B27BN audited episode artifact: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491; pooled OOS BULL 313; BEAR 242.**

## Pooled OOS — cumulative wick-break router

| Origin | Age | Risk N | BREAK N | P(TRANSITION \| BREAK) | HOLD N | P(TRANSITION \| HOLD) | Lift |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 1 / 4h | 313 | 87 | 49.4% | 226 | 41.6% | +7.8pp |
| BULL | 2 / 8h | 180 | 95 | 54.7% | 85 | 49.4% | +5.3pp |
| BULL | 3 / 12h | 99 | 63 | 52.4% | 36 | 44.4% | +7.9pp |
| BEAR | 1 / 4h | 242 | 71 | 59.2% | 171 | 52.0% | +7.1pp |
| BEAR | 2 / 8h | 131 | 44 | 72.7% | 87 | 56.3% | +16.4pp |
| BEAR | 3 / 12h | 53 | 16 | 68.8% | 37 | 45.9% | +22.8pp |

## OOS stability — primary age 2 / 8h

| Partition | Origin | Risk N | BREAK N | P(T|BREAK) | HOLD N | P(T|HOLD) | Lift |
|---|---|---:|---:|---:|---:|---:|---:|
| external | BULL | 106 | 58 | 44.8% | 48 | 39.6% | +5.2pp |
| external | BEAR | 66 | 23 | 69.6% | 43 | 44.2% | +25.4pp |
| reference_validation | BULL | 74 | 37 | 70.3% | 37 | 62.2% | +8.1pp |
| reference_validation | BEAR | 65 | 21 | 76.2% | 44 | 68.2% | +8.0pp |

## Development — age 2 diagnostic

| Origin | Risk N | BREAK N | P(T|BREAK) | HOLD N | P(T|HOLD) | Lift |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 96 | 50 | 72.0% | 46 | 56.5% | +15.5pp |
| BEAR | 110 | 47 | 59.6% | 63 | 49.2% | +10.4pp |

## Secondary diagnostic — cumulative close-break

| Origin | Age | BREAK N | P(T|CLOSE BREAK) | HOLD N | P(T|NO CLOSE BREAK) | Lift |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 1 / 4h | 62 | 51.6% | 251 | 41.8% | +9.8pp |
| BULL | 2 / 8h | 66 | 65.2% | 114 | 44.7% | +20.4pp |
| BULL | 3 / 12h | 47 | 59.6% | 52 | 40.4% | +19.2pp |
| BEAR | 1 / 4h | 46 | 56.5% | 196 | 53.6% | +3.0pp |
| BEAR | 2 / 8h | 33 | 72.7% | 98 | 58.2% | +14.6pp |
| BEAR | 3 / 12h | 9 | 66.7% | 44 | 50.0% | +16.7pp |

## Frozen primary gate

- Exact parent identity / boundary availability: **PASS**.
- Age-2 pooled-OOS risk N >=30/origin: **PASS**.
- Age-2 pooled-OOS BREAK/HOLD N >=20/origin: **PASS**.
- Age-2 pooled-OOS transition lift >0 for both origins: **PASS**.
- Age-2 lift positive in external AND validation for both origins with >=5/cell: **PASS**.
- Age-2 pooled-OOS lift > age-1 lift for both origins: **FAIL**.
- Causal age/boundary accounting and no live change: **PASS**.

**Frozen verdict: `B27BR_AGE2_BOUNDARY_ROUTER_NOT_SUPPORTED`.**

## Interpretation

The age-2 wick-break signal is positive and OOS-stable in sign for both origins, but the preregistered synergy condition fails because BULL-origin lift does not strengthen from age 1 to age 2 (7.8pp -> 5.3pp). BEAR-origin does strengthen materially (7.1pp -> 16.4pp).

The secondary close-break diagnostic is materially stronger at age 2 (BULL +20.4pp; BEAR +14.6pp), but it is diagnostic-only in B27BR and cannot rescue the frozen primary verdict.

Research only. Live BBC unchanged.
