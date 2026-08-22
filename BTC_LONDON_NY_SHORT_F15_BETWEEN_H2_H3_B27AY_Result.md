# B27AY — BTC London->NY SHORT F15 Entry Between Retest #2 and #3 — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen original #1→#2 E20-hybrid baseline reproduced exactly before the timing-shift cohort was interpreted.

Original pooled-major #1→#2 baseline: N=163, E20 activated=92, total **$-15.058**.

| Partition | K1 | Valid H2 | Clean leave2 | F15 fills #2→#3 | H3 hits | H3/fill | Break after H3 | E20 act | E20/fill | WR | PF | Exp/trade $ | Total $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 94 | 28 | 13 | 10 | 4 | 40.0% | 2 | 3 | 30.0% | 40.0% | 0.579 | -0.716 | -7.157 |
| development | 192 | 59 | 42 | 26 | 14 | 53.8% | 13 | 17 | 65.4% | 65.4% | 1.223 | 0.242 | 6.289 |
| reference_validation | 92 | 19 | 14 | 6 | 3 | 50.0% | 3 | 3 | 50.0% | 83.3% | 3.283 | 1.053 | 6.318 |
| august | 2 | 1 | 1 | 1 | 1 | 100.0% | 0 | 0 | 0.0% | 0.0% | 0.000 | -2.420 | -2.420 |
| POOLED_MAJOR | 378 | 106 | 69 | 42 | 21 | 50.0% | 18 | 23 | 54.8% | 61.9% | 1.114 | 0.130 | 5.450 |

## Frozen readout

Pooled-major timing-shift total: **$+5.450** vs original **$-15.058** (delta **$+20.508**).
Pooled-major F15 fills between #2→#3: **42**; H3 rate: **50.0%**; E20 activation rate: **54.8%**.

**Status:** `B27AY_PASS__TIMING_SHIFT_POOLED_IMPROVED_NOT_ROBUST`

No alternative F fraction, stop, activation, confirmation, regime, threshold, or runner parameter was tested. Research only; live BBC unchanged.
