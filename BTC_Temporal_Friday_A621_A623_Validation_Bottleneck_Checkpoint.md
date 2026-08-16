# BTC Temporal Friday15 — A6.21–A6.23 Validation Bottleneck Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** PROVISIONAL RESEARCH — NOT LIVE / NOT FINAL  
**Symbol:** BTCUSDT  
**Entry:** every Friday exact 15:00 WIB BUY  
**Sample:** 138 Fridays; first82 discovery / last56 validation  
**Live BBC:** untouched

## Starting point: A6.20 parity-correct canonical

- 138/138 Friday entries
- WR 60.87%
- PnL +$116.406
- PF 1.565
- max loss streak 4
- validation: WR51.79%, PnL -$16.648, PF0.853

A6.20 uses parent BUY TP2/SL0.7/max6h, parity-correct 120m failed-thesis sequential SHORT TP1.3/SL0.7, and the selective A6.15 distribution protection.

## A6.21 validation loss attribution

Purpose: explain the remaining last56 validation loss without tuning new thresholds.

Validation A6.20:
- 56 occurrences
- 29 positive / 27 non-positive
- WR51.79%
- PnL -$16.648

### Route attribution

#### Normal parent route — no wrong-way intervention
39 occurrences:
- WR48.72%
- PnL **+$19.846**
- PF1.318

This is important: the untouched/non-wrongway Friday subset is still profitable in validation. The remaining validation deficit is concentrated in failed-thesis management routes rather than every Friday BUY.

Final negative normal-parent cases =20:
- A wrong-way <0.3 MFE: 8, PnL -$18.325
- B weak pop 0.3–0.5: 4, PnL -$13.084
- C giveback 0.5–1.0: 8, PnL -$31.081
- D deep giveback >=1.0: 0

#### Post-stop sequential SHORT
10 validation occurrences where parent BUY had already exited before 120m:
- occurrence WR60.0% (6 positive / 4 negative)
- occurrence PnL **-$23.583** under A6.20 TP1.3/SL0.7
- standalone SHORT leg PnL **+$18.917**, PF2.214, WR60%
- parent sunk loss across route = -$42.50

Interpretation: the SHORT signal itself has edge, but the recovery geometry does not fully compensate the already-realized BUY loss; failed rescue creates a double loss.

#### Still-open 120m flip
6 validation occurrences where original BUY remained open at120:
- current FLIP route WR50%
- route PnL -$13.160
- same occurrences under untouched parent: -$11.017
- delta = **-$2.144**
- 2 original winners became final losses.

Thus the still-open flip is not robust in validation.

#### Distribution protection
1 validation action:
- parent -$0.892 -> protected +$0.250
- delta +$1.142

Distribution layer remains directionally useful but has too little validation count to solve the overall deficit alone.

## A6.22 post-stop rescue geometry

Only post-stop sequential SHORT geometry was changed. Still-open flip and distribution layer remained frozen. Candidate selection used first82 discovery engine PnL only.

Compact candidates tested around tighter rescue risk / larger reward than A6.20 reference 1.3/0.7.

### Selected discovery-only geometry: SHORT TP1.5 / SL0.5

Discovery:
- WR67.07%
- PnL **+$137.053**
- PF2.498

Validation:
- WR51.79%
- PnL **-$8.065**
- PF0.927

Full:
- 138 entries
- WR **60.87%**
- PnL **+$128.989**
- expectancy +$0.9347/Friday
- PF **1.637**
- max DD $51.993
- max loss streak 4
- 7/8 chronological blocks positive delta vs original parent

By year:
- 2024: +$96.991, WR67.31%
- 2025: +$8.864, WR53.85%
- 2026 through Jul: +$16.953, WR60.00%

Versus A6.20, A6.22 improves full PnL by about $12.58 while preserving the same 60.87% headline WR, and cuts validation deficit roughly in half again (-$16.648 -> -$8.065).

### Mechanism

With $500 notional and 0.15% roundtrip fee, post-stop recovery needs both sufficient reward and controlled second-leg loss. TP1.5/SL0.5 gives successful rescue enough room to pay more of the sunk BUY loss while reducing failed-rescue damage versus TP1.3/SL0.7.

## A6.23 still-open failure policy

With A6.22 post-stop TP1.5/SL0.5 frozen, compare only the 120m confirmed-failure cases where original BUY is still open. Policies: HOLD, CUT, or FLIP. Selection again used discovery engine PnL only.

### HOLD
Full:
- WR58.70%
- +$127.472
- PF1.635

Validation:
- WR50.00%
- -$5.921

### CUT at actual 120m open — discovery winner
Full:
- WR **57.25%**
- PnL **+$132.621**
- expectancy **+$0.9610/Friday**
- PF **1.699**
- max DD $52.763
- 8/8 chronological blocks positive delta vs original parent

Discovery:
- WR64.63%
- +$138.706
- PF2.613

Validation:
- WR46.43%
- **-$6.085**
- PF0.941

### FLIP current reference
Full:
- WR60.87%
- +$128.989
- PF1.637

Validation:
- WR51.79%
- -$8.065

### Interpretation

The still-open flip buys win count, but not stable expectancy. CUT is the discovery-PnL winner and gives the highest overall PnL/PF with 8/8 positive-delta blocks, but it converts all still-open confirmed failures into realized negative occurrences and therefore reduces headline WR.

This is a genuine objective trade-off, not a free upgrade.

## Current Friday research versions

### Balanced candidate — preferred when WR + PnL are both important
**A6.22**
- all 138 Friday entries
- WR **60.87%**
- PnL **+$128.989**
- PF **1.637**
- validation -$8.065
- 7/8 positive-delta blocks

### PnL-first alternate
**A6.23 CUT**
- all 138 Friday entries
- WR **57.25%**
- PnL **+$132.621**
- PF **1.699**
- validation -$6.085
- 8/8 positive-delta blocks

Do not silently substitute A6.23 for A6.22 when the objective includes maintaining WR around 60%+.

## Remaining bottleneck

The validation engine is now near break-even but not positive. The cleanest unresolved mechanism is the **post-stop re-entry decision**, not the normal Friday subset:
- the standalone post-stop SHORT leg is profitable;
- the sunk first-leg loss makes combined occurrence expectancy negative;
- simply increasing size would resemble loss-recovery sizing and is not preferred;
- next research should therefore ask whether the post-stop SHORT winners vs losers can be separated causally at/after120m, or obtain genuinely new OOS data / cross-pair transfer evidence before more threshold tuning.

## Locks / cautions

- A6.21 is diagnostic only.
- A6.22 TP1.5/SL0.5 was selected on discovery before validation evaluation.
- A6.23 CUT was selected on discovery PnL, but is a PnL-first alternate due lower WR.
- Do not optimize directly on the 56 validation cases and call the result OOS.
- No live implementation yet.
