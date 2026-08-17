# BTC Temporal Saturday T-Method S5.2A — Post-Failure Recovery / Shallow Runner Forensic

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — PRIOR FAILURE MEMORY IS CONTEXT, NOT A STANDALONE PROTECT GATE  
**Research only:** live BBC untouched  
**No management action promoted.**

## Frozen references

Parent — Saturday 18:00 WIB BUY / TP2.6% / SL1.2% / max18h:
- 139 trades
- PnL **+$87.200**

A7.19 full-coverage champion:
- 139 trades
- WR **50.36%**
- PnL **+$103.383**

A7.26 selective benchmark remains preserved separately:
- 123 trades
- WR **52.03%**
- PnL **+$109.587**

## S5.2A question

S5.1/S5.1B proved that early FAILURE is real diagnostically but cannot be monetized safely with direct CUT/FLIP. S5.2A therefore keeps FAILURE only as path memory and asks:

> once a Saturday BUY has causally proven some favorable impulse by reaching +0.50% MFE, does the path before that hinge identify recovery quality and the probability of graduating to +0.80%?

All pre-hinge variables use completed 5m information known no later than the +0.50 hinge-completion decision. DEEP/SHALLOW labels are forensic future outcomes only and cannot be used as live triggers.

## Frozen parity

- Parent: 139 trades / +$87.200
- A7.19: +$103.383
- First +0.50 hinge: **89 trades**
- Eventual DEEP runner >=+0.80: **61**
- Eventual SHALLOW runner +0.50..<+0.80: **28**

## 1. The +0.50 hinge remains extremely meaningful

### Reached +0.50
- N89
- parent WR **70.79%**
- parent PnL **+$249.638**
- A7.19 PnL **+$265.822**
- deep-runner rate **68.54%**
- discovery deep **70.37%**
- validation deep **65.71%**

### Never reached +0.50
- N50
- parent WR **4.00%**
- PnL **-$162.439**

This confirms that Saturday management should occur after favorable impulse rather than during early weakness.

## 2. Prior FAILURE memory: useful context, not a standalone selector

### CLEAN — no frozen FAILURE before +0.50
- N48
- WR **75.00%**
- parent PnL **+$177.833**
- A7.19 PnL **+$188.566**
- deep rate **72.92%**
- discovery deep **72.00%**
- validation deep **73.91%**

This is exceptionally stable.

### FAILURE then EMA reclaim before +0.50
- N40
- WR **65.00%**
- parent PnL **+$67.841**
- A7.19 PnL **+$73.292**
- deep rate **62.50%**
- discovery deep **68.97%**
- validation deep **45.45%**

The direction is weaker than CLEAN, but the discovery/validation gap is too large to use prior failure memory as a hard protection gate.

### FAILURE with no reclaim before +0.50
- N1 only
- not actionable.

## 3. Key reversal: CLEAN shallow is worse than recovered shallow

### CLEAN + DEEP
- N35
- WR **91.43%**
- parent PnL **+$212.652**
- A7.19 **+$216.893**

### CLEAN + SHALLOW
- N13
- WR **30.77%**
- parent PnL **-$34.819**
- A7.19 **-$28.327**

### FAILURE→RECLAIM + DEEP
- N25
- WR **76.00%**
- parent PnL **+$68.643**
- A7.19 **+$66.795**

### FAILURE→RECLAIM + SHALLOW
- N15
- WR **46.67%**
- parent PnL **-$0.802**
- A7.19 **+$6.497**

This is the most important S5.2A result:

> prior weakness does **not** identify the worst failed shallow runners. CLEAN trades that fail to graduate are economically worse than recovered-shallow trades.

Therefore do not route PROTECT simply because a trade had prior FAILURE.

## 4. Time-to-+0.50 is not a robust standalone quality score

Natural descriptive bins:
- <=60m: N8 / deep 75.00%
- 65–120m: N14 / deep 71.43%
- 125–240m: N28 / deep 67.86%
- >240m: N39 / deep 66.67%

There is a mild aggregate decline, but chronological behavior is not stable enough to use time-to-hinge as a hard rule. Among prior-failure trades the median time-to-+0.50 for deep vs shallow even reverses between discovery and validation.

Do not optimize a time-to-hinge cutoff.

## 5. Prior-failure persistence also fails as a standalone selector

