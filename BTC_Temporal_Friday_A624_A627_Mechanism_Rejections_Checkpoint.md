# BTC Temporal Friday15 — A6.24–A6.27 Mechanism Tests Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** MECHANISM PASS COMPLETE — A6.22 BALANCED REFERENCE UNCHANGED  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Reference entering this pass — A6.22 balanced

- original Friday entries: **138 / 138**
- parent BUY: TP2.0%, SL0.7%, max6h
- failed-thesis detector: 60m initial + persistent120m
- if BUY already exited before120: immediate sequential SHORT TP1.5% / SL0.5%
- if BUY still open at120: existing balanced FLIP path TP1.3% / SL0.7%
- nonwrongway selective A6.15 distribution protection remains active

Reference metrics:
- WR **60.87%**
- PnL **+$128.989**
- expectancy +$0.9347/Friday
- PF **1.637**
- max DD $51.993
- max loss streak 4
- 7/8 chronological blocks positive delta vs original parent
- discovery: WR67.07%, +$137.053, PF2.498
- validation: WR51.79%, **-$8.065**, PF0.927

A6.23 CUT remains a separate PnL-first alternate: WR57.25%, +$132.621, PF1.699, validation -$6.085, 8/8 positive-delta blocks. It is not substituted for A6.22 when WR+PnL are jointly important.

---

## A6.24 — post-stop SHORT confirmation / exhaustion guard

Purpose: determine whether the 15 post-stop sequential SHORTs can be filtered or delayed causally without changing their TP1.5/SL0.5 geometry.

Policies tested:
- NO_REENTRY
- IMMEDIATE_120 — A6.22 reference
- inherited EMA20 distance guard `d20 > -0.10%`
- wait15m and require continued downside
- wait30m and require continued downside
- wait15 + EMA20 guard

Selection used **first82 discovery engine PnL only**.

### Result

**IMMEDIATE_120 won discovery. A6.22 remains unchanged.**

Reference immediate:
- discovery WR67.07%, +$137.053
- validation WR51.79%, -$8.065
- full WR60.87%, +$128.989

EMA20 guard:
- full WR57.25%, +$104.989
- validation -$18.565

Wait15 continuation:
- full WR57.97%, +$104.228
- validation -$11.815

Wait30 continuation:
- full WR57.97%, +$107.919
- validation -$17.714

### Important mechanism

The post-stop SHORT itself remains strong:
- full N15
- SHORT-leg WR66.67%
- standalone SHORT-leg PnL +$47.531
- PF3.925
- discovery: 4/5 positive, +$20.031
- validation: 6/10 positive, +$27.500

Simple delay or EMA20 exhaustion filtering throws away too many rescue winners. **Do not add a pre-SHORT delay/guard from this pass.**

---

## A6.25 — economic recovery lock after SHORT +1.0%

Hypothesis: after a prior BUY SL (~-$4.25 net), a +1.0% favorable SHORT move produces roughly +$4.25 net on the second leg after fee, so it is the economic point where the sunk first-leg loss has been repaid.

Strict-causal rule tested:
- post-stop SHORT still enters immediately at120 with TP1.5/SL0.5;
- once a completed5m bar establishes SHORT MFE >= +1.0%, arm +1.0% protection from the next5m open;
- retain TP1.5.

### Result — REJECTED HARD

Reference A6.22:
- WR60.87%
- +$128.989

Economic lock:
- WR **55.80%**
- PnL **+$106.621**
- PF1.521
- delta **-$22.368**
- 0 positive-delta blocks vs A6.22

Validation:
- reference -$8.065
- managed **-$23.750**
- delta -$15.686

The rule converted **7 reference winners into non-wins**. Successful post-stop SHORTs frequently retrace through +1.0 before eventually reaching TP1.5. **Do not protect this second leg at +1.0.**

---

## A6.26 — causal online regime chooser for still-open failures

Purpose: avoid choosing HOLD/CUT/FLIP from hindsight or validation. Use only prior completed still-open events.

Online expanding rule:
- first still-open event defaults FLIP, preserving incumbent balanced policy;
- before each later event, choose HOLD/CUT/FLIP with highest cumulative counterfactual PnL across all earlier completed still-open events;
- ties prefer FLIP > HOLD > CUT;
- after current Friday's 6h horizon completes, update all policy scores for use on later Fridays.

This is causal and parameter-light but events are sparse: only 12 full-sample still-open failure cases.

### Result — REJECTED

A6.22 reference:
- WR60.87%
- +$128.989
- validation -$8.065

Online chooser:
- WR **58.70%**
- +$117.351
- PF1.568
- validation **-$17.036**

The meta-policy is too noisy at this event count and reacts poorly to regime changes. **Do not use online expanding policy selection here.**

---

## A6.27 — proven-rebound failure at120m

Fixed, non-swept state:
- not in wrong-way state;
- BUY still open at120;
- first120m MFE >= +0.50%;
- actual120m-open progress <0%;
- any earlier A6.15 distribution action retains temporal precedence.

Interpretation: rebound was proven, then completely failed below entry by120m.

Policies compared: HOLD, CUT, FLIP SHORT TP1.5/SL0.5. Selection used discovery PnL only.

### Signal count

Only **3 cases full sample**:
- discovery: 1 case, which was an original +$9.25 winner
- validation: 2 cases, both C-giveback losses (-$4.25 each)

Discovery therefore selected **HOLD**.

Official result is exactly A6.22 unchanged:
- WR60.87%
- +$128.989
- validation -$8.065

A validation-only FLIP would have rescued both validation cases and produced validation +$5.702 / WR55.36%, but discovery explicitly rejects FLIP and N=3. This is **not evidence and must not be promoted**. Treat it only as a hypothesis for future unseen/OOS data.

---

## Verdict of A6.24–A6.27

No valid balanced upgrade emerged.

Rejected:
1. filtering/delaying the post-stop SHORT;
2. EMA20 d20 guard on post-stop SHORT;
3. +1.0 economic break-even lock on the post-stop SHORT;
4. sparse online HOLD/CUT/FLIP meta-policy;
5. hindsight use of the 120m proven-rebound validation anomaly.

### Current Friday research reference remains A6.22

- **138 / 138 Friday entries**
- **WR60.87%**
- **PnL +$128.989**
- **PF1.637**
- max loss streak4
- 7/8 positive-delta blocks vs original parent
- discovery +$137.053 / WR67.07%
- validation -$8.065 / WR51.79%

### PnL-first alternate remains A6.23 CUT

- 138 entries
- WR57.25%
- +$132.621
- PF1.699
- 8/8 positive-delta blocks
- validation -$6.085

## Research lock / next evidence

The BTC Friday sample has now been inspected deeply. Do **not** locally squeeze additional thresholds on the same 971-day sample and label them OOS improvements.

A genuinely new next mechanism, if Friday research continues on BTC, should be a **predeclared chronological walk-forward regime-management test** (all Friday entries retained) using information available before each Friday, or genuinely unseen future Fridays / cross-asset transfer. Validation-only anomalies from this pass must not be converted into rules.

No live implementation has been made.
