# ETH Economic-First E12S — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E12S_NO_LONG_CHARACTER**

Research/shadow only. No live promotion or profit guarantee.

## Result-bearing run
- workflow run ID: **34562088711**
- job ID: **103146754897**
- head SHA: **88f4f6f859bb8d992606b9b320506a4fca9520e1**
- artifact ID: **10184689463**
- targeted workflow conclusion: **success**
- raw ETHUSDT 5m coverage: **100.0000%**

## Frozen discovery scope
- ETHUSDT
- LONG only
- time habitat: **07:00–08:00 WIB**
- anchors: 07:00, 07:15, 07:30, 07:45 WIB
- Development only; OOS unopened
- exact same E12A–E12R grammar, 90 causal rules, lookbacks, holds, fees, gates and ranking
- 3,240 candidates

## Formal result
**0 / 3,240 candidates passed the full preregistered anchor-stability + pooled-economics + all-era gate.**

Unlike E12N/Q/R, E12S produced **no candidate that passed both pooled and era gates**, and in fact none passed the era gate at all. Only seven candidates passed the anchor gate. This is therefore a weaker hour-level LONG habitat than the earlier risk-only near-miss hours.

## Closest structural near-miss
### EFF_MID__RANGE_LOW / LB240 / hold720m
- N **375**
- WR **55.20%**
- net **+$576.97**
- expectancy **+$1.54/trade**
- PF **1.542**
- max DD **$119.51**
- max loss streak **9**
- supportive anchors **3/4**
- anchor gate: **PASS**
- pooled gate: **FAIL only on max loss streak (9 > 8)**
- era gate: **FAIL**

### Cross-era Development
- 2022: N 147, WR **57.82%**, exp **+$2.56**, PF **1.863**
- 2023: N 117, WR **55.56%**, exp **+$1.40**, PF **1.797**
- 2024: N 111, WR **51.35%**, exp **+$0.33**, PF **1.087**

The 2024 miss is narrow on WR (51.35% vs required 52%), but it remains a formal era failure and cannot be rescued after observing results.

### Quarter-hour atlas
- 07:00 WIB: N **92**, WR **46.74%**, net **-$115.10**, exp **-$1.25**, PF **0.687**, DD **$126.12**, supportive **NO**
- 07:15 WIB: N **105**, WR **57.14%**, net **+$220.42**, exp **+$2.10**, PF **1.940**, DD **$45.70**, supportive **YES**
- 07:30 WIB: N **84**, WR **59.52%**, net **+$265.26**, exp **+$3.16**, PF **2.286**, DD **$53.07**, supportive **YES**
- 07:45 WIB: N **94**, WR **57.45%**, net **+$206.40**, exp **+$2.20**, PF **1.808**, DD **$53.73**, supportive **YES**

This is a strong intrahour asymmetry: the exact 07:00 anchor is clearly adverse while 07:15–07:45 are consistently supportive for this near-miss. Because the hour-level preregistration allows 3/4 supportive anchors, this pattern alone does not rescue the candidate; pooled streak and 2024 stability still fail.

## Stronger headline-WR near-miss
### EFF_MID__RV_MID / LB240 / hold720m
- N **344**
- WR **57.56%**
- net **+$423.76**
- exp **+$1.23/trade**
- PF **1.409**
- max DD **$158.90**
- max loss streak **10**
- supportive anchors **3/4**
- anchor gate PASS
- pooled gate FAIL
- era gate FAIL because 2024 WR **49.14%**, expectancy **-$0.21**, PF **0.939**

This confirms that good pooled headline WR at E12S is not enough: the hour contains genuine cross-era instability in addition to path-risk issues.

## 24-hour sweep progress
The E12 series now covers a continuous **19 / 24 hours**:
- E12A 13:00–14:00
- ...
- E12R 06:00–07:00
- E12S 07:00–08:00

Remaining unswept hours are **08:00–13:00 WIB**: five one-hour habitats.

## Temporal interpretation
Current visible sequence from 23:00 through 08:00 WIB:
- 23:00–00:00 PASS
- 00:00–01:00 PASS
- 01:00–02:00 PASS
- 02:00–03:00 FAIL
- 03:00–04:00 PASS
- 04:00–05:00 FAIL
- 05:00–06:00 FAIL
- 06:00–07:00 FAIL
- 07:00–08:00 FAIL

Therefore the post-E12O fragmented zone now extends across **four consecutive formal no-passer hours (04:00–08:00 WIB)**. E12S is especially important because its failure is not merely pooled sequencing risk: all-era robustness disappears too. That is stronger evidence of a broader temporal deterioration in clean LONG habitat quality.

At the same time, the 07:15–07:45 supportive cluster shows the deterioration is not uniform inside the hour. Preserve this as a descriptive clue for a later separately preregistered one-position/anchor-selection experiment; do not use it to retroactively rescue E12S.

## Integrity
- OOS unopened
- no SHORT search
- no gate relaxation
- no TP/SL tuning
- no post-result coordinate rescue
- non-passing candidates remain non-passing

## Next action
Continue unchanged LONG-only sweep to **E12T = 08:00–09:00 WIB**. Complete the remaining five hours through 13:00 WIB before changing the discovery grammar or launching the later one-position selection secondary experiment.
