# BTC Temporal Saturday S6.3 — Exact Friday FIB5 Transfer

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — **CROSS-CONTEXT TRANSFER PASS; PROVISIONAL**  
**Research only:** live BBC untouched. No Saturday threshold tuning.

## Frozen transferred rule
The exact Friday F6.12 rule was ported to Saturday 18:00 WIB BUY without any parameter change:

At +5m, exit BUY at the actual +5m open iff:
1. first completed 5m candle closed below entry;
2. position is still alive at +5m;
3. pre-entry 2h retracement depth from the 2h high is <= **38.2%**;
4. pre-entry 2h range is greater than its causal rolling prior-24h median 2h range.

## Saturday static parent
Frozen Saturday parent:
- 139 trades
- 65W / 74L
- WR **46.76%**
- PnL **+$87.200**
- PF **1.364**
- max DD **$45.124**

With exact Friday FIB5 transfer:
- actions **3**
- parent winners cut **0**
- parent losers cut **3**
- positive/negative action deltas **3 / 0**
- PnL **+$95.698**
- improvement **+$8.498**
- Discovery delta **+$8.277**
- Validation delta **+$0.221**
- PF **1.414**
- max DD **$44.903**
- jackknife minimum remaining delta after removing any one action **+$3.023**

Action dates:
- 2024-05-04: parent **-$6.750** -> FIB5 **-$1.274**, delta **+$5.476**; retr2h 5.43%, expansion ratio 1.98x.
- 2024-05-25: parent **-$3.762** -> FIB5 **-$0.960**, delta **+$2.801**; retr2h 15.07%, expansion ratio 1.80x.
- 2025-09-27: parent **-$1.062** -> FIB5 **-$0.841**, delta **+$0.221**; retr2h 14.93%, expansion ratio 1.002x.

## Incremental test on frozen S5.7G champion
S5.7G `NO_BULL_TOP_Q_30` champion:
- 139 trades
- WR **54.68%**
- PnL **+$111.240**
- PF **1.510**
- max DD **$28.346**

FIB5 given chronological priority before the champion logic:
- integrated PnL **+$119.738**
- incremental vs champion **+$8.498**
- Discovery / Validation incremental **+$8.277 / +$0.221**
- PF **1.571**
- max DD **$28.125**
- FIB5/champion action overlap **0**
- unique FIB5 actions **3**

Therefore FIB5 is complementary to the existing Saturday S5.7G management rather than a duplicate.

## Interpretation
This is meaningful evidence that the Friday mechanism can transfer across weekday/parent contexts:

> **local 2h expansion + shallow retracement + immediate first-5m loss of acceptance can identify a subset of BUY trades worth cutting early.**

The exact Friday thresholds were not fitted to Saturday, and every Saturday FIB5 trigger was an eventual parent loser. That makes this stronger evidence of a potentially generic BUY failure detector than Friday same-sample performance alone.

However, Saturday support is still sparse: only **3 actions**, with only **1 Validation action** and a small Validation delta. This is a positive transfer result, not sufficient evidence to call the detector universal or live-ready.

## Guardrails
- Do not tune 38.2%, +5m timing, 2h horizon, or expansion baseline on Saturday from this result.
- Keep the exact definition frozen.
- Seek future unseen Saturday triggers / true OOS evidence.
- A logical separate research branch is the mirrored SELL version on Tuesday, but it should also be tested with fixed definitions rather than fitted post hoc.

## Execution
- Full workflow run: **32044969297** — success
- Artifact: `s63-output`, ID **9292661148**
- Fast parity run: **32045090332** — success
- Fast artifact: `s63a-output`, ID **9292673167**
- Script: `research/s63_saturday_friday_fib5_transfer.py`
- Workflow commit: `77978c0e3b6ba86978f81359e5ce00947abfd1e0`
- Live BBC untouched.