Among +0.50 hinge trades with prior FAILURE:
- persistence >=10m: N35 / deep 60.00%; discovery 64.00%, validation 50.00%
- >=15m: N34 / deep 58.82%; discovery 62.50%, validation 50.00%
- >=20m: N31 / deep 58.06%; discovery 61.90%, validation 50.00%
- >=30m: N24 / deep 62.50%; discovery **62.50%**, validation **62.50%**

Persistence contains information but does not create a clean monotonic separation worth tuning.

## 6. Causal hinge features: one adaptive interaction is worth preserving

For all +0.50 trades, global hinge features are weak. But conditioned on **PRIOR FAILURE**, cumulative taker edge at the +0.50 hinge separates future deep vs shallow in the same direction in both chronology halves:

### PRIOR FAILURE — discovery
- future DEEP hinge taker median **+0.01918**
- future SHALLOW **+0.00113**

### PRIOR FAILURE — validation
- future DEEP **+0.00449**
- future SHALLOW **-0.00784**

Hinge EMA20 distance is also higher for deep than shallow in both halves:
- discovery: +0.3305% vs +0.2907%
- validation: +0.4429% vs +0.3433%

However, CLEAN trades show a different taker relationship, so a global taker threshold would be wrong. This is an **interaction**, not a universal gate.

Natural zero-sign diagnostic for prior-failure trades:
- hinge taker <=0: N17, deep 52.94%; discovery 63.64%, validation 33.33%
- hinge taker >0: N24, deep 70.83%; discovery 72.22%, validation 66.67%

Useful clue, but validation groups are only N6/N6 and no action is promoted.

## 7. Post-+0.50 path remains the strongest place to manage

### GRADUATE_FIRST — reaches +0.80 before meaningful giveback
- N22
- WR **86.36%**
- parent PnL **+$95.553**
- deep 100%

Once this happens, preserve the runner.

### PULLBACK_BEFORE_GRADUATE
- N37
- WR **78.38%**
- parent PnL **+$127.096**
- deep **67.57%**

For CLEAN trades specifically:
- N22
- deep 72.73%
- discovery deep 69.23%
- validation deep 77.78%
- WR 81.82%

This is strong evidence that a normal pullback after +0.50 should **not** be mechanically protected too aggressively.

### FAST_GIVEBACK — close <=+0.40 within 5m after +0.50
- N30
- WR 50.00%
- deep 46.67%
- discovery deep **60.00%** / WR 60.00%
- validation deep **20.00%** / WR 30.00%

Fast giveback remains strongly regime-dependent and cannot be used alone.

Conditioning FAST_GIVEBACK on prior-failure memory does not solve this:
- prior failure + fast giveback: N16
- discovery deep 54.55% / WR 63.64%
- validation deep 20.00% / WR 20.00%

So the original hypothesis `prior failure + fast giveback = protect` is **not robust enough**.

## 8. Shadow clue only: STRETCHED + prior FAILURE

Among +0.50 trades with prior FAILURE and pre-entry STRETCHED:
- N4 total = 2 discovery / 2 validation
- deep rate **0%**
- WR **0%**
- parent PnL **-$6.573**

Mechanistically compelling but far too sparse for promotion. Preserve only as a shadow observation; do not tune around it.

## S5.2A verdict

**PASS as forensic clarification.**

The initial idea was partly wrong in a useful way:

- prior FAILURE memory does lower aggregate recovery quality,
- but it is **not** the correct hard selector for protection,
- CLEAN shallow failures are actually more economically damaging than recovered shallow failures,
- time-to-hinge and failure persistence are not stable standalone selectors,
- normal pullbacks after +0.50 remain healthy,
- fast giveback alone remains regime-dependent,
- the most promising adaptive clue is an interaction: on trades that had prior FAILURE, the quality of flow/EMA confirmation at the +0.50 hinge matters.

## Correct continuation

Proceed to **S5.2B — Selective RUNNER vs PROTECT action test**, but do not restrict it to prior-failure trades.

The action test should start only after a causal +0.50 hinge and should:
1. automatically PRESERVE any trade that has already graduated to +0.80,
2. avoid protecting ordinary post-hinge pullbacks indiscriminately,
3. evaluate protection only when a shallow runner shows a causal giveback/failure event,
4. use prior-failure memory only as a context modifier, not a mandatory gate,
5. compare every result against exact A7.19 +$103.383 and preserved A7.26 +$109.587.

No thresholds should be selected from future DEEP/SHALLOW labels.