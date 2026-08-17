# BTC Friday15 T-Method — F5.0 to F5.2 Milestone Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** APPLE-TO-APPLE TUESDAY PROCESS REPLICATION — FIRST MATERIAL DIVERGENCE AT F5.2  
**Live BBC:** untouched  
**A6.x Friday research:** parked; not used in this branch

## Purpose

Replicate the **Tuesday A5 discovery process milestone-by-milestone**, not copy its final rules as a package.

Frozen diagnostic parent for this branch:
- BTCUSDT
- every Friday exact 15:00 WIB
- BUY
- TP 2.00%
- SL 0.70%
- max hold 6h
- $500 notional reference ($10 margin x 50)
- 0.15% round-trip fee
- all Friday occurrences retained

No A6.33/A6.50 management is used in F5.0-F5.2.

---

# F5.0 — Parent Loss Forensics

Script: `btc_temporal_friday15_f50_parent_forensics.py`

Parent result:
- N 138
- wins 66 / losses 72
- WR 47.83%
- PnL +$64.630
- TP exits 19
- SL exits 51
- timeouts 68

Path medians:
- winner MFE 1.3504%, MAE 0.2336%
- loser MFE 0.4248%, MAE 0.9902%

Early path separation is already visible:
- 5m winner vs loser net: +0.0575% vs -0.0132%
- 10m: +0.1142% vs -0.0082%
- 15m: +0.1243% vs +0.0145%
- 30m: +0.1963% vs +0.0132%
- 60m: +0.2228% vs -0.0463%

Winner/loser taker flow also separates early:
- 5m +0.0768 vs -0.0172
- 10m +0.0448 vs -0.0038
- 60m +0.0095 vs -0.0210

## Delayed-entry capacity

Only **2** SL losses later reached the original +2.00% BUY target within the same 6h horizon.

=> Like Tuesday A5.0, generic delayed entry is not the main improvement path.

## Bad-exit / giveback capacity

Among 72 eventual negative trades:
- MFE >=0.20: 56; 48 before SL
- >=0.30: 46; 37 before SL
- >=0.40: 37; 29 before SL
- >=0.50: **32; 23 before SL**
- >=0.60: 25; 17 before SL
- >=0.80: 14; 9 before SL
- >=1.00: 8; 5 before SL

This closely mirrors the Tuesday A5.0 insight: many eventual losers were meaningfully profitable first.

## Wrong-direction oracle capacity

For negative parent trades still alive, an oracle close-BUY + SHORT could theoretically turn many occurrences positive. Example:
- 10m: 71 negatives alive; 42 could become total-positive with SHORT 0.7/0.7
- 15m: 70 alive; 45 could become total-positive

This is capacity only, not a causal rule.

### F5.0 verdict

The same two families justified by Tuesday A5.0 are justified for Friday:
1. early wrong-direction flip,
2. profit protection after useful MFE.

---

# F5.1 — Early Flip vs Unconditional Profit Protection

Script: `btc_temporal_friday15_f51_parent_interventions.py`

Chronological split:
- discovery first 82 Fridays
- validation last 56

Baseline:
- discovery WR54.88%, +$99.194, PF1.828, DD24.424
- validation WR37.50%, -$34.563, PF0.719, DD50.085
- full WR47.83%, +$64.630, PF1.266, DD56.530

## Early FLIP

The discovery-selected flip family does **not** improve discovery.

Representative 15m bearish flip to SHORT 0.7/0.7:
- discovery +$89.668, delta **-$9.526**
- validation +$5.872, delta +$40.435
- full +$95.540, WR53.62%, PF1.441, DD38.452

Representative SHORT 2.0/0.7:
- discovery +$89.961, delta **-$9.233**
- validation +$37.372, delta +$71.935
- full +$127.332

But the strict cross-period flip shortlist is **EMPTY**.

=> Large F5.0 oracle capacity cannot be converted into a discovery->validation causal early-flip rule. No early flip is promoted.

## Unconditional protection

As on Tuesday, broad profit protection can manufacture high WR while destroying expectancy.

Example trigger +0.40%, lock +0.20%:
- discovery WR76.83%, +$41.879 vs parent +$99.194
- validation WR57.14%, -$67.167
- full WR68.84%, **-$25.288**, PF0.836

Example trigger +0.50%, lock +0.20%:
- full WR64.49%
- PnL **-$21.448**

=> High WR is mechanically available, but broad protection cuts the large runners that create Friday expectancy.

### F5.1 verdict

Same lesson as Tuesday A5.1:
- generic direction flip is not established,
- unconditional protect is harmful,
- therefore the next justified question is selective RUNNER vs PROTECT.

---

# F5.2 — Selective RUNNER vs PROTECT

