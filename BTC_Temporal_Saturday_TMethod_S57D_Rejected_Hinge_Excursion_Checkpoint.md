# BTC Temporal Saturday T-Method S5.7D — Rejected-Hinge Excursion Monetization Atlas

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — EXCURSION CEILING ROBUSTNESS PASS; NO MONETIZATION TARGET PROMOTED  
**Research only:** live BBC untouched

## Critical causal convention
The +0.50 hinge candle morphology is only known after that candle completes. Therefore all monetizable excursion in S5.7D starts at the `h05` decision time. The rejected hinge candle's own intrabar high is excluded.

This prevents using an excursion that had already happened before the adaptive state was knowable.

## Frozen parity
- Static parent all 139: **+$87.200**
- A7.19 all 139: **+$103.383**
- +0.50 hinge trades: **89**
- Exact S5.7C `REJECTED_HINGE`: **16**
- `ACCEPTED_HINGE`: **73**

## Main result — a real post-signal excursion ceiling exists
### REJECTED_HINGE
- N **16**
- median future post-hinge MFE: **+0.670%**
- median future max completed close: **+0.638%**
- Discovery median post-MFE: **+0.670%**
- Validation median post-MFE: **+0.718%**
- A7.19 cohort PnL remains **+$36.946**

### ACCEPTED_HINGE
- N **73**
- median future post-hinge MFE: **+1.182%**
- median future max completed close: **+1.058%**
- Discovery median post-MFE: **+1.290%**
- Validation median post-MFE: **+1.010%**
- A7.19 cohort PnL **+$228.876**

Thus the morphology distinction survives even after removing the hinge candle's own wick/high:
> rejected proof-of-strength leaves materially less favorable excursion available after the signal is actually knowable.

## Natural future-reach curve after morphology is known
No TP sweep was performed. These are fixed natural levels inherited from prior strategy geometry.

| Future level | Rejected full | Rejected D | Rejected V | Accepted full | Accepted D | Accepted V |
|---|---:|---:|---:|---:|---:|---:|
| +0.6% | **56.2%** | 60.0% | 50.0% | **91.8%** | 97.7% | 82.8% |
| +0.8% | **43.8%** | 40.0% | 50.0% | **72.6%** | 77.3% | 65.5% |
| +1.0% | **37.5%** | 40.0% | 33.3% | **56.2%** | 59.1% | 51.7% |
| +1.3% | **31.2%** | 30.0% | 33.3% | **47.9%** | 50.0% | 44.8% |
| +1.5% | **18.8%** | 20.0% | 16.7% | **37.0%** | 38.6% | 34.5% |
| +2.0% | **18.8%** | 20.0% | 16.7% | **23.3%** | 25.0% | 20.7% |
| +2.6% | **6.2%** | 10.0% | 0.0% | **17.8%** | 18.2% | 17.2% |

For rejected trades that do reach:
- +0.6% median time after hinge: **30m**
- +0.8%: **85m**
- +1.0%: **120m**
- +1.3%: **525m**

The sharp economic implication is not a target recommendation; it is that the rejected state has substantially less post-signal upside availability.

## Horizon view
Rejected median post-hinge MFE develops only slowly:
- +30m: **+0.491%**
- +60m: **+0.542%**
- +120m: **+0.601%**
- +240m: **+0.601%**
- +360m: **+0.649%**

Accepted median MFE continues expanding:
- +30m: **+0.638%**
- +60m: **+0.703%**
- +120m: **+0.792%**
- +240m: **+0.924%**
- +360m: **+0.930%**

This is consistent with `REJECTED_HINGE` being a lower-excursion-quality state rather than an immediate failure state.

## Four chronological folds
Median future post-hinge MFE:
1. Fold 1: rejected N2 **+2.159%** vs accepted N20 **+1.897%** — reversal, tiny rejected N
2. Fold 2: rejected N7 **+0.575%** vs accepted N17 **+0.963%** — expected direction
3. Fold 3: rejected N2 **+0.544%** vs accepted N14 **+1.071%** — expected direction
4. Fold 4: rejected N5 **+0.862%** vs accepted N22 **+1.168%** — expected direction

Expected lower rejected excursion holds in **3/4 folds**, with the sole reversal having only two rejected observations.

**Excursion ceiling robustness gate: PASS.**

## Crucial negative result — no reliable natural monetization plateau
A descriptive plateau screen required a natural level to:
- be reached by >=60% of rejected trades in both discovery and validation; and
- show a lower reach rate at the next natural level in both halves.

**Result: NONE.**

Even +0.6% is reached by only:
- Discovery **60%**
- Validation **50%**

Therefore the data do NOT justify:
- rejected hinge -> TP +0.6%;
- rejected hinge -> TP +0.8%;
- automatic partial TP at any tested natural level;
- lowering A7.19/parent target merely from hinge rejection.

## S5.7D verdict
**PASS as a robust adaptive excursion-quality dimension; FAIL to identify a standalone monetization target.**

What survives:
> `REJECTED_HINGE` genuinely predicts a lower amount of favorable excursion still available after morphology becomes knowable.

What does not follow:
> there is no sufficiently reliable fixed future level at which rejected trades can simply be harvested.

This suggests that if the branch continues, the next adaptive question should not be `what fixed TP should rejected trades use?`; it should investigate whether a **post-rejection confirmation event** can distinguish the rejected trades that still expand from those whose excursion has actually stalled.

A7.19 remains the official full-coverage Saturday champion. A7.26 remains the preserved selective benchmark.
