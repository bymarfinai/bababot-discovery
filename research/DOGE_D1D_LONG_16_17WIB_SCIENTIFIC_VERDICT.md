# DOGE D1D Scientific Verdict — 16:00–17:00 WIB LONG

## Status
**DOGE_D1D_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1d-long-16-17wib-character`
- Workflow run ID: **34579447653**
- Job ID: **103199356838**
- Head SHA: **488b13eb6fef941564d0c543f9582acd08a2307e**
- Artifact ID: **10190999864**
- Artifact SHA256: `bbf892e36ce2318456d63a1d4fcc5c88bbefd552c419a42fb8bf93dad885e924`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **16:00–17:00 WIB**
- anchors: 16:00, 16:15, 16:30, 16:45 WIB
- Development only
- same frozen pair-agnostic 90-rule causal grammar as D1A–D1C
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **10 / 3,240**
- pooled gate: **1 / 3,240**
- era gate: **3 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 16:00–17:00 WIB DOGE LONG character passes the frozen formal definition**.

However, D1D is the closest DOGE hour so far to a formal character because candidates now clear the cross-era gate and anchor breadth simultaneously.

## Strongest preregistered near-miss
### `RV_LOW__RANGE_MID / LB240 / hold960m`
Pooled Development:
- N: **185**
- WR: **59.46%**
- net: **+$531.67**
- expectancy: **+$2.87/trade**
- PF: **1.581**
- max DD: **$181.64**
- max loss streak: **9**
- supportive anchors: **4/4**
- anchor gate: **PASS**
- era gate: **PASS**
- pooled gate: **FAIL**

Pooled rejection mechanisms only:
- DD $181.64 > $125 gate
- max loss streak 9 > 8 gate

Cross-era Development:
- 2022: N76, WR **59.21%**, exp **+$2.88**, PF **1.647**
- 2023: N45, WR **64.44%**, exp **+$3.76**, PF **1.935**
- 2024: N64, WR **56.25%**, exp **+$2.24**, PF **1.363**

This is the first DOGE near-miss in the sweep with broad **4/4 anchor support and clear positive behavior in all three Development eras**. The remaining blocker is chronological path risk, not lack of edge or era instability.

## Second high-quality near-miss
### `RV_HIGH__RANGE_MID / LB240 / hold960m`
- N170
- WR **58.24%**
- net **+$727.63**
- expectancy **+$4.28/trade**
- PF **1.661**
- DD **$307.84**
- max loss streak **12**
- supportive anchors **3/4**
- anchor gate: **PASS**
- era gate: **PASS**
- pooled failure: **DD + loss streak**

The coexistence of both `RV_LOW__RANGE_MID` and `RV_HIGH__RANGE_MID` at **LB240 / H960** suggests that, within D1D, the medium-range path state may be more structurally important than a single volatility polarity. This is descriptive context only and must not be used to repair D1D or seed D1E ranking.

## Sole pooled-gate clue
### `RV_HIGH__RANGE_MID / LB240 / hold60m`
- N170
- WR **57.65%**
- net **+$100.03**
- expectancy **+$0.59/trade**
- PF **1.404**
- DD **$97.72**
- max loss streak **8**
- supportive anchors **2/4**
- pooled gate: **PASS**
- anchor gate: **FAIL**
- era gate: **FAIL**

This contrast is informative: the short payoff horizon controls path risk but loses breadth and cross-era stability, while H960 preserves breadth/era robustness but accumulates too much drawdown. Character discovery must not optimize between these after the fact; that is an execution-stage question only after the 24-hour map is complete.

## D1A → D1D temporal progression
- **D1A 13:00–14:00 WIB:** 4 anchor, 0 pooled, 0 era, 0 full. Negative/high-stress rebound clue; path-risk and 2024 decay.
- **D1B 14:00–15:00 WIB:** 3 anchor, 1 pooled, 0 era, 0 full. Shift toward high-volatility / medium-range or efficiency states.
- **D1C 15:00–16:00 WIB:** 10 anchor, 0 pooled, 0 era, 0 full. Broad negative-drive rebound signature, including a 4/4-anchor clue; 2022 weakness remained.
- **D1D 16:00–17:00 WIB:** **10 anchor, 1 pooled, 3 era, 0 full**. First hour where strong candidates pass the cross-era gate; strongest near-miss passes **anchor + era** and misses formal qualification only on DD and loss streak.

This is a meaningful progression, but not evidence that later hours must continue improving. The full 24-hour sweep remains mandatory.

## Scientific interpretation
D1D is materially different from D1C. The dominant local family rotates away from strong negative-drive rebound and toward a **medium-range state with a long payoff horizon**, while cross-era robustness improves sharply.

The strongest D1D candidate is not a formal character because its chronological risk path exceeds the frozen tolerances. The correct conclusion is therefore:

> **16:00–17:00 WIB is the strongest DOGE LONG habitat encountered so far in terms of combined breadth, economics, and cross-era robustness, but it still fails the formal character definition because drawdown and loss clustering remain too high.**

## Integrity
- No gate relaxation.
- No post-result rescue.
- No promotion of a 2/3-gate near-miss.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into character discovery.
- D1A–D1C coordinates were not seeded into D1D ranking.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to **D1E — 17:00–18:00 WIB**, changing only the four clock anchors. D1A–D1D findings remain comparison context only and must not seed D1E candidate ranking.