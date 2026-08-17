# BTC Temporal Friday F6.14 — Remaining Loss Anatomy Checkpoint

**Status:** COMPLETE — FORENSIC ONLY; NO RULE TUNING  
**Research only; live BBC untouched.**

## Frozen stack preserved
Priority remains unchanged:
1. F6.12 FIB5 +5m
2. F6.9 EARLY10
3. F6.5 +60 true-failure upper-wick cut

Parent Friday15 BUY benchmark: 138 trades, 66W/72L, PnL +$64.630405.  
Three-layer managed PnL: +$105.818200. WR remains unchanged because loss cuts remain negative trades.

## Loss coverage
- Original parent losses: **72**
- Intercepted by frozen/provisional three-layer stack: **23**
- Still untouched by all three layers: **49**
- Untouched parent exits: **32 SL / 17 TIMEOUT**

## Untouched loss anatomy
Natural risk R = 0.70%.

| Archetype | Count | Meaning |
|---|---:|---|
| A_IMMEDIATE_SINK | 1 | first 5m red and never trades back to entry |
| B_NEVER_GOT_0.5R | 23 | never reaches +0.35% favorable excursion |
| C_PARTIAL_LT_1R | 12 | reaches +0.5R but never +1R |
| D_GOOD_START_GIVEBACK_1_2R | 13 | reaches +1R but never +2R, then loses |
| E_RUNNER_GIVEBACK_2_2.5R | 0 | none |
| F_ALMOST_TP_GIVEBACK_GE_2.5R | 0 | none |

Therefore:
- **24/49** untouched losses never reach +0.5R: thesis/acceptance failure or non-development.
- **25/49** reach at least +0.5R before losing: failed continuation/giveback.
- **13/49** reach at least +1R before losing.
- **0/49** reach +2R before losing.

This is the central F6.14 finding: residual Friday losses are approximately split between **failure-to-develop** and **initially-correct-but-giveback** mechanisms.

## Early path: why one universal +5m cut cannot work
Untouched losses do not look catastrophically bad immediately after entry.

At +5m, among positions still alive:
- untouched-loss median progress: **+0.0232%**
- winner median progress: **+0.0574%**
- close above entry: **58.3% losses vs 71.2% winners**
- median taker imbalance: **+0.0807 losses vs +0.1537 winners**

The difference is real but not large enough to justify an unconditional early cut. This agrees with F6.7, where naive `not reclaimed yet` cuts clipped too many recoveries.

## Separation grows around +30m to +60m
At +30m:
- median progress: **+0.0711% losses vs +0.1964% winners**
- above entry: **64.4% vs 81.8%**
- median MFE: **0.246R vs 0.458R**
- taker imbalance: **+0.0236 vs +0.0669**

At +60m:
- median progress: **+0.0249% losses vs +0.2228% winners**
- above entry: **60.0% vs 83.3%**
- median MFE: **0.298R vs 0.655R**
- taker imbalance: **-0.0038 vs +0.0456**
- median EMA7 distance: losses slightly below EMA7 while winners remain above.

Interpretation: many remaining Friday losers are not immediate collapses. They **fail to accelerate**. By roughly +30m to +60m, winners have built price progress and sustained buyer flow; residual losers are still hovering near entry and taker flow has faded toward neutral/negative.

## Later path confirms stalled thesis
At +120m:
- median progress: **+0.1010% losses vs +0.3817% winners**
- above entry: **54.3% vs 81.3%**
- median MFE: **0.531R vs 0.863R**

At +180m:
- median progress: **+0.0775% losses vs +0.4871% winners**
- above entry: **62.5% vs 86.9%**
- median MFE: **0.503R vs 0.995R**

## Fibonacci context
Untouched losses still show a broader shallower-retracement tendency even after FIB5 removes the extreme shallow+expanded cases:
- untouched-loss median 2h retracement: **53.24%**
- winner median 2h retracement: **74.23%**
- shallow <=38.2%: **32.65% of untouched losses vs 18.18% of winners**
- 2h expansion frequency is similar: **34.69% losses vs 36.36% winners**

So expansion alone is not the explanation. The remaining context clue is more consistent with **insufficient pullback / buying too high within the local 2h range**, while FIB5 already handles the most extreme shallow+expanded subset.

## Discovery / Validation
Untouched losses remain in both halves:
- Discovery: **30** untouched losses; archetypes B/C/D/A = 12/9/8/1
- Validation: **19** untouched losses; archetypes B/C/D = 11/3/5

The failure-to-develop mechanism is especially prominent in Validation.

## Research implication
Do not retune the frozen FIB5, EARLY10, or F6.5 rules.

The next Friday work should branch cleanly:
1. **STALL / FAILURE-TO-DEVELOP branch** — target the 24 untouched losses that never reach +0.5R, with causal evidence concentrated around +30m to +60m (lack of progress + buyer-flow fade + weak EMA acceptance).
2. **GIVEBACK branch** — target the 25 losses that first reach +0.5R, especially the 13 that reach +1R, using profit-protection/state-transition logic rather than an entry filter.

Any next rule must be evaluated separately for these archetypes and tested D/V without modifying the existing three-layer stack.
