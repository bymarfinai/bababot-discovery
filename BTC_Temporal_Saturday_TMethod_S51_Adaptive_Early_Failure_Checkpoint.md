# BTC Temporal Saturday T-Method S5.1 — Adaptive Early-Failure Action Test

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — +60m FAILURE IS DIAGNOSTIC, NOT A ROBUST IMMEDIATE CUT/FLIP TRIGGER  
**Research only:** live BBC untouched  
**All 139 Saturday entries retained. Non-routed occurrences remain exact A7.19.**

## Frozen references

Static parent — Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h:
- 139 trades
- WR **46.76%**
- PnL **+$87.200**
- PF 1.364
- max DD $45.124
- loss streak 7

A7.19 full-coverage champion:
- 139 trades
- WR **50.36%**
- PnL **+$103.383**
- PF 1.462
- max DD $33.136
- loss streak 5

Frozen +60m `FAILURE_CANDIDATE` parity:
- 30 live-position signals
- discovery 17
- validation 13
- 23/30 eventual parent losses
- loss precision **76.67%**

## S5.1 question

Can the strong +60m causal diagnosis be monetized immediately without destroying Saturday's slow-runner economics?

No threshold search was performed. Predeclared actions at the exact +60m open:
1. `CUT60`
2. `FLIP12_12` — close BUY and open SHORT TP1.2 / SL1.2
3. `FLIP26_12` — close BUY and open SHORT TP2.6 / SL1.2

FLIP economics include the second round-trip fee and short-side historical funding. Short may run only until the original 18h horizon.

Predeclared routing cohorts used only previously frozen Saturday states:
- all FAILURE
- FAILURE + PULLBACK
- FAILURE + NORMAL
- FAILURE + STRETCHED
- FAILURE + no +0.3% impulse by +60m
- FAILURE + STRETCHED + no +0.3% impulse by +60m

All non-routed occurrences retain exact A7.19.

## Main results vs A7.19

| Policy | Actions D/V | WR | PnL | Delta | Disc Δ | Val Δ | Improved / Damaged |
|---|---:|---:|---:|---:|---:|---:|---:|
| STRETCHED+NO03 CUT60 | 1/3 | 50.36% | **+$105.606** | **+$2.223** | +$0.781 | +$1.441 | 3 / 1 |
| STRETCHED+NO03 FLIP12 | 1/3 | 50.36% | +$104.833 | +$1.450 | +$0.814 | +$0.636 | 3 / 1 |
| STRETCHED+NO03 FLIP26 | 1/3 | 50.36% | +$104.833 | +$1.450 | +$0.814 | +$0.636 | 3 / 1 |
| STRETCHED CUT60 | 2/3 | 49.64% | +$103.228 | -$0.155 | -$1.596 | +$1.441 | 3 / 2 |
| NORMAL CUT60 | 7/7 | 47.48% | +$94.139 | **-$9.244** | +$1.606 | **-$10.851** | 6 / 8 |
| NORMAL FLIP12 | 7/7 | 49.64% | +$87.637 | **-$15.746** | +$9.001 | **-$24.747** | 6 / 8 |
| PULLBACK CUT60 | 8/3 | 47.48% | +$80.284 | **-$23.099** | -$10.043 | -$13.056 | 4 / 7 |
| ALL FAILURE CUT60 | 17/13 | 43.88% | **+$70.884** | **-$32.499** | -$10.033 | -$22.465 | 13 / 17 |
| NO03 CUT60 | 14/13 | 44.60% | +$66.772 | **-$36.611** | -$14.145 | -$22.465 | 11 / 16 |
| ALL FAILURE FLIP26 | 17/13 | 46.04% | +$32.283 | **-$71.100** | -$20.403 | -$50.697 | 12 / 18 |
| ALL FAILURE FLIP12 | 17/13 | 46.76% | +$26.957 | **-$76.426** | -$25.729 | -$50.697 | 12 / 18 |

## Cohort structure

### All +60m FAILURE
- N30 = 17 discovery / 13 validation
- parent-loss precision **76.67%**
- A7.19 cohort WR **30.00%**
- A7.19 cohort PnL **-$22.886**

Despite being a genuinely bad cohort, immediate intervention is worse:
- every CUT60 outcome is still net-negative at +60m because the failure definition already requires adverse progress and fees still apply
- CUT can only help by reducing future loss magnitude, but it also truncates recoveries
- full FAIL_ALL CUT delta = **-$32.499**
- full FAIL_ALL flips are dramatically worse, with deltas **-$71 to -$76**

### FAILURE + PULLBACK
- N11
- parent-loss rate 63.64%
- A7.19 cohort is still **+$3.054**

This is the cleanest evidence that a weak first hour does not invalidate a pullback-born Saturday BUY. Direct CUT/FLIP destroys slow recovery.

### FAILURE + NORMAL
- N14, balanced 7 discovery / 7 validation
- parent-loss rate 78.57%
- A7.19 cohort -$17.566

This looks actionable descriptively, but response is chronologically unstable:
- CUT: discovery +$1.606, validation -$10.851
- FLIP12: discovery +$9.001, validation -$24.747

Rejected.

### FAILURE + STRETCHED
- N5 only, 2 discovery / 3 validation
- parent-loss rate **100%**
- A7.19 cohort -$8.374

The narrower `STRETCHED + FAILURE + NO03` state has only N4 (1 discovery / 3 validation):
- CUT60 delta +$2.223
- 3 improved / 1 damaged
- full PnL +$105.606
- max DD about $32.355

This is mechanistically interesting: pre-entry stretch + first-hour failure + no meaningful +0.3% impulse may represent a truly broken BUY thesis. However discovery contains only one routed case, so this is **far too sparse for promotion**.

## Robustness gate

Predeclared strong gate:
- at least 5 routed actions in discovery
- at least 5 routed actions in validation
- positive delta vs A7.19 in discovery
- positive delta vs A7.19 in validation

**No S5.1 policy passes.**

## S5.1 verdict

**FAIL as an immediate management upgrade / PASS as causal diagnosis.**

The +60m FAILURE state is real and stable, but Saturday's payoff is path-dependent: many trades that look weak after one hour still require time to recover. A correct loss classifier is not automatically a profitable exit trigger.

Do not tune the -0.10% progress boundary, taker threshold, flip TP/SL, or +60m timing on this same sample.

The one small clue to preserve as a shadow hypothesis is:

`pre-entry STRETCHED + +60m FAILURE + MFE60 < +0.30%`

but it remains **N4 / not validated** and must not replace A7.19.

## Correct continuation

Proceed to **S5.2 — selective RUNNER vs PROTECT**. Saturday has 26 causal parent losers that first reach +0.5% and S5.0A showed deep runners >=+0.8% have very strong economics. The next question should therefore be how to protect failed shallow runners **after the trade has first proven some BUY impulse**, while preserving deep runners — the same conceptual milestone that unlocked Tuesday, adapted to Saturday's slower character.
