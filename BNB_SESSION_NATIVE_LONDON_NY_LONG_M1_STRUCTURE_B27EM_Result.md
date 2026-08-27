# BNB Session-Native London→New York LONG M1 Structure — B27EM Result

Raw BNB 5m coverage: **100.0000%**. Actual raw span: **2020-02-10 08:00:00+00:00 to 2026-08-26 00:00:00+00:00**.

Clocking is DST-aware: reference = **08:00 Europe/London → 09:30 America/New_York**; execution = **09:30 → 16:00 America/New_York**.

B27EM is LONG structural only: no F85/F35, entry, stop, target, PnL, short-side test, or zone-time optimization.

## Pooled-major LONG structure

- Complete sessions: **1688**
- High K1 OPP0: **351 (20.8%)**
- Causal leaves: **205 (58.4%)** of qualified K1
- H2 arrivals after leave: **156 (76.1%)**
- Opposite breaks before H2: **19**; ambiguous: **0**; no H2 by NY close: **30**
- Resolved H2 share: **89.1%**; median leave→H2: **15.0 min**
- Structural label: **STRONG_HIGH_REVISIT**

## Reference-duration regimes

- Pooled-major counts: **{'NORMAL_6H30': 1568, 'DST_MISMATCH_5H30': 120}**
- Unexpected regimes: **NONE**

| Scope | Sessions | K1 OPP0 | K1 rate | Leave | H2 rate | Resolved H2 | Median leave→H2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| POOLED_MAJOR | 1688 | 351 | 20.8% | 205 | 76.1% | 89.1% | 15.0m |
| external | 495 | 95 | 19.2% | 63 | 71.4% | 95.7% | 10.0m |
| development | 782 | 165 | 21.1% | 97 | 78.4% | 86.4% | 15.0m |
| reference_validation | 411 | 91 | 22.1% | 45 | 77.8% | 87.5% | 15.0m |
| august | 17 | 5 | 29.4% | 3 | 100.0% | 100.0% | 15.0m |
| DST_MISMATCH_5H30 | 120 | 26 | 21.7% | 14 | 64.3% | 90.0% | 10.0m |
| NORMAL_6H30 | 1568 | 325 | 20.7% | 191 | 77.0% | 89.1% | 15.0m |

**Status: B27EM_BNB_LONDON_NY_LONG_STRUCTURE_COMPLETE**

STOP: B27EM ends here. No SHORT, entry discovery, zone-time search, economics, or live integration is run automatically.
