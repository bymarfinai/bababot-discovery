# BTC Friday15 T-Method — F5.17 Regime Attribution Forensic

**Date:** 2026-08-17 WIB  
**Status:** F5.17 FORENSIC COMPLETE — SLOW RESPONSE-HEALTH CLUE FOUND, NO RULE PROMOTED  
**Live BBC:** untouched

## Objective

F5.16 found a chronology inversion in persistent-state BUY management:
- P15/P20 `HALF_RISK_STOP` improved the weak validation era,
- but did not improve the strong discovery era.

F5.17 asks the justified next question:

> What causal pre-entry / prior-Friday regime state explains when persistent P15/P20 half-risk helps versus hurts?

No P15/P20 duration was retuned. The -0.35% half-risk stop was frozen. Every Friday15 occurrence remains BUY; no SHORT and no entry filter are introduced.

## Reproducibility gate

A new research-only harness (`research/f517_regime_attribution.py`) independently rebuilt the Friday15 parent and F5.16 persistence management from official Binance Data Vision USD-M BTCUSDT archives before any attribution result was accepted.

### Frozen parent reproduction

Reproduced:
- N **138**
- wins/losses **66 / 72**
- WR **47.826%**
- PnL **+$64.6304**
- PF **1.2664**
- max DD **$56.5295**
- TP / SL / timeout **19 / 51 / 68**

This matches the frozen F5.0/F5.16 parent.

### F5.16 P15 reproduction

Discovery:
- persistent states **9**
- changed outcomes **6**
- delta **-$3.4521**
- 4 improved / 2 damaged

Validation:
- states **11**
- changed **8**
- delta **+$7.6644**
- 7 improved / 1 damaged

Full:
- states **20**
- changed **14**
- delta **+$4.2123**
- 11 improved / 3 damaged

### F5.16 P20 reproduction

Discovery:
- states **6**
- changed **4**
- delta **-$0.5151**

Validation:
- states **9**
- changed **7**
- delta **+$4.5743**

Full:
- states **15**
- changed **11**
- delta **+$4.0593**

The F5.17 simulator therefore passed the required apple-to-apple reproduction gate.

## Attribution scope

F5.17 did **not** mine new thresholds. It reused natural/pre-existing causal states from the Friday lineage:

1. prior-Friday response health:
   - FAST = prior 8 frozen-parent Friday average PnL,
   - SLOW = prior 13 frozen-parent Friday average PnL;
2. low 24h volatility versus trailing Friday history;
3. pre-entry `stress_core`;
4. pre-entry `stress_unwind`;
5. top-trader crowding state;
6. natural zero-crossing hidden positioning states;
7. OI non-increasing context.

Attribution focuses on the **14 P15 actual-changed outcomes**, because these are the cases where half-risk has economic effect.

## Main finding — slow Friday response health

The strongest chronology clue is:

`SLOW13 < 0`

meaning the average frozen Friday15 parent PnL over the **13 completed prior Fridays** is negative before the current Friday entry.

Among P15 changed outcomes:

### Discovery
- `SLOW13 < 0`: **0 cases**

### Validation
- `SLOW13 < 0`: **4 changed cases**
- improved: **4 / 4**
- damaged: **0 / 4**
- total P15 half-risk uplift: **+$7.000**

This is the clearest explanation of the chronology inversion: persistent half-risk becomes useful during a period in which the Friday15 parent response itself has deteriorated over a slow multi-week horizon.

However, it **cannot be promoted as a cross-period rule**, because discovery contains no P15 changed outcome in the negative-SLOW13 state.

## Descriptive shadow economics — NOT validation proof

For completeness, applying the exact causal shadow condition:

> every Friday remains BUY; only if P15 is persistent **and** prior-13-Friday parent average PnL is negative, tighten SL from -0.70% to -0.35%; otherwise HOLD parent.

produces historically:

### P15 + SLOW13<0

Discovery:
- gated persistent states **0**
- changed outcomes **0**
- PnL unchanged **+$99.194**

