# ETH Economic-First E12R — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12R_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34561412021**
- job ID: **103144724904**
- head SHA: **ae8847d3f7e3bb67bbe185e8bb079dd7179f686e**
- artifact ID: **10184444272**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- ETHUSDT
- LONG only
- one time habitat only: **06:00–07:00 WIB**
- quarter-hour anchors: 06:00, 06:15, 06:30, 06:45 WIB
- Development only
- exact same E12A–E12Q grammar, 90 causal character rules, gates, fees, lookbacks and holds
- 3,240 candidates
- no TP / no SL
- OOS unopened

## Formal result
**0 / 3,240 candidates passed the full preregistered hour-level anchor-stability + pooled-economics + all-era gate.**

This creates three consecutive formal no-pass hours after E12O's 03:00–04:00 WIB recovery:
- 03:00–04:00 PASS
- 04:00–05:00 FAIL
- 05:00–06:00 FAIL
- 06:00–07:00 FAIL

## Strongest formal near-miss
### EFF_LOW__RANGE_MID / LB60 / hold720m
- N **264**
- WR **56.06%**
- net **+$385.61**
- expectancy **+$1.46/trade**
- PF **1.461**
- max DD **$138.55**
- max loss streak **7**
- supportive quarter-hour anchors **3/4**
- anchor gate: **PASS**
- all-era gate: **PASS**
- pooled gate: **FAIL only on DD**

### Cross-era Development
- 2022: N 63, WR **55.56%**, exp **+$1.59**, PF **1.311**
- 2023: N 103, WR **54.37%**, exp **+$1.23**, PF **1.616**
- 2024: N 98, WR **58.16%**, exp **+$1.62**, PF **1.516**

### Quarter-hour atlas
- 06:00 WIB: N 67, WR **50.75%**, net **+$51.87**, exp **+$0.77**, PF **1.195**, DD **$84.13**, supportive NO
- 06:15 WIB: N 61, WR **60.66%**, net **+$77.40**, exp **+$1.27**, PF **1.399**, DD **$62.63**, supportive YES
- 06:30 WIB: N 66, WR **57.58%**, net **+$87.48**, exp **+$1.33**, PF **1.411**, DD **$49.02**, supportive YES
- 06:45 WIB: N 70, WR **55.71%**, net **+$168.86**, exp **+$2.41**, PF **2.039**, DD **$37.76**, supportive YES

The rejection is narrow and specifically caused by pooled drawdown: **$138.55** versus the frozen maximum **$125**. The loss-streak gate still passes at **7 <= 8**.

No candidate in E12R passed the pooled gate at all, so there is no alternative formal coordinate available under the frozen methodology.

## Controlled-risk but era-unstable clue
### EFF_MID__RANGE_HIGH / LB240 / hold120m
- N **280**
- WR **54.64%**
- net **+$358.68**
- expectancy **+$1.28/trade**
- PF **1.908**
- max DD **$70.33**
- max loss streak **9**
- supportive anchors **4/4**

This coordinate shows the familiar trade-off seen in E12P: a much shorter 120-minute harvest horizon controls drawdown well and is broad across anchors, but it fails the frozen pooled gate on WR/loss streak and fails all-era stability because 2023 WR is only **48.51%**.

## Direct comparison with E12Q near-miss family
E12Q's strongest near-miss was:
- `RV_HIGH__RANGE_MID / LB360 / hold960`
- WR **58.29%**
- positive cross-era economics

The exact same coordinate at E12R becomes:
- N **188**
- WR **39.89%**
- net **-$147.74**
- expectancy **-$0.79/trade**
- PF **0.841**
- DD **$299.11**
- max loss streak **28**
- supportive anchors **0/4**
- formal gate **FAIL**

Therefore the E12Q long-horizon state collapses immediately one hour later. This is strong evidence that even apparently robust near-miss families remain sharply hour-local.

## Interpretation
E12R is not a clean absence of LONG economics. A cross-era, 3/4-anchor state exists and misses the full gate only because pooled DD is slightly too high. However, the broader candidate set is weaker than in some earlier no-pass hours: **zero candidates pass the pooled gate**.

The updated sequence is:
- 23:00–00:00 PASS
- 00:00–01:00 PASS
- 01:00–02:00 PASS
- 02:00–03:00 FAIL
- 03:00–04:00 PASS
- 04:00–05:00 FAIL
- 05:00–06:00 FAIL
- 06:00–07:00 FAIL

The evidence now supports a **post-04:00 fragmented zone lasting at least three consecutive hours**, but the mechanism inside that zone is not constant. E12P, E12Q, and E12R fail for different mixtures of pooled risk, era instability, and changing payoff horizon.

This also weakens any attempt to define one universal morning ETH rule. State grammar, lookback, harvest horizon, anchor breadth, and risk path all remain hour-native.

## Integrity
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No TP/SL tuning.
- No post-result coordinate rescue.
- Near-misses remain descriptive and are not promoted to formal winners.

## Next action
Continue the unchanged LONG-only hourly sweep to **07:00–08:00 WIB**. This is needed to determine whether the post-04:00 fragmented zone extends into the next hour or whether a new clean habitat reappears. Preserve E12P–R for a later separately preregistered one-position selection experiment, especially because E12R's best candidate misses the pooled DD limit only narrowly.
