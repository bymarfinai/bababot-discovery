# BTC Friday15 T-Method — F5.6 Fresh OOS Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** FRESH OOS OBSERVED — MANAGEMENT RULE NOT YET EXERCISED  
**Live BBC:** untouched

## Frozen rule entering OOS

No threshold was changed after F5.4/F5.5:
- Friday 15:00 WIB BUY
- parent TP2.0 / SL0.7 / hold6h
- after causal +0.50% MFE hinge:
  - `range_ratio >= 2.683993`
  - AND `pre_eff240 >= 0.165628`
  - then PROTECT +0.20%
  - otherwise remain RUNNER

Historical research sample ended 2026-07-30.

Fresh OOS Fridays:
- 2026-07-31
- 2026-08-07
- 2026-08-14

## Results

Parent across 3 fresh Fridays:
- N 3
- WR 33.33%
- PnL -$2.312
- avg -$0.7706
- PF 0.669

Frozen candidate:
- N 3
- WR 33.33%
- PnL -$2.312
- avg -$0.7706
- PF 0.669

**Candidate delta vs parent = $0.000.**

Reason: the frozen management conjunction did not fire on any of the three fresh Fridays.

## Case audit

### 2026-07-31
- parent -$4.250
- parent exit: SL
- +0.50% hinge: NO
- protect fired: NO

The management rule had no causal opportunity to intervene.

### 2026-08-07
- parent +$4.663
- parent exit: TIMEOUT
- +0.50% hinge: YES
- time to hinge: 45m
- trigger range_ratio: **5.8255** (well above 2.683993)
- pre_eff240: **0.0207** (well below 0.165628)
- protect fired: NO

This is mechanistically interesting: the local expansion condition alone was strongly true, but the broader pre-entry regime confirmation was absent, so the conjunction deliberately preserved the runner. The parent ultimately remained profitable at +$4.663.

This does not prove the counterfactual PROTECT action would have lost money, but it is directionally consistent with the F5.3/F5.4 thesis that local expansion alone is too permissive for Friday.

### 2026-08-14
- parent -$2.725
- parent exit: TIMEOUT
- +0.50% hinge: NO
- protect fired: NO

Again, no causal management opportunity existed.

## Scientific interpretation

The first three genuinely unseen Fridays are **neutral evidence for the management rule** because there were zero actual F5.4/F5.5 interventions.

Therefore:
- do NOT claim fresh-OOS success,
- do NOT claim fresh-OOS failure,
- do NOT retune thresholds because no action occurred.

The rule has passed an important operational selectivity check: it did not force an intervention merely because local range expansion was extreme on 2026-08-07; the pre-entry regime gate prevented action.

However, fresh-OOS action quality remains untested until an unseen Friday satisfies both conditions after reaching the +0.50% hinge.

## Current status

Historical/provisional evidence:
- full 138 PnL +$64.630 -> +$73.720
- WR 47.83% -> 51.45%
- PF 1.266 -> 1.327
- DD $56.530 -> $52.030
- LS 8 -> 5
- discovery delta +$6.459
- validation delta +$2.630
- all 8 leave-one-block-out uplifts positive

Fresh OOS evidence:
- 3 unseen Fridays observed
- 0 management actions
- management delta $0.000

**Verdict: PROVISIONAL CANDIDATE, FRESH-OOS ACTION NOT YET TESTED.**

The correct next step is to keep the rule frozen and accumulate additional unseen Fridays until the conjunction actually fires. No live BBC changes were made.
