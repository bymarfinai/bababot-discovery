# BNB B38-S6R — Historical Reference Character Test

**Scientific identity:** `BNB_B38_S6R_HISTORICAL_REFERENCE_V1`

## Purpose

Directly test whether the frozen B38 structural character and B38-S5 adaptive policy remain present in later historical data already available in the repository.

This is a **historical reference test**, not a clean OOS claim.

## Frozen character

`H1 bullish BOS -> causal H1 demand -> 15m expansion/new high -> corrective return -> first demand interaction -> reclaim state -> adaptive execution`

No structure, entry, SL or TP rule may change.

## Period

Reference:
- first-touch / execution events from **2025-01-01** through the final complete bar in the frozen B31 dataset (2026-08).

Development comparator:
- 2022-01-01 through 2024-12-31.

## Structural persistence diagnostics

For reference events report:
- parent visual-family N;
- event frequency by year;
- A/B/C/D first-touch archetype census;
- full-reclaim share = A + C;
- in-zone share = B + D;
- +1ZW, +2ZW, and full-continuation rates by archetype;
- MFE distribution by archetype.

These use the exact frozen B38-S1/B38-S2 definitions.

## Frozen adaptive policy

Exact B38-S5 mapping:
- IMMEDIATE_CLEAN_RECLAIM -> TP1
- IMMEDIATE_SWEEP_RECLAIM -> TP1
- DELAYED_CLEAN_RECLAIM -> TP1
- DELAYED_SWEEP_RECLAIM -> TP2
- missing required target -> NO_POLICY_TARGET

Entry and structural SL remain exactly B38-S3.

## Scoring

Resolve selected structural TP vs structural SL using exact 5m bars strictly after entry close.

Report:
- entry count;
- target-available count;
- W/L;
- hit rate;
- expectancy R;
- total R;
- profit factor;
- max loss streak;
- max cumulative-R drawdown;
- by execution mode;
- by 2025 and 2026*.

## Comparison

Compare later-reference character statistics with 2022-2024 development statistics descriptively.

No threshold, filter, mode, target, or entry rule may be altered from the reference result.

## Stop rule

Do not:
- call this clean OOS;
- optimize on 2025-2026;
- add filters;
- change target assignment;
- change SL;
- drop weak modes;
- add time/session/indicator/derivatives gates.
