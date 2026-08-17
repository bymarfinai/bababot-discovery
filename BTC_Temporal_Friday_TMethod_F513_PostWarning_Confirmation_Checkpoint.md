# BTC Friday15 T-Method — F5.13 Post-Warning Confirmation Timing

**Date:** 2026-08-17 WIB  
**Status:** F5.13 FAIL — WARNING DOES NOT CONVERT TO EXECUTABLE SHORT  
**Live BBC:** untouched

## Objective

Freeze the successful F5.12 `HIDDEN_CORE_EMA` causal `REVERSAL_WARNING` and test whether a compact causal confirmation after that warning identifies a profitable BUY->SHORT execution point.

F5.12 warning remained unchanged:
- `top_vs_global <= 0`
- `top_account_chg_15 < 0`
- `global_account_chg_15 < 0`
- `ema_spread_chg15 < 0`

Frozen parent:
- Friday15 WIB BUY
- TP2.0 / SL0.7 / hold360m

Frozen diagnostic SHORT:
- TP0.7 / SL0.7 / hold180m
- own 0.15% round-trip fee

Usable futures-metrics subset:
- 136 Friday occurrences
- discovery 81
- validation 55

## Confirmation families tested

No hidden-state threshold was retuned.

Fixed delays after warning:
- immediate (`DELAY_0`)
- +5m
- +10m
- +15m
- +20m

Natural completed-bar confirmations:
- first red 5m bar
- bearish structure: red bar + lower low
- seller flow: 5m return < 0 and taker imbalance < 0
- EMA deterioration: completed price below EMA7 while EMA spread remains contracting
- seller flow + EMA deterioration

For every confirmation three portfolios were compared:
1. HOLD original BUY parent
2. EXIT_ONLY at the execution open
3. REVERSE = close BUY + open frozen SHORT

A valid reversal required in discovery:
- at least 5 actions
- REVERSE PnL > parent PnL
- REVERSE PnL > EXIT_ONLY PnL
- standalone SHORT legs net positive

Validation was report-only and would have needed the same economic signs for milestone PASS.

## Result

**Discovery reversal candidates: 0.**

Therefore no validation selection occurred and F5.13 fails before any production-style promotion.

### Immediate reverse after F5.12 warning

Discovery:
- 26 actions
- parent PnL +$103.527
- EXIT_ONLY +$68.784 (delta -$34.743)
- REVERSE +$30.367 (delta -$73.160)
- standalone SHORT legs **-$38.418**
- SHORT WR 19.23%

Validation:
- 28 actions
- parent -$30.397
- EXIT_ONLY -$29.377 (delta +$1.020)
- REVERSE -$33.684 (delta -$3.287)
- standalone SHORT legs **-$4.307**

Full:
- 54 actions
- parent +$73.130
- EXIT_ONLY +$39.407
- REVERSE **-$3.318**
- standalone SHORT legs **-$42.725**

Immediate shorting is decisively rejected.

## Fixed-delay result

Waiting does not solve the problem.

Discovery standalone SHORT PnL:
- +5m: -$25.184
- +10m: -$12.321
- +15m: -$29.462
- +20m: -$29.199

Validation standalone SHORT PnL:
- +5m: -$5.872
- +10m: -$14.926
- +15m: -$4.282
- +20m: -$19.656

All REVERSE portfolios remain below the original parent in discovery.

## Confirmation result

### First red bar
Discovery:
- EXIT delta -$34.363
- REVERSE delta -$60.766
- SHORT leg -$26.403

Validation:
- EXIT delta +$0.232
- REVERSE delta -$10.779
- SHORT leg -$11.011

### Bearish structure (red + lower low)
Discovery:
- REVERSE delta -$65.284
- SHORT leg -$30.943

Validation:
- REVERSE delta -$13.746
- SHORT leg -$13.605

### Seller-flow confirmation
Discovery:
- EXIT delta -$29.935
- REVERSE delta -$54.076
- SHORT leg -$24.141

Validation:
- EXIT delta -$1.404
- REVERSE delta -$14.772
- SHORT leg -$13.368

### EMA deterioration
Discovery:
- EXIT delta -$28.552
- REVERSE delta -$56.886
- SHORT leg -$28.335

Validation:
- EXIT delta -$3.984
- REVERSE delta -$18.065
- SHORT leg -$14.081

### Seller flow + EMA deterioration
Discovery:
- REVERSE delta -$65.661
- SHORT leg -$30.308

Validation:
- REVERSE delta -$19.262
- SHORT leg -$17.705

No confirmation converts the warning into a profitable frozen-geometry SHORT.

## Interpretation

F5.12 remains a valid **risk-state warning**: it enriches the probability that a future useful reversal window will occur.

F5.13 shows that this does **not** imply a simple transition:

> warning -> wait a few minutes / see first bearish evidence -> SHORT

The market response after warning is still path-dependent. The warning marks deterioration of the Friday BUY response function, but the opposite directional edge is not yet strong or persistent enough to monetize with a sequential SHORT.

This also clarifies EMA's role:
- EMA contraction materially improved F5.12 warning timing.
- Further EMA deterioration does **not** provide a profitable SHORT confirmation in F5.13.
- Therefore EMA is currently supported as a **warning/context sensor**, not a direction-flip trigger.

## Scientific verdict

**F5.13 = FAIL / STOP for the direct reversal-router branch.**

Do not proceed directly to an F5.14 production BUY->SHORT router from this lineage.

The justified next question is different:

> Can the proven F5.12 warning improve the Friday BUY itself through risk / profit management while preserving all Friday entries, without assuming a new SHORT edge?

This would compare actions such as:
- hold unchanged,
- tighten downside risk only after warning,
- partial risk reduction,
- profit protection only after warning,
- potentially release the protection if hidden state recovers.

That direction is consistent with the earlier A6.50 finding that regime information behaved better as a **risk governor** than as a signal generator.

No live code was changed.
