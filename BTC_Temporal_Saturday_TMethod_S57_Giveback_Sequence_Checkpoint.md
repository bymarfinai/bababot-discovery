# BTC Temporal Saturday T-Method S5.7 — Giveback Sequence Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — FORENSIC PASS; NO FASTMR ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen parity
- +0.50 hinge trades: **89** = 61 future-deep / 28 shallow
- Static parent all-trade PnL: **+$87.200**
- A7.19 full-coverage PnL: **+$103.383**

## Predeclared sequence geometry
No threshold sweep was used. Natural levels were inherited from prior Saturday work:
1. after causal +0.50 hinge, first completed close <=+0.40 = giveback;
2. for 60m after giveback, observe whether completed-close rebuild >=+0.50 or deeper breakdown <=+0.20 happens first;
3. if rebuild happens first, observe whether a second completed-close failure <=+0.30 occurs within the next 60m;
4. no trade action is attached to any state.

## Main result: recovery itself is extremely runner-like
### REBUILD50_FIRST
- N **34**
- future deep **88.2%**
- Discovery: 25 / **88.0% deep** / A7.19 **+$95.922**
- Validation: 9 / **88.9% deep** / A7.19 **+$38.555**
- Full A7.19 cohort PnL **+$134.477**

This is one of the cleanest Saturday path findings so far: after a <=+0.40 giveback, a causal completed-close rebuild back to >=+0.50 before deeper <=+0.20 breakdown strongly identifies a runner that should be preserved.

## Critical negative result: `rebuild -> second failure` is NOT a failure signature
### GB40_REBUILD50_SECONDFAIL30
- N **13**
- future deep **84.6%**
- Discovery: 11 / **81.8% deep** / **+$32.345**
- Validation: only 2 / **100% deep** / **+$16.467**
- Full A7.19 PnL **+$48.813**

Therefore a trade can:
> reach +0.50 -> give back <=+0.40 -> rebuild >=+0.50 -> fall again <=+0.30

and still very often become a >=+0.80 deep runner.

This invalidates the simple `failed recovery => FastMR/protect` hypothesis for Saturday.

### Rebuild then hold >+0.30 for 60m
- N **21**
- deep **90.5%**
- Discovery **92.9%**
- Validation **85.7%**
- A7.19 **+$85.664**

Both rebuild branches are highly runner-like; the second-failure branch is only slightly weaker and remains overwhelmingly healthy.

## Deeper breakdown before rebuild is more suspicious, but not strong enough
### GB40_BREAK20_FIRST
- N **31**
- deep **51.6%** / shallow 48.4%
- Discovery: N20 / deep **50.0%** / A7.19 **+$63.699**
- Validation: N11 / deep **54.5%** / A7.19 **-$4.580**
- Full A7.19 **+$59.119**

This is materially weaker than REBUILD50_FIRST, but still not a reliable failure state: more than half eventually become deep runners, and discovery economics remain strongly positive.

### GB40_NEITHER60
- N **16**
- deep **56.2%**
- Discovery 62.5% / **+$9.786**
- Validation 50.0% / **+$9.378**
- Full **+$19.164**

Also not economically broken.

## Giveback-speed result confirms regime instability
### <=15m giveback
- N47 / full deep **61.7%**
- Discovery: **73.5% deep**, A7.19 **+$126.504**
- Validation: **30.8% deep**, A7.19 **-$7.062**

This is a severe chronology reversal. `fast giveback => failure` must not be promoted.

### 20–60m giveback
- N17 / deep 64.7%
- Discovery deep 50.0%
- Validation deep 85.7%

Also unstable.

### >60m giveback
- N17 / deep **88.2%**
- Discovery **77.8%**
- Validation **100%**

A later giveback after the +0.50 hinge is strongly runner-like and should not be treated as a failure trigger.

## Giveback-state continuous clues
At the first <=+0.40 completed-close giveback, two descriptive features keep the same favorable direction in discovery and validation:

1. **Higher post-hinge high-water close before giveback**
   - discovery deep/shallow median: about **+0.476% / +0.425%**
   - validation: about **+0.613% / +0.360%**

2. **Less-negative post-hinge taker flow before giveback**
   - discovery deep/shallow median: about **-0.116 / -0.148**
   - validation: about **-0.019 / -0.040**

These are forensic clues only. EMA distance at giveback is not chronologically stable enough to promote.

## S5.8 shadow eligibility
Predeclared shadow gate required a full sequence with:
- >=5 observations in discovery and validation; and
- future-deep rate <40% in both halves.

**Result: NONE.**

No observed giveback sequence earns a FastMR action test under the predeclared gate.

## S5.7 verdict
**PASS as forensic knowledge, but FAIL to produce a robust failure sequence for S5.8 FastMR.**

The strongest positive state is actually runner preservation:
> `+0.50 proven -> giveback <=+0.40 -> rebuild >=+0.50 before <=+0.20` = highly runner-like (~88% deep in both chronology halves).

The important negative lesson is equally strong:
> even `rebuild -> second giveback <=+0.30` remains highly runner-like and must not be treated as automatic failure.

Do not tune +0.35/+0.25 levels, 30/45/75m windows, or combine giveback-speed post hoc on this sample.

## Research decision
Do **not** proceed mechanically to a Saturday S5.8 FastMR action using these failed failure-sequence hypotheses. Preserve the runner-rebuild finding. A7.19 remains the official full-coverage Saturday champion; A7.26 remains the preserved selective benchmark.
