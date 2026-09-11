# ETH Economic-First E12X Scientific Verdict — 12:00–13:00 WIB

## Run identity
- Branch: `eth-e12x-long-12-13wib-character`
- Workflow run: `34574008251`
- Job: `103182277565`
- Head SHA: `639720fbe38154873efefea22e3d506d3564bfbb`
- Artifact: `10188900295`
- Artifact digest: `sha256:6632fcd126588bc8c4d801f2c6ff434d9c5bb07580338c164991144da3710e26`
- Raw ETHUSDT 5m coverage: 100.0000%
- OOS remained closed.

## Formal result
**0 / 3,240 full-gate passers.**

Status: `ETH_ECONOMIC_FIRST_E12X_NO_LONG_CHARACTER`.

Gate counts:
- anchor gate: 19 / 3,240
- pooled gate: 0 / 3,240
- era gate: 0 / 3,240
- full gate: 0 / 3,240

Therefore no 12:00–13:00 WIB LONG character is formally selected under the frozen E12A–E12W methodology.

## Strongest robust near-miss
`DRIVE_UP__STR_B80_100 / LB240 / hold360m`

Pooled Development:
- N: 351
- WR: 55.8405%
- net: +$519.3441
- expectancy: +$1.47961/trade
- PF: 1.79746
- max DD: $73.7246
- max loss streak: 15
- supportive anchors: 4/4
- anchor gate: PASS
- pooled gate: FAIL
- era gate: FAIL

The pooled gate fails specifically on max loss streak (15 > 8); the remaining pooled thresholds pass.

Cross-era Development:
- 2022: N 107, WR 64.4860%, exp +$1.69400, PF 1.80025
- 2023: N 106, WR 51.8868%, exp +$0.75100, PF 1.44294
- 2024: N 138, WR 52.1739%, exp +$1.87304, PF 2.05492
- years with WR >= 55%: 1

Era rejection is narrow in 2023 WR (51.8868% < 52%) plus the frozen requirement that at least two years have WR >= 55%.

Quarter-hour anchors:
- 12:00 WIB / 05:00 UTC: N87, WR55.1724%, net +$96.4168, exp +$1.10824, PF1.67270, DD$32.5022 — supportive
- 12:15 WIB / 05:15 UTC: N88, WR54.5455%, net +$149.1904, exp +$1.69535, PF2.01093, DD$28.8955 — supportive
- 12:30 WIB / 05:30 UTC: N89, WR55.0562%, net +$138.6550, exp +$1.55792, PF1.75720, DD$34.9817 — supportive
- 12:45 WIB / 05:45 UTC: N87, WR58.6207%, net +$135.0819, exp +$1.55267, PF1.76220, DD$33.0693 — supportive

This is not an anchor-breadth failure. The local hour is economically positive across all four quarter-hour anchors, but the pooled chronological path creates a 15-loss streak and the edge is not sufficiently persistent under the frozen era gate.

## Other structural clues
`EFF_HIGH__RV_HIGH / LB240 / hold720m` has N491, WR55.3971%, net +$1,105.7660, exp +$2.25207, PF1.56408, and 3/4 supportive anchors, but fails pooled DD ($306.6791) and loss streak (13), while only one year reaches WR >=55%.

`DRIVE_UP__STR_B80_100 / LB240 / hold720m` has N351, WR55.8405%, net +$789.5766, exp +$2.24951, PF1.59717, and 4/4 supportive anchors, but fails pooled DD ($402.3273), loss streak (12), and 2022 WR (48.5981%).

Thus longer harvest horizons increase payoff but worsen path risk and/or era stability. H360 is the cleaner risk form for the strongest family, yet still fails the frozen streak and era requirements.

## Hour-local comparison
The E12V strongest coordinate `DRIVE_UP__STR_B80_100 / LB120 / hold960m` collapses at E12X to N357, WR46.4986%, net +$257.0876, exp +$0.72013, PF1.12703, DD$560.7095, max loss streak32, and 0/4 supportive anchors.

The E12W strongest coordinate `EFF_MID__RANGE_HIGH / LB360 / hold720m` also collapses at E12X to N266, WR51.5038%, net +$21.6059, exp +$0.08123, PF1.01481, DD$692.8385, max loss streak9, and 0/4 supportive anchors.

This reinforces the hour-local character hypothesis: neighboring-hour winners/near-winners do not transport mechanically into 12:00–13:00 WIB.

## 24-hour sweep implication
E12X completes the contiguous 24-hour ETH LONG-character sweep that began at 13:00 WIB.

The latest sequence around the morning block is:
- 03:00–04:00 WIB: PASS
- 04:00–05:00: FAIL
- 05:00–06:00: FAIL
- 06:00–07:00: FAIL
- 07:00–08:00: FAIL
- 08:00–09:00: FAIL
- 09:00–10:00: FAIL
- 10:00–11:00: FAIL
- 11:00–12:00: FAIL
- 12:00–13:00: FAIL

So the frozen formal no-pass block extends from **04:00 through 13:00 WIB: nine consecutive hours**.

This should not be interpreted as nine hours with no economic signal. Several hours contain positive all-anchor or cross-era economics, but fail for different reasons: pooled DD, loss clustering, era instability, or combinations thereof. The 24-hour sweep therefore supports hour-native state grammar / lookback / harvest-horizon / path-risk calibration rather than a universal ETH LONG rule.

## Scientific integrity
No gate relaxation, no post-result coordinate rescue, no SHORT search, no TP/SL tuning, and no OOS exposure were used. Secondary one-position / sequence-risk experiments may use these Development clues only under a new preregistration.
