# DOGE D1I Scientific Verdict — 21:00–22:00 WIB LONG

## Status
**DOGE_D1I_NO_LONG_CHARACTER**

Research/shadow only. OOS remained closed.

## Result-bearing run
- Branch: `doge-d1i-long-21-22wib-character`
- Workflow run ID: **34607973507**
- Job ID: **103291007131**
- Head SHA: **26857ccdb3c9dd247e06431b6f3eee66e380b8fd**
- Artifact ID: **10267104793**
- Artifact SHA256: `b64861ca9327399d8fe5d0d6f51fffe103457b81c41b9038ece9259aff773da7`
- Raw DOGEUSDT 5m coverage: **100.0000%**

## Formal gate counts
- anchor gate: **50 / 3,240**
- pooled gate: **1 / 3,240**
- era gate: **26 / 3,240**
- full gate: **0 / 3,240**

No candidate passed anchor + pooled + era simultaneously.

## Strongest preregistered near-miss
`RV_HIGH__RANGE_MID / LB360 / H960`
- N **187**
- WR **59.36%**
- net **+$1,082.70**
- expectancy **+$5.79/trade**
- PF **2.180**
- DD **$206.05**
- max loss streak **10**
- supportive anchors **4/4**
- anchor gate: PASS
- era gate: PASS
- pooled gate: FAIL on DD and loss streak

Cross-era:
- 2022: N48, WR 52.08%, exp +$5.97, PF 2.134
- 2023: N61, WR 67.21%, exp +$5.35, PF 2.772
- 2024: N78, WR 57.69%, exp +$6.02, PF 1.977

## Sole pooled-gate passer
`DRIVE_UP__STR_B40_60 / LB60 / H960`
- N **271**
- WR **58.67%**
- net **+$999.94**
- exp **+$3.69/trade**
- PF **1.766**
- DD **$124.59**
- max loss streak **5**
- supportive anchors **4/4**
- anchor gate: PASS
- pooled gate: PASS
- era gate: FAIL because 2023 WR **50.59%** < 52% floor

## Important secondary near-miss
`EFF_MID__RANGE_MID / LB240 / H960`
- N **314**
- WR **58.28%**
- net **+$1,318.58**
- exp **+$4.20/trade**
- PF **1.910**
- DD **$148.84**
- loss streak **8**
- supportive anchors **4/4**
- anchor gate: PASS
- era gate: PASS
- pooled gate: FAIL only on DD

D1I is the strongest DOGE hour so far in breadth: 50 anchor-pass and 26 era-pass candidates, plus one clean pooled passer. The current grammar clearly detects economically meaningful DOGE structure here, but no single candidate yet satisfies all robustness gates.

## Integrity
No gate relaxation, no rounding, no post-result rescue, no OOS exposure, no TP/SL tuning, no SHORT mixing, and no execution optimization.

## D1 → D2 policy
Continue D1 unchanged through D1X. If the completed 24-hour atlas still has no sufficiently robust formal DOGE character/coherent formal cluster, proceed to **DOGE D2 — Pair-Native Structure Discovery From Zero** without assuming the current 90-rule grammar is the correct DOGE coordinate system.

## Next direction
Continue to **D1J — 22:00–23:00 WIB**, changing only the four clock anchors. D1A–D1I remain comparison context only and must not seed ranking.
