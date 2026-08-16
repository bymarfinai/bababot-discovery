# BTC Temporal Saturday 18 WIB — A7.12/A7.13 Loss Taxonomy Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** LOSS ANALYSIS COMPLETE FOR THIS PASS — NO NEW TRADE RULE FROZEN  
**Parent remains:** Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h  
**Sample:** 139 trades / 65 positive / 74 negative / WR46.76% / +$87.20 funding-adjusted  
**Research only:** no live BBC code modified

## A7.12 — mutually exclusive loss families

The 74 negative parent trades are not one homogeneous failure mode.

| Family | Losses | Share of losses | Discovery share | Validation share | Core path |
|---|---:|---:|---:|---:|---|
| A1 immediate wrong-way | 25 | 33.78% | 30.23% | 38.71% | never reaches +0.3%; -0.3 occurs first |
| A2 no impulse | 1 | 1.35% | 0% | 3.23% | neither meaningful favorable nor strong adverse impulse |
| B weak pop | 20 | 27.03% | 30.23% | 22.58% | reaches +0.3% but not +0.5% |
| C giveback | 19 | 25.68% | 27.91% | 22.58% | reaches +0.5% but <+0.8%, then loses |
| D deep giveback | 9 | 12.16% | 11.63% | 12.90% | reaches >=+0.8%, then loses |

Broad mechanism counts:
- never reaches +0.3%: 26
- reaches +0.3 but <+0.5: 20
- reaches +0.5 but <+0.8: 19
- reaches >=+0.8: 9
- SL losses: 22
- timeout losses: 52

### A1 immediate wrong-way
This is the largest single loss family and is stable across chronological halves.

Full medians:
- MFE 0.1155%
- MAE 0.9829%
- peak time 45m
- trough time 635m
- 8 SL / 17 timeout

At 15m:
- progress -0.0553%
- taker edge -0.0613
- only 36% above EMA20

At 60m:
- progress -0.1242%
- MFE 0.0493%
- MAE 0.2192%
- taker edge -0.0432
- distance EMA20 -0.0301%
- only 25% above EMA20

The same qualitative weakness appears in both discovery and validation, more strongly in validation.

### B weak-pop family
20 losses. These usually get a small rebound but fail to become real runners.
- median MFE 0.3540%
- median peak time 287.5m
- 70% touch +0.3 before -0.3
- mostly timeout losses (15/20)

This family is slower and less separable early than A1.

### C giveback 0.5–0.8
19 losses.
- median MFE 0.6236%
- median peak time 250m
- median trough time 810m
- 78.95% touch +0.5 before -0.5
- 12/19 timeout

By 360m the group shows meaningful deterioration:
- median progress only +0.0226%
- distance EMA20 -0.0628%
- only 17.65% above EMA20

The 360m EMA20 deterioration appears in both chronological halves.

### D deep giveback >=0.8
9 losses, remarkably stable share across splits.
- median MFE 1.1822%
- median peak time 340m
- 100% touch +0.5 before -0.5
- only 2 SL / 7 timeout

These are genuine profitable runners that later fail to monetize.

## Important implication for achievable WR

28/74 losses (C+D) first reach at least +0.5% favorable excursion.
If an impossible perfect management oracle converted all 28 to positive without damaging winners, headline WR ceiling from post-entry giveback management alone would be about 66.9% (93/139). This is an oracle capacity ceiling, not an actionable result.

Separately, a perfect pre-entry filter that removed only the 25 A1 immediate-wrong-way losses and no winners would raise executed-trade WR to about 57.0% (65/114). Again this is an oracle ceiling.

Thus Saturday has enough structural loss capacity for a materially higher WR; the bottleneck is causal identification without clipping profitable runners.

## A7.13 — can A1 wrong-way losses be recognized causally?

A compact, hand-specified classification atlas was tested at completed 15/30/60m checkpoints. No trade management was changed.

The most stable family was around 60m, not 15m.

### 60m progress + flow
Rule:
- progress <= -0.10%
- taker edge < 0

Full:
- 30 signals
- 23/30 are eventual losses = 76.67% loss precision
- winner false positives 7
- winner FP rate 10.77%

Discovery loss precision: 76.47%  
Validation loss precision: 76.92%

### 60m progress + EMA20 + EMA20 slope
Rule:
- progress <= -0.10%
- below EMA20
- EMA20 3-bar slope < 0

Full:
- 35 signals
- 27/35 eventual losses = **77.14% loss precision**
- winner false positives: 8
- winner FP rate: 12.31%
- A1 immediate-wrong-way recall: 54.17%

Discovery:
- loss precision **78.95%**
- winner FP rate 10.0%

Validation:
- loss precision **75.0%**
- winner FP rate 16.0%

This is materially more stable across periods than the A7.5 early CUT/FLIP mapping.

## Current interpretation

Saturday low WR is produced by at least two different economic problems:

1. **Thesis never becomes valid** — especially A1 immediate wrong-way and part of B weak-pop. These are candidates for causal thesis-validation after entry, likely around 60m rather than immediate 15m action.
2. **Thesis becomes valid but profit is not monetized** — C/D giveback families. These need runner/profit management, not direction prediction.

A single universal protection or flip rule is therefore structurally inappropriate.

## Next justified research step

Do not retune TP/SL yet.

The next clean experiment should be a **two-stage Saturday state machine** evaluated causally and walk-forward:

- Stage 1 around 60m: VALID / FAILED BUY THESIS using the stable loss-state signature. First test CUT-to-smaller-loss / break-even logic before considering a SHORT flip.
- Stage 2 only for trades that subsequently prove favorable (e.g. +0.5/+0.8 MFE): runner vs giveback management as a separate problem.

The objective should be to improve WR and PnL simultaneously while preserving most of the 65 original winners. No rule from A7.12/A7.13 is frozen for live use yet.
