# BTC Temporal Saturday T-Method S5.2C — False Failure / Runner Recovery Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — RECOVERY IS CAUSALLY VISIBLE, BUT COVERAGE IS TOO LOW TO RESCUE S5.2B  
**Research only:** live BBC untouched  
**No cancel-protect action promoted.**

## Frozen S5.2B parity

FLOW_EMA_PROTECT warning cohort reproduced exactly:
- 43 warnings = 28 discovery / 15 validation
- 19 warnings later become DEEP runners >= +0.80%
- 24 remain nondeep
- 15 future-deep runners are damaged by protection
- protection contribution on nondeep trades: **+$29.222**
- protection contribution on future-deep trades: **-$81.569**

This reproduces the S5.2B failure mechanism: protection does rescue failed runners, but latent runners cost much more than the rescue benefit.

## Causal recovery-window integrity

Recovery evidence is counted only if it becomes knowable **before** the frozen +0.20% lock would close the trade.

- 15/43 warnings are dead-on-arrival: the +0.20% lock has already been lost at the warning decision-open.
- 4/19 future-deep warnings are dead-on-arrival.
- if a 5m bar touches the lock, recovery information from that bar close is excluded (adverse-first execution).

Therefore no hindsight recovery after the theoretical protection exit is credited.

## Predeclared recovery signals

| Signal | N D/V | Future-deep precision | Deep capture | D deep capture | V deep capture | Damaged-deep recoverable | Improved-nondeep at risk | Median after warning |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| REBUILD_030 | 11 8/3 | 63.64% | 36.84% | 42.86% | 20.00% | **5** | **1** | 10.0m |
| CUM_TAKER_POS | 12 9/3 | 58.33% | 36.84% | 42.86% | 20.00% | **5** | 2 | 7.5m |
| EMA7_RECLAIM | 10 7/3 | 60.00% | 31.58% | 35.71% | 20.00% | 4 | **1** | 12.5m |
| TWO_CLOSES_ABOVE_EMA7 | 10 7/3 | 60.00% | 31.58% | 35.71% | 20.00% | 4 | **1** | 20.0m |
| EMA7_AND_TAKER15 | 10 7/3 | 60.00% | 31.58% | 35.71% | 20.00% | 4 | **1** | 17.5m |
| REBUILD030_AND_EMA7 | 10 7/3 | 60.00% | 31.58% | 35.71% | 20.00% | 4 | **1** | 12.5m |
| TAKER15_POS | 11 7/4 | 54.55% | 31.58% | 35.71% | 20.00% | 4 | 2 | 15.0m |
| EMA20_RECLAIM | 12 9/3 | 50.00% | 31.58% | 35.71% | 20.00% | 4 | 2 | 10.0m |
| EMA20_RISING_RECLAIM | 12 9/3 | 50.00% | 31.58% | 35.71% | 20.00% | 4 | 2 | 10.0m |
| REBUILD040_AND_TAKER15 | 6 5/1 | 66.67% | 21.05% | 28.57% | **0.00%** | 2 | 0 | 22.5m |
| REBUILD_040 | 7 6/1 | 57.14% | 21.05% | 28.57% | **0.00%** | 2 | 0 | 20.0m |
| DEEP_080 | 3 3/0 | 100% | 15.79% | 21.43% | **0.00%** | 1 | 0 | 45.0m |

## What matters

The best broad causal recovery clues are:

1. **REBUILD_030**
   - catches 5/15 damaged future-deep runners before protection exits
   - only one nondeep trade that protection genuinely improved would be put at risk
   - median recovery appears 10m after warning

2. **CUM_TAKER_POS**
   - also catches 5/15 damaged deep runners
   - but puts two improved nondeep trades at risk

3. EMA7-based recovery family
   - catches 4/15 damaged deep runners
   - usually only one improved nondeep trade at risk

However transferability is weak:
- the best signals recover 4 damaged deep cases in discovery but only **1** in validation
- +0.40 rebuild and actual +0.80 re-graduation have **zero validation deep capture** before lock

## Critical conclusion

S5.2C confirms that fake deterioration exists and can sometimes be recognized causally before a profit lock executes. However this is **not enough to repair S5.2B**.

The problem is structural:
- protection creates +$29.22 of value on nondeep trades,
- but destroys -$81.57 on future-deep trades,
- the strongest natural recovery signal can intercept only 5 of the 15 damaged latent runners,
- and only one of those five occurs in validation.

Therefore do **not** tune EMA7/EMA20, taker windows, rebuild percentages, or cancel timing on this same sample to force a runner-recovery rule.

## S5.2 branch verdict

**Selective protection after +0.50 remains rejected as a Saturday upgrade.**

Useful truths to preserve:
- +0.50 favorable impulse is still a major quality hinge.
- deep runners are extremely valuable and can look badly deteriorated before eventual continuation.
- early FAILURE, post-hinge giveback, negative flow, and EMA weakness are all useful diagnostics but individually insufficient as exit/protect triggers.
- causal runner recovery exists but is too sparse/chronologically weak to offset protection damage.

## Correct continuation

Do not run a S5.2D cancel-protect optimization on this sample.

Return to the frozen T-Method roadmap and proceed to **S5.4 — EMA failure-state forensic** (S5.3 robustness is unnecessary because S5.2B did not produce a candidate worth stress-testing).

The S5.4 objective is diagnostic, not a new global EMA exit: determine whether EMA behaviour can identify a *specific failure/mean-reversion state* around runner deterioration without mechanically clipping the Saturday runner population.
