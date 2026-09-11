# ETH E13D — Winner-Hour Selection Scientific Verdict

**Status:** Development-only. OOS CLOSED. No live authorization.

## Frozen question
Can a static subset of the four formal E12 LONG winner-hours improve the one-position sequential execution portfolio without changing any native E12 rule, lookback, hold, fee, or entry semantics?

Parent baseline = E13C K+L+M+O:
- N 476
- WR 55.2521%
- net +$622.52
- expectancy +$1.3078
- PF 1.3507
- DD $131.02
- max loss streak 6

## Result summary

All 15 preregistered non-empty subsets were evaluated. **8/15 passed the frozen ROBUST pooled+era gate.**

Robust subsets:
- K
- K+L
- K+O
- L+O
- K+M+O
- L+M+O
- K+L+O
- K+L+M+O baseline

### Primary robustness-ranked winner — L+M+O

Under the preregistered worst-era-first ranking, **L+M+O** ranks #1:
- N 377
- WR 56.4987%
- net +$559.74
- expectancy +$1.4847
- PF 1.4336
- DD $123.85
- max loss streak 5
- min-year expectancy +$1.3293
- years WR>=55%: 2/3

Cross-era:
- 2022: N122, WR59.84%, net +$162.17, exp +$1.33, PF1.287
- 2023: N120, WR55.83%, net +$202.66, exp +$1.69, PF1.636
- 2024: N135, WR54.07%, net +$194.91, exp +$1.44, PF1.479

Interpretation: removing K greatly improves the *worst-era* economics and reduces loss clustering, but total net falls below E13C. Therefore L+M+O is a **robustness trade-off winner**, not an unqualified all-metric improvement.

### Only strict pooled Pareto improver — K+L+O

**K+L+O is the only preregistered subset marked STRICT_PARETO_IMPROVER versus E13C.** It removes M (01–02 WIB / H960) while retaining K, L and O.

Metrics:
- N 381
- WR 55.6430%
- net +$647.28
- expectancy +$1.6989
- PF 1.4695
- DD $96.03
- max loss streak 6
- min-year expectancy +$0.7949
- years WR>=55%: 2/3

Cross-era:
- 2022: N111, WR53.15%, net +$88.24, exp +$0.79, PF1.135
- 2023: N140, WR55.71%, net +$226.07, exp +$1.61, PF1.596
- 2024: N130, WR57.69%, net +$332.97, exp +$2.56, PF1.967

Relative to E13C K+L+M+O:
- WR: 55.25% -> 55.64% (improved)
- net: +$622.52 -> +$647.28 (improved)
- expectancy: +$1.31 -> +$1.70 (improved ~29.9%)
- PF: 1.351 -> 1.469 (improved ~8.8%)
- DD: $131.02 -> $96.03 (improved ~26.7%)
- max loss streak: 6 -> 6 (not worse)
- N: 476 -> 381 (fewer executed trades; not treated as an improvement)

Hour contribution inside K+L+O:
- K / 23 WIB / H720: executed 203, WR55.17%, net +$373.84, exp +$1.84, PF1.483
- L / 00 WIB / H720: executed 131, WR54.96%, net +$192.48, exp +$1.47, PF1.388
- O / 03 WIB / H240: executed 47, WR59.57%, net +$80.97, exp +$1.72, PF1.743

## What E13D says about M

M (01–02 WIB / E12M / H960) remains a valid standalone E12 formal character, but in a one-position portfolio its 16-hour occupancy can degrade the portfolio opportunity set. The exact E13D evidence supports excluding M from the **strict pooled Pareto** portfolio; this does not invalidate or relabel E12M itself.

## Frozen interpretation

There are two legitimate E13D readouts and they must not be conflated:

1. **Worst-era robustness objective:** L+M+O ranks first.
2. **No-sacrifice pooled improvement over E13C:** K+L+O is the only strict Pareto improver.

Given the project objective of improving the whole economics+risk package without sacrificing a core pooled metric, **K+L+O is the cleanest execution architecture to carry forward as the strict-Pareto candidate**, while L+M+O remains the strongest worst-era robustness trade-off candidate.

No TP/SL/exit optimization has yet been performed on either candidate. Any next-phase exit research must be separately preregistered and must not retroactively modify E13D.
