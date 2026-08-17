# BTC Temporal Saturday T-Method S5.1B — FAIL → No EMA20 Reclaim 60m CUT

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — REJECTED AS MANAGEMENT UPGRADE; EARLY-FAILURE ACTION BRANCH CLOSED  
**Research only:** live BBC untouched  
**Control:** exact A7.19 full-coverage strategy

## Frozen references

Parent — Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h:
- 139 trades
- WR 46.76%
- PnL +$87.200

A7.19 full-coverage champion:
- 139 trades
- WR 50.36%
- PnL +$103.383
- PF 1.462
- max DD $33.136
- loss streak 5

A7.26 selective benchmark remains preserved separately:
- 123 trades
- WR 52.03%
- PnL +$109.587

## Frozen S5.1B rule

1. Detect first frozen FAILURE on a completed 5m decision between +15m and +180m:
   - decision-open progress <= -0.10%
   - cumulative taker edge < 0
2. Observe a full 60 minutes after that first failure.
3. Frozen EMA20 reclaim requires:
   - decision-open > completed-bar EMA20
   - EMA20 slope60 > 0
4. If no reclaim occurs through the full +60m confirmation decision and A7.19 is still alive, CUT at that exact causal decision-open.
5. Otherwise preserve A7.19 exactly.

No timing, threshold, routing, or action sweep was performed.

## Integrity detail

S5.1A's descriptive atlas stopped first-failure scanning at +180m. S5.1B still gives every detected failure a complete 60-minute post-failure reclaim observation (therefore confirmation can occur as late as +240m). This prevents late failure episodes from being labeled `NO_RECLAIM60` merely because the descriptive scan ended.

## Result

- First-failure occurrences: **77**
- Full no-EMA-reclaim-60m states: **57**
- Actual CUT actions: **57** = 36 discovery / 21 validation
- No eligible state was lost because A7.19 exited before confirmation
- Confirmation median: **+105m**
- Q25 / Q75: **+80m / +160m**

### A7.19 → S5.1B

- PnL: **+$103.383 → +$85.142**
- Delta: **-$18.241**
- WR: **50.36% → 38.13%**
- Expectancy: **+$0.744 → +$0.613/trade**
- PF: **1.462 → 1.487**
- Max DD: **$33.136 → $53.882**
- Loss streak: **5 → 8**

Chronological deltas:
- Discovery: **-$9.552**
- Validation: **-$8.689**

Action effects:
- 29 improved
- 28 damaged
- 1 negative → positive
- **18 positive → negative**

Predeclared robustness gate:
- >=5 actions discovery: PASS (36)
- >=5 actions validation: PASS (21)
- discovery delta >0: **FAIL**
- validation delta >0: **FAIL**
- overall: **FAIL**

## Pre-entry diagnostics of actual actions (descriptive only)

| State | N (D/V) | A7.19 loss | A7.19 PnL | CUT PnL | Delta |
|---|---:|---:|---:|---:|---:|
| PULLBACK | 24 (18/6) | 54.17% | -$1.755 | -$32.377 | **-$30.621** |
| NORMAL | 28 (16/12) | 75.00% | -$62.605 | -$52.309 | **+$10.296** |
| STRETCHED | 5 (2/3) | 100.00% | -$9.459 | -$7.375 | +$2.084 |

These are diagnostics only. NORMAL and STRETCHED are not promoted as routing rules: STRETCHED is too sparse and S5.1B was explicitly a single-action test, not a new same-sample routing search.

## Interpretation

S5.1A was correct that persistence and failure-to-recover carry information. However, even after waiting for a full 60m failure-to-reclaim confirmation, a direct CUT is not economically robust. The diagnostic state catches many eventual losers but still truncates too many Saturday slow recoveries and profitable runners.

The clearest damage is PULLBACK-born trades: CUT loses an additional $30.62 versus preserving A7.19. This reinforces the Saturday-native lesson that early weakness, even persistent weakness, is not enough by itself to terminate a pullback-origin BUY.

PF rises slightly because the CUT reshapes the loss distribution, but this is not a useful upgrade: total PnL, WR, expectancy, drawdown, loss streak, discovery PnL, and validation PnL all deteriorate materially.

## Final S5.1 branch verdict

**CLOSE EARLY-FAILURE ACTION BRANCH.**

Do not tune:
- first-failure timing
- -0.10% failure boundary
- taker threshold
- EMA20 reclaim window
- EMA slope condition
- CUT timing
- FLIP geometry

The branch remains useful only as diagnostic state information.

## Correct continuation

Proceed to **S5.2 — selective RUNNER vs PROTECT**.

Reason: Saturday needs evidence of favorable impulse before intervention. S5.0/S5.0A established a large management opportunity among failed shallow runners after +0.5% MFE, while deep runners >=+0.8% have very strong economics and should be preserved. The next research question is therefore how to protect failed shallow runners after the trade has first proven BUY impulse, rather than trying to terminate trades during early weakness.
