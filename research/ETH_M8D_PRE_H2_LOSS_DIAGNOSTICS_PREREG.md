# ETH M8D — Pre-H2 Loss Diagnostics (Preregistered)

## Purpose
Diagnose why high H2 reach does not translate into positive economics. This milestone does **not** optimize or promote a new rule.

## Frozen upstream
- M5 entries: ALT F95, RAW0530 F90, LONDON F90, RAW2330 F95.
- M6 hard/close pre-H2 protection candidates unchanged.
- No post-H2 exit optimization in this milestone.

## Questions
For each habitat × M6 protection candidate, split entries into:
1. H2 reached before protection/time exit.
2. Pre-H2 hard stop / close invalidation.
3. No-H2 session time exit.

Measure, without selecting thresholds:
- count/rate by major partition;
- pre-H2 MAE in R units;
- maximum favorable excursion toward H in R units;
- peak recovery fraction of the entry→H gap before failure;
- time from entry to exit/H2;
- for failures, whether price first recovered to F97.5 / F99 / H before eventual failure (descriptive landmarks only, not candidate rules);
- economic loss contribution under the frozen M6 protection;
- loss concentration (worst 10% and 20% of losing trades as share of gross losses).

## Diagnostic comparison
Compare H2 winners vs pre-H2 failures using distribution summaries (median/P75/P90 MAE, MFE/recovery, time). Report only separation that is visible across all three major partitions. August remains telemetry.

## Guardrails
- No new entry level.
- No new stop level.
- No TP/exit mechanism search.
- No threshold is promoted from M8D.
- Any apparent early-failure feature must be preregistered and tested in a later milestone on a new lineage.

## Completion
M8D completes when the diagnostic tables are reproducible from raw ETH 5m data and identify where gross loss is concentrated. Status: `ETH_M8D_PRE_H2_LOSS_DIAGNOSTICS_COMPLETED`.