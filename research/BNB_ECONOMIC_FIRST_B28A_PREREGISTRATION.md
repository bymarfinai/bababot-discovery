# BNB Economic-First B28A — Preregistration

## Purpose
B28 is a clean methodological reset of BNB discovery after B27 established useful structural facts but failed to support a trading edge when economics were finally applied. B28 reverses that order: **economic validity is tested first; structural explanations come only after a formal passer exists.**

## Scope
- Pair: **BNBUSDT**
- Direction: **LONG only**
- First time habitat: **00:00–01:00 WIB only**
- Quarter-hour anchors: **00:00, 00:15, 00:30, 00:45 WIB** (17:00, 17:15, 17:30, 17:45 UTC)
- Development only; OOS/holdout remains closed.
- $500 notional per trade.
- No TP / no SL; causal fixed-horizon hold only.

## Frozen hour order
The B28 LONG discovery clock is preregistered before BNB economic results are observed:
**00:00–01:00, 01:00–02:00, 02:00–03:00, ... , 23:00–00:00 WIB.**

A failed hour is persisted as a failure and the discovery moves to the next hour. No failed hour may be rescued by post-result clock shifts, geometry changes, weekday selection, or threshold relaxation.

## Frozen character grammar
Use the neutral 90-rule causal character grammar already validated operationally in ETH E12, but evaluate it entirely on BNB data. This is a **search grammar, not an inherited ETH strategy**: no ETH winning rule, lookback, hold, or hour receives priority.

The grammar covers:
- directional drive sign,
- causal drive-strength percentile,
- path efficiency state,
- realized-volatility state,
- normalized realized-range state,
- range-extension state,
- preregistered single-state and two-state combinations.

Lookbacks are frozen at **15 / 30 / 60 / 120 / 240 / 360 minutes**.
Holds are frozen at **60 / 120 / 240 / 360 / 720 / 960 minutes**.
Total candidate identities per hour: **3,240**.

## Frozen economics and formal gates
Use the same conservative E12 economic engine and decision gates so BNB receives no favorable treatment.

### Quarter-hour anchor support
An anchor is evaluable at N >= 40 and supportive only if all hold:
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

Hour-level anchor gate: at least **3 evaluable anchors and 3 supportive anchors**.

### Pooled economic/risk gate
All must hold:
- N >= 160
- WR >= 55%
- net PnL > 0
- expectancy >= $0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

### Cross-era gate
Each of 2022 / 2023 / 2024 must have:
- N >= 40
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05

Additionally at least **2 of 3 years must have WR >= 55%**.

Candidate ranking is frozen to the existing E12 order: minimum yearly expectancy first, then anchor support, pooled expectancy, WR, PF, lower DD, lower loss streak, shorter hold, shorter lookback, deterministic rule name tie-break.

## B27 information boundary
B27 structural findings (K1 -> leave -> H2, 01:00 structural leader, 05:00 reference boundary, P10, H2/leave rates, etc.) are **not selection objectives and are not candidate-ranking variables in B28A**.

They may be used only **after** a B28 formal passer is found, as explanatory diagnostics for why a BNB-native economic character works. H2/leave can never substitute for WR, expectancy, PF, DD, loss streak, anchor stability, or cross-era stability.

## Anti-overfit rules
- No SHORT search inside B28A.
- No TP/SL tuning.
- No weekday filtering.
- No post-result threshold edits.
- No post-result lookback/hold expansion.
- No clock rescue inside the hour.
- No OOS exposure.
- No substitution of a higher-WR row that fails the full gate.

## Decision
If one or more candidates pass every frozen gate, select the top preregistered-ranked candidate and mark:
`BNB_ECONOMIC_FIRST_B28A_LONG_CHARACTER_FOUND`.

Otherwise mark:
`BNB_ECONOMIC_FIRST_B28A_NO_LONG_CHARACTER`, persist the strongest descriptive clues without promoting them, and move unchanged to 01:00–02:00 WIB.

Research/shadow only. No live promotion or profit guarantee.