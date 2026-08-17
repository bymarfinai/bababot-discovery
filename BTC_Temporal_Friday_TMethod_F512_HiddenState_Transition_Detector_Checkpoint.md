# BTC Friday15 T-Method — F5.12 Hidden-State Transition Detector

**Date:** 2026-08-17 WIB  
**Status:** F5.12 PASS — CAUSAL REVERSAL WARNING FOUND; NO SHORT RULE YET  
**Live BBC:** untouched

## Objective

F5.11 found a stable hidden-state transition before future-good Friday15 BUY->SHORT reversal opportunities. F5.12 tests whether that mechanism can emit a causal first-fire `REVERSAL_WARNING` before a materially better future reversal window.

No SHORT is opened in this milestone. No TP/SL is optimized.

## Data / causality

- Friday15 BUY parent lineage unchanged.
- 136 Friday occurrences have usable futures metrics.
- 60/40 chronological split; validation is report-only.
- All metrics snapshots and EMA values are strictly available before the decision open.
- OI is context only and never a gate.
- Only natural zero-crossings were used; no threshold sweep.

Six compact architectures were tested:
1. `RELATIVE_ONLY`
2. `ACCOUNT_DECAY`
3. `DECAY_EMA`
4. `HIDDEN_CORE`
5. `HIDDEN_CORE_EMA`
6. `TWO_OF_THREE`

## Selected discovery architecture

`HIDDEN_CORE_EMA`

At a causal 5m decision open, warning requires:

1. `top_vs_global <= 0`
   - top-trader position L/S is no longer elevated versus global-account L/S;
2. `top_account_chg_15 < 0` AND `global_account_chg_15 < 0`
   - both top-trader and global account long/short ratios are deteriorating over the prior 15 minutes;
3. `ema_spread_chg15 < 0`
   - completed-bar EMA7/EMA20 bullish spread is contracting over the prior 15 minutes.

This is a warning state only, not an order instruction.

## Baseline future-good reversal probability

At the first eligible +15m decision point:

### Discovery
- GOOD_REVERSE within 15m: 23.5%
- within 30m: 24.7%
- within 60m: 30.9%
- within 120m: 39.5%

### Validation
- within 15m: 41.8%
- within 30m: 43.6%
- within 60m: 47.3%
- within 120m: 58.2%

## HIDDEN_CORE_EMA results

### Discovery
- entries: 81
- warnings: 26 (32.1%)
- median warning time: +40m
- parent-loss rate among warned occurrences: 50.0%
- parent-SL rate: 34.6%
- parent-TP warning rate: 19.2%

Future GOOD_REVERSE after warning:
- 15m: 30.8% — **1.311x baseline**
- 30m: 30.8% — **1.247x**
- 60m: 38.5% — **1.246x**
- 120m: 38.5% — 0.975x

Forward price path from warning:
- median 15m return: +0.0106%
- median 30m return: +0.0307%
- median 60m return: **+0.1734%**
- median 120m return: -0.0180%

This is important: the warning improves reversal probability, but the market can still continue upward after the warning. Therefore F5.12 is NOT an immediate-short signal.

### Validation
- entries: 55
- warnings: 28 (50.9%)
- median warning time: +37.5m
- parent-loss rate: 64.3%
- parent-SL rate: 53.6%
- parent-TP warning rate: 14.3%

Future GOOD_REVERSE after warning:
- 15m: 50.0% — **1.196x baseline**
- 30m: 53.6% — **1.229x**
- 60m: 60.7% — **1.283x**
- 120m: 67.9% — **1.167x**

Forward price path:
- median 15m return: -0.0068%
- median 30m return: -0.0372%
- median 60m return: -0.0565%
- median 120m return: -0.1167%

### Full
- warnings: 54 / 136 = 39.7%
- median warning time: +40m
- parent-loss rate: 57.4%
- parent-SL rate: 44.4%
- parent-TP warning rate: 16.7%

Future GOOD_REVERSE:
- 15m: 40.7% — **1.317x baseline**
- 30m: 42.6% — **1.315x**
- 60m: 50.0% — **1.333x**
- 120m: 53.7% — **1.140x**

## What EMA adds

This milestone gives a clean answer to the EMA question.

`HIDDEN_CORE` without EMA fires on essentially the same occurrences but much earlier:
- discovery median warning +17.5m
- validation median +15m

However its discovery 60m GOOD_REVERSE lift is only **0.997x** baseline, so it does not yet identify a better reversal window in discovery.

Adding EMA-spread contraction delays the warning to about +40m and changes discovery 60m lift to **1.246x**, while validation remains strong at **1.283x**.

Therefore EMA is useful here as a **timing/confirmation layer**. It is not the primary hidden-state trigger and it is not supported as a standalone reversal detector.

## Other architectures

- `RELATIVE_ONLY` is useful but weaker at 60m in discovery: 1.078x; validation 1.268x.
- `ACCOUNT_DECAY` is too common (92.6% of all occurrences) and has ~1.0x lift; rejected as non-discriminative.
- `DECAY_EMA` also fires too often and gives only 1.136x/1.015x 60m lift.
- `TWO_OF_THREE` fires on ~95% of occurrences and is non-discriminative.

The conjunction matters; individual ingredients alone are insufficient.

## Scientific verdict

F5.12 passes the predeclared cross-period gate:
- discovery warnings >=8 and validation >=5;
- 60m GOOD_REVERSE lift >1.15 discovery and >1.10 validation;
- parent-TP warning rate <45% in both periods.

The evidence supports a causal state transition:

> relative positioning weakens + account long-bias deteriorates + EMA bullish spread contracts -> probability of a useful reversal window increases.

But F5.12 does **not** justify immediate SHORT entry, because especially in discovery the price can continue upward after warning. The warning is an early state signal, not the execution point.

## Allowed next milestone

**F5.13 — Post-Warning Confirmation Timing**

Freeze the F5.12 `HIDDEN_CORE_EMA` warning. Do not retune its thresholds.

F5.13 should determine what causal event after the warning identifies the actual transition from warning to executable reversal, comparing fixed delays and a compact set of confirmation families. It should explicitly test whether waiting improves SHORT economics versus immediate reversal and versus EXIT-only.

No additional hidden-state feature mining is justified before F5.13.

**Live BBC remains untouched.**
