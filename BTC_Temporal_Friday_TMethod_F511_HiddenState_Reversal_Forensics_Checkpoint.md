# BTC Friday15 T-Method — F5.11 Hidden-State Reversal Forensics

**Date:** 2026-08-17 WIB  
**Status:** F5.11 FORENSICS PASS — HIDDEN-STATE TRANSITION FOUND; NO TRADING RULE YET  
**Live BBC:** untouched

## Research question

F5.7 confirmed large oracle BUY->SHORT reversal capacity, but F5.8-F5.10 rejected causal reversal routers built from ordinary price/volume/taker-flow features and multiple SHORT geometries.

F5.11 asks:

> Is there a futures hidden-state transition visible before a future-good reversal even while price still looks bullish?

This milestone is diagnostics only. No threshold, direction-switch rule, or production change is selected.

## Data / causality

Frozen Friday15 parent:
- every Friday exact 15:00 WIB BUY
- TP2.0 / SL0.7 / max hold360m
- decision opens every 5m from +15m to +180m while parent BUY remains alive
- diagnostic SHORT frozen TP0.7 / SL0.7 / hold180m

Future diagnostic label:
- GOOD_REVERSE if SHORT net >= $1 and combined BUY-close + SHORT improves parent by >= $2

Causal features at each decision open use information strictly before that open.

Sources:
- official Binance USD-M daily metrics archives for OI / top-trader / global-account / taker-LS snapshots
- completed BTCUSDT 5m klines for price, taker-flow proxy, and EMA state

Coverage:
- 3,945 causal decision events
- 136 Friday occurrences with usable metrics
- 74 strong oracle-reversal occurrences
- GOOD_REVERSE event rate 19.29%
- chronological split cut: 2025-07-11

## Main finding

Hidden positioning state is materially more stable across discovery and validation than the price-only signatures tested in F5.8.

### Strongest stable hidden-state rankers

Lower values are associated with GOOD_REVERSE when AUC < 0.5.

1. `top_pos_vs_account`
- discovery AUC 0.4169
- validation AUC 0.3815
- stable direction

2. `top_vs_global` = top-trader position L/S relative to global-account L/S
- discovery AUC 0.4250
- validation AUC 0.3712
- stable direction

GOOD_REVERSE median `top_vs_global` = -0.00237  
Other-event median = +0.18526

Thus future-good reversal points tend to occur when top-trader position long-bias is **less elevated relative to the broader account long-bias**.

3. `global_account_chg_30`
- discovery AUC 0.4168
- validation AUC 0.4418

4. `global_account_chg_15`
- discovery AUC 0.4469
- validation AUC 0.4491

GOOD_REVERSE median global-account 15m change = -0.0999%  
Other-event median = -0.00664%

5. `top_account_chg_30`
- discovery AUC 0.4063
- validation AUC 0.4506

6. `top_account_chg_15`
- discovery AUC 0.4339
- validation AUC 0.4619

GOOD_REVERSE median top-account 15m change = -0.11399%  
Other-event median = -0.02652%

Interpretation: the account-level long/short ratios are deteriorating more strongly into future-good reversal states.

## OI result — NOT a standalone detector

OI changes do **not** survive chronology consistently:
- OI 5m AUC 0.5407 discovery / 0.4722 validation
- OI 15m 0.5628 / 0.4717
- OI 30m 0.5671 / 0.4528

Therefore do not use `OI up` or `OI down` alone as a reversal rule.

Paired strong-pivot transitions nevertheless show that OI value commonly rises into the ex-post pivot while price is still rising. This means the relevant mechanism is likely a divergence / composition change, not the sign of OI itself.

## EMA result

EMA is **not useless**, but it is not supported as a standalone exact-pivot detector.

Useful stable EMA feature:

`ema_spread_chg15` = 15m change in 5m EMA7/EMA20 spread
- discovery AUC **0.4682**
- validation AUC **0.4339**
- same direction

GOOD_REVERSE median = **-0.00217%**  
Other-event median = **+0.00453%**

Thus future-good reversals tend to occur when the EMA7-vs-EMA20 bullish spread is **contracting / losing expansion**, even though price itself can still be rising.

Other EMA states are not stable enough alone:
- EMA7 distance: direction flips discovery/validation
- EMA20 distance: direction flips
- EMA7 slope15: direction flips
- EMA20 slope15: direction flips
- EMA spread level is strong in discovery but nearly neutral in validation

So EMA's justified role is currently **confirmation / momentum-decay context**, not the primary reversal trigger.

## What happens into the oracle pivot?

The paired transition analysis confirms the F5.8 paradox: the ex-post pivot usually arrives during continued bullish-looking price action.

From 15m before to strong oracle pivot (59 paired cases):
- path progress median +0.13582%
- ret5 +0.08846%
- ret15 +0.10273%
- ret30 +0.10475%
- EMA20 distance +0.10648%
- EMA7 distance +0.07170%
- EMA spread +0.02896%
- OI15 change +0.14238 percentage points
- OI30 change +0.09312 percentage points

At the same time, positioning composition shows deterioration:
- top-position 15m-change itself becomes more negative in the paired transition (median change -0.04707)
- future-good event population has materially more negative top-account and global-account L/S changes
- EMA spread *change* is weaker/contracting relative to ordinary events

This supports a hidden-divergence story:

> price and OI can still expand upward, while long-positioning participation / composition deteriorates and EMA momentum expansion begins to weaken.

## Scientific verdict

F5.11 is a **PASS to the next milestone**, because hidden-state features show materially better discovery/validation direction stability than the F5.8 price-only features.

However this is still only ranking / forensic evidence. No threshold has been proven economically.

### Allowed next milestone

**F5.12 — Hidden-State Transition Detector**

It should use a compact, predeclared architecture based on the F5.11 mechanism, not a broad feature sweep:
1. positioning deterioration / relative top-vs-global state as the primary hidden-state warning,
2. optionally EMA-spread contraction as confirmation,
3. OI sign only as context, not as a standalone gate,
4. all decisions causal and first-fire sequential,
5. discovery selection only; validation report-only.

F5.12 should first test whether this warning predicts a materially better *future reversal window*. It should **not immediately open SHORT**. Direction switching belongs only after the warning itself is proven.

**Live BBC remains untouched.**
