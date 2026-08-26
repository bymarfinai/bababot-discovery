# B27DZ — 24H Post-Rebreak SHORT Economic Discovery — Preregistration

## Purpose
Search for a bearish setup that is mechanically different from F15. B27DZ tests entry only **after** a prior-range Low has broken, the first retest reclaimed L, and a later completed 5m bar re-breaks below L. No F15/F65 rule is used.

Research only. No live BBC changes.

## Frozen source / causality
- BTCUSDT Binance USD-M perpetual raw 5m, same 698,112-row dataset/partitions as B27CE/B27CI.
- Reproduce the exact B27CI confirmed-rebreak cohort: external 149, development 237, reference_validation 133 (519 total source; eligible followthrough 513 historically).
- Prior 4H H/L/R4 is frozen before the observation block.
- Rebreak confirmation is a **completed 5m close < L** after a prior first-retest reclaim.
- Entry is the next raw 5m open, timestamp equal to `rebreak_complete_ts`.
- Skip if no next bar before block end, next open >= L, or next open <= frozen T10 (move already missed).
- No future bar may affect entry eligibility.

## Frozen target
B27CI target: `T10 = L - 0.10*R4`.

## Frozen risk lanes
Three mechanical hard-stop lanes only; no parameter sweep beyond these preregistered RR values:
- `RR100`: reward:risk = 1.0:1
- `RR150`: reward:risk = 1.5:1
- `RR200`: reward:risk = 2.0:1

For entry E and target T10, reward distance `D=E-T10 > 0`; stop = `E + D/RR`.

Exit semantics:
- raw 5m from entry bar onward;
- if stop and target both touched in same bar, STOP wins conservatively;
- otherwise first touch wins;
- unresolved exits at observation-block end next/open price;
- $500 illustrative notional; $0.40 round-trip fee.

## Clock blocks
Evaluate independently: `00-04`, `04-08`, `08-12`, `12-16`, `16-20`, `20-00` UTC. No clock is promoted because of pooled totals alone.

## Development selection per clock
For each clock, an RR lane is development-eligible iff:
- development N >= 25;
- WR >= 65%;
- PF >= 1.30;
- expectancy > 0.

If >1 lane qualifies for a clock, rank by PF, then WR, expectancy, N, then tighter/higher RR (`RR200`, `RR150`, `RR100`) only as final deterministic tie-break.

## Historical replication gate
The selected lane for a clock survives replication only if BOTH:
- external N >= 15, WR >= 60%, PF >= 1.20, expectancy > 0;
- reference_validation N >= 15, WR >= 60%, PF >= 1.20, expectancy > 0.

External/reference_validation are reused historical partitions, not pristine unseen OOS; label results accordingly.

## Chronological stability
Frozen windows:
- W1 2020-01-01 to 2021-07-01
- W2 2021-07-01 to 2023-01-01
- W3 2023-01-01 to 2024-07-01
- W4 2024-07-01 to 2026-01-01
- W5_YTD diagnostic only

A replicated clock must have >=3/4 completed windows with N>=5, net>0, PF>=1.05. No window may have PF<0.70 when N>=5.

## Slippage stress
For each replicated clock, apply adverse slippage per fill of 0/2/5/10 bps to both entry and exit execution prices while keeping trigger levels frozen.

5bps gate: pooled-major WR >= 60%, PF >= 1.20, net > 0.

## Current-portfolio compatibility
Only after all standalone gates pass, add the survivor to the current pre-B27DX control portfolio (B27DQ LONG + validated SHORT20, N=283 / WR~73.1% / PF~2.34 / net~+$367.49) using chronological one-BTC-position lock.

Compatibility gate:
- combined net > control net;
- displaced current accepted trades <= 2% of 283;
- incremental accepted candidate net > 0.

This compatibility readout is provisional until B27DX corrects the one known LONG historical phantom.

## Promotion interpretation
A clock is a **B27DZ historical candidate** only if development selection + historical replication + chronological stability + 5bps stress + portfolio compatibility all pass.

If none pass, do not tune T10, RR, filters, or clocks inside B27DZ. A new preregistered mechanism is required.
