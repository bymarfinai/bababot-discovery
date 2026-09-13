# BNB R4d — H22 Hold-Duration Sweep Preregistration

## Purpose
Convert the already-frozen BNB R4c H22 execution policy into a deployment-duration decision without changing the entry logic. This is an execution optimization diagnostic, not a new discovery search and not fresh OOS validation.

## Frozen entry policy
- Pair: BNBUSDT
- Direction: LONG only
- Habitat: H22 WIB
- Anchors: 22:00 / 22:15 / 22:30 / 22:45 WIB (15:00 / 15:15 / 15:30 / 15:45 UTC)
- Character: `RV_HIGH__RANGE_MID`
- Voters: LB180 / LB240 / LB360
- Entry: minimum 2-of-3 active voters
- Anchor selection: earliest qualifying H22 anchor
- Position rule: maximum one position per WIB day; no pyramiding
- Signal universe: inherited weekday-only R4b/R4c universe
- Notional: $500 fixed
- Fee: $0.75/trade
- No TP/SL search
- No consensus-threshold search
- No coordinate search
- No weekday/weekend search
- No rule/feature search

## Only variable opened
Hold duration only:
- H360 = 6h
- H480 = 8h
- H720 = 12h
- H960 = 16h

The same entry policy must be replayed for every hold. No hold may receive bespoke entry filtering.

## Evaluation window
2022-01-01 through 2025-12-31 only. 2025 has already been observed in prior R4b/R4c work, so this is explicitly labeled execution-synthesis/optimization, not fresh OOS. **2026 remains hard-closed and must not be loaded into feature construction or scoring.**

## Cost stress
For every hold, score 0 / 2 / 5 / 10 bps slippage per side in addition to the frozen $0.75 fee.

## Gates
At 0 bps, each annual slice (2022, 2023, 2024, 2025) passes if:
- N >= 24
- WR >= 52%
- Net > 0
- Expectancy > 0
- PF >= 1.15
- Max DD <= $160

Pooled 2022-2025 gate at 0 bps:
- N >= 96
- WR >= 55%
- Net > 0
- Expectancy >= $0.50/trade
- PF >= 1.25
- Max DD <= $160

2 bps/side stress gate:
- pooled Net > 0
- pooled Expectancy > 0
- pooled PF >= 1.15
- at least 3/4 individual years Net-positive

Loss streak is diagnostic only.

## Pre-registered hold ranking
Holds are ranked lexicographically by:
1. annual 0-bps gates passed (higher better)
2. pooled 0-bps gate pass
3. 2-bps stress gate pass
4. minimum annual 0-bps expectancy (higher better)
5. pooled 0-bps expectancy (higher better)
6. pooled 0-bps PF (higher better)
7. pooled 0-bps max DD (lower better)
8. shorter hold as final tie-breaker

A hold is `FORMALLY_SUPPORTED` only if all 4 annual gates + pooled gate + 2-bps stress gate pass. If none is formally supported, the ranking may identify a `BEST_EXECUTION_CANDIDATE_NOT_FORMALLY_SUPPORTED`, but this must not be relabeled as a formal pass.

## Required outputs
- One true de-duplicated ledger per hold
- Per-year and pooled metrics per hold at each slippage level
- Gate audit
- Ranked hold comparison
- Selected formal hold if one exists, otherwise best non-formal candidate

Research/shadow only. 2026 remains closed.