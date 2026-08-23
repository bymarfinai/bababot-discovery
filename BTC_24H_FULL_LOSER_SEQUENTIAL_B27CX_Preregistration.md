# B27CX — BTC 24H F05 SHORT Sequential Full-Loser Persistence — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether requiring the existing B27CV BAD classifier to remain elevated from +10m through +15m after F05 fill reduces false-positive GOOD cuts while preserving useful capture of catastrophic `FULL_SL_HIGH_BREAK` trades.

This is **classifier/anatomy research only**. No entry, TP, SL, runner, model family, feature, clock/regime exclusion, or live rule is changed. Trading WR/PF/expectancy/PnL from a hypothetical abort are N/A.

External and reference_validation are reused lineage data, not untouched OOS.

## Frozen source/model identity
Reproduce B27CV exactly from `BTC_24H_CLOCK_TP_SL_B27CS_SelectedTrades.csv` and `research/btc_24h_full_loser_separability_b27cv.py`.

Required identity:
- executable F05 trades: external 183 / development 297 / reference_validation 172 / pooled major 652;
- BAD `FULL_SL_HIGH_BREAK`: pooled 78;
- GOOD frozen clock-target reached: pooled 348;
- OTHER: pooled 226;
- B27CV +10m development AUC: 0.8452298452298452;
- B27CV +15m development AUC: 0.8860088365243004.

Frozen global thresholds from B27CV:
- +10m SAFE = 0.5898635948838399;
- +15m SAFE = 0.6079191233470493;
- +10m AGGRESSIVE = 0.5494693389519317;
- +15m AGGRESSIVE = 0.4101988544354365.

Probability comparison is inclusive with numerical tolerance 1e-12 to reproduce boundary cases.

## Primary sequential rule
`SAFE_PERSIST_10_15` flags a trade for hypothetical abort at +15m only if:
1. the trade is BAD/GOOD-model-eligible and alive at +10m;
2. its B27CV +10m BAD probability >= frozen +10m SAFE threshold;
3. it remains BAD/GOOD-model-eligible and alive at +15m;
4. its B27CV +15m BAD probability >= frozen +15m SAFE threshold.

A trade that resolves before +15m is not abortable at +15m. GOOD target exits before +15m are safely resolved and cannot become false cuts. BAD High-break exits before or at +15m are counted as too-late misses.

No threshold is recalibrated by clock, regime, external, or validation.

## Frozen comparators
Report against:
- `PLUS15_SAFE`: ordinary B27CV global +15m SAFE flag;
- `PLUS10_SAFE`: ordinary B27CV global +10m SAFE flag;
- `SAFE_PERSIST_10_15`: primary sequential rule.

Secondary descriptive-only rule:
- `AGG_PERSIST_10_15`: +10m AGGRESSIVE AND +15m AGGRESSIVE.

The secondary rule cannot determine the overall PASS verdict.

## Required metrics
For each partition and pooled reused/major, report:
- BAD total;
- BAD too-late by +15m;
- BAD sequentially flagged;
- BAD capture / all BAD;
- GOOD total;
- GOOD safely resolved before +15m;
- GOOD sequentially flagged;
- GOOD sacrifice / all GOOD;
- precision among BAD+GOOD flags;
- number flagged.

Report the six 4H clocks independently for `SAFE_PERSIST_10_15` first, then pooled aggregates, then regime splits secondarily. No clock/regime deletion.

Also report transition counts among trades alive at +15m:
- SAFE at +10 only;
- SAFE at +15 only;
- SAFE at both;
- SAFE at neither;
separately for BAD and GOOD.

## Frozen support gate
`B27CX_SEQUENTIAL_PERSISTENCE_REUSED_CANDIDATE` requires audit PASS and all of:
1. development `SAFE_PERSIST_10_15` GOOD sacrifice <= development PLUS15_SAFE GOOD sacrifice;
2. development BAD capture >= 60% of development PLUS15_SAFE BAD capture;
3. external GOOD sacrifice <= external PLUS15_SAFE GOOD sacrifice;
4. validation GOOD sacrifice <= validation PLUS15_SAFE GOOD sacrifice;
5. pooled reused GOOD sacrifice improves by at least 3 percentage points versus PLUS15_SAFE;
6. pooled reused BAD capture retains at least 70% of PLUS15_SAFE BAD capture;
7. pooled major flag precision > PLUS15_SAFE flag precision.

Otherwise verdict: `B27CX_SEQUENTIAL_PERSISTENCE_NOT_SUPPORTED`.

Even a candidate PASS is reused-data anatomy evidence only. A separate preregistered causal economic abort simulation is required before interpreting WR/PF/expectancy/PnL or changing live BBC.

<!-- no-semantic workflow trigger -->
