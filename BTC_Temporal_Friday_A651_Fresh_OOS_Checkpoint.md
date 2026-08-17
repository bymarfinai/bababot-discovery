# BTC Temporal Friday15 — A6.51 Fresh OOS Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** FRESH OOS OBSERVATION — INSUFFICIENT TO VALIDATE A6.50  
**Historical research cutoff:** 2026-07-30  
**Fresh OOS Fridays:** 2026-07-31, 2026-08-07, 2026-08-14  
**Frozen rules tested:** A6.33 + A6.48 + A6.50, no OOS retuning  
**Live BBC:** untouched

## Result

The first genuinely unseen Friday sample is small (N=3) and negative:

| Date | A6.48 state | stress_unwind | A6.50 scale | A6.33/A6.50 PnL |
|---|---|---:|---:|---:|
| 2026-07-31 | NORMAL | true | 1.00x | -$4.250 |
| 2026-08-07 | NORMAL | false | 1.00x | +$4.663 |
| 2026-08-14 | NORMAL | false | 1.00x | -$2.725 |

Fresh OOS aggregate:
- N3
- WR33.33%
- PnL **-$2.312**
- expectancy -$0.7706/Friday
- PF0.669
- MDD $4.250
- LS1

Because no OOS Friday satisfied `DEFENSIVE + stress_unwind`, A6.50 never reduced risk. Therefore A6.33 and A6.50 produce identical OOS outcomes here.

## Per-Friday causal state

### 2026-07-31

Before entry:
- A6.48 DEFENSIVE = false
- FAST8 average shadow PnL = +$0.3706
- SLOW13 = +$0.7882
- rolling conditional stress history N1, below minimum N2
- current stress_unwind = true
- scale = 1.00x

Outcome:
- A6.33/A6.50 = -$4.250
- parent exit reason = SL
- raw 120m return = -0.344%

This is the most important miss: current pre-entry stress was present, but the prior-outcome regime detector was still healthy, so the two-layer A6.50 trigger intentionally did not fire.

### 2026-08-07

Before entry:
- DEFENSIVE = false
- FAST8 = -$0.4731
- SLOW13 = -$0.2503
- conditional N2, conditional PnL -$5.375, conditional 120m return -0.3634%
- current stress_unwind = false
- scale = 1.00x

Outcome:
- +$4.663
- parent timeout
- raw 120m return +0.809%

This is useful counterevidence against simply reducing risk whenever recent shadow health is negative: this Friday was profitable despite negative FAST/SLOW/conditional history.

### 2026-08-14

Before entry:
- DEFENSIVE = false
- FAST8 = +$0.0709
- SLOW13 = +$0.0892
- conditional N2, PnL -$5.375, conditional 120m return -0.3634%
- current stress_unwind = false
- scale = 1.00x

Outcome:
- -$2.725
- parent timeout
- raw 120m return -0.197%

This loss was not preceded by the current stress-unwind mechanism, so A6.50 was not designed to reduce it.

## Combined historical + fresh OOS bookkeeping

If the three OOS Fridays are simply appended to A6.33 history:
- N141
- WR60.28%
- PnL +$138.713
- expectancy +$0.9838
- PF1.684
- MDD remains $46.318
- max loss streak remains4

A6.50 has the same N141 figures because none of the three OOS cases triggered scaling.

Important: these combined figures are bookkeeping only. The original historical A6.50 result (+$149.305) included historical half-risk scaling on nine prior cases, while this simple combined report preserves the script's historical A6.33 shadow outcomes plus the OOS actual-scale outcomes. Do not use the N141 line to replace the previously reported historical A6.50 backtest summary.

## Scientific interpretation

1. N=3 is far too small to validate or reject the Friday edge.
2. Fresh OOS is currently negative, so there is no basis to claim A6.33 or A6.50 has passed fresh OOS.
3. A6.50 received **zero direct OOS trigger tests** because `DEFENSIVE + stress_unwind` never occurred together.
4. 2026-07-31 shows a possible lag cost in the two-layer detector: current stress appeared before the historical response-health state became DEFENSIVE.
5. 2026-08-07 is the counterexample preventing a retrospective relaxation of the trigger: recent health metrics were negative but the Friday made money.
6. 2026-08-14 shows losses also occur outside stress_unwind, so the stress mechanism is not intended to explain every losing Friday.
7. Do **not** modify FAST/SLOW windows, hysteresis, or remove the DEFENSIVE requirement based on these three outcomes. That would contaminate the first fresh OOS sample and turn it into training data.

## Correct next step

Keep A6.33/A6.48/A6.50 frozen and continue collecting future Fridays in shadow mode. The next key observation is not merely whether Friday wins or loses; it is whether a future Friday actually enters `DEFENSIVE + stress_unwind`, allowing A6.50's 50% risk action to receive a genuinely fresh test.

No live trading code was changed.