Script: `btc_temporal_friday15_f52_runner_protect.py`

Frozen hinge/action for this milestone:
- first +0.50% BUY MFE
- wait for completed trigger 5m candle
- decision at next 5m open
- PROTECT action = +0.20% lock
- if lock already lost by decision open, exit at actual open
- otherwise RUNNER leaves TP2.0/SL0.7/6h unchanged

No EMA is used.

## Hinge atlas

Full hinge occurrences: 86
- PROTECT would be economically better: 25
- RUNNER better: 61

Full median state, protect-better vs runner-better:
- time to hinge: 90m vs 70m
- trigger-close progress: 0.4938% vs 0.4680%
- MFE: 0.5904% vs 0.5564%
- MAE: 0.1191% vs 0.0926%
- taker avg: 0.0193 vs 0.0328
- range ratio: 2.1814 vs 1.6898
- volume ratio: 2.7198 vs 2.1689

Unlike Tuesday A5.2, the Friday protect-better group is **not cleanly described by weak trigger close + high prior MAE**. The relationship is weaker and changes across chronological halves.

Protect all hinge trades remains destructive:
- full WR63.04%
- PnL **-$24.959** vs +$64.630 parent

## Local Friday detector search

Only compact interpretable price-path families were tested:
- weak close
- weak close + seller flow
- trigger rejection
- slow/weak hinge
- high-MAE + weak close
- low-efficiency + weak close
- seller-flow + rejection

Critical outcome:

**Strict cross-period shortlist = EMPTY.**

No F5.2 price-path protector simultaneously:
- improves discovery PnL,
- improves validation PnL,
- preserves/beats full parent economics,
- and improves WR.

Representative best discovery-ranked candidate, SLOW_WEAK close<=0.40 and time>=60m:
- discovery +$96.379, delta **-$2.815**
- validation -$34.439, delta +$0.124
- full +$61.940, WR48.55%

WEAK_CLOSE <=0.35:
- discovery delta -$7.900
- validation delta +$7.381
- full +$64.112 vs parent +$64.630
- DD worsens to $57.420

Therefore Friday does **not** reproduce the Tuesday A5.2 breakthrough.

---

# F5.2T — Exact Tuesday A5.2 Transfer Negative Control

Script: `btc_temporal_friday15_f52t_exact_tuesday_transfer.py`

Exact directional mirror of frozen Tuesday A5.2:

> after +0.50% BUY MFE, if the completed trigger close retains <=+0.35% BUY progress and cumulative MAE is >=0.20%, protect +0.20%; otherwise keep runner.

Result:
- discovery: 2 actions, WR53.66%, +$91.879, delta **-$7.315**, 0 rescued, 1 damaged winner
- validation: 1 action, +$31.933 negative total (baseline -$34.563), delta +$2.630, 0 rescued
- full: 3 actions, WR47.10%, **+$59.945**, delta **-$4.685**, PF1.248

The Tuesday plateau sibling close<=0.40 / MAE>=0.20 is worse:
- discovery delta -$11.815
- validation delta -$1.018
- full PnL **+$51.798**, delta -$12.832
- DD worsens to $59.996

Thus the failure is not merely because the Friday-local detector search chose the wrong threshold. The actual Tuesday A5.2 mechanism itself does not transfer.

---

# Scientific comparison with Tuesday

## Parallel through the first two milestones

Tuesday A5.0 and Friday F5.0 both found:
- delayed entry is not the main issue,
- eventual losers often first develop substantial favorable MFE,
- wrong-direction oracle capacity exists but is not yet actionable.

Tuesday A5.1 and Friday F5.1 both found:
- generic early flip is not a robust causal upgrade,
- broad profit protection can raise WR sharply but destroys runner expectancy.

## First material divergence: A5.2 / F5.2

Tuesday A5.2 discovered a robust selective path state:
- +0.50 MFE
- weak retained progress
- meaningful prior adverse excursion
- selectively protect +0.20
- discovery and validation both improve
- new Tuesday champion formed.

Friday F5.2:
- no such robust price-path separator exists in the tested interpretable family,
- strict cross-period shortlist is empty,
- exact Tuesday A5.2 mirror also fails.

### Consequence

**Do not create a fake Friday F5.3 robustness milestone.** There is no F5.2 winner to freeze.

Also do not claim that Friday has reached the Tuesday A5.4 EMA milestone by the same path. Tuesday only moved to EMA after A5.2 established a new robust residual population. Friday did not achieve that milestone.

The faithful apple-to-apple replication therefore currently **stops at F5.2** and records a genuine structural divergence.

A6.x Friday research remains useful as a separate research lineage, but it must not be retroactively described as the Tuesday-method continuation.

**Live BBC remains untouched.**
