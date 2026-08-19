# BTC Global/Pooled Regime Engine — G0 Result

**Status: PASS — advance to G1**

Research only; live BBC untouched.

## Locked label
One hourly market state; 50bp symmetric first-passage over the next 6h. Down first = SELL_COMPATIBLE, up first = BUY_COMPATIBLE, neither or same-5m-bar dual touch = NEUTRAL.

## Historical pooled dataset
- Candidate hourly states: **23,304**
- Eligible states: **23,304**
- Excluded: **0** — `{}`
- SELL_COMPATIBLE: **10,280 (44.11%)**
- BUY_COMPATIBLE: **10,225 (43.88%)**
- NEUTRAL: **2,799 (12.01%)**
- Same-bar dual-touch neutrals: **21**
- No-50bp-in-6h neutrals: **2,778**

## Yearly class distribution
| Year | N | SELL | BUY | NEUTRAL |
|---:|---:|---:|---:|---:|
| 2023 | 720 | 45.14% | 46.94% | 7.92% |
| 2024 | 8,784 | 44.60% | 47.18% | 8.22% |
| 2025 | 8,760 | 42.82% | 41.30% | 15.88% |
| 2026 | 5,040 | 45.36% | 42.16% | 12.48% |

## Feature finite-value audit
| Feature | Finite | Missing/nonfinite |
|---|---:|---:|
| ret1h | 100.00% | 0 |
| ret3h | 100.00% | 0 |
| ret6h | 100.00% | 0 |
| ret12h | 100.00% | 0 |
| ret24h | 100.00% | 0 |
| ema_spread | 100.00% | 0 |
| dist_ema20 | 100.00% | 0 |
| ema20_slope1h | 100.00% | 0 |
| loc24 | 100.00% | 0 |
| range6 | 100.00% | 0 |
| range24 | 100.00% | 0 |
| range6_to_24 | 100.00% | 0 |
| taker1h | 100.00% | 1 |
| taker4h | 100.00% | 0 |
| rv1h | 100.00% | 0 |
| rv6h | 100.00% | 0 |
| atr20_pct | 100.00% | 0 |

## Frozen Tuesday cross-check
- Historical Tuesday rows: **139**
- Historical Tuesday label rates: SELL **62.59%**, BUY **33.81%**, NEUTRAL **3.60%**.
- Frozen A5.11 historical parity: **PASS**.

### August Tuesday labels — report only
| Date WIB | G0 label | Reason | First hit min |
|---|---|---|---:|
| 2026-08-04 | BUY_COMPATIBLE | up_first | 165.0 |
| 2026-08-11 | NEUTRAL | no_50bp_hit_6h | nan |
| 2026-08-18 | NEUTRAL | no_50bp_hit_6h | nan |

## Acceptance gate
- PASS — `causal_integrity_by_construction`
- PASS — `intrabar_dual_touch_is_neutral`
- PASS — `coverage_ge_15000`
- PASS — `sell_class_ge_20pct`
- PASS — `buy_class_ge_20pct`
- PASS — `all_features_finite_ge_99pct`
- PASS — `a511_historical_parity_pass`
- PASS — `tuesday_historical_n139`

**Final G0 verdict: PASS. Dataset/label layer is viable; proceed to preregistered embargoed G1 baseline.**

G0 does not fit a model and does not claim a tradable edge.
