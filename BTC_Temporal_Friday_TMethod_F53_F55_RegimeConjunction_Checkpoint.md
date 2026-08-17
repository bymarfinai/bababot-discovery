# BTC Friday15 T-Method — F5.3 to F5.5 Regime-Conjunction Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL T-METHOD FRIDAY CANDIDATE — NOT FRESH OOS / NOT LIVE  
**Live BBC:** untouched  
**A6.x lineage:** remains separate and parked for this branch

## Context

F5.0-F5.2 replicated the Tuesday A5 process and found the first material divergence at F5.2: Friday did not have a robust local price-path RUNNER-vs-PROTECT separator using the Tuesday-style hinge logic.

F5.3-F5.5 asked why.

Frozen Friday parent throughout:
- BTCUSDT
- Friday exact 15:00 WIB BUY
- TP 2.00%
- SL 0.70%
- max hold 6h
- $500 notional reference
- 0.15% round-trip fee
- all 138 Friday occurrences retained

Frozen management hinge/action:
- first +0.50% favorable BUY MFE
- wait for trigger 5m candle completion
- decide at next 5m open
- PROTECT action = +0.20% lock
- if condition absent, leave parent as RUNNER

---

# F5.3 — Separability Attribution

Script: `btc_temporal_friday15_f53_separability_attribution.py`

Tuesday A5.2 population was used as control; Friday F5.2 population was the target.

For every feature:
- measure PROTECT-better vs RUNNER-better rank separation,
- compare discovery vs validation direction,
- select a single threshold using discovery only,
- freeze it into validation.

## Key correction

Friday does **not** lack separability information entirely.

Stable local features:
- `range_ratio`: AUC discovery 0.6646 / validation 0.6111
- `volume_ratio`: 0.6235 / 0.6056

Stable pre-entry regime features:
- `pre_taker240`: 0.6494 / 0.6389
- `pre_eff240`: 0.6174 / 0.6222
- `pre_ret15`: 0.6905 / 0.6000
- `pre4`: 0.5899 / 0.6222

However:
- Friday single-feature local cross-positive shortlist = **EMPTY**
- Friday single-feature regime cross-positive shortlist = **EMPTY**

So the failure is not purely classification failure. Friday has rank information, but false-positive PROTECT actions are economically expensive because they clip large runners.

Tuesday control, in contrast, produced at least one cross-positive local transfer (`range_ratio >= 2.604458`), confirming that a local-only economic separator is easier to obtain there.

### F5.3 interpretation

Friday needs higher-confidence management than Tuesday. A local event alone or a broader regime variable alone is insufficient. The next justified architecture is a conjunction of local event severity plus pre-entry regime context.

---

# F5.4 — High-Confidence Local + Regime Conjunction

Script: `btc_temporal_friday15_f54_highconfidence_conjunction.py`

Compact predeclared families only:
- local expansion: `range_ratio` or `volume_ratio`
- pre-entry regime: `pre_taker240`, `pre_eff240`, `pre_ret15`, or `pre4`
- discovery quantile thresholds only
- optional stricter range+volume+regime conjunction

353 causal configurations were tested; initial Friday entries were never filtered.

## Best cross-positive candidate

**RANGE_RATIO_AND_PRE_EFF240**

Frozen F5.4 candidate:
- after +0.50% MFE hinge,
- trigger `range_ratio >= 2.683993` (discovery 80th percentile),
- and `pre_eff240 >= 0.165628` (discovery median),
- then PROTECT +0.20%; else RUNNER.

Discovery:
- parent +$99.194
- candidate +$105.653
- delta **+$6.459**
- 5 actions
- 4 PROTECT-better / 1 RUNNER-better
- action precision 80%
- true gain $8.249 / false damage $1.790
- gain/damage 4.609

Validation:
- parent -$34.563
- candidate -$31.933
- delta **+$2.630**
- 5 actions
- 3 PROTECT-better / 2 RUNNER-better
- action precision 60%
- true gain $11.630 / false damage $9.000
- gain/damage 1.292

Full:
- parent +$64.630
- candidate **+$73.720**
- delta **+$9.090**
- 10 actions
- 7 PROTECT-better / 3 non-improving or RUNNER-better actions
- action precision 70%
- true gain $19.879 / false damage $10.790
- gain/damage 1.842

The stricter range+volume+pre_eff240 variants also cross-positive, but have fewer actions and lower total uplift. They are not promoted over the simpler two-feature conjunction.

