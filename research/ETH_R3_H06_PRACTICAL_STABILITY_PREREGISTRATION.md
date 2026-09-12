# ETH R3 H06 — Practical Stability Preregistration

Hour under test: **06:00–07:00 WIB**. ETHUSDT 5m. LONG only.

This protocol is frozen before H06 results are inspected. It transfers the R3 practical-stability methodology from H04/H05; it does not transfer any winning character or timing.

## Stage A — 2022 Development
- Search the existing frozen 90-rule character grammar only.
- Coarse timing grid only: LB (60,120,180,240,360) × Hold (120,240,360,480), 1,800 cells.
- Candidate eligibility: N >= 60, WR >= 55%, Net > 0, Exp >= +$0.50, PF >= 1.20, DD <= $125, both 2022 half-years Exp > 0 and PF > 1, and >=2/4 positive anchors.
- Maximum loss streak is diagnostic only, not a binary eligibility gate.
- Freeze exactly one Development representative by the preregistered ranking: highest minimum half-year expectancy, then expectancy, PF, lower DD, lower LS, higher N, deterministic lexical/timing tie-breaks.

## Stage B — 2023 Practical Stability
- Open 2023 only after Stage A freezes one rule/timing.
- Test the same character rule only.
- Timing may drift at most one Manhattan grid step from the Development LB/Hold.
- Economic viability: N >= 50, WR >= 52%, Net > 0, Exp > 0, PF >= 1.15, DD within the frozen Development-derived envelope.
- Performance stability: economically viable AND WR no worse than Development by 5 percentage points, expectancy retention >= 60%, PF retention >= 70%.
- At least two local timing cells must remain economically viable.
- LS is reported as a risk-clustering warning only.

## Stage C — 2024
- 2024 remains unopened unless Stage B passes formally.
- If Stage B passes, freeze one 2023 local coordinate under the preregistered ranking, then test 2024 once with no reselection.
- If Stage B does not formally pass, any later 2024 look is explicitly exploratory/diagnostic and cannot retroactively convert the Stage-B result into a formal pass.

## OOS
- 2025+ remains closed final OOS/reference.

The goal is practical robustness: a recognizable positive edge with reasonable degradation and small parameter drift, not exact mathematical invariance.