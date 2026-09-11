# ETH Temporal A2 — 23:00 WIB Minimal-State Scientific Verdict

## Frozen outcome
**NO_FORMAL_PASS** under the preregistered A2 one-dimensional state search.

- Scope: ETHUSDT LONG, exactly 23:00 WIB / 16:00 UTC, Development 2022-2024 only.
- Search: 5 state families × 6 lookbacks × 3 bins × 6 holds = 540 candidates.
- State thresholds were calibrated on 2022 only and frozen before application to 2023/2024.
- OOS remained closed.
- No gate relaxation or post-result rescue was used.

## Main finding
The unconditional 23:00 WIB LONG temporal edge is negative across every tested fixed hold. Conditioning on a single state dimension can improve economics materially, but no single family is sufficient to satisfy the full pooled + era robustness gates.

The strongest diagnostic family is realized volatility:
- `RV / LB240 / HIGH / H720`
- N=191
- WR=53.40%
- net=+$100.23
- expectancy=+$0.5248
- PF=1.085
- DD=$308.30
- max loss streak=7
- 2022: N=122, WR=50.82%, net=-$66.97, exp=-$0.5489, PF=0.928
- 2023: N=16, WR=62.50%, net=+$29.37, exp=+$1.8359, PF=1.721
- 2024: N=53, WR=56.60%, net=+$137.82, exp=+$2.6004, PF=1.665

This is not a formal candidate because pooled WR/PF/DD fail, 2022 is negative, and 2023 sample size is below the era minimum. It is diagnostic only.

## Family-level conclusion
- RV is the most informative single state for 23:00 WIB.
- DRIVE and TREND can create positive pooled PnL, but forward direction/WR consistency remains weak.
- RANGE_POS and EFFICIENCY alone are insufficient.

## Scientific implication
A2 rejects the hypothesis that one coarse state dimension alone explains the previously discovered E12K LONG character at 23:00 WIB. The next scientifically justified step is a preregistered A3 that conditions on the A2-leading RV state and tests one additional orthogonal dimension at a time, without relaxing the frozen economic/risk gates.
