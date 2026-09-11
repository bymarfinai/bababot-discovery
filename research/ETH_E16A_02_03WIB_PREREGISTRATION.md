# ETH E16A — 02:00–03:00 WIB LONG Native Character Rediscovery

## Status

**Development-only discovery. OOS CLOSED. No live authorization.**

## Frozen question

Can the 02:00–03:00 WIB ETHUSDT LONG window produce a robust native character with useful opportunity after pair/hour-specific timing calibration, without changing the E12 character grammar or relaxing any E12 gate?

## Why this window first

E15A's 02:00–03:00 WIB representative was already economically strong in pooled Development data:

- `DRIVE_DOWN__STR_B60_80 / LB120 / H360`
- N 311
- WR 60.13%
- net +$258.70
- expectancy +$0.83/trade
- PF 1.313
- max DD $111.90
- max loss streak 8
- anchor gate: PASS (4/4 supportive/evaluable)
- pooled gate: PASS

It failed only the era gate because 2024 was weak:

- 2022: WR 61.34%, expectancy +$1.28
- 2023: WR 64.84%, expectancy +$1.37
- 2024: WR 54.46%, expectancy -$0.18, PF 0.933

This study therefore tests timing resolution rather than changing the rule family or lowering the standard.

## Frozen data and economics

- Pair: ETHUSDT
- Source timeframe: 5m
- Direction: LONG only
- Partition: existing `development` partition only (2022/2023/2024)
- Notional: $500
- Fee: $0.75 per candidate trade
- OOS: not read for selection or verdict

## Frozen character grammar

Reuse the exact 90 E12 character rules. No new rule, threshold, feature, state label, or direction is introduced in E16A.

## Frozen 02 WIB anchors

The same four quarter-hour anchors are retained for 02:00–03:00 WIB:

- 02:00 WIB
- 02:15 WIB
- 02:30 WIB
- 02:45 WIB

No anchor is removed after results are seen.

## Stage 0 — exact E15A baseline reproduction

Re-run the E15A max-6h grid for hour 02 using:

- lookbacks: 15, 30, 60, 120, 240, 360 minutes
- holds: 60, 120, 240, 360 minutes
- all 90 rules

The runner must reproduce the known representative `DRIVE_DOWN__STR_B60_80 / LB120 / H360` before the refined result is trusted.

## Stage 1 — preregistered timing-resolution grid

Only the timing grid is expanded:

- lookbacks: **15, 30, 60, 90, 120, 150, 180, 210, 240, 360 minutes**
- holds: **60, 120, 180, 210, 240, 270, 300, 330, 360 minutes**
- rules: exact E12 90-rule grammar

Total refined candidates: **8,100**.

This grid preserves every original E15A timing point and adds intermediate horizons. Maximum hold remains 6 hours.

## Frozen formal gates

E16A uses the original E12 formal gates unchanged.

### Anchor supportive

An anchor is supportive only if:

- evaluable N >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- DD <= $125
- max loss streak <= 10

### Anchor gate

- >=3 evaluable anchors
- >=3 supportive anchors

### Pooled gate

- N >= 160
- WR >= 55%
- net > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- DD <= $125
- max loss streak <= 8

### Era gate

For each of 2022, 2023, and 2024:

- N >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05

Additionally, at least 2 of the 3 years must have WR >= 55%.

A formal PASS requires anchor gate + pooled gate + era gate.

## Development ranking

If multiple candidates pass, rank exactly as in E15A:

1. minimum yearly expectancy descending
2. supportive anchors descending
3. pooled expectancy descending
4. pooled WR descending
5. PF descending
6. DD ascending
7. max loss streak ascending
8. hold ascending
9. lookback ascending
10. rule name ascending

## Executable-opportunity diagnostic

For the selected representative only, perform a chronological flat-only diagnostic inside the hour:

- earliest eligible signal enters while flat
- later anchor signals before that trade exits are marked blocked
- re-entry allowed after exit
- no future knowledge

This diagnostic reports accepted trades, blocked signals, WR, net, expectancy, PF, DD, loss streak, and per-year results.

**It is diagnostic only and does not alter the formal E12 candidate gate.** It exists to quantify how much of the pooled character remains executable after internal anchor overlap.

## Frozen verdict labels

- At least one refined full-gate passer: `ETH_E16A_02_03WIB_NATIVE_CHARACTER_FOUND`
- No refined full-gate passer: `ETH_E16A_02_03WIB_NO_FORMAL_PASS`

No threshold may be changed after results are observed.
