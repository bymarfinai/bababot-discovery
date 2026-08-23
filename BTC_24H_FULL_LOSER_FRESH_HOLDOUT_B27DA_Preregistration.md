# B27DA — BTC 24H F05 SHORT Fresh Holdout Detector Confirmation — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Run the first genuinely fresh confirmation for the frozen B27CV/B27CX/B27CZ BAD-trade detectors on BTCUSDT data strictly after the historical research cutoff.

This experiment does **not** tune any detector, entry, TP, SL, clock, regime, model, feature, or threshold. No live BBC file is modified.

## Fresh holdout boundary
The historical loader used by the current lineage ends at **2026-08-21 00:00:00 UTC**. Therefore the fresh holdout begins exactly at:

`FRESH_START = 2026-08-21 00:00:00 UTC`

For this first run, use only fully archived BTCUSDT 5m daily files for **2026-08-21 and 2026-08-22**, so:

`FRESH_DATA_END = 2026-08-23 00:00:00 UTC` (exclusive)

Only observation blocks whose complete trade/outcome horizon is available are eligible. Because the frozen B27CS trade path may extend to `obs_end + 4h`, require:

`obs_end + 4h <= FRESH_DATA_END`.

The pre-2026-08-21 history may be used only as causal warm-up for previous-4H range, regime state, EMA state, and to reconstruct the already-frozen B27CV model. It is not part of the fresh evaluation labels.

The pre-existing `august` partition is **not** called fresh holdout because it has already been inspected by prior 24H research.

## Frozen source reconstruction
Reconstruct fresh F05 SHORT candidates directly from raw 5m candles using the frozen causal semantics already used by B27BE -> B27BZ -> B27CE -> B27CS:

1. Six sequential UTC 4H blocks: 00-04, 04-08, 08-12, 12-16, 16-20, 20-00.
2. Each observation block uses the immediately previous completed 4H H/L.
3. Causal 4H regime is the latest regime whose availability timestamp is <= observation start.
4. First Low visit K1 with OPP0.
5. Direct first strict completed close `< L` before a distinct Low #2.
6. First subsequent retest `high >= L`.
7. Keep only `RETEST_RECLAIMED`: retest completed close `> L`.
8. Reclaim completion must occur before block end.
9. Frozen executable SHORT entry is F05 = `L + 0.05*R4`, using exact B27CS BASE_H fill semantics and actual gap-open handling.
10. Frozen clock TP map from B27CR/B27CS:
   - 00-04 UTC -> T5
   - 04-08 -> T15
   - 08-12 -> T15
   - 12-16 -> T10
   - 16-20 -> T10
   - 20-00 -> T15.
11. Use exact B27CS BASE_H management/outcome semantics. No added pre-T5 stop.

Fresh labels remain frozen:
- `BAD` = eventual `FULL_SL_HIGH_BREAK`;
- `GOOD` = frozen clock target reached;
- `OTHER` = all other completed outcomes.

## Frozen detector models
Reconstruct the B27CV logistic models **only from the original historical development partition**, exactly as before. Mandatory parent reproduction before any fresh scoring:
- +10m AUC = 0.8452298452298452;
- +15m AUC = 0.8860088365243004;
- +10m SAFE threshold = 0.5898635948838399;
- +15m SAFE threshold = 0.6079191233470493.

No fresh candle, fresh feature, fresh label, or fresh score may enter model fitting or threshold selection.

## Frozen detector A — GLOBAL_PLUS15_SAFE
At +15m after fill, flag BAD when frozen B27CV +15 BAD probability >= 0.6079191233470493.

## Frozen detector B — PERSIST_10_15
Flag at +15m only when:
- +10m BAD probability >= 0.5898635948838399; AND
- +15m BAD probability >= 0.6079191233470493.

## Frozen detector C — REFINED_BULL_IMPULSE
Use exact B27CZ state machine:
- BOTH (+10 SAFE and +15 SAFE) -> flag;
- PLUS10_ONLY -> do not flag;
- PLUS15_ONLY -> flag only if `max_bull_body_r4 >= 0.28173076923076923`;
- NEITHER -> do not flag.

No threshold may be changed after fresh outcomes are observed.

## Required metrics
Show six 4H clocks independently first, then pooled fresh holdout.

For each detector and clock / pooled fresh scope report:
- fresh source blocks;
- reclaimed source events;
- F05 fills;
- BAD total;
- GOOD total;
- OTHER total;
- BAD flagged / BAD capture;
- GOOD flagged / GOOD sacrifice;
- precision among BAD+GOOD flagged.

Also report fresh event timestamps and labels in a persisted detail CSV for audit.

Trading WR/PF/expectancy/PnL for detector-driven aborts are **N/A** in B27DA. This is confirmation anatomy only.

## Readiness gate
Fresh detector confirmation is statistically **not ready** unless the pooled fresh holdout contains at least:
- 10 BAD trades; and
- 30 GOOD trades.

If either count is smaller, frozen status must be:

`B27DA_FRESH_HOLDOUT_INSUFFICIENT`

and no detector may be promoted or rejected from this holdout.

## Stability diagnostics if readiness is met
Historical reused benchmarks are frozen only for comparison, never calibration:
- GLOBAL_PLUS15_SAFE reused: BAD capture 42.5%, GOOD sacrifice 15.3%, precision 37.0%.
- PERSIST_10_15 reused: BAD capture 27.5%, GOOD sacrifice 10.6%, precision 35.5%.
- REFINED_BULL_IMPULSE reused: BAD capture 35.0%, GOOD sacrifice 10.6%, precision 41.2%.

If readiness is met, report for each detector whether fresh metrics remain directionally compatible with its benchmark. No new best-detector selection or live promotion is authorized by B27DA alone.

## Mandatory assertions
1. Historical old loader still reproduces 698,112 rows ending before 2026-08-21 UTC.
2. Fresh raw rows contain no timestamp before FRESH_START or at/after FRESH_DATA_END.
3. Fresh raw 5m rows are complete and continuous for the two archived UTC days.
4. Every fresh observation starts >= FRESH_START.
5. Every evaluated trade has `obs_end + 4h <= FRESH_DATA_END`.
6. Previous-4H range and regime availability are causal.
7. Historical B27CV parent AUCs and thresholds reproduce before fresh scoring.
8. No fresh row enters model fit or threshold selection.
9. No live BBC file or live rule is modified.

Research only.