# ETH Economic-First E12Q — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12Q_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34560622892**
- job ID: **103142419907**
- head SHA: **9dca8732b8a87c79b29567271a1939d0524351cf**
- artifact ID: **10184189012**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- ETHUSDT
- LONG only
- one time habitat only: **05:00–06:00 WIB**
- quarter-hour anchors: 05:00, 05:15, 05:30, 05:45 WIB
- Development only
- exact same E12A–E12P grammar, 90 causal character rules, gates, fees, lookbacks and holds
- 3,240 candidates
- no TP / no SL
- OOS unopened

## Formal result
**0 / 3,240 candidates passed the full preregistered hour-level anchor-stability + pooled-economics + all-era gate.**

This is the second consecutive formal no-passer after E12P. Therefore the post-02:00 sequence is not a clean alternating PASS–FAIL pattern.

## Strongest full-structure near-miss
### RV_HIGH__RANGE_MID / LB360 / hold960m
- N **211**
- WR **58.29%**
- net **+$558.13**
- expectancy **+$2.65/trade**
- PF **1.784**
- max DD **$196.57**
- max loss streak **11**
- supportive quarter-hour anchors **3/4**
- anchor gate: **PASS**
- all-era gate: **PASS**
- pooled gate: **FAIL**

### Cross-era Development
- 2022: N 78, WR **55.13%**, exp **+$2.91**, PF **1.711**
- 2023: N 69, WR **63.77%**, exp **+$2.43**, PF **2.201**
- 2024: N 64, WR **56.25%**, exp **+$2.55**, PF **1.646**

### Quarter-hour atlas
- 05:00 WIB: N 55, WR **63.64%**, net **+$168.99**, exp **+$3.07**, PF **1.965**, DD **$59.98**, supportive YES
- 05:15 WIB: N 50, WR **62.00%**, net **+$183.83**, exp **+$3.68**, PF **2.470**, DD **$40.07**, supportive YES
- 05:30 WIB: N 56, WR **51.79%**, net **+$96.71**, exp **+$1.73**, PF **1.422**, DD **$72.67**, supportive NO
- 05:45 WIB: N 50, WR **56.00%**, net **+$108.60**, exp **+$2.17**, PF **1.595**, DD **$72.67**, supportive YES

The rejection is again driven by pooled chronological risk: DD **$196.57** exceeds the frozen $125 ceiling and max loss streak **11** exceeds the frozen limit of 8.

## Important horizon clue
For the same `RV_HIGH__RANGE_MID / LB360` family, the 05:00–06:00 habitat behaves very differently across hold horizons:
- hold120: WR **47.87%**, DD **$92.21**, 0/4 supportive anchors
- hold240: WR **45.02%**, DD **$106.37**, 1/4 supportive anchors
- hold360: WR **48.34%**, DD **$78.90**, 1/4 supportive anchors
- hold720: WR **55.45%**, exp **+$2.00**, 3/4 anchors, but pooled risk fails
- hold960: WR **58.29%**, exp **+$2.65**, 3/4 anchors, all-era PASS, but pooled risk fails

Therefore the payoff horizon does **not** continue the E12P compression toward 120–240 minutes. At E12Q, meaningful edge emerges only at much longer 720–960 minute harvest horizons. This is another strong indication that ETH payoff timing is hour-local.

## Only pooled-gate passer
### DRIVE_DOWN__STR_B60_80 / LB120 / hold360m
- N **268**
- WR **57.46%**
- net **+$154.79**
- expectancy **+$0.58/trade**
- PF **1.311**
- max DD **$72.77**
- max loss streak **7**
- pooled gate: **PASS**
- anchor gate: **FAIL** (2/4 supportive)
- all-era gate: **FAIL**

Cross-era:
- 2022 WR **67.50%**, exp **+$1.13**
- 2023 WR **49.04%**, exp **-$0.11**, PF **0.917**
- 2024 WR **58.33%**, exp **+$0.89**

Its risk is controlled, but the edge is neither broad enough across anchors nor stable across eras. It cannot rescue the hour.

## Direct temporal interpretation
The formal sequence is now:
- 23:00–00:00 PASS
- 00:00–01:00 PASS
- 01:00–02:00 PASS
- 02:00–03:00 FAIL — strong economics, pooled-risk clustering
- 03:00–04:00 PASS
- 04:00–05:00 FAIL — fragmented risk/era trade-off
- 05:00–06:00 FAIL — strong long-horizon cross-era economics, pooled-risk clustering

Thus the tentative alternating PASS–FAIL hypothesis after 02:00 is rejected by E12Q. A cleaner reading is that the early-morning ETH habitat is increasingly **micro-regime dependent**: direction can remain economically positive, while the required state grammar, harvest horizon, anchor breadth and chronological risk change sharply hour by hour.

E12Q is particularly valuable because it shows the opposite horizon behavior from E12P: E12P contained shorter-horizon 120–240 minute clues, while E12Q's strongest robust state requires 720–960 minutes. A single morning hold rule is therefore not supported.

## Integrity
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No TP/SL tuning.
- No post-result coordinate rescue.
- Near-misses remain descriptive and are not promoted to formal winners.

## Next action
Continue the unchanged LONG-only hourly sweep to **06:00–07:00 WIB** before deciding where to stop the primary clock-character map. Preserve E12N, E12P and E12Q for a later separately preregistered one-position selection / sequence-risk experiment; all three contain economically meaningful LONG states that fail for different combinations of pooled path risk, anchor breadth or era stability.
