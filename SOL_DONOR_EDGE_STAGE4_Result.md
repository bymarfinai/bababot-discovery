# SOL Donor Post-Shock Edge Extraction — Stage 4 Result

Raw SOLUSDT 5m coverage: **100.0000%**.
Stage 4 used **2023 SEARCH + 2024 INTERNAL VALIDATION only**. 2025/2026 were not evaluated.

## Population

- Labeled shock-hours: **5718**.
- SEARCH events: **2789**.
- INTERNAL VALIDATION events: **2929**.

## Strongest raw SEARCH median separations

| Feature | Win median | Loss median | Gap |
|---|---:|---:|---:|
| cci_delta15 | 29.027 | 30.5492 | -1.52216 |
| rsi4_delta15 | 1.86711 | 2.53273 | -0.665628 |
| rsi4_end | 40.1453 | 40.6794 | -0.534096 |
| rsi14_end | 41.5568 | 41.7022 | -0.145423 |
| cci14_end | -71.6771 | -71.6223 | -0.0547979 |
| vol15_vs_prev45 | 0.848395 | 0.883475 | -0.0350798 |
| lower_wick_frac | 0.315789 | 0.336697 | -0.0209078 |
| hour_clv | 0.342857 | 0.362533 | -0.0196756 |
| upper_wick_frac | 0.16 | 0.166432 | -0.00643192 |
| hour_range | 0.0140435 | 0.0130157 | 0.00102779 |

## Top frozen candidate rules after 2024 internal validation

| Rule | 2023 trades/day | 2023 WR | 2024 trades/day | 2024 WR | 2024 avg net | Promote |
|---|---:|---:|---:|---:|---:|---|
| ema20_dist >= -0.00046124673 | 2.022 | 50.8% | 2.115 | 50.8% | -0.1% | NO |
| ema20_slope >= -4.854993e-05 | 2.022 | 50.8% | 2.115 | 50.8% | -0.1% | NO |
| ema20_dist >= -0.00046124673 AND ema20_slope >= -4.854993e-05 | 2.022 | 50.8% | 2.115 | 50.8% | -0.1% | NO |
| prev1h_ret <= -0.006611419 | 1.479 | 52.2% | 1.781 | 50.6% | -0.1% | NO |
| ret15 <= -0.0038177812 | 1.482 | 52.1% | 1.702 | 50.6% | -0.1% | NO |
| ema8_dist <= -0.0033896582 | 1.490 | 50.7% | 1.713 | 50.6% | -0.1% | NO |
| ema20_dist >= 0.0057260027 | 1.288 | 54.0% | 1.262 | 50.2% | -0.1% | NO |
| ema20_slope >= 0.00060310064 | 1.288 | 54.0% | 1.262 | 50.2% | -0.1% | NO |
| ema20_dist >= 0.0057260027 AND ema20_slope >= 0.00060310064 | 1.288 | 54.0% | 1.262 | 50.2% | -0.1% | NO |
| ema20_dist >= 0.0057260027 AND ema20_slope >= -4.854993e-05 | 1.288 | 54.0% | 1.262 | 50.2% | -0.1% | NO |
| ema20_slope >= 0.00060310064 AND ema20_dist >= -0.00046124673 | 1.288 | 54.0% | 1.262 | 50.2% | -0.1% | NO |
| vol15_vs_prev45 >= 1.4974724 | 1.414 | 50.6% | 1.555 | 48.9% | -0.2% | NO |

## Decision

**Status: SOL_DONOR_EDGE_STAGE4_NO_PROMOTABLE_EDGE**

Best internal-validation rule: **ema20_dist >= -0.00046124673**.
2024: 2.115/day, WR 50.8%, avg net -0.1%.
No rule met all frozen Stage-4 frequency, WR, positive-net, and stability gates. Stage 5 should not test a donor-derived rule unless a new preregistered hypothesis is created.
