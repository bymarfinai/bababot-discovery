# ETH Economic-First E12N — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12N_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34559714961**
- job ID: **103139753341**
- head SHA: **c0f6673105a8833c1905cb1c358f5598107e633a**
- artifact ID: **10183883714**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- ETHUSDT
- LONG only
- one time habitat only: **02:00–03:00 WIB**
- quarter-hour anchors: 02:00, 02:15, 02:30, 02:45 WIB
- Development only
- exact same E12A–E12M grammar, 90 causal character rules, gates, fees, lookbacks and holds
- 3,240 candidates
- no TP / no SL
- OOS unopened

## Formal result
**0 / 3,240 candidates passed the full preregistered hour-level anchor-stability + pooled-economics + all-era gate.**

This is the first no-passer after three consecutive formal LONG habitats at 23:00–00:00, 00:00–01:00, and 01:00–02:00 WIB.

## Strongest scientific near-miss
### EFF_HIGH__RV_HIGH / LB360 / hold720m
- N **464**
- WR **59.70%**
- net **+$1,248.03**
- expectancy **+$2.69/trade**
- PF **2.122**
- max DD **$178.31**
- max loss streak **15**
- supportive quarter-hour anchors **4/4**
- anchor gate: **PASS**
- all-era gate: **PASS**
- pooled gate: **FAIL**

### Cross-era Development
- 2022: N 115, WR **59.13%**, expectancy **+$1.73**, PF **1.494**
- 2023: N 199, WR **56.28%**, expectancy **+$1.43**, PF **1.708**
- 2024: N 150, WR **64.67%**, expectancy **+$5.09**, PF **3.493**

### Quarter-hour atlas for the near-miss
- 02:00 WIB: N 111, WR **61.26%**, net **+$289.53**, exp **+$2.61**, PF **2.031**, DD **$60.28**, supportive YES
- 02:15 WIB: N 110, WR **61.82%**, net **+$291.88**, exp **+$2.65**, PF **2.154**, DD **$56.23**, supportive YES
- 02:30 WIB: N 120, WR **60.00%**, net **+$322.10**, exp **+$2.68**, PF **2.198**, DD **$59.16**, supportive YES
- 02:45 WIB: N 123, WR **56.10%**, net **+$344.51**, exp **+$2.80**, PF **2.111**, DD **$52.22**, supportive YES

The rejection is therefore not caused by weak economics, poor anchor breadth, or one bad era. It is caused by **pooled path risk**: after all four anchor streams are chronologically combined, DD rises to $178.31 and the loss streak reaches 15, beyond the frozen pooled limits of $125 DD and 8 losses.

## Additional clue
The same state at `hold360` remains strong:
- WR **58.41%**
- net **+$931.40**
- exp **+$2.01**
- PF **1.973**
- 4/4 supportive anchors
- all-era gate PASS

But pooled DD **$173.54** and max loss streak **12** still fail the frozen pooled-risk gate.

A smaller `EFF_HIGH__EXT_LOW / LB60 / hold360` row reaches WR **60.78%** and DD **$39.13**, but only N **102** pooled and no individually evaluable anchors, so it cannot substitute for the preregistered formal test.

## Interpretation
02:00–03:00 WIB should **not** be described as an absence of LONG edge. The evidence is more specific: the hour contains a broad, cross-era, all-anchor positive LONG state, but its combined opportunity stream produces clustered losses that violate the frozen risk gate.

This marks a likely **risk-regime boundary**, rather than a clean economic-regime boundary. The formal three-hour passing sequence ends here, but the underlying ETH LONG tendency does not disappear.

This distinction matters for later refinement: if the target execution model eventually allows only one selected position rather than treating every qualifying quarter-hour opportunity as part of the pooled stream, E12N is a high-value habitat to revisit under a separately preregistered one-position selection experiment. That must not be used to rescue E12N retroactively.

## Integrity
- OOS unopened.
- No SHORT search.
- No gate relaxation.
- No TP/SL tuning.
- No post-result coordinate rescue.
- Near-misses remain descriptive and are not promoted to formal winners.

## Next action
Continue the unchanged LONG-only hourly sweep to **03:00–04:00 WIB** before deciding whether 02:00–03:00 is an isolated pooled-risk discontinuity or the start of a broader temporal regime change. Preserve E12N as a formal no-passer for any later one-position-only secondary experiment.
