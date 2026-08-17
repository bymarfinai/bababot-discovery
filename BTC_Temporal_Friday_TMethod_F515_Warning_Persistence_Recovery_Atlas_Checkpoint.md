# BTC Friday15 T-Method — F5.15 Warning Persistence & Recovery Atlas

**Date:** 2026-08-17 WIB  
**Status:** F5.15 PASS — PERSISTENCE TRAJECTORY IS CAUSALLY SEPARABLE  
**Live BBC:** untouched

## Objective

F5.12 found a causal `HIDDEN_CORE_EMA` warning, but F5.13 showed it was not an immediate SHORT trigger and F5.14 showed acting on the first warning was too early for BUY management.

F5.15 therefore performs **forensics only** on the trajectory after the first frozen warning:

> Does transient warning/recovery behave differently from persistent deterioration?

No trading action, no entry filter, no warning retune, and no fitted management threshold were used.

Frozen F5.12 warning remains:
- `top_vs_global <= 0`
- `top_account_chg_15 < 0`
- `global_account_chg_15 < 0`
- `ema_spread_chg15 < 0`

Usable metrics:
- 136 Friday occurrences
- 54 warned occurrences
- discovery warned N26
- validation warned N28
- chronological split date: 2025-07-11

## Warned baseline

### Discovery
- parent SL rate: **34.6%**
- parent TP rate: 19.2%
- parent loss rate: 50.0%
- future GOOD_REVERSE within 60m: 38.5%
- median initial warning run: 15m
- median warning share over 60m: 39.2%

### Validation
- parent SL rate: **53.6%**
- parent TP rate: 14.3%
- parent loss rate: 64.3%
- future GOOD_REVERSE within 60m: 60.7%
- median initial warning run: 15m
- median warning share over 60m: 46.2%

## Strongest cross-period continuous result

### EMA contraction persistence over 60m (`ema_share_60`)

This is the clearest stable trajectory feature.

For **parent SL** discrimination:
- discovery AUC **0.8105**
- validation AUC **0.7308**

Median EMA-contraction share among eventual SL vs non-SL:
- discovery: **92.3% vs 46.2%**
- validation: **84.6% vs 61.5%**

For **parent loss** discrimination:
- discovery AUC **0.8314**
- validation AUC **0.7750**

Median EMA-contraction share among eventual loss vs non-loss:
- discovery: **84.6% vs 46.2%**
- validation: **80.8% vs 53.9%**

This materially improves on the first-warning interpretation: EMA is useful not simply because contraction occurs once, but because **contraction remains persistent after the hidden-state warning**.

## Full-warning persistence also separates

### `warning_share_30`
Parent SL AUC:
- discovery **0.7190**
- validation **0.6846**

Median warning share in eventual SL vs non-SL:
- discovery: **71.4% vs 42.9%**
- validation: **71.4% vs 57.1%**

### `warning_share_60`
Parent SL AUC:
- discovery **0.6503**
- validation **0.7179**

Parent loss AUC:
- discovery **0.6420**
- validation **0.7417**

Future GOOD_REVERSE60 discrimination is even stronger:
- `warning_share_60`: discovery AUC **0.9313**, validation **0.7299**
- `ema_share_60`: discovery AUC **0.9313**, validation **0.7059**

So persistent deterioration is strongly associated with a later useful reversal window even though F5.13 showed it still should not be converted directly into a SHORT without a new bearish edge.

## Natural persistence states

These states were descriptive/predeclared, not optimized.

### No full recovery within 15m
Discovery N11:
- SL rate **45.5%** vs warned baseline 34.6% (1.315x)
- future GOOD_REVERSE60 **63.6%**

Validation N12:
- SL rate **66.7%** vs baseline 53.6% (1.244x)
- future GOOD_REVERSE60 **66.7%**

This state has usable counts and same-direction SL enrichment.

### No recovery within 20m / recovery takes >20m
This is especially interesting and remains descriptive only.

Discovery N8:
- SL **50.0%**
- TP **0%**
- loss 62.5%
- future GOOD_REVERSE60 **75.0%**

Validation N10:
- SL **70.0%**
- TP 20.0%
- loss 70.0%
- future GOOD_REVERSE60 **70.0%**

This is a plausible candidate persistence state for the next economic test because it has non-trivial counts in both periods and is much more selective than acting on first warning.

### No recovery within 30m
Very strong but too sparse to promote directly:
- discovery N3: SL 66.7%, loss 100%, future GOOD_REVERSE60 100%
- validation N7: SL 85.7%, loss 85.7%, future GOOD_REVERSE60 85.7%

### No recovery within 60m
Even stronger but too sparse:
- discovery N2
- validation N4
- all 6 were losses; 5/6 were SL; all 6 had future GOOD_REVERSE60

Do not promote these tiny-N states directly.

## What did NOT matter as much

- Initial warning run length alone is not stable enough.
- Re-warning count after recovery is weak/inconsistent.
- Relative-positioning state (`top_vs_global`) stays true for most warned paths and is not the main post-warning separator.
- Account-decay persistence is weaker than EMA contraction persistence.

The key post-warning discriminator is therefore **persistence of momentum deterioration**, especially EMA-spread contraction, combined with continued/full warning occupancy.

## Recovery component clue

When the first warning clears because the EMA component recovers, discovery outcomes are materially healthier than when account deterioration is the component that clears first.

Full sample:
- first recovery via account component: N28, SL 53.6%, TP 3.6%, loss 64.3%
- first recovery via EMA component: N25, SL 28.0%, TP 32.0%, loss 48.0%

This supports the interpretation that **EMA re-expansion/recovery is meaningful**, whereas account-ratio normalization alone is not sufficient evidence that the BUY is healthy again.

Caveat: the validation contrast is less dramatic, so this recovery-component observation is secondary to the stronger continuous persistence results.

## Scientific verdict

F5.15 passes the predeclared forensic gate: at least one trajectory feature has same-direction AUC separation >=0.08 away from random in both chronology periods for parent SL/loss.

The strongest result is:

> **First warning is too early. Persistent EMA contraction / persistent full-warning occupancy is the real deterioration state.**

This reconciles F5.12-F5.14:
- first warning = early fragility signal;
- many warnings recover and runners survive;
- if deterioration persists for ~15-20m and EMA contraction remains dominant, the probability of parent failure and future reversal opportunity increases materially.

## Allowed next milestone

**F5.16 — Persistent-State Economic Management Test**

Freeze one simple discovery-justified persistence architecture before looking at economic validation. Recommended first candidate:

> F5.12 warning occurs, then **no full recovery for 20 minutes**, with EMA contraction still active at the decision open.

Do not add SHORT yet. Test HOLD vs a small set of BUY defensive actions at that later persistent-state decision point. Validation must remain report-only.

A secondary comparator can use the 15m no-recovery state, because it has larger sample size.

Do not tune 30m/60m sparse states or add new thresholds on the same sample.

**Live BBC remains untouched.**
