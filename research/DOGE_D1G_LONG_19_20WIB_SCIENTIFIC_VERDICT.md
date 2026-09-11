# DOGE D1G Scientific Verdict — 19:00–20:00 WIB LONG

## Status
**DOGE_D1G_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- Branch: `doge-d1g-long-19-20wib-character`
- Workflow run ID: **34581531879**
- Job ID: **103205965269**
- Head SHA: **d65945a4b9a1a413b01c796591c02c50a5825937**
- Artifact ID: **10191822383**
- Artifact SHA256: `8dd76fe11cd23dffc55d08d1e824e22b47e336716c28964c55e385202bf5cc0f`
- Target workflow conclusion: **success**
- Raw DOGEUSDT 5m coverage: **100.0000%**
- OOS remained closed.

## Frozen discovery scope
- DOGEUSDT
- LONG only
- one habitat only: **19:00–20:00 WIB**
- anchors: 19:00, 19:15, 19:30, 19:45 WIB
- Development only
- same frozen pair-agnostic 90-rule causal grammar as D1A–D1F
- lookbacks 15, 30, 60, 120, 240, 360m
- payoff-horizon probes 60, 120, 240, 360, 720, 960m
- **3,240 candidates**
- no TP / no SL
- no SHORT
- no one-position selector

## Formal gate counts
- anchor gate: **4 / 3,240**
- pooled gate: **0 / 3,240**
- era gate: **5 / 3,240**
- full gate: **0 / 3,240**

Therefore **no 19:00–20:00 WIB DOGE LONG character passes the frozen formal definition**.

## Strongest preregistered near-miss
### `EFF_MID__EXT_HIGH / LB120 / hold960m`
Pooled Development:
- N: **290**
- WR: **55.52%**
- net: **+$748.01**
- expectancy: **+$2.58/trade**
- PF: **1.427**
- max DD: **$281.29**
- max loss streak: **7**
- supportive anchors: **3/4**
- anchor gate: **PASS**
- pooled gate: **FAIL**
- era gate: **FAIL**

Pooled rejection mechanism:
- DD $281.29 > $125 gate

All other pooled thresholds are satisfied, including N, WR, net, expectancy, PF, and max loss streak.

Cross-era Development:
- 2022: N87, WR **58.62%**, exp **+$2.96**, PF **1.529**
- 2023: N111, WR **50.45%**, exp **+$1.23**, PF **1.229**
- 2024: N92, WR **58.70%**, exp **+$3.84**, PF **1.527**

The setup remains profitable in all three eras, but 2023 WR falls below the frozen 52% era threshold, so the era gate fails formally.

## Secondary structural clues
### `EFF_MID__RV_HIGH / LB360 / hold960m`
- N312
- WR **56.73%**
- net **+$2,474.84**
- expectancy **+$7.93/trade**
- PF **2.181**
- DD **$325.44**
- max loss streak **8**
- supportive anchors **3/4**
- anchor gate: **PASS**
- pooled failure: **DD only**
- era gate: **FAIL**

This is D1G's strongest aggregate economics among the leading broad candidates. The economics are not sufficient for promotion because the fixed chronological drawdown gate remains violated and cross-era requirements are not satisfied.

### High-WR but sample/breadth-limited clue
`RV_HIGH__RANGE_MID / LB360 / H960`:
- N150
- WR **71.33%**
- net **+$1,170.97**
- expectancy **+$7.81/trade**
- PF **3.644**
- DD **$148.02**
- loss streak **9**
- supportive/evaluable anchors **1/1**

Despite the exceptional WR/PF, it fails the pooled minimum sample (N < 160), drawdown, loss-streak, and anchor-breadth requirements. It is a descriptive clue only, not a character candidate.

## Temporal interpretation: D1D → D1G
- **D1D 16:00–17:00 WIB:** `RV_LOW__RANGE_MID / LB240 / H960`; 4/4 anchors and era PASS; pooled failed only DD/streak. Closest formal hour so far.
- **D1E 17:00–18:00 WIB:** `RV_HIGH__RANGE_MID / LB120 / H960`; 4/4 anchors but cross-era robustness weakened and DD/streak rose.
- **D1F 18:00–19:00 WIB:** rotated sharply to `DRIVE_DOWN__RV_HIGH / LB240 / H120`; 4/4 anchors and era PASS, but DD/streak remained excessive.
- **D1G 19:00–20:00 WIB:** rotates back to **H960**, now dominated by efficiency/extension or efficiency/high-volatility states. Loss streak improves materially, but drawdown remains the decisive pooled blocker and 2023 weakens the leading setup's era gate.

This reinforces the clock-specific nature of DOGE LONG: both state family and payoff horizon rotate by hour.

## D1A → D1G progression
- **D1A 13:00–14:00 WIB:** 4 anchor, 0 pooled, 0 era, 0 full.
- **D1B 14:00–15:00 WIB:** 3 anchor, 1 pooled, 0 era, 0 full.
- **D1C 15:00–16:00 WIB:** 10 anchor, 0 pooled, 0 era, 0 full.
- **D1D 16:00–17:00 WIB:** 10 anchor, 1 pooled, 3 era, 0 full.
- **D1E 17:00–18:00 WIB:** 6 anchor, 0 pooled, 2 era, 0 full.
- **D1F 18:00–19:00 WIB:** 6 anchor, 0 pooled, 4 era, 0 full.
- **D1G 19:00–20:00 WIB:** **4 anchor, 0 pooled, 5 era, 0 full**.

## Scientific interpretation
D1G contains strong aggregate LONG economics but no formal character. The leading candidate satisfies the anchor gate and every pooled threshold except drawdown, while remaining positive in all three Development eras; however, 2023 WR is below the frozen era floor. A second broad H960 candidate reaches **+$2,474.84** net and PF **2.181**, yet still fails the same core requirement: chronological drawdown control.

The correct conclusion is:

> **19:00–20:00 WIB shows a strong long-horizon DOGE LONG economic motif, but drawdown remains structurally too large and the leading state is not sufficiently stable across eras for formal qualification.**

## Integrity
- No gate relaxation.
- No post-result rescue.
- No promotion of near-misses.
- No OOS exposure.
- No TP/SL tuning.
- No SHORT search.
- No execution selector mixed into character discovery.
- D1A–D1F coordinates were not seeded into D1G ranking.

## Next preregistered direction
Continue the exact same DOGE LONG character engine to **D1H — 20:00–21:00 WIB**, changing only the four clock anchors. D1A–D1G findings remain comparison context only and must not seed D1H candidate ranking.
