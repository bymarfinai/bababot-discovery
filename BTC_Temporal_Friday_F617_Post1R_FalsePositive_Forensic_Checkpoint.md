# BTC Temporal Friday F6.17 — Post-+1R False-Positive Forensic Checkpoint

**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT RULE TUNED OR PROMOTED  
**Live BBC untouched. Existing F6.12/F6.9/F6.5 stack unchanged.**

## Question
Why did F6.16 P1 (`post +1R, observe 15m, median taker<0 AND latest close<EMA7`) correctly identify true givebacks but also cut eventual winners?

## Exact cohort parity
The active F6.16 P1 cohort is reproduced exactly:
- **16 active P1 actions**
- **6 true residual +1R givebacks**
- **10 eventual parent winners (false positives)**
- Discovery: 4 true givebacks + 10 false-positive winners
- Validation: 2 true givebacks + **0 false-positive winners**

The absence of Validation false-positive winners means no separator from this atlas can yet be called independently D/V-confirmed.

## Central finding — momentum death looks like bearish displacement, not merely EMA7 loss
Both groups already satisfy taker-flow deterioration + close below EMA7 by construction. The strongest additional causal separator at the exact F6.16 decision time is the **morphology/severity of the final completed 5m candle**.

### Final 5m candle body
- True giveback median body/range: **79.79%**
- False-positive winner median: **54.02%**
- AUC toward true giveback: **0.817**
- Discovery AUC: **0.750**

Validation true givebacks independently show very large final bearish bodies:
- 2025-11-21: **87.10% body**, upper wick **0.38% of range**
- 2026-02-27: **80.11% body**, upper wick **0%**

All 16 final candles are bearish, so the distinction is not simply red vs green. It is **how decisively bearish the candle is**.

### Upper wick
- True giveback median upper wick: **7.40%** of range
- False-positive winner median: **28.89%**
- AUC true-high = 0.233, i.e. lower upper wick is associated with true death (inverse strength ~0.767)

Interpretation: many false-positive winners are undergoing a wicky/noisy pullback, while true givebacks more often print a relatively one-directional bearish displacement candle with little rejection of sellers.

### Last-bar price displacement
- True giveback median last close vs previous close: **-0.255R**
- False-positive winner median: **-0.129R**
- inverse AUC strength ~**0.717**

So true givebacks are falling about twice as hard on the final confirmation bar.

## Trend-structure context
`EMA7 > EMA20` at the decision point:
- True givebacks: **66.7%**
- False-positive winners: **100%**
- Discovery true/false: **75% / 100%**
- Validation true: **50%**

This is only a partial clue: breaking the EMA7/EMA20 stack is more specific to true death, but many true givebacks still have EMA7 above EMA20. Therefore EMA20 should be treated as context/guard, not a standalone classifier.

Median close distance to EMA20:
- true: **-0.060%**
- false-positive winner: **+0.028%**

Directionally, winners more often retain deeper trend support even after losing EMA7.

## Profit retention / drawdown
- median retained fraction of post-+1R excursion: true **39.7%** vs false-positive winner **53.3%**
- median progress at decision: true **0.493R** vs false winner **0.622R**
- median drawdown from observed best: true **0.770R** vs false winner **0.520R**

These are directionally sensible but weaker cross-case separators than final-candle morphology.

## What does NOT solve the false-positive problem
- `stretch 1.618` remains similar inside this already-triggered cohort: **66.7% true vs 60.0% false winner**.
- milestone rejection candle: **16.7% true vs 30.0% false winner**.
- taker flow itself is already negative in both groups and does not cleanly separate the two after conditioning on P1.
- simple last-close-up/recovery is absent: all 16 still have a falling final close at this decision time.

Therefore the F6.16 false positives are not caused by missing a simple green recovery candle before the decision. The more useful distinction is **weak/noisy pullback vs decisive bearish displacement**.

## Mechanistic reading
The current best causal sequence is:

### Healthy pullback / false P1 alarm
`+1R achieved -> flow temporarily weakens -> EMA7 lost -> pullback remains comparatively wicky / smaller-bodied -> EMA7-EMA20 structure often intact -> later re-acceleration`

### True momentum death
`+1R achieved -> flow weakens -> EMA7 lost -> final 5m develops large bearish body with little upper wick -> larger last-bar displacement / greater giveback -> sometimes deeper EMA20 structure also breaks -> trade later finishes negative`

## Guardrail
This is a 16-case same-sample forensic atlas. In particular, all 10 false-positive winners are in Discovery and Validation contains only two true givebacks. **Do not tune a body-ratio or wick threshold from this sample and do not promote a new exit yet.**

The next clean test should predeclare a very small number of natural hypotheses around **bearish displacement confirmation** (e.g. flow+EMA7 deterioration plus final-candle severity / EMA20 structure) and test economics without threshold sweeps. Genuine future Friday triggers are still needed for independent OOS confirmation.
