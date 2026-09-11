# ETH Economic-First E12V Scientific Verdict — 10:00–11:00 WIB

## Execution identity
- Branch: `eth-e12v-long-10-11wib-character`
- Workflow run: `34573091797`
- Job: `103179325873`
- Head SHA: `05905ed4df29b23ea00db294ac486056c9c2db47`
- Artifact: `10188548303`
- Artifact digest: `sha256:7e9c4c538be40531f7aeaef5f0fa80dd2c06b707e3eb871bbd3f6a764e5ead79`
- Raw ETHUSDT 5m coverage: 100.0000%
- Candidate grid: 3,240
- OOS: closed throughout

## Formal result
**0 / 3,240 full-gate passers.**

Status: `ETH_ECONOMIC_FIRST_E12V_NO_LONG_CHARACTER`.

Gate counts:
- anchor_gate: 21
- pooled_gate: 0
- era_gate: 2
- candidate_gate: 0
- anchor + era but not pooled: 2
- anchor + pooled but not era: 0
- pooled + era but not anchor: 0

## Strongest robust near-miss
`DRIVE_UP__STR_B80_100 / LB120 / hold960`

- N: 316
- WR: 59.4937%
- net: +$726.3785
- expectancy: +$2.2987/trade
- PF: 1.5904
- max DD: $186.7649
- max loss streak: 8
- supportive anchors: 4/4
- anchor gate: PASS
- era gate: PASS
- pooled gate: FAIL

The pooled gate fails **only on max drawdown**: $186.76 exceeds the frozen $125 ceiling. Trade count, WR, net, expectancy, PF, and max loss streak all satisfy the pooled thresholds.

### Cross-era
- 2022: N 92, WR 60.87%, exp +$3.5120, PF 1.7951
- 2023: N 94, WR 58.51%, exp +$0.8685, PF 1.2295
- 2024: N 130, WR 59.23%, exp +$2.4741, PF 1.6870

### Quarter-hour anchors
- 10:00 WIB: N 74, WR 58.11%, net +$59.76, exp +$0.8075, PF 1.1881, DD $83.76 — supportive
- 10:15 WIB: N 77, WR 62.34%, net +$152.88, exp +$1.9854, PF 1.4280, DD $79.96 — supportive
- 10:30 WIB: N 80, WR 60.00%, net +$243.95, exp +$3.0494, PF 1.8120, DD $66.10 — supportive
- 10:45 WIB: N 85, WR 57.65%, net +$269.79, exp +$3.1741, PF 2.0586, DD $57.30 — supportive

This is therefore not an absence-of-edge result. All four anchors are supportive and all three eras pass. Rejection is caused by the pooled chronological equity path, specifically drawdown clustering.

## Second anchor+era passer
`DRIVE_UP__RANGE_HIGH / LB240 / hold960`

- N 537
- WR 56.42%
- net +$813.36
- exp +$1.5146
- PF 1.3334
- DD $462.21
- max loss streak 21
- supportive anchors 3/4
- anchor gate PASS
- era gate PASS
- pooled gate FAIL

This reinforces the same conclusion with a more severe path-risk profile.

## Hold-horizon structure
For `DRIVE_UP__STR_B80_100 / LB120`, economics improve sharply as hold length expands:

- H60: WR 32.91%, exp -$0.7894
- H120: WR 38.61%, exp -$0.4574
- H240: WR 47.78%, exp -$0.0640
- H360: WR 55.38%, exp +$1.0008
- H720: WR 58.86%, exp +$2.1869
- H960: WR 59.49%, exp +$2.2987

Thus 10:00–11:00 WIB is a distinctly long-horizon habitat under the frozen grammar. The H960 version is cross-era and anchor stable, but still violates pooled drawdown control.

## Hour-locality check
E12U's strongest near-miss coordinate, `EFF_LOW__RANGE_HIGH / LB15 / H720`, does not transfer to E12V:

- E12V N 256
- WR 46.88%
- net -$347.03
- exp -$1.3556
- PF 0.7700
- DD $441.88
- supportive anchors 0/4
- all gates FAIL

This again confirms that ETH character is sharply hour-local. A coordinate that is economically interesting at 09:00–10:00 WIB cannot be shifted one hour forward mechanically.

## Scientific interpretation
E12V extends the formal no-passer block to **04:00–11:00 WIB**, now seven consecutive hours after the isolated E12O recovery at 03:00–04:00 WIB.

However, E12V is economically stronger than a simple 'dead zone' label would imply. The strongest candidate passes every anchor, every era, WR, PF, expectancy, trade-count and loss-streak requirement. Its sole formal defect is pooled maximum drawdown. This is strong evidence that the 10:00–11:00 failure is primarily a **chronological path-risk / clustering problem**, not a directional-economics problem.

The correct next step remains continuation of the frozen hourly sweep. Do not rescue this candidate, relax DD, tune exits, or open OOS. Preserve E12V for a later separately preregistered one-position/sequence-risk study after the 24-hour sweep is complete.
