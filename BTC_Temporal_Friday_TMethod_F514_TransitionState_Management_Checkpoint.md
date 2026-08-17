# BTC Friday15 T-Method — F5.14 Transition-State BUY Management

**Date:** 2026-08-17 WIB  
**Status:** F5.14 FAIL — FIRST WARNING IS NOT SUFFICIENT FOR BUY MANAGEMENT ACTION  
**Live BBC:** untouched

## Objective

F5.13 rejected direct BUY->SHORT execution after the successful F5.12 `HIDDEN_CORE_EMA` warning. F5.14 therefore tested whether the same frozen warning can improve management of the existing Friday BUY without assuming a bearish edge.

Hard constraints:
- all **138 / 138 Friday15 BUY entries retained**;
- parent unchanged: TP2.0 / SL0.7 / hold360m;
- F5.12 warning unchanged;
- no SHORT;
- no entry filter;
- no fitted threshold sweep;
- 2 Friday dates without usable futures metrics simply HOLD parent.

Frozen F5.12 warning:
- `top_vs_global <= 0`
- `top_account_chg_15 < 0`
- `global_account_chg_15 < 0`
- `ema_spread_chg15 < 0`

## Parent baseline

All 138 Fridays:
- WR **47.83%**
- PnL **+$64.630**
- expectancy +$0.4683/trade
- PF **1.266**
- max DD **$56.530**
- max loss streak 8

Chronology:
- discovery N82: +$99.194
- validation N56: -$34.563

## Management families tested

Mechanistic only:
1. `HALF_RISK_STOP`: SL -0.70 -> -0.35 (half original risk distance)
2. `BE_IF_GREEN`: if warning-open > entry, stop to entry
3. `LOCK_HALF_GAIN`: if warning-open > entry, lock half current open gain
4. `PARTIAL50`: close 50% at warning, retain 50% frozen parent
5. `PARTIAL50_HALF_RISK`: close half + half-risk stop on remainder
6. `TEMP_HALF_RISK`: half-risk stop only while frozen warning persists
7. `TEMP_BE_IF_GREEN`: BE only while warning persists
8. `TEMP_LOCK_HALF_GAIN`: half-gain lock only while warning persists

Temporary governors release at the first later causal decision-open where the exact F5.12 warning conjunction is false.

## Milestone result

**No discovery management candidate passed the predeclared gate.**

`discovery_rank = []`

The only policy with positive discovery uplift was `TEMP_HALF_RISK`, but it changed only 4 discovery trades, below the minimum action count of 5, and then lost in validation.

Therefore:

> **F5.14 = FAIL / NO DISCOVERY MANAGEMENT CANDIDATE.**

## Representative results

### HALF_RISK_STOP

Discovery:
- 26 warnings, 17 actual changed outcomes
- parent +$99.194
- managed +$78.225
- delta **-$20.969**
- MDD worsened $24.424 -> $36.506

Validation:
- 28 warnings, 21 changed outcomes
- parent -$34.563
- managed -$38.623
- delta **-$4.060**
- DD improves by $6.823, but expectancy deteriorates

Full:
- 38 changed outcomes
- 24 improved / 14 damaged
- gross rescue gain **+$41.047**
- runner damage **-$66.075**
- net delta **-$25.028**
- PnL falls $64.630 -> $39.602

The stop does rescue many parent SLs: a standard -$4.25 SL becomes about -$2.50, a +$1.75 rescue. But false interventions on runners are much more expensive. Two parent TP examples alone each lose roughly $11.75 of opportunity.

### BE_IF_GREEN

Discovery:
- delta **-$22.254**

Validation:
- delta **+$11.381**
- DD improves by $4.082

Full:
- delta **-$10.872**
- PnL $64.630 -> $53.758

This has chronology inversion: it helps the weak later period but materially damages the strong discovery period.

### LOCK_HALF_GAIN

Discovery:
- delta **-$24.528**

Validation:
- delta **+$8.255**

Full:
- delta **-$16.272**
- DD improves by $4.957

Again, later-period rescue is real, but runner clipping dominates full-history economics.

### PARTIAL50

Discovery:
- delta **-$17.372**
- DD improves by $5.995

Validation:
- delta **+$0.510**
- DD improves by $6.414

Full:
- delta **-$16.861**
- DD improves $56.530 -> $50.116

Partial sizing behaves as a drawdown reducer, not an expectancy enhancer.

### PARTIAL50_HALF_RISK

Full:
- delta **-$29.375**
- DD improves by $9.311

The stronger protection further sacrifices expectancy.

### TEMP_HALF_RISK

Discovery:
- only **4 actual changed outcomes**
- delta **+$0.776**
- DD improves $0.777

Validation:
- 11 changed outcomes
- delta **-$3.351**

Full:
- 15 changed outcomes
- 12 improved / 3 damaged
- rescue gain +$20.047
- damage -$22.621
- net delta **-$2.573**
- PnL $64.630 -> $62.057
- DD improves by $0.991

This is the closest policy to neutral and provides an important structural clue: most first warnings clear before the temporary protection can alter the parent outcome.

### TEMP_BE / TEMP_LOCK_HALF_GAIN

Both remain net negative. Temporary release reduces intervention frequency but does not create cross-period expectancy uplift.

## Main interpretation

F5.12 should not be reinterpreted as an action signal.

It is a valid probabilistic warning that future reversal opportunity becomes more likely, but F5.14 shows:

> **the first occurrence of the warning is too early / too transient to justify tightening, de-risking, or profit-locking the BUY.**

The economic asymmetry is the same lesson previously seen in unconditional protection:
- rescuing a parent SL typically saves only a few dollars;
- clipping one genuine Friday runner can lose many times that rescue amount.

This explains why many policies improve drawdown while reducing total PnL.

## New clue: warning persistence vs transient recovery

Temporary governors are highly selective because the F5.12 conjunction often clears again before a managed stop is touched.

That means the next scientifically justified question is **not another stop level** and not another SHORT trigger.

It is:

> Does the *trajectory after the first warning* separate transient fragility from persistent regime deterioration?

The relevant next forensic milestone should measure, without trading:
- warning duration / consecutive 5m persistence;
- time to first full recovery;
- number of warning recurrences after recovery;
- which warning components recover first or remain weak;
- persistent EMA-spread contraction vs quick re-expansion;
- persistent positioning deterioration vs normalization;
- relation of those trajectories to parent SL, TP, timeout and future-good reversal windows;
- discovery/validation stability.

A future management action is justified only if **persistent-warning state** is materially more selective than first warning.

Do not retune stop distances on the same 138-Friday sample to force a positive result.

**Live BBC remains untouched.**
