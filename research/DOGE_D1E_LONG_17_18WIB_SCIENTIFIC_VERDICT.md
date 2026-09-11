# DOGE D1E Scientific Verdict — 17:00–18:00 WIB LONG

## Status
**DOGE_D1E_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1e-long-17-18wib-character`
- Workflow run ID: **34580654664**
- Job ID: **103203166654**
- Head SHA: **a67a551ea39820b594d4adb66c62068723f8c25f**
- Artifact ID: **10191473375**
- Artifact SHA256: `5f712896ebb65083258f1526e51731e225f578c57decde29dfe1000a417820c3`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **17:00–18:00 WIB**
- anchors: 17:00, 17:15, 17:30, 17:45 WIB
- Development only
- same frozen pair-agnostic 90-rule causal grammar as D1A–D1D
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **6 / 3,240**
- pooled gate: **0 / 3,240**
- era gate: **2 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 17:00–18:00 WIB DOGE LONG character passes the frozen formal definition**.

## Strongest preregistered near-miss
### `RV_HIGH__RANGE_MID / LB120 / hold960m`
Pooled Development:
- N: **185**
- WR: **56.22%**
- net: **+$739.55**
- expectancy: **+$4.00/trade**
- PF: **1.777**
- max DD: **$238.36**
- max loss streak: **13**
- supportive anchors: **4/4**
- anchor gate: **PASS**
- pooled gate: **FAIL**
- era gate: **FAIL**

Pooled rejection mechanisms:
- DD $238.36 > $125 gate
- max loss streak 13 > 8 gate

Cross-era Development:
- 2022: N55, WR **58.18%**, exp **+$7.90**, PF **3.607**
- 2023: N59, WR **52.54%**, exp **-$0.34**, PF **0.947**
- 2024: N71, WR **57.75%**, exp **+$4.58**, PF **1.788**

This candidate is economically strong and broad across all four quarter-hour anchors, but 2023 turns slightly negative and the chronological path risk remains far above the frozen tolerance.

## Secondary structural clues
### `RV_HIGH__RANGE_MID / LB240 / hold960m`
- N168
- WR **56.55%**
- net **+$444.53**
- expectancy **+$2.65/trade**
- PF **1.381**
- DD **$236.46**
- max loss streak **14**
- supportive anchors **3/4**
- anchor gate: **PASS**
- pooled failure: **DD + loss streak**
- era gate: **FAIL**

The repeated `RV_HIGH__RANGE_MID` family at H960 across LB120 and LB240 suggests the medium-range / high-volatility long-horizon motif persists into D1E. This is descriptive context only and cannot seed later-hour ranking.

### Large-PnL but path-risk-heavy examples
- `DRIVE_DOWN__RV_HIGH / LB360 / H960`: N504, WR **55.95%**, net **+$2,263.23**, exp **+$4.49**, PF **1.579**, DD **$478.29**, loss streak **12**, supportive anchors **1/4**.
- `DRIVE_DOWN__RANGE_HIGH / LB360 / H960`: N547, WR **56.31%**, net **+$2,089.75**, exp **+$3.82**, PF **1.501**, DD **$524.66**, loss streak **11**, supportive anchors **0/4**.

These are not candidates for promotion. Their high total PnL is overwhelmed by weak anchor breadth and excessive chronological path risk.

## D1A → D1E temporal progression
- **D1A 13:00–14:00 WIB:** 4 anchor, 0 pooled, 0 era, 0 full. Negative/high-stress rebound clue; path-risk and 2024 decay.
- **D1B 14:00–15:00 WIB:** 3 anchor, 1 pooled, 0 era, 0 full. Shift toward high-volatility / medium-range or efficiency states.
- **D1C 15:00–16:00 WIB:** 10 anchor, 0 pooled, 0 era, 0 full. Broad negative-drive rebound signature; 2022 weakness remained.
- **D1D 16:00–17:00 WIB:** 10 anchor, 1 pooled, 3 era, 0 full. Strongest hour so far; best candidate passed anchor + era and missed pooled only on DD/streak.
- **D1E 17:00–18:00 WIB:** **6 anchor, 0 pooled, 2 era, 0 full**. The medium-range long-horizon family persists, but cross-era stability weakens again and path risk remains elevated.

## Scientific interpretation
D1E does not improve on D1D formally. It preserves an economically strong **medium-range / H960** motif and even produces a broad 4/4-anchor near-miss with **+$739.55** net, but the 2023 slice is slightly negative and chronological drawdown/loss clustering remain too high.

The correct conclusion is:

> **17:00–18:00 WIB retains a strong DOGE LONG economic motif, especially around high-volatility medium-range states with long payoff horizons, but it is less robust than D1D and does not pass the frozen character definition.**

## Integrity
- No gate relaxation.
- No post-result rescue.
- No promotion of a near-miss.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into character discovery.
- D1A–D1D coordinates were not seeded into D1E ranking.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to **D1F — 18:00–19:00 WIB**, changing only the four clock anchors. D1A–D1E findings remain comparison context only and must not seed D1F candidate ranking.
