# DOGE D1H Scientific Verdict — 20:00–21:00 WIB LONG

## Status
**DOGE_D1H_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1h-long-20-21wib-character`
- Workflow run ID: **34607203527**
- Job ID: **103288443043**
- Head SHA: **7975fbb4722ab5238bcb28c59110bff907697b6e**
- Artifact ID: **10266192815**
- Artifact SHA256: `7332f4e2323b8c10091f5b1f4af7caf91c01269546c915cd74dfca7606c980ac`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **20:00–21:00 WIB**
- anchors: 20:00, 20:15, 20:30, 20:45 WIB
- Development only
- same frozen pair-agnostic 90-rule causal grammar as D1A–D1G
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **15 / 3,240**
- pooled gate: **0 / 3,240**
- era gate: **9 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 20:00–21:00 WIB DOGE LONG character passes the frozen formal definition**.

## Strongest preregistered near-miss
### `EFF_HIGH__RANGE_MID / LB15 / hold960m`
Pooled Development:
- N: **334**
- WR: **56.29%**
- net: **+$706.93**
- expectancy: **+$2.12/trade**
- PF: **1.400**
- max DD: **$162.87**
- max loss streak: **10**
- supportive anchors: **3/4**
- anchor gate: **PASS**
- era gate: **PASS**
- pooled gate: **FAIL**

Pooled rejection mechanisms:
- DD $162.87 > $125 gate
- max loss streak 10 > 8 gate

Cross-era Development:
- 2022: N97, WR **60.82%**, exp **+$2.25**, PF **1.388**
- 2023: N131, WR **52.67%**, exp **+$1.35**, PF **1.292**
- 2024: N106, WR **56.60%**, exp **+$2.94**, PF **1.521**

The setup is positive in all three eras and formally passes the era gate. Rejection is driven by pooled path-risk only.

## Important near-threshold structural clue
### `RV_HIGH__RANGE_MID / LB240 / hold960m`
- N180
- WR **56.11%**
- net **+$574.91**
- expectancy **+$3.19/trade**
- PF **1.605**
- DD **$125.90**
- max loss streak **8**
- supportive anchors **4/4**
- anchor gate: **PASS**
- pooled gate: **FAIL** only because DD **$125.90** is $0.90 above the frozen $125 ceiling
- era gate: **FAIL**

This candidate is extremely close to the pooled path-risk threshold but cannot be rescued or rounded into a pass. Its era failure also prevents full qualification independently.

## Secondary economic clues
### `DRIVE_UP__STR_B60_80 / LB240 / H960`
- N286
- WR **59.79%**
- net **+$1,063.30**
- exp **+$3.72/trade**
- PF **1.606**
- DD **$259.15**
- loss streak **9**
- supportive anchors **3/4**
- 2/3 gates; pooled rejected by DD and loss streak.

### `EFF_MID__RV_HIGH / LB60 / H960`
- N347
- WR **55.91%**
- net **+$1,958.44**
- exp **+$5.64/trade**
- PF **1.787**
- DD **$221.38**
- loss streak **6**
- supportive anchors **3/4**
- strong economics but pooled DD and era stability still fail.

### `EFF_MID__RANGE_HIGH / LB60 / H960`
- N312
- WR **54.17%**
- net **+$2,267.25**
- exp **+$7.27/trade**
- PF **2.019**
- DD **$189.55**
- loss streak **6**
- supportive anchors **3/4**
- rejected by pooled WR/DD and era stability.

## Temporal interpretation: D1D → D1H
- **D1D 16:00–17:00 WIB:** `RV_LOW__RANGE_MID / LB240 / H960`; 4/4 anchors, era PASS, pooled failed DD/streak.
- **D1E 17:00–18:00 WIB:** `RV_HIGH__RANGE_MID / LB120 / H960`; 4/4 anchors but era robustness weakened.
- **D1F 18:00–19:00 WIB:** rotated to `DRIVE_DOWN__RV_HIGH / LB240 / H120`; 4/4 anchors and era PASS, pooled failed DD/streak.
- **D1G 19:00–20:00 WIB:** returned to H960 with efficiency/extension/high-volatility states; DD decisive and 2023 weakened the leading setup.
- **D1H 20:00–21:00 WIB:** H960 remains dominant. Breadth improves sharply (15 anchor-pass candidates; 9 era-pass candidates), but **no pooled candidate survives the frozen risk gate**. The leading near-miss passes anchor + era and fails pooled path-risk only.

D1H therefore strengthens the hypothesis that the current grammar can locate economically meaningful DOGE states, especially at long payoff horizons, but still does not consistently isolate the lower-path-risk mechanism needed for formal character qualification.

## D1A → D1H progression
- **D1A 13:00–14:00 WIB:** 4 anchor, 0 pooled, 0 era, 0 full.
- **D1B 14:00–15:00 WIB:** 3 anchor, 1 pooled, 0 era, 0 full.
- **D1C 15:00–16:00 WIB:** 10 anchor, 0 pooled, 0 era, 0 full.
- **D1D 16:00–17:00 WIB:** 10 anchor, 1 pooled, 3 era, 0 full.
- **D1E 17:00–18:00 WIB:** 6 anchor, 0 pooled, 2 era, 0 full.
- **D1F 18:00–19:00 WIB:** 6 anchor, 0 pooled, 4 era, 0 full.
- **D1G 19:00–20:00 WIB:** 4 anchor, 0 pooled, 5 era, 0 full.
- **D1H 20:00–21:00 WIB:** **15 anchor, 0 pooled, 9 era, 0 full**.

## Scientific interpretation
D1H is one of the strongest hours so far in terms of breadth and cross-era support, yet it still produces zero pooled-gate passers. That pattern matters: the current generic grammar is increasingly good at identifying profitable DOGE conditions, but it is not yet controlling the adverse path strongly enough.

The correct conclusion is:

> **20:00–21:00 WIB contains broad, era-robust, long-horizon DOGE LONG structure, but the current grammar still fails to isolate a formal low-path-risk character.**

## Integrity
- No gate relaxation.
- No rounding $125.90 down to $125.
- No post-result rescue.
- No promotion of 2/3-gate near-misses.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into character discovery.
- D1A–D1G coordinates were not seeded into D1H ranking.

## D1 → D2 reset policy
The D1 temporal sweep remains mandatory through **D1X**. D1H failure alone does not justify truncating the atlas.

If the completed D1A–D1X atlas still fails to produce a sufficiently robust formal DOGE LONG character or coherent formal cluster, the next stage is explicitly **DOGE D2 — Pair-Native Structure Discovery From Zero**. D2 will not copy SOL/ETH coordinates and will not assume the current 90-rule grammar is the correct DOGE structure. It will rediscover DOGE-native causal state/mechanism from price-path behavior, using D1 only as baseline evidence.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to **D1I — 21:00–22:00 WIB**, changing only the four clock anchors. D1A–D1H remain comparison context only and must not seed D1I ranking.
