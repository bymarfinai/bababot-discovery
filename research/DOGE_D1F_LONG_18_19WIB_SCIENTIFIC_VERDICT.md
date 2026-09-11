# DOGE D1F Scientific Verdict — 18:00–19:00 WIB LONG

## Status
**DOGE_D1F_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1f-long-18-19wib-character`
- Workflow run ID: **34581124897**
- Job ID: **103204668651**
- Head SHA: **aa26260d967a01e95152762552587cf0e2a9f8b0**
- Artifact ID: **10191663434**
- Artifact SHA256: `6e065c3fdcee93ff3c17258d01e5bab667fcd68889d2382de40a5c1c15d2b668`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **18:00–19:00 WIB**
- anchors: 18:00, 18:15, 18:30, 18:45 WIB
- Development only
- same frozen pair-agnostic 90-rule causal grammar as D1A–D1E
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **6 / 3,240**
- pooled gate: **0 / 3,240**
- era gate: **4 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 18:00–19:00 WIB DOGE LONG character passes the frozen formal definition**.

## Strongest preregistered near-miss
### `DRIVE_DOWN__RV_HIGH / LB240 / hold120m`
Pooled Development:
- N: **563**
- WR: **56.13%**
- net: **+$577.90**
- expectancy: **+$1.03/trade**
- PF: **1.395**
- max DD: **$351.14**
- max loss streak: **14**
- supportive anchors: **4/4**
- anchor gate: **PASS**
- era gate: **PASS**
- pooled gate: **FAIL**

Pooled rejection mechanisms only:
- DD $351.14 > $125 gate
- max loss streak 14 > 8 gate

Cross-era Development:
- 2022: N187, WR **55.08%**, exp **+$1.72**, PF **1.583**
- 2023: N173, WR **57.23%**, exp **+$1.19**, PF **2.033**
- 2024: N203, WR **56.16%**, exp **+$0.25**, PF **1.071**

All three Development eras are positive and all three are above 55% WR. This makes D1F's leading setup a genuinely broad and era-robust near-miss. Its rejection is driven by chronological path risk rather than lack of edge, insufficient sample, anchor localization, or era instability.

## Secondary structural clues
### `DRIVE_DOWN__STR_B80_100 / LB360 / hold240m`
- N349
- WR **54.15%**
- net **+$674.20**
- expectancy **+$1.93/trade**
- PF **1.514**
- DD **$247.56**
- max loss streak **11**
- supportive anchors **4/4**
- anchor gate: **PASS**
- pooled failure: **WR + DD + loss streak**
- era gate: **FAIL**

### High-economics but localized examples
- `EFF_MID__RV_HIGH / LB120 / H960`: N329, WR **55.32%**, net **+$1,558.57**, exp **+$4.74**, PF **1.676**, DD **$289.33**, loss streak **8**, supportive anchors **1/4**.
- `EFF_LOW__RV_HIGH / LB60 / H960`: N334, WR **57.49%**, net **+$1,407.59**, exp **+$4.21**, PF **1.577**, DD **$429.41**, loss streak **12**, supportive anchors **1/4**.

These high-PnL candidates remain non-promotable because anchor breadth and/or path-risk gates fail.

## Temporal interpretation: D1D → D1F
- **D1D 16:00–17:00 WIB:** strongest near-miss `RV_LOW__RANGE_MID / LB240 / H960`; 4/4 anchors, era PASS, pooled failed only DD/streak.
- **D1E 17:00–18:00 WIB:** medium-range / H960 motif persisted, but era robustness weakened because 2023 turned slightly negative.
- **D1F 18:00–19:00 WIB:** dominant family rotates back to **negative-drive / high-volatility rebound**, and preferred payoff horizon compresses sharply to **H120**. The leading setup regains strong cross-era robustness and 4/4 anchor support, but DD and clustered losses remain severe.

This rotation reinforces the working observation that DOGE LONG character is highly clock-specific. A family that is important for one adjacent hour cannot be assumed to remain dominant in the next.

## D1A → D1F progression
- **D1A 13:00–14:00 WIB:** 4 anchor, 0 pooled, 0 era, 0 full.
- **D1B 14:00–15:00 WIB:** 3 anchor, 1 pooled, 0 era, 0 full.
- **D1C 15:00–16:00 WIB:** 10 anchor, 0 pooled, 0 era, 0 full.
- **D1D 16:00–17:00 WIB:** 10 anchor, 1 pooled, 3 era, 0 full. Closest hour so far overall.
- **D1E 17:00–18:00 WIB:** 6 anchor, 0 pooled, 2 era, 0 full.
- **D1F 18:00–19:00 WIB:** **6 anchor, 0 pooled, 4 era, 0 full**. Strong era robustness returns, but no pooled passer survives the fixed path-risk gate.

## Scientific interpretation
D1F contains a real economic and cross-era signal, but it is not a formal character. The leading candidate has a relatively large sample (**563 trades**), broad **4/4 anchor** support, positive results in every Development era, and WR above 55% in every era. Nevertheless, a **$351.14** drawdown and **14-loss streak** violate the frozen pooled risk constraints by a wide margin.

The correct conclusion is:

> **18:00–19:00 WIB shows a robust negative-drive/high-volatility DOGE LONG rebound signature across anchors and eras, but its chronological path risk is still too large for formal character qualification.**

## Integrity
- No gate relaxation.
- No post-result rescue.
- No promotion of a 2/3-gate near-miss.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into character discovery.
- D1A–D1E coordinates were not seeded into D1F ranking.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to **D1G — 19:00–20:00 WIB**, changing only the four clock anchors. D1A–D1F findings remain comparison context only and must not seed D1G candidate ranking.
