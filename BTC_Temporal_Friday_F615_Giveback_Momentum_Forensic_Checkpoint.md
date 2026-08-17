# BTC Temporal Friday F6.15 — Giveback Momentum Forensic Checkpoint

**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT RULE TUNED  
**Live BBC untouched. Existing F6.12/F6.9/F6.5 stack unchanged.**

## Question
Why do the 25 residual Friday losses that first move favorably (+0.5R or more) later lose momentum and finish negative? Is the failure mainly Fibonacci resistance, candle rejection, or flow/EMA deterioration?

## Causal protocol
- Parent Friday15 BUY unchanged: TP +2.0%, SL -0.7%, max hold 6h.
- Residual giveback cohort: 25 parent losses untouched by FIB5/EARLY10/F6.5 that reached at least +0.5R but less than +2R.
- 12 reached +0.5R but never +1R; 13 reached +1R but never +2R.
- Analysis is anchored to the **first completed 5m bar that reaches +0.5R / +1R**, not to hindsight peak bars.
- Winner controls are parent winners that reached the same milestone.
- FIB resistance uses only fully known pre-entry 2h/4h structure. Tested levels include retracement 38.2/50/61.8/78.6/100 and range-extension 1.272/1.618.

## +0.5R milestone: little immediate separation
Givebacks N=25 vs winner controls N=65.

At the milestone candle itself:
- bearish candle: 12.0% giveback vs 13.85% controls
- median upper wick: 23.58% vs 25.80%
- upper wick > body: 20.0% vs 32.31%
- taker imbalance: +0.293 vs +0.198

So the +0.5R milestone candle itself does **not** identify failure. Givebacks can still look healthy when first reaching +0.5R.

FIB exact-proximity also does not separate:
- within 0.10% of nearest pre-entry 2h FIB level: 72.0% giveback vs 70.77% controls
- median 2h distance: 0.0543% vs 0.0569%
- within 0.10% of nearest 4h FIB level: 48.0% vs 56.92%

Therefore exact FIB contact is not the primary cause at +0.5R.

## After +0.5R: flow fades and EMA acceptance weakens
By +15m after first reaching +0.5R:
- median taker flow: **-0.0084 giveback vs +0.0457 controls**
- below EMA7: 32.0% vs 24.62%

By +30m:
- median taker flow: **-0.0266 vs +0.0197**
- below EMA7: **56.0% vs 30.77%**
- median progress remains ~+0.306% giveback vs +0.359% controls

A simple descriptive conjunction `taker<0 AND below EMA7` at +30m occurs in 40.0% of givebacks vs 15.4% of winner controls. This direction is present in both Discovery (35.3% vs 13.6%) and Validation (50.0% vs 19.0%). This is forensic evidence only, not a tuned exit rule.

## +1R milestone: strongest structural clue
Givebacks N=13 vs winner controls N=56.

At the first +1R milestone candle:
- median upper wick: **46.94% giveback vs 29.28% controls**
- upper wick > body: **53.85% vs 28.57%**
- bearish milestone candle: 23.08% vs 12.5%
- taker imbalance already weaker: **+0.124 vs +0.229**

This suggests a rejection/exhaustion signature becomes much clearer only after the trade has already made meaningful progress.

Caveat: candle morphology alone is not equally strong in both halves. Upper-wick > body is 25% vs 27% in Discovery but 100% vs 31.6% in Validation. Therefore a single rejection-candle rule is not robust enough by itself.

## Fibonacci / inverse-FIB finding
Exact proximity to a pre-entry FIB level still does **not** discriminate at +1R:
- within 0.10% of nearest 2h FIB: 46.15% giveback vs 50.0% controls
- median distance: 0.1276% vs 0.0991%
- within 0.10% of nearest 4h FIB: 38.46% vs 51.79%

However there is a useful *context* clue: the nearest 2h level is **1.618 extension** for 11/13 = **84.6%** of +1R givebacks versus 26/56 = **46.4%** of winner controls.
- Discovery: 75.0% giveback vs 40.5% controls
- Validation: 100% giveback vs 57.9% controls

But the givebacks are not consistently closer to the exact 1.618 price than controls. Therefore the defensible interpretation is:
> 2h 1.618 acts as a **stretched-context marker**, not proven mechanical resistance by itself.

## What happens after +1R
The clearest causal deterioration happens during the next 15–30 minutes.

### +10m after first +1R
- progress: +0.562% giveback vs +0.716% controls
- drawdown from best: -0.261% vs -0.173%
- taker median: +0.031 vs +0.057

### +15m
- progress: +0.525% vs +0.740%
- drawdown from best: **-0.357% vs -0.167%**
- taker median: **-0.044 vs +0.036**
- below EMA7: **53.85% vs 17.86%**

Discovery:
- taker median -0.080 vs -0.003
- below EMA7 62.5% vs 27.0%

Validation:
- taker median -0.041 vs +0.078
- below EMA7 40.0% vs 0%

### +30m
- progress: **+0.424% giveback vs +0.729% controls**
- drawdown from best: **-0.396% vs -0.214%**
- taker median: **-0.099 vs -0.003**
- below EMA7: **53.85% vs 30.36%**

The progress gap is stable:
- Discovery +0.453% giveback vs +0.714% controls
- Validation +0.362% vs +0.779%

A descriptive `taker<0 AND below EMA7` conjunction at +30m occurs in 53.8% of +1R givebacks vs 21.4% of controls; Discovery 62.5% vs 29.7%, Validation 40.0% vs 5.3%. Again: descriptive forensic, not yet an action rule.

## F6.15 verdict
The 25 givebacks are best explained as a **failed continuation state**, not a single Fibonacci rejection.

For the 13 stronger +1R givebacks the typical sequence is:
1. BUY works and reaches +1R.
2. The trade is often in a stretched 2h context, frequently nearest the 1.618 extension.
3. The milestone/rejection candle often shows more upper wick, but candle alone is insufficient.
4. Within ~15m, taker buyer flow fades/turns negative.
5. Price loses EMA7 acceptance much more often than winners.
6. Drawdown from the post-milestone best becomes roughly twice as deep as winner controls.
7. By +30m, progress has materially decayed instead of continuing.

**Best current reading:** `stretched context -> rejection/exhaustion -> buyer-flow reversal -> EMA7 loss -> giveback`.

The next clean experiment should test a frozen causal **post-profit protection state** after +1R (and separately after +0.5R), using predeclared combinations of flow reversal + EMA7 loss + drawdown from best. Do not tune FIB levels or existing failure layers on the same sample.
