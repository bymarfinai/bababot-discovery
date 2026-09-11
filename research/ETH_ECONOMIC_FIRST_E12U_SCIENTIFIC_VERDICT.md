# ETH Economic-First E12U Scientific Verdict — 09:00–10:00 WIB

## Run identity
- Branch: `eth-e12u-long-09-10wib-character`
- Trigger/head commit: `9b82ae4d02e7267f315838a98d7ff8f17b9b1b62`
- Workflow run: `34572712617`
- Job: `103178133263`
- Artifact: `10188400706`
- Artifact digest: `sha256:d1e634047d02f7501482d36ce39c80410dbe2a45c39a735cbedd8b2145e8d71c`
- Raw ETHUSDT 5m coverage: 100.0000%
- Development only; OOS remained closed.

## Formal result
**0 / 3,240 full-gate passers.**

Gate counts:
- anchor gate: 17 / 3,240
- pooled gate: 0 / 3,240
- era gate: 0 / 3,240
- candidate gate: 0 / 3,240

Therefore the formal status remains `ETH_ECONOMIC_FIRST_E12U_NO_LONG_CHARACTER`.

## Closest robust near-miss
`EFF_LOW__RANGE_HIGH / LB15 / hold720m`

Pooled Development:
- N 250
- WR 56.40%
- net +$458.41
- expectancy +$1.8336/trade
- PF 1.4707
- max DD $114.02
- max loss streak 9
- max win streak 10
- supportive anchors 3/4

This candidate passes every frozen pooled criterion except **max loss streak**, where 9 exceeds the preregistered maximum of 8.

Cross-era Development:
- 2022: N 68, WR 63.24%, exp +$2.2057, PF 1.3560
- 2023: N 91, WR 47.25%, exp +$0.6487, PF 1.2692
- 2024: N 91, WR 60.44%, exp +$2.7406, PF 1.7485
- years with WR >=55%: 2

The era gate fails only because **2023 WR 47.25% is below the frozen 52% floor**. Net, expectancy, PF, sample size, and the two-years-WR>=55 condition otherwise remain satisfied.

Quarter-hour atlas for this near-miss:
- 09:00 WIB: N55, WR58.18%, net +$84.57, exp +$1.5376, PF1.388, DD$77.48 — supportive
- 09:15 WIB: N67, WR59.70%, net +$163.10, exp +$2.4344, PF1.571, DD$51.31 — supportive
- 09:30 WIB: N58, WR48.28%, net +$121.28, exp +$2.0910, PF1.818, DD$45.43 — not supportive because WR<52%
- 09:45 WIB: N70, WR58.57%, net +$89.47, exp +$1.2781, PF1.278, DD$61.16 — supportive

This is economically interesting but is **not** a formal character and cannot be promoted or rescued retroactively.

## Secondary structural clue
`EFF_HIGH__RV_HIGH / LB60 / hold720m` has N435, WR56.09%, net +$689.66, exp +$1.5854, PF1.3909, max loss streak7, and all 4 anchors supportive. It fails pooled risk because max DD is $233.62 and fails era persistence because 2023 WR is 51.01% and only one year reaches WR>=55%.

## Hour-local discontinuity versus E12T
The strongest E12T family `EFF_LOW__RANGE_MID / LB360 / hold720m`, which at 08:00–09:00 WIB had broad positive economics, collapses at E12U:
- N302
- WR44.04%
- net -$366.35
- expectancy -$1.2131
- PF0.7527
- max DD $654.19
- max loss streak15
- supportive anchors 0/4
- all three era WRs below 47%

This one-hour reversal is strong evidence that ETH's LONG character is hour-local rather than a smoothly transferable neighboring-hour rule.

## Scientific interpretation
E12U is a formal FAIL, extending the post-E12O no-full-passer block through 10:00 WIB. However, it is not an absence of local LONG economics: several anchor-stable states remain positive. The failure is a combination of chronological clustering and cross-era instability, with the closest near-miss missing only the pooled loss-streak criterion and the 2023 era WR floor.

Current local sequence:
`03–04 PASS -> 04–05 FAIL -> 05–06 FAIL -> 06–07 FAIL -> 07–08 FAIL -> 08–09 FAIL -> 09–10 FAIL`.

No gate relaxation, no post-result coordinate rescue, no SHORT search, no TP/SL tuning, and no OOS exposure.
