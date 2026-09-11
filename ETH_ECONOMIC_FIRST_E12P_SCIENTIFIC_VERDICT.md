# ETH Economic-First E12P — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12P_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34560213856**
- job ID: **103141205959**
- head SHA: **a0f4254b1eb54580e90c9e09e5a575b2d2febe85**
- artifact ID: **10184049831**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- ETHUSDT
- LONG only
- one time habitat only: **04:00–05:00 WIB**
- quarter-hour anchors: 04:00, 04:15, 04:30, 04:45 WIB
- Development only
- exact same E12A–E12O grammar, 90 causal character rules, gates, fees, lookbacks and holds
- 3,240 candidates
- no TP / no SL
- OOS unopened

## Formal result
**0 / 3,240 candidates passed the full preregistered hour-level anchor-stability + pooled-economics + all-era gate.**

The prior 03:00–04:00 WIB formal recovery therefore does not extend cleanly into 04:00–05:00 WIB.

## Strongest cross-era + anchor near-miss
### EFF_HIGH__RV_HIGH / LB120 / hold960m
- N **447**
- WR **55.48%**
- net **+$854.96**
- expectancy **+$1.91/trade**
- PF **1.427**
- max DD **$210.35**
- max loss streak **11**
- supportive quarter-hour anchors **4/4**
- anchor gate: **PASS**
- all-era gate: **PASS**
- pooled gate: **FAIL**

### Cross-era Development
- 2022: N 137, WR **52.55%**, expectancy **+$1.45**, PF **1.212**
- 2023: N 147, WR **57.14%**, expectancy **+$2.12**, PF **1.899**
- 2024: N 163, WR **56.44%**, expectancy **+$2.11**, PF **1.481**

### Quarter-hour atlas
- 04:00 WIB: N 115, WR **53.04%**, net **+$188.33**, exp **+$1.64**, PF **1.331**, DD **$120.96**, supportive YES
- 04:15 WIB: N 108, WR **58.33%**, net **+$148.59**, exp **+$1.38**, PF **1.293**, DD **$85.14**, supportive YES
- 04:30 WIB: N 100, WR **53.00%**, net **+$82.58**, exp **+$0.83**, PF **1.178**, DD **$88.34**, supportive YES
- 04:45 WIB: N 124, WR **57.26%**, net **+$435.45**, exp **+$3.51**, PF **1.946**, DD **$65.28**, supportive YES

The rejection is caused by pooled path risk: DD **$210.35** exceeds the frozen $125 limit and the max loss streak **11** exceeds the frozen limit of 8.

## Short-horizon risk-boundary clue
### DRIVE_DOWN__STR_B80_100 / LB120 / hold240m
- N **331**
- WR **57.70%**
- net **+$341.90**
- expectancy **+$1.03/trade**
- PF **1.368**
- max DD **$178.59**
- max loss streak **8**
- supportive anchors **4/4**
- anchor gate: **PASS**
- all-era gate: **PASS**
- pooled gate: **FAIL only on DD**

Cross-era WR:
- 2022: **56.86%**
- 2023: **52.25%**
- 2024: **63.56%**

This is important because a 240-minute payoff horizon remains economically viable after the E12O hold240 winner, but at 04:00–05:00 WIB the chronological pooled stream is still too drawdown-heavy to pass the frozen risk gate.

## Controlled-risk but era-unstable clue
### RV_HIGH__RANGE_MID / LB360 / hold120m
- N **220**
- WR **56.82%**
- net **+$150.59**
- expectancy **+$0.68/trade**
- PF **1.543**
- max DD **$66.68**
- max loss streak **8**
- supportive anchors **3/4**
- pooled gate: **PASS**
- anchor gate: **PASS**
- all-era gate: **FAIL**

Cross-era WR:
- 2022: **50.00%**
- 2023: **53.73%**
- 2024: **64.71%**

This suggests further payoff compression toward 120 minutes can control path risk, but the effect is not sufficiently stable across eras.

## Direct comparison with E12O winner family
E12O formal winner at 03:00–04:00 WIB:
- `RV_HIGH__RANGE_MID / LB360 / hold240`
- WR **60.40%**
- PF **1.937**
- DD **$116.44**
- 4/4 anchors

The exact same coordinate at 04:00–05:00 WIB becomes:
- N **220**
- WR **51.36%**
- net **+$335.65**
- exp **+$1.53**
- PF **1.805**
- DD **$87.53**
- 3/4 anchors
- 2022 WR **45.59%**, 2023 **55.22%**, 2024 **52.94%**
- formal gate **FAIL**

Therefore E12O's winner is hour-local and should not be generalized into E12P.

## Interpretation
E12P is best described as a **fragmented LONG habitat** rather than a clean absence of edge. Broad cross-era/all-anchor positive states exist but fail pooled path risk; shorter-horizon states can control DD but lose cross-era stability.

The sequence from 23:00 through 05:00 WIB is now:
- 23:00–00:00 PASS
- 00:00–01:00 PASS
- 01:00–02:00 PASS
- 02:00–03:00 FAIL (strong economics, pooled-risk clustering)
- 03:00–04:00 PASS
- 04:00–05:00 FAIL (fragmented risk/era trade-off)

This argues against a simple single regime boundary at 02:00. Instead ETH appears to move through hour-local micro-regimes where the state grammar, payoff horizon, and path-risk structure can change sharply from one hour to the next.

## Integrity
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No TP/SL tuning.
- No post-result coordinate rescue.
- Near-misses remain descriptive and are not promoted to formal winners.

## Next action
Continue the unchanged LONG-only hourly sweep to **05:00–06:00 WIB**. Do not infer a stable morning regime from E12O alone. Preserve E12N and E12P for a later separately preregistered one-position selection experiment, because both contain meaningful LONG economics whose failure is strongly related to pooled sequencing/risk rather than a complete disappearance of edge.
