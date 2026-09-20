# BNB B38-S2 — H1 Demand / 15m Structural Archetype Discovery

**2022-2024 DEVELOPMENT STUDY — NO OOS CLAIM**

Frozen parent: **788 H1-demand / 15m-execution visual-family events**.

## Primary archetypes

- **A CLEAN_PROXIMAL_RECLAIM**: distal demand holds; first 15m close reclaims above demand_high.
- **B CLEAN_IN_ZONE_HOLD**: distal demand holds; first 15m close remains inside demand.
- **C SWEEP_FULL_RECLAIM**: 15m low sweeps below demand_low, then close recovers above demand_high.
- **D SWEEP_PARTIAL_RECLAIM**: 15m low sweeps below demand_low, then close recovers only inside demand.

## Archetype census and path

| Archetype | N | Share | 2022/23/24 | +1ZW | +2ZW | Full cont. | MFE median | MFE IQR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A_CLEAN_PROXIMAL_RECLAIM | 415 | 52.7% | 140/124/151 | 72.3% | 56.4% | 38.1% | 2.57ZW | 1.01–6.55ZW |
| B_CLEAN_IN_ZONE_HOLD | 226 | 28.7% | 89/60/77 | 50.4% | 37.2% | 33.2% | 1.43ZW | 0.35–4.85ZW |
| C_SWEEP_FULL_RECLAIM | 65 | 8.2% | 16/28/21 | 70.8% | 63.1% | 33.8% | 6.10ZW | 2.27–15.41ZW |
| D_SWEEP_PARTIAL_RECLAIM | 82 | 10.4% | 30/30/22 | 41.5% | 31.7% | 13.4% | 1.66ZW | 0.09–4.69ZW |

## Geometry available at the retest close

| Archetype | Risk to demand_low | Risk to touch low | Room nearest 15m pivot | Room expansion high | Bullish touch | Compressed approach |
|---|---:|---:|---:|---:|---:|---:|
| A_CLEAN_PROXIMAL_RECLAIM | 1.38ZW | 0.63ZW | 2.46ZW | 2.70ZW | 19.8% | 41.9% |
| B_CLEAN_IN_ZONE_HOLD | 0.83ZW | 0.16ZW | 2.47ZW | 2.76ZW | 0.0% | 48.2% |
| C_SWEEP_FULL_RECLAIM | 2.01ZW | 3.02ZW | 8.18ZW | 8.24ZW | 18.5% | 24.6% |
| D_SWEEP_PARTIAL_RECLAIM | 0.39ZW | 0.98ZW | 5.01ZW | 5.87ZW | 0.0% | 34.1% |

## Successful +1ZW path

| Archetype | Median bars to +1ZW | Median adverse excursion before +1ZW |
|---|---:|---:|
| A_CLEAN_PROXIMAL_RECLAIM | 2.00 x15m | 1.05ZW |
| B_CLEAN_IN_ZONE_HOLD | 7.50 x15m | 0.49ZW |
| C_SWEEP_FULL_RECLAIM | 1.00 x15m | 3.17ZW |
| D_SWEEP_PARTIAL_RECLAIM | 2.00 x15m | 1.34ZW |

## Year-by-year +1ZW rebound

| Archetype | 2022 | 2023 | 2024 |
|---|---:|---:|---:|
| A_CLEAN_PROXIMAL_RECLAIM | 77.1% | 73.4% | 66.9% |
| B_CLEAN_IN_ZONE_HOLD | 52.8% | 51.7% | 46.8% |
| C_SWEEP_FULL_RECLAIM | 62.5% | 75.0% | 71.4% |
| D_SWEEP_PARTIAL_RECLAIM | 40.0% | 50.0% | 31.8% |

## Adaptive-execution questions created by S2
- **A CLEAN_PROXIMAL_RECLAIM:** test whether reclaim-close can be an immediate trigger and demand_low a structural invalidation reference.
- **B CLEAN_IN_ZONE_HOLD:** test a delayed confirmation trigger because price has not yet reclaimed the proximal edge.
- **C SWEEP_FULL_RECLAIM:** test whether the sweep low becomes the better structural invalidation reference than the original demand_low.
- **D SWEEP_PARTIAL_RECLAIM:** test whether entry must wait for a later 15m micro-BOS / proximal reclaim.

**No entry, SL, or TP rule is selected in S2.** The archetypes and their geometry are now mapped for B38-S3 adaptive execution design.
