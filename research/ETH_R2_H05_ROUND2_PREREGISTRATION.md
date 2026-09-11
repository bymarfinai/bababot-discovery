# ETH R2 H05 — Round 2 Preregistration

## Input from Round 1

Round 1 was diagnostic only and selected exactly one family hypothesis: `DRIVE_DOWN__STR_B80_100`.

Observed failure mode was **TIMING_FRAGILITY**, not anchor fragility: the strongest R1 cell had 4/4 supportive anchors and 3/4 positive half-years, but the family did not form a connected timing plateau.

This Round 2 asks whether the underlying *character definition* is stable, rather than tuning the winning LB/Hold.

## Hard firewall

- H05 only: 05:00–06:00 WIB.
- LONG only.
- 2022–2023 only.
- 2024 remains HARD LOCKED.
- OOS 2025+ CLOSED.
- Same notional, fee, entry anchors, event semantics, and coarse timing grid as R1.
- No new rule families and no fine LB/Hold grid in this round.

## Frozen hypothesis

The candidate character is:

> negative drive (`drive_return < 0`) combined with **upper-tail drive strength**.

Instead of selecting one strength cutoff, test three precommitted nested definitions:

- T70: `strength_pct >= 0.70`
- T80: `strength_pct >= 0.80` — the legacy `STR_B80_100` definition
- T90: `strength_pct >= 0.90`

These are perturbations, not candidates to rank. **No threshold winner will be selected.** A robust character should tolerate a meaningful change in the upper-tail cutoff.

## Frozen timing grid

Exactly the existing R1 coarse grid:

- Lookbacks: 60, 120, 180, 240, 360 minutes
- Holds: 120, 240, 360, 480 minutes
- 20 timing cells × 3 threshold definitions = 60 diagnostic cells

No interpolation or local refinement is allowed in Round 2.

## Per-cell metrics and gates

For each threshold/timing cell, use the exact R1 H05 evaluation semantics.

### R1 plateau-supportive cell

Reuse the existing R1 definition unchanged:

- pooled N >= 100
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= 150
- max loss streak <= 10
- both 2022 and 2023 have N >= 25, expectancy > 0, PF >= 1.00

### R1 strict+temporal cell

Reuse the existing R1 strict and temporal gates unchanged, including pooled economics, year checks, anchor checks, >=3/4 positive half-years, and half-year floor.

## Threshold-stable timing cell

A timing point `(LB, Hold)` is `threshold_stable` only if:

1. T80 is plateau-supportive; **and**
2. at least one of T70 or T90 is also plateau-supportive; therefore >=2/3 perturbations survive; and
3. median expectancy across T70/T80/T90 > 0; and
4. median PF across T70/T80/T90 >= 1.05.

This prevents selecting a new threshold that merely replaces the legacy definition.

## Robust timing region

Connected components use the same orthogonal adjacency in coarse-grid index space as R1.

A Round-2 region qualifies only if:

- >= 4 threshold-stable timing cells;
- spans >= 2 distinct lookbacks;
- spans >= 2 distinct holds;
- contains >= 1 T80 strict+temporal cell;
- median of the timing-level median expectancy > 0;
- median of the timing-level median PF >= 1.05.

No alternative region definition may be substituted after results are observed.

## Round-2 verdict

- `THRESHOLD_ROBUST_TIMING_REGION` if at least one region qualifies.
- `CHARACTER_THRESHOLD_OR_TIMING_FRAGILE` otherwise.

Round 2 cannot freeze a 2024 validation candidate even if it passes. A passing result advances to a separately preregistered Round 3 robustness/walk-forward test.

If Round 2 fails, the result is evidence against this exact upper-tail-strength character. Any Round-3 hypothesis must be structurally different and separately preregistered; it may not rescue the result by choosing the best threshold or by micro-tuning LB/Hold.