### Scientific caveat

F5.4 architecture was motivated by F5.3, whose validation was already visible. Therefore F5.4 validation is **supportive but not pristine fresh OOS**. The candidate is provisional research, not production proof.

---

# F5.5 — Fixed Candidate Robustness

Script: `btc_temporal_friday15_f55_fixed_conjunction_robustness.py`

No threshold retuning was allowed.

## Parent vs fixed candidate — full 138 Fridays

Parent:
- WR 47.83%
- PnL +$64.630
- expectancy +$0.4683 / Friday
- PF 1.266
- max DD $56.530
- max loss streak 8

Fixed F5.4 candidate:
- WR **51.45%**
- PnL **+$73.720**
- expectancy **+$0.5342 / Friday**
- PF **1.327**
- max DD **$52.030**
- max loss streak **5**
- delta +$9.090

Discovery:
- WR 58.54%
- +$105.653
- PF 1.928
- DD $16.826
- LS 3
- delta +$6.459

Validation:
- WR 41.07%
- -$31.933
- PF 0.714
- DD $45.585
- LS 5
- delta +$2.630 vs parent validation

The candidate improves the weak validation period but does not transform Friday validation into a profitable standalone half.

## Block attribution

8 chronological blocks, candidate delta vs parent:
1. 0.000
2. +7.598
3. -1.790
4. +0.651
5. 0.000
6. +4.500
7. +4.500
8. -6.370

=> 4 positive, 2 zero, 2 negative.

## Leave-one-block-out

Because the rule is fixed, remove each block and recompute remaining uplift:
- drop B1: +9.090
- drop B2: +1.492
- drop B3: +10.880
- drop B4: +8.439
- drop B5: +9.090
- drop B6: +4.590
- drop B7: +4.590
- drop B8: +15.460

**All 8 leave-one-block-out totals remain positive.**

The largest dependency is Block 2, but removing it still leaves +$1.492 uplift.

## Year attribution

2023 (partial): delta 0.000, 0 actions
2024: delta +$5.808, 4 actions
2025: delta +$5.152, 3 actions
2026 through Jul: delta -$1.870, 3 actions

So the mechanism improves 2024 and 2025 but is mildly negative in the 2026 partial period. This is an important reason not to call it fresh-OOS proven.

## Incremental execution-cost stress

Additional cost applied to every PROTECT action, on top of the research fee model:
- +$0.05/action: full delta +$8.590
- +$0.10/action: +$8.090
- +$0.15/action: +$7.590
- +$0.25/action: +$6.590
- +$0.50/action: +$4.090
- +$0.75/action: +$1.590
- +$1.00/action: -$0.910

Thus the small +$9.09 uplift is not erased by modest incremental friction, but it is not a huge-margin edge either.

## Action-level facts

10 actions occurred over 138 Fridays.

Notable PROTECT improvements include several parent -$4.25 losses converted to approximately +$0.25 outcomes.

Largest false-positive damage:
- 2026-04-17 parent +$9.25 runner
- PROTECT +$0.25
- delta **-$9.00**

This single false positive explains why Friday needs high precision: one clipped large runner can erase multiple small successful protections.

---

# Mechanistic conclusion

The faithful Tuesday-style research path has now identified a real Friday-specific distinction:

**Tuesday:** local post-entry path state can be sufficient to decide RUNNER vs PROTECT.

**Friday:** local event severity carries information, and broader pre-entry regime carries information, but neither is economically reliable alone. A high-confidence conjunction is needed because the cost of clipping a true Friday runner is very large.

Provisional Friday T-Method management candidate:

> Friday15 BUY parent TP2.0/SL0.7/6h. After +0.50% MFE, wait for the trigger 5m candle to complete. If trigger range expansion is >=2.683993x its pre-entry 60m median and the pre-entry 4h directional efficiency is >=0.165628, protect +0.20%; otherwise keep the runner.

This preserves all 138 initial entries and only changes management on 10 historical occurrences.

## Status / next proof

**PROVISIONAL RESEARCH CANDIDATE — NOT LIVE.**

Do not retune the thresholds on the same 138 Fridays.

The correct next proof is either:
1. fresh unseen Fridays, or
2. fixed-rule transfer to a comparable BUY temporal slot without retuning.

A6.x remains a separate lineage and should not be merged into this rule until the T-Method candidate receives cleaner out-of-sample evidence.

**Live BBC remains untouched.**
