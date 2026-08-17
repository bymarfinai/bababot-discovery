# BTC Temporal Saturday T-Method S5.2B — Selective RUNNER vs PROTECT

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — BOTH PREDECLARED PROTECT POLICIES REJECTED  
**Research only:** live BBC untouched  
**Frozen controls preserved:** A7.19 full coverage; A7.26 selective benchmark.

## Frozen controls

Parent — Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h:
- 139 trades
- WR **46.76%**
- PnL **+$87.200**

A7.19 full-coverage champion:
- 139 trades
- WR **50.36%**
- PnL **+$103.383**
- discovery **+$66.588**
- validation **+$36.795**

A7.26 selective benchmark:
- 123 trades
- PnL **+$109.587**

Frozen hinge parity:
- +0.50 hinge: **89**
- eventual +0.80 deep runner: **61**

## Predeclared S5.2B policies

No threshold sweep was performed.

### FLOW_EMA_PROTECT
After a causal +0.50 hinge, and only before any completed-bar +0.80 graduation:
- completed close progress <= +0.30%
- cumulative post-hinge taker edge < 0
- next decision-open < completed-bar EMA20
- then arm +0.20% profit lock at that exact causal next-open
- if +0.20 is already lost at decision-open, exit actual open
- if lock/TP never triggers before frozen A7.19 exit, preserve A7.19 exactly.

### ADAPTIVE_MEMORY_PROTECT
Same rule, except a trade with prior frozen FAILURE before +0.50 must also have hinge cumulative taker <= 0 before it is eligible. CLEAN trades use the generic FLOW/EMA event directly.

## Main results vs exact A7.19

| Policy | Actions D/V | WR | PnL | Delta | Disc delta | Val delta | Improved / Damaged | Neg→Pos / Pos→Neg | Future-deep actions / damaged | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ADAPTIVE_MEMORY_PROTECT | 21 / 13 | **51.08%** | **+$60.694** | **-$42.689** | **-$28.033** | **-$14.656** | 11 / 21 | 7 / 6 | 17 / 14 | FAIL |
| FLOW_EMA_PROTECT | 28 / 15 | **52.52%** | **+$51.035** | **-$52.348** | **-$39.585** | **-$12.763** | 14 / 25 | 9 / 6 | 19 / 15 | FAIL |

Both policies have adequate action counts in both chronological halves, but both fail because discovery and validation deltas are negative.

## Why the rules fail

### FLOW_EMA_PROTECT
- 43 actions
- A7.19 PnL on those action trades: **+$63.586**
- protected PnL on the same trades: **+$11.238**
- delta **-$52.348**
- 19 actions occurred on trades that would later become +0.80 deep runners
- those future-deep actions alone contribute about **-$81.57** delta
- non-deep actions contribute about **+$29.22** delta

Thus the event *does* rescue failed/non-deep runners, but it cannot distinguish them from temporarily damaged future-deep runners.

Execution outcomes among FLOW_EMA actions:
- LOCK: 24
- actual-open exit because +0.20 was already lost: 15
- A7.19 fallback: 4
- median event time about +250m after entry.

### ADAPTIVE_MEMORY_PROTECT
- 34 actions
- delta **-$42.689**
- 17 actions on eventual deep runners; 14 of those are economically damaged
- future-deep delta about **-$69.57**
- non-deep delta about **+$26.88**
- median event time about +222.5m.

Prior FAILURE memory reduces the number of actions but does not solve the false-positive deep-runner problem.

## Core interpretation

S5.2B confirms an important Saturday-native property:

> A trade can causally reach +0.50, give back to <=+0.30, show negative post-hinge taker flow, trade below EMA20, and still later become a valuable +0.80+ deep runner.

Therefore `deterioration -> immediate profit lock` remains too aggressive even when deterioration is much more selective than the old C1 fast-giveback rule.

This mirrors the earlier Saturday lesson at a later phase: classifier quality and management timing are not the same problem.

The +0.80 guard only protects runners that have **already** graduated. It cannot protect latent deep runners that temporarily deteriorate *before* graduation. Those latent runners are the dominant source of economic damage in S5.2B.

## S5.2B verdict

**REJECT both predeclared policies.**

Do not tune on this same sample:
- +0.30 giveback boundary
- +0.20 lock
- taker sign boundary
- EMA20 condition
- prior-FAILURE hinge-taker modifier.

A7.19 remains the frozen full-coverage champion at **+$103.383 / WR 50.36%**. A7.26 remains preserved separately at **+$109.587 / 123 trades**.

## Correct continuation

The next useful research question is **false-positive runner recovery**, not another protection threshold sweep.

Forensic next step should compare S5.2B protect events that later become deep runners against events that remain failed/non-deep using only information available at and after the protect event. Candidate concepts include:
- whether deterioration persists versus rapidly reclaims,
- EMA7/EMA20 rejection/reclaim sequence after the event,
- post-event flow re-acceleration,
- duration since +0.50 hinge and prior maximum excursion,
- whether a latent runner can be recognized before the +0.20 lock is actually touched.

This is conceptually analogous to Tuesday Runner Recovery: arm protection on a credible failure event, but cancel/restore the runner if causal evidence shows the giveback was a fake failure. No recovery rule is promoted by S5.2B itself.
