# B27BM — BTC 24H SIDEWAYS Age-Hazard Audit — Result

**Audit status: PASS.** Cause-specific temporal regime anatomy only; no classifier/refit, price threshold, LONG/SHORT mapping, entry, stop, target, fee, WR, PF, PnL, session filter, or live change was used.

B27BH identity reproduced exactly: **1,023 episodes = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491.**

Hazards are conditional on the SIDEWAYS episode still being alive at the stated age. `h_resume + h_transition + h_survive = 1` by construction.

## Pooled OOS cause-specific hazards

| Origin | Age | Risk N | h RESUME | h TRANSITION | h SURVIVE | TRANSITION-RESUME |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 1 / 4h | 313 | 28.8% | 13.7% | 57.5% | -15.0pp |
| BULL | 2 / 8h | 180 | 20.0% | 25.0% | 55.0% | +5.0pp |
| BULL | 3 / 12h | 99 | 13.1% | 22.2% | 64.6% | +9.1pp |
| BULL | 4 / 16h | 64 | 9.4% | 7.8% | 82.8% | -1.6pp |
| BULL | 5 / 20h | 53 | 9.4% | 7.5% | 83.0% | -1.9pp |
| BULL | 6 / 24h | 44 | 4.5% | 6.8% | 88.6% | +2.3pp |
| BEAR | 1 / 4h | 242 | 25.2% | 20.7% | 54.1% | -4.5pp |
| BEAR | 2 / 8h | 131 | 19.1% | 40.5% | 40.5% | +21.4pp |
| BEAR | 3 / 12h | 53 | 20.8% | 30.2% | 49.1% | +9.4pp |
| BEAR | 4 / 16h | 26 | 30.8% | 30.8% | 38.5% | +0.0pp |
| BEAR | 5 / 20h | 10 | 0.0% | 20.0% | 80.0% | +20.0pp |
| BEAR | 6 / 24h | 8 | 0.0% | 12.5% | 87.5% | +12.5pp |

## OOS partition stability — ages 1 and 2

| Partition | Origin | Age1 T-R | Age2 T-R | Upward shift? |
|---|---|---:|---:|---|
| external | BULL | -17.8pp | -0.9pp | YES |
| external | BEAR | -7.4pp | +10.6pp | YES |
| reference_validation | BULL | -12.0pp | +13.5pp | YES |
| reference_validation | BEAR | -2.2pp | +32.3pp | YES |

## Pooled-major combined-origin descriptive hazard

| Age | Risk N | h RESUME | h TRANSITION | h SURVIVE | T-R |
|---:|---:|---:|---:|---:|---:|
| 1 / 4h | 1023 | 29.9% | 19.6% | 50.5% | -10.4pp |
| 2 / 8h | 517 | 23.8% | 32.5% | 43.7% | +8.7pp |
| 3 / 12h | 226 | 17.3% | 31.9% | 50.9% | +14.6pp |
| 4 / 16h | 115 | 17.4% | 25.2% | 57.4% | +7.8pp |
| 5 / 20h | 66 | 10.6% | 10.6% | 78.8% | +0.0pp |
| 6 / 24h | 52 | 3.8% | 7.7% | 88.5% | +3.8pp |

## Frozen support gate

- Exact parent identity / hazard accounting: **PASS**.
- Both origins pooled-OOS age1 resume hazard > transition hazard: **PASS**.
- Both origins pooled-OOS have transition hazard > resume hazard at age2 or age3: **PASS**.
- Age1->age2 T-R margin shifts upward in external AND validation for both origins: **PASS**.
- OOS risk N >=30 per origin at ages1-3: **PASS**.

**Frozen verdict: `B27BM_PHASED_SIDEWAYS_HAZARD_SUPPORTED`.**

## Interpretation boundary

A supported result validates only a reproducible age-dependent SIDEWAYS hazard shape. It does not yet define a production PENDING state or any trading behavior. Ages 4-6 are descriptive only and cannot rescue the primary gate.

Research only. Live BBC unchanged.