Validation:
- gated states **6**
- changed outcomes **4**
- all 4 improved / 0 damaged
- parent -$34.563 -> **-$27.563**
- delta **+$7.000**
- validation DD about **$46.585**

Full:
- all 138 Friday entries retained
- 6 gated persistent states
- 4 economically changed outcomes
- 4 improved / 0 damaged
- parent +$64.630 -> **+$71.630**
- delta **+$7.000**
- PF **1.304**
- max DD about **$53.030**
- WR unchanged **47.83%**

This is descriptive only. The state was identified from the same 138-Friday sample, and discovery provides zero negative-SLOW13 action cases.

### P20 + SLOW13<0 comparator

Discovery again has zero gated states.

Validation/full:
- gated states **4**
- changed outcomes **3**
- 3 improved / 0 damaged
- uplift **+$4.8049**
- full PnL about **+$69.435**

P15 remains the more informative shadow architecture, but neither is promoted.

## What did NOT explain the chronology robustly

### FAST8 < 0

Not sufficient. In the full P15 changed cohort:
- FAST-negative cases: N6, total delta **-$2.393**
- FAST-nonnegative cases: N8, total delta **+$6.605**

So the faster health state does not identify when persistent half-risk is useful.

### Low RV24

Inconsistent across chronology. It does not explain the F5.16 inversion.

### `stress_core` / `stress_unwind`

Too sparse inside the P15 changed cohort and not stable:
- each has only 2 full changed cases in the relevant true state,
- discovery true-state action is damaging while validation true-state action is beneficial.

These remain useful mechanism descriptors from A6.x, but they do not explain F5.16 action economics by themselves.

### OI non-increasing

Also non-transferable:
- discovery OI-nonincreasing changed cases have negative half-risk delta,
- validation OI-nonincreasing cases are positive.

This is consistent with prior Friday work that rejected OI sign as a standalone regime detector.

### Current relative-positioning zero crossings

They provide no separation here because the persistent F5.12 action cohort already naturally sits inside the hidden-state deterioration family. They are part of the warning mechanism, not the missing era discriminator.

## Scientific interpretation

F5.17 narrows the F5.16 chronology inversion substantially.

The evidence does **not** support the idea that one current-Friday microstructure flag tells us whether P15 half-risk should be used.

The more plausible mechanism is a **slow response-function regime shift**:

> when the Friday15 BUY edge has been healthy over the prior multi-week horizon, persistent warnings can still recover into valuable runners, so defensive management can be costly; when the edge's own prior-13-Friday realized response becomes negative, the same persistent deterioration is more likely to deserve risk reduction.

This is importantly different from a calendar-era rule. `SLOW13` is causal and known before the current Friday entry.

But the same-sample evidence remains insufficient to promote it because negative-SLOW13 P15 actions occur only in the later chronology.

## F5.17 verdict

**PASS as regime attribution / FAIL as promotable management rule.**

What is now justified:
- freeze `SLOW13 < 0` as a **shadow hypothesis**;
- do not retune 13 weeks, P15, or the -0.35% stop on the 138-Friday sample;
- test the frozen architecture only on post-sample / forward observations or an independent temporal family.

What is not justified:
- promoting P15+SLOW13 live;
- using calendar dates as regime labels;
- adding another threshold sweep;
- using FAST8, stress_unwind, low-vol, or OI sign as a substitute gate just because they existed in earlier Friday research.

## Allowed next milestone

**F5.18 — Frozen Slow-Health Shadow Check**

Freeze exactly:

`Friday15 BUY -> F5.12 warning -> P15 persistent -> prior13 frozen-Friday parent average PnL < 0 -> HALF_RISK_STOP -0.35%`

All other occurrences HOLD the parent. No SHORT, no occurrence deletion, no parameter tuning.

The next check should use post-2026-07-30 observations only and should be reported as a shadow / post-sample test. Because some post-sample aggregate Friday outcomes have already been viewed in other research branches, it should not be overstated as pristine unseen OOS.

**Live BBC remains untouched.**
