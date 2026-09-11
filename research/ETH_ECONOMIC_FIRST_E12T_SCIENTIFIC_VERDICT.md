# ETH Economic-First E12T Scientific Verdict — 08:00–09:00 WIB

## Run identity
- Branch: `eth-e12t-long-08-09wib-character`
- Head/trigger commit: `619dbea4ed831d25331b128b65b4f7c22c27de3e`
- Workflow run: `34572009200`
- Job: `103175943590`
- Artifact: `10188133891`
- Artifact digest: `sha256:d839b38026aa046c44bf2025db6afa81edbc407f0d4485b02d58dd3ecbe3866d`
- Raw ETHUSDT 5m coverage: 100.0000%
- Development only; OOS remained closed.

## Formal result
**FAIL — 0 / 3,240 candidates passed all preregistered gates.**

Gate population:
- Anchor gate pass: **5 / 3,240**
- Pooled gate pass: **0 / 3,240**
- Era gate pass: **0 / 3,240**
- Full candidate gate pass: **0 / 3,240**

This is therefore not a case where one otherwise-complete formal candidate missed only a single global gate. The hour contains local LONG economics, but the frozen grammar found no candidate with both pooled risk/economics and cross-era robustness.

## Strongest economically meaningful near-miss
`EFF_LOW__RANGE_MID / LB360 / hold720m`

Pooled:
- N **307**
- WR **56.68%**
- net **+$531.65**
- expectancy **+$1.73/trade**
- PF **1.561**
- max DD **$118.79**
- max loss streak **12**
- supportive anchors **4/4**

Gate diagnosis:
- Anchor gate: **PASS**
- Pooled gate: **FAIL** solely because max loss streak **12 > 8**; N, WR, net, expectancy, PF, and DD all satisfy their pooled thresholds.
- Era gate: **FAIL** because 2024 loses positive-economics robustness.

Cross-era:
- 2022: N80, WR **60.00%**, exp **+$4.24**, PF **2.160**
- 2023: N98, WR **58.16%**, exp **+$2.12**, PF **2.364**
- 2024: N129, WR **53.49%**, exp **-$0.12**, PF **0.970**

Quarter-hour decomposition:
- 08:00 WIB: N68, WR **58.82%**, net **+$160.59**, exp **+$2.36**, PF **1.791**, DD **$39.85**, supportive YES
- 08:15 WIB: N78, WR **55.13%**, net **+$89.82**, exp **+$1.15**, PF **1.330**, DD **$45.35**, supportive YES
- 08:30 WIB: N76, WR **55.26%**, net **+$83.53**, exp **+$1.10**, PF **1.318**, DD **$100.74**, supportive YES
- 08:45 WIB: N85, WR **57.65%**, net **+$197.70**, exp **+$2.33**, PF **1.938**, DD **$43.84**, supportive YES

The anchor atlas is therefore broad and positive. The formal failure comes from chronological loss clustering plus deterioration of the same character in 2024, not from one bad quarter-hour anchor.

## Secondary clue
`EFF_LOW__EXT_MID / LB240 / hold720m` also passes the anchor gate (3/4) and has positive expectancy/PF in all three years, but fails the era gate because only one year reaches WR >=55%, while pooled WR/PF/DD also miss their frozen thresholds. It is not promotable.

## Temporal interpretation
E12T extends the post-E12O formal no-passer block:

`03–04 PASS -> 04–05 FAIL -> 05–06 FAIL -> 06–07 FAIL -> 07–08 FAIL -> 08–09 FAIL`

So the current evidence supports a **04:00–09:00 WIB fragmented LONG zone** under the frozen E12 grammar. However, E12T is not simply an absence of local edge: its strongest near-miss is supportive at all four quarter-hour anchors. The weakness is in chronological risk clustering and especially cross-era persistence, with 2024 degrading versus 2022–2023.

This strengthens the pair-native/hour-native hypothesis: a locally attractive LONG state can remain visible inside an hour while still being unsuitable as a robust pooled rule across the Development eras.

## Integrity
No gate relaxation, no coordinate rescue, no SHORT search, no TP/SL tuning, and no OOS exposure. No non-passer is promoted.

## Sweep status
E12A–E12T now cover **20 / 24 continuous WIB hours**, from **13:00 WIB through 09:00 WIB**. Remaining hours are 09:00–10:00, 10:00–11:00, 11:00–12:00, and 12:00–13:00 WIB.
