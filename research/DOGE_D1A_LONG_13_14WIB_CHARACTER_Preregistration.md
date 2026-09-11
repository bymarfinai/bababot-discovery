# DOGE D1A — 13:00–14:00 WIB LONG Character Discovery

## Scientific question
Within one fixed DOGE time habitat only — **13:00–14:00 WIB (06:00–07:00 UTC)** — what causal pre-entry character produces robust positive LONG trade economics?

This is the first hour of a mandatory pair-native 24-hour DOGE LONG character sweep. The research process is transferred from the canonical pair-native playbook; no ETH, SOL, BTC, or BNB winning coordinate is transferred.

## Frozen direction and time habitat
- Symbol: **DOGEUSDT** Binance Futures raw 5m
- Weekdays only
- Direction: **LONG only**
- Evaluation anchors: **06:00, 06:15, 06:30, 06:45 UTC** = 13:00, 13:15, 13:30, 13:45 WIB
- Clock is fixed context; no other hour is searched in D1A
- Entry: exact 5m open at the anchor
- Exit: exact 5m open after the fixed candidate hold
- No TP / no SL / no post-entry filter
- Fixed notional: **$500**
- Round-trip fee: **$0.75**
- Development only. OOS / external / reference-validation partitions remain closed regardless of result.
- Raw intended Development coverage must be **>=99.5%** or the experiment aborts.

## Frozen candidate grid
Lookbacks: **15, 30, 60, 120, 240, 360 minutes**.

Payoff-horizon probes: **60, 120, 240, 360, 720, 960 minutes**.

Character grammar contains the same **90 causal pair-agnostic rules** used by the canonical pair-native process:
1. `ALL` baseline.
2. `DRIVE_UP` / `DRIVE_DOWN`.
3. Causal absolute-drive strength quintiles: `STR_B0_20`, `STR_B20_40`, `STR_B40_60`, `STR_B60_80`, `STR_B80_100`.
4. Causal EFF / RV / RANGE / EXT LOW-MID-HIGH states and the preregistered two-feature interactions.
5. DRIVE_UP / DRIVE_DOWN interacted with each single state.
6. DRIVE_UP / DRIVE_DOWN interacted with each causal strength quintile.

Total frozen search: **90 × 6 × 6 = 3,240 candidates**.

No result-driven rule or coordinate may be added after this preregistration.

## Causal normalization
EFF / RV / RANGE / EXT use causal same-clock/same-lookback percentile machinery only. Current/future observations may not enter their own threshold. Drive strength uses the existing causal same-clock/same-lookback percentile machinery.

## Per-anchor supportive gate
An anchor is evaluable at **N >= 40** Development trades.

An anchor is supportive only when all are true:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Hour-level anchor gate:
- evaluable anchors >= 3
- supportive anchors >= 3

## Pooled Development gate
Across chronologically pooled opportunities from the four anchors:
- trades >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

## Cross-era Development gate
For each frozen Development era 2022, 2023, and 2024 separately:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

At least **2 of 3 eras** must have WR >= 55%.

## Formal candidate gate
`candidate_gate = anchor_gate AND pooled_gate AND era_gate`

A candidate is a formal PASS only if all three gates pass. High PnL, high WR, or high PF cannot override a failed formal gate.

## Frozen ranking among formal passers
1. higher minimum-era expectancy
2. more supportive anchors
3. higher pooled expectancy
4. higher pooled WR
5. higher PF
6. lower DD
7. lower max loss streak
8. lower hold
9. lower lookback
10. lexical rule-name tie-break

## Failure taxonomy
If no candidate passes, persist the scientifically strongest near-miss and classify the failure mechanism, including as applicable: no economic edge, anchor-local edge, pooled path-risk, era instability, sample weakness, or mixed failure. A near-miss is descriptive evidence only and cannot be promoted retroactively.

## Integrity / stop rules
- Development-only selection.
- OOS remains closed.
- No gate relaxation after results.
- No post-result coordinate rescue.
- No TP/SL optimization.
- No SHORT search.
- No one-position selector mixed into character discovery.
- No scanning another hour inside D1A.
- Pooled opportunity economics are character-discovery statistics, not executable one-position portfolio returns.
- The full 24-hour DOGE LONG map remains mandatory even if D1A passes.

## Allowed outcomes
- `DOGE_D1A_NO_LONG_CHARACTER`
- `DOGE_D1A_LONG_CHARACTER_FOUND`

The next experiment changes only the one-hour habitat to the next contiguous hour while preserving the frozen grammar, economics, gates, and causal discipline.