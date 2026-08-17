# BTC Saturday18 T-Method — S5.0 Parent Loss Forensics

**Date:** 2026-08-17 WIB  
**Status:** S5.0 COMPLETE — FROZEN PARENT REPRODUCED; LOSS FORENSICS ONLY  
**Live BBC:** untouched  
**Preserved prior best:** A7.19 full-coverage champion and A7.26 selective candidate remain unchanged

## Purpose

Start a new Saturday T-Method research lineage that mirrors the Tuesday A5 milestone process without copying Tuesday's trading thresholds.

S5.0 asks only the same first questions as Tuesday A5.0:
- is entry timing the main problem?
- is wrong direction the main problem?
- how many eventual losers first become meaningfully profitable?
- when do winner/loser paths begin to separate?

No management rule is selected here.

## Frozen Saturday parent

Every Saturday exact **18:00 WIB**:
- BUY
- TP **2.6%**
- SL **1.2%**
- max hold **18h**
- $500 reference notional ($10 margin x 50)
- 0.15% round-trip fee
- historical BTCUSDT funding using canonical A7.3 methodology
- same-5m ambiguity adverse-first

## Reproduction gate — PASS

Independent S5.0 harness reproduced the frozen parent:
- N **139**
- wins/losses **65 / 74**
- WR **46.76%**
- PnL **+$87.1997**
- expectancy **+$0.6273/trade**
- PF **1.364**
- max DD **$45.124**
- max loss streak **7**
- TP / SL / timeout **14 / 22 / 103**
- funding cost **$6.9616** across 240 settlements

Chronology:
- discovery first83: WR **48.19%**, PnL **+$52.667**, PF 1.349
- validation last56: WR **44.64%**, PnL **+$34.533**, PF 1.388

## Winner / loser path anatomy

Winner medians:
- MFE **1.4102%**
- MAE **0.2344%**

Loser medians:
- MFE **0.3451%**
- MAE **0.8224%**

The basic Saturday structure is therefore very similar to the useful Tuesday A5.0 question: many winners create substantial favorable excursion while losers suffer materially deeper adverse excursion.

## Strict-causal giveback capacity among 74 negative trades

Using favorable excursion observed **before the parent actually exits**:
- MFE >=0.30%: **46**
- MFE >=0.40%: **31**
- MFE >=0.50%: **26**
- MFE >=0.60%: **19**
- MFE >=0.80%: **9**
- MFE >=1.00%: **6**

Important reconciliation with the older A7 checkpoint:
- A7.4's descriptive section reported 28 loser paths >=+0.50%;
- the later causal A7.6 hinge section in the same research lineage reported **89 total +0.50 hinge trades = 63 winners + 26 losers**;
- S5.0 independently reproduces exactly **89 = 63 + 26**.

For T-Method management research, the strict-causal **26** count is the relevant one because only favorable excursion reached before exit can trigger a real management action.

## Entry-too-early hypothesis

Among the **22 SL exits**, number that later reached the original +2.6% BUY target within the same original 18h horizon:

**0**

Thus the main Saturday weakness is not simply that the exact 18:00 entry gets stopped before the original BUY thesis later works.

## Early path separation

Median completed-path state:

### +5m
- winner progress **+0.0092%**
- loser progress **+0.0013%**
- winner taker bias **+0.1125**
- loser taker bias **+0.0107**

### +10m
- winner progress **+0.0203%**
- loser progress **-0.0059%**
- winner taker **+0.0503**
- loser taker **+0.0201**

### +15m
- winner progress **+0.0083%**
- loser progress **-0.0282%**
- winner taker **+0.0489**
- loser taker **-0.0429**

### +30m
- winner progress **+0.0314%**
- loser progress **-0.0098%**
- winner taker **+0.0343**
- loser taker **-0.0375**

### +60m
- winner progress **+0.0755%**
- loser progress **-0.0421%**
- winner taker **+0.0337**
- loser taker **-0.0366**

Separation strengthens materially by roughly 15–60m, but this does not yet prove an actionable flip/cut rule.

## Wrong-direction oracle capacity — diagnostic only

S5.0 uses the stricter Tuesday-style definition: close the BUY at the checkpoint, open a symmetric SHORT 1.2/1.2, charge the second round-trip fee, and ask whether the **combined trade** could finish net-positive.

Among parent-negative trades still alive:
- 10m: **35 / 74** theoretically total-positive
- 15m: **32 / 74**
- 30m: **32 / 74**
- 60m: **28 / 73**

This confirms material wrong-direction oracle capacity, but it is not a causal signal.

## S5.0 interpretation

Three facts are now frozen for the new Saturday T-Method lineage:

1. **Delayed entry is not the primary problem.** No parent SL later reaches the original +2.6% target in-horizon.
2. **Wrong-direction capacity is real but only oracle-level so far.** A large subset of losers could theoretically benefit from a reversal, but identification remains unproven.
3. **Giveback capacity is meaningful.** 26 actual negative trades first reach >=+0.50% favorable excursion before exit; 9 reach >=+0.80%.

Therefore Saturday justifies the same next milestone as Tuesday A5.1:

## Allowed next milestone — S5.1

Test two broad hypotheses separately, using discovery selection and validation reporting:

1. **early wrong-direction FLIP/CUT**, and
2. **unconditional favorable-MFE protection**.

The goal is not to promote either broad rule automatically. As on Tuesday, S5.1 should determine whether:
- early flip is chronologically stable, and
- high WR can be manufactured by protection only at the cost of runner expectancy.

Do not use A7.19 or A7.26 as the parent for this T-Method branch. They remain preserved as comparison champions only.

**Existing best results remain preserved:**
- A7.19 full coverage: 139 trades / WR50.36% / +$103.383 / PF1.462 / DD$33.136
- A7.26 selective: 123 trades / WR52.03% / +$109.587 / PF1.536 / DD$28.483

**Live BBC remains untouched.**
