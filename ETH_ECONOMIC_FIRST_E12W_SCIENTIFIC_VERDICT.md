# ETH Economic-First E12W Scientific Verdict — 11:00–12:00 WIB

## Run identity
- Branch: `eth-e12w-long-11-12wib-character`
- Trigger/head SHA: `f35d72fbca00bf300b6a98def6151b216426e32f`
- Workflow run: `34573664264`
- Job: `103181155463`
- Artifact: `10188763747`
- Artifact digest: `sha256:ca6872faf317177bd9834fba574a2c1cef16a84f612ec4a3b870b3f5d366cf43`
- Raw ETHUSDT 5m coverage: 100.0000%
- Development only; OOS remained closed.

## Formal result
**0 / 3,240 full-gate passers.**

Status: `ETH_ECONOMIC_FIRST_E12W_NO_LONG_CHARACTER`.

Gate counts:
- anchor_gate: 11
- pooled_gate: 0
- era_gate: 0
- candidate_gate: 0

Therefore no 11:00–12:00 WIB LONG character can be promoted under the frozen E12A methodology.

## Strongest robust near-miss
`EFF_MID__RANGE_HIGH / LB360 / hold720`

Pooled Development:
- N 269
- WR 58.3643%
- net +$503.1788
- expectancy +$1.8706/trade
- PF 1.4060
- max DD $196.7557
- max loss streak 8
- supportive anchors 3/4

Formal gates:
- anchor gate: PASS
- pooled gate: FAIL only on max DD ($196.76 > $125)
- era gate: FAIL only on 2023 WR (47.9452% < 52%)

Cross-era Development:
- 2022: N69, WR 60.8696%, exp +$2.6021, PF 1.3084
- 2023: N73, WR 47.9452%, exp +$0.3635, PF 1.1356
- 2024: N127, WR 62.9921%, exp +$2.3393, PF 1.6438

Quarter-hour anchors:
- 11:00 WIB: N64, WR 65.6250%, net +$80.3111, exp +$1.2549, PF 1.2616, DD $87.4493 — supportive
- 11:15 WIB: N71, WR 63.3803%, net +$223.1906, exp +$3.1435, PF 1.8818, DD $94.3539 — supportive
- 11:30 WIB: N67, WR 56.7164%, net +$140.9080, exp +$2.1031, PF 1.4146, DD $78.0667 — supportive
- 11:45 WIB: N67, WR 47.7612%, net +$58.7690, exp +$0.8771, PF 1.1731, DD $96.5516 — not supportive

This is economically interesting but cannot be rescued. The failure combines chronological drawdown clustering with 2023 win-rate instability, while 11:45 WIB is the weak intrahour anchor.

## Harvest-horizon clue for the near-miss family
For `EFF_MID__RANGE_HIGH / LB360`, the character changes materially with hold horizon:
- H60: WR 40.52%, net -$103.01, exp -$0.38, 0/4 anchors
- H120: WR 42.75%, net -$17.92, exp -$0.07, 0/4 anchors
- H240: WR 45.35%, net +$106.83, exp +$0.40, 0/4 anchors
- H360: WR 56.13%, net +$124.06, exp +$0.46, 3/4 anchors
- H720: WR 58.36%, net +$503.18, exp +$1.87, 3/4 anchors
- H960: WR 61.71%, net +$499.84, exp +$1.86, but DD $294.11, loss streak 12, only 2/4 anchors and 2022 expectancy negative

Thus 11:00–12:00 WIB also prefers a relatively long payoff horizon, but extending too far to H960 worsens chronological and era robustness.

## Hour-locality check versus E12V
The E12V strongest near-miss/full-structure coordinate was `DRIVE_UP__STR_B80_100 / LB120 / hold960`.
At E12W the exact same coordinate becomes:
- N373
- WR 50.6702%
- net +$366.1647
- exp +$0.9817
- PF 1.1894
- DD $251.9677
- max loss streak 18
- supportive anchors 1/4
- anchor, pooled, and era gates all FAIL

So the 10:00–11:00 WIB structure does not persist cleanly one hour later. This is further evidence that ETH LONG structure is hour-local.

## Temporal interpretation
Current local sequence around the morning boundary:

`03–04 PASS -> 04–05 FAIL -> 05–06 FAIL -> 06–07 FAIL -> 07–08 FAIL -> 08–09 FAIL -> 09–10 FAIL -> 10–11 FAIL -> 11–12 FAIL`

The formal no-pass block now spans **04:00–12:00 WIB, eight consecutive hours**.

However, this should not be treated as one homogeneous no-edge regime. Failure mechanics rotate by hour. E12V had strong cross-era/all-anchor economics rejected primarily by pooled drawdown; E12W has no pooled-gate or era-gate passer at all, with the strongest near-miss simultaneously showing pooled DD stress and a 2023 WR hole.

## Scientific verdict
E12W is a formal FAIL under frozen gates. It extends the post-04:00 formal fragmented zone to eight hours, while reinforcing the pair-native/hour-native thesis: state grammar, lookback, payoff horizon, quarter-hour quality, chronological risk, and cross-era persistence rotate materially even between adjacent ETH hours.

No gate relaxation, no coordinate rescue, no OOS exposure, and no promotion to live use.
