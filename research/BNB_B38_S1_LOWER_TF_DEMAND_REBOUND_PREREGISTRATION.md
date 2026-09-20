# BNB B38-S1 — Lower-TF Demand Structural Rebound Study Preregistration

**Scientific identity:** `BNB_B38_S1_LOWER_TF_DEMAND_REBOUND_V1`

## Motivation

B37 used H4 demand with H1 structure and defined structural success as a full continuation close back above the frozen pre-retest expansion high before demand invalidation.

That outcome is intentionally strict. A setup can produce a meaningful tradable rebound and still be labelled a B37 structural LOSS if it later fails to reclaim the entire expansion high.

B38 asks two new questions without altering B37:

1. Does BNB express the same structural family more naturally from **lower-timeframe demand**?
2. How often do apparent full-continuation failures still produce a meaningful rebound before demand invalidation?

## Development period

- 2022-01-01 through 2024-12-31 only.
- 2025-2026 is **not used for confirmation or validation in B38-S1**.
- This is an exploratory structural study, not an OOS claim.

## Two frozen timeframe configurations

### D1 — H1 demand / 15m execution
- demand timeframe: exact H1
- execution / expansion / retest timeframe: exact 15m

### D2 — 15m demand / 5m execution
- demand timeframe: exact 15m
- execution / expansion / retest timeframe: exact 5m

This preserves the original multi-timeframe 4:1 relationship used by H4-demand/H1-execution.

## Demand construction

For either demand timeframe:

1. strict swing high = 2 bars left + 2 bars right;
2. swing becomes usable only after the second right bar closes;
3. prior demand-TF close <= latest confirmed swing high;
4. current demand-TF close > that swing high = bullish BOS;
5. origin = latest bearish demand-TF candle among the six completed bars before BOS;
6. demand zone = origin low to origin open;
7. one demand zone per broken swing high.

No ATR, percentage, indicator, volume, session, derivative or learned threshold is used.

## Visual family on the execution timeframe

After demand activation:

1. wait for a strict execution-TF pivot high confirmed causally;
2. pivot high must exceed max(demand-TF broken swing level, demand-TF BOS close);
3. keep the latest eligible confirmed pivot before first demand touch;
4. first execution-TF overlap with demand is the retest;
5. parent visual-equivalent requires:
   - confirmed expansion exists strictly before retest;
   - retest close >= demand_low;
   - >=2 completed execution bars after expansion pivot and before retest;
   - path contains a lower-high observation OR lower-low observation.

This is the same visual story as B37, only moved down in timeframe.

## Outcome decomposition

Outcome begins strictly after the retest bar.

Demand invalidation:
- first execution-TF close < demand_low.

Four descriptive reaction levels are recorded before invalidation/end of 2024:

### R1 — REACTION
At least one later execution-TF close > retest_high before invalidation.

### R2 — REBOUND_1ZW
At least one later execution-TF close > demand_high + 1 * demand_width before invalidation.

### R3 — REBOUND_2ZW
At least one later execution-TF close > demand_high + 2 * demand_width before invalidation.

### R4 — FULL_CONTINUATION
At least one later execution-TF close > frozen pre-retest expansion_high before invalidation.

Also persist maximum favorable close excursion above demand_high in demand-zone-width units before invalidation:
`MFE_ZW = (max_close_before_invalidation - demand_high) / demand_width`.

These are descriptive structural outcomes, not TP/SL rules.

## Key diagnostic

For events that fail R4 FULL_CONTINUATION, report:
- share still reaching R1;
- share still reaching R2;
- share still reaching R3;
- MFE_ZW distribution.

This directly tests whether the B37 full-continuation label was too strict for the practical question of rebound quality.

## Outputs

For D1 and D2:
- demand-zone census;
- visual-family event ledger;
- yearly frequency;
- R1/R2/R3/R4 rates;
- full-continuation-failure rebound decomposition;
- MFE_ZW distribution;
- result summary.

## Stop rule

Do not optimize any detector or target threshold in B38-S1. The 1ZW and 2ZW levels are native demand-zone geometry, not fitted values.
