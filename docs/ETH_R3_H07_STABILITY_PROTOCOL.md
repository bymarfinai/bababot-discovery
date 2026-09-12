# ETH R3 H07 Practical Stability Protocol

Hour under study: **07:00–08:00 WIB**.

This protocol is frozen before observing any H07 Development/Test result.

## Stage A — 2022 Development
- ETHUSDT, 5m, LONG only.
- Four 15m anchors inside H07.
- Original 90-rule grammar.
- Coarse timing grid only: LB (60,120,180,240,360) × Hold (120,240,360,480).
- Candidate eligibility: N>=60, WR>=55%, Net>0, Exp>=+$0.50, PF>=1.20, DD<=125; both 2022 halves Exp>0/PF>1; >=2 positive anchors.
- Maximum loss streak is diagnostic only.
- Freeze exactly one representative by the existing deterministic ranking; no reselection after seeing 2023.

## Stage B — 2023 Practical Stability
- Test only the same frozen character rule.
- Exact Development coordinate plus Manhattan-distance <=1 neighbors on the same coarse grid.
- Economically viable: N>=50, WR>=52%, Net>0, Exp>0, PF>=1.15, DD<=min(160,1.5×DevDD+20).
- Performance-stable: economically viable + WR no worse than Dev by >5 percentage points + Exp retention>=60% + PF retention>=70%.
- At least two local cells must be economically viable.
- Maximum loss streak remains a risk-clustering warning, not a binary robustness gate.

## Stage C — 2024
Only if Stage B freezes a stable edge. 2024 is then opened once at the frozen 2023 coordinate; no 2024 reselection. If Stage B clearly collapses, 2024 stays unopened.

## OOS
2025+ remains closed.
