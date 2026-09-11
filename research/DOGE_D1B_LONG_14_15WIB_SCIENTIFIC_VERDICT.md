# DOGE D1B Scientific Verdict — 14:00–15:00 WIB LONG

## Status
**DOGE_D1B_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1b-long-14-15wib-character`
- Workflow run ID: **34578061481**
- Job ID: **103194995418**
- Head SHA: **ae94de3bad8bc5fc63223031044d02febcc242f8**
- Artifact ID: **10190456795**
- Artifact SHA256: `e5838daf6d2ea6fae9d1975cdba33ad41450eba4749f1dab61ab3306243e0824`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **14:00–15:00 WIB**
- anchors: 14:00, 14:15, 14:30, 14:45 WIB
- Development only
- same pair-agnostic 90-rule causal character grammar as D1A
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **3 / 3,240**
- pooled gate: **1 / 3,240**
- era gate: **0 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 14:00–15:00 WIB DOGE LONG character passes the frozen formal definition**.

## Strongest preregistered near-miss
### `DRIVE_UP__RANGE_MID / LB120 / hold960m`
Pooled Development:
- N: **443**
- WR: **51.47%**
- net: **+$562.00**
- expectancy: **+$1.27/trade**
- PF: **1.213**
- max DD: **$457.37**
- max loss streak: **13**
- supportive anchors: **3/4**
- anchor gate: **PASS**
- pooled gate: **FAIL**
- era gate: **FAIL**

Pooled rejection mechanisms:
- WR 51.47% < 55% gate
- DD $457.37 > $125 gate
- max loss streak 13 > 8 gate

Cross-era Development:
- 2022: N149, WR **45.64%**, exp **+$0.15**, PF **1.023**
- 2023: N132, WR **62.88%**, exp **+$3.56**, PF **1.922**
- 2024: N162, WR **47.53%**, exp **+$0.43**, PF **1.059**

Interpretation: the apparent edge is strongly regime-dependent. 2023 is excellent, while 2022 and 2024 do not satisfy the frozen era definition.

## Most important D1B clue — first pooled-gate passer
### `RV_HIGH__RANGE_MID / LB120 / hold360m`
- N170
- WR **57.06%**
- net **+$191.65**
- expectancy **+$1.13/trade**
- PF **1.361**
- DD **$110.05**
- max loss streak **7**
- supportive/evaluable anchors: **2/3**
- pooled gate: **PASS**
- anchor gate: **FAIL**
- era gate: **FAIL**

This is the first DOGE hour in the sweep to produce a candidate that clears the full pooled economics/risk definition. It fails because the behavior is not broad enough across the four quarter-hour anchors and is not cross-era stable.

## Secondary structural clues
### `EFF_MID__RV_HIGH / LB240 / hold360m`
- N295
- WR **51.53%**
- net **+$390.13**
- expectancy **+$1.32/trade**
- PF **1.292**
- DD **$221.17**
- loss streak **8**
- supportive anchors **3/4**
- formal failure: pooled WR + DD; cross-era stability

### `EFF_MID__RV_HIGH / LB240 / hold240m`
- N295
- WR **52.88%**
- net **+$395.29**
- expectancy **+$1.34/trade**
- PF **1.322**
- DD **$261.06**
- loss streak **9**
- supportive anchors **3/4**
- formal failure: pooled WR + DD + loss streak; cross-era stability

These two independent variants reinforce a D1B fingerprint around **high-volatility / medium-efficiency path states**, but risk concentration and regime instability remain material.

## D1A → D1B comparison
D1A (13:00–14:00 WIB) produced 4 anchor-gate passers, 0 pooled-gate passers, 0 era-gate passers, and 0 full passers. Its strongest clue was a post-negative-drive/high-stress LONG rebound pattern.

D1B (14:00–15:00 WIB) produces 3 anchor-gate passers, **1 pooled-gate passer**, 0 era-gate passers, and 0 full passers. The local character shifts away from a pure post-down-drive rebound toward **high-volatility / medium-range or medium-efficiency states**.

This is meaningful pair-native differentiation: adjacent hours do not share one fixed DOGE setup.

## Scientific interpretation
D1B is stronger economically than D1A in one important sense: a preregistered candidate now clears pooled WR/expectancy/PF/DD/loss-streak requirements. However, the candidate is too localized within the hour and remains regime-unstable.

The working DOGE fingerprint after two hours is therefore:

> **DOGE LONG opportunity appears highly clock-specific. 13:00–14:00 WIB leans toward stressed/down-drive rebound behavior, while 14:00–15:00 WIB shows a higher-volatility path-state edge. Neither hour is yet cross-era robust.**

## Integrity
- No gate relaxation.
- No post-result coordinate rescue.
- Near-misses remain near-misses.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into opportunity-character discovery.
- D1A coordinates were not seeded into D1B ranking.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to the next contiguous habitat, **15:00–16:00 WIB**, changing only the four fixed clock anchors. D1A/D1B findings remain comparison context only and must not seed D1C candidate ranking.