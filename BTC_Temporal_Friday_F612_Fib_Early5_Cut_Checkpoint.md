# BTC Temporal Friday F6.12 — Causal Fib Context +5m Early Cut

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — **SAME-SAMPLE ECONOMIC PASS; PROVISIONAL**  
**Research only:** live BBC untouched.

## Frozen test rule
At +5m, exit the Friday BUY at the actual +5m open only when all are true:
1. first completed 5m candle closed below entry;
2. position is still alive at +5m;
3. pre-entry 2h retracement depth from the 2h high is <= **38.2%**;
4. pre-entry 2h range is greater than its causal rolling prior-24h median 2h range.

All Fib/swing information uses completed bars strictly before entry. No threshold sweep was performed in F6.12.

## Result
Parent: 138 trades, 66W/72L, WR 47.83%, PnL **+$64.630**, PF **1.266**, max DD **$56.530**.

With F6.12 +5m cut:
- actions: **9**
- parent winners cut: **0**
- parent losers cut: **9**
- positive/negative action deltas: **8 / 1**
- PnL: **+$85.229**
- improvement: **+$20.598**
- Discovery delta: **+$2.215**
- Validation delta: **+$18.383**
- PF: **1.384**
- max DD: **$47.508**
- DD improvement: **$9.022**

## Sink/recovery behavior
- strict immediate sinks in parent sample: **10**
- strict sinks caught by F6.12: **4/10 = 40%**
- first5-red recover/non-strict-sink cohort: **48**
- F6.12 actions within that cohort: **5**

Crucially, all five of those non-strict-sink actions were still eventual **parent losers**, not winners. So the rule did not merely identify `never-reclaim` paths; it also found recover-to-entry trades that later failed anyway.

Action cohort parent PnL was **-$34.418** and becomes **-$13.819** with +5m exits.

## Robustness notes
- jackknife: removing any single action leaves aggregate improvement positive; remaining delta range **+$17.237 to +$21.378**.
- all four chronological action-bearing broad blocks are positive.
- Discovery has only **1 action**, so same-sample D/V positivity is encouraging but Discovery support is thin.

## Interpretation
F6.11's Fib clue is economically useful when expressed as a causal context state:

> **local 2h expansion is elevated + BUY enters after only a shallow <=38.2% retracement + first 5m immediately loses acceptance -> cut earlier at +5m.**

This is stronger than using `first5 red` alone and earlier than F6.9's +10m failed-acceptance detector.

## Guardrail
The Fib context itself was motivated by F6.11 inspection of this same 971-day sample. Therefore F6.12 is **not independent OOS confirmation** and must remain provisional. Do not retune the 38.2% level, baseline horizon, or +5m timing on this sample.

## Execution
- workflow run: **32042790879** — success
- artifact: `f612-output`, ID **9292261857**
- script: `research/f612_friday_fib_early5_cut.py`
- workflow commit: `c8046fcfa1332931f1dfc6c0382009d465864e76`
- live BBC untouched.
