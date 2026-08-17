# BTC Friday15 T-Method — F5.7 to F5.10 Reversal-Pivot Checkpoint

**Date:** 2026-08-17 WIB  
**Status:** REVERSAL CAPACITY CONFIRMED, CAUSAL ROUTER REJECTED  
**Live BBC:** untouched  

## Research question

Can Friday15 BUY improve by identifying a near-optimal reversal point, closing BUY, and reversing into SHORT instead of merely protecting profit?

Frozen parent throughout:
- BTCUSDT
- every Friday exact 15:00 WIB BUY
- TP 2.00%
- SL 0.70%
- max hold 6h
- $500 notional reference
- 0.15% round-trip fee
- all 138 Friday entries retained

---

# F5.7 — Oracle Reversal Pivot Atlas

Script: `btc_temporal_friday15_f57_reversal_pivot_atlas.py`

Diagnostic SHORT geometry was fixed deliberately:
- SHORT TP0.70 / SL0.70 / hold180m
- own 0.15% round-trip fee

Every causal 5m decision open from +15m through +180m was evaluated while the parent BUY was still alive. The oracle then selected the best historical BUY-close + SHORT pivot only to measure capacity.

Parent:
- N 138
- WR 47.83%
- PnL +$64.630
- PF 1.266
- DD $56.530
- LS 8

Oracle capacity:
- qualifying reversal occurrences: **88 / 138 = 63.8%**
- strong reversal occurrences: **74 / 138**
- total theoretical oracle uplift: **+$469.491**
- qualifying median pivot: **77.5m**
- strong median pivot: **67.5m**
- strong median MFE before pivot: 0.3905%
- strong median progress at pivot: +0.3379%
- strong median giveback: only 0.0780%

Chronology:
- discovery: 45/82 qualifying, 54.9%, oracle gain +$247.365, median pivot 85m
- validation: 43/56 qualifying, 76.8%, oracle gain +$222.125, median pivot 70m

Parent-loss attribution:
- parent SL: 51 occurrences; **46 / 51 = 90.2%** have oracle reversal capacity; theoretical gain +$333.790
- TIMEOUT: 40 / 68 qualifying; gain +$133.060
- TP: only 2 / 19 qualifying

Important caveat: pivot distribution is not a clean single cluster. 15m and 180m scan boundaries contain many oracle selections. Therefore 67.5m/77.5m must NOT be interpreted as a deployable fixed reversal time.

### F5.7 conclusion

The economic capacity is real and very large. Many eventual Friday BUY losses could theoretically be improved by reversing before the later decline. But this is pure future-information capacity.

---

# F5.8 — Pre-Pivot Causal Signature

Script: `btc_temporal_friday15_f58_prepivot_causal_signature.py`

At each causal 5m decision point, features available at that exact time were computed. Future diagnostic label:

> GOOD_REVERSE = fixed SHORT leg net >= $1 and combined BUY-close + SHORT improves frozen parent by >= $2.

Dataset:
- 138 entries
- 3,945 causal candidate events
- future-good event rate 19.3%

## Key finding: exact-pivot state is not causally separable

Feature discovery/validation AUC values are generally near 0.50 and many reverse direction across chronology.

The only same-direction features have negligible discovery strength:
- taker30: AUC 0.4853 / 0.4254
- MAE: 0.4924 / 0.4853
- taker5: 0.4942 / 0.4530

Features that looked stronger in discovery fail direction stability:
- volume_ratio: 0.6141 / 0.4691
- range_ratio: 0.5759 / 0.4707
- progress: 0.5453 / 0.4597

## What happens immediately before the oracle pivot?

Among 48 strong oracle pivots with a valid 15m-before comparison, the market usually becomes **more bullish**, not visibly bearish, into the ex-post optimum:
- progress median change: **+0.1386%**
- ret5: +0.0847%
- ret15: +0.0833%
- ret30: +0.0916%
- MFE: +0.0654%
- range_ratio: +0.1612
- volume_ratio: +0.1510
- giveback change: **-0.0438%**

Thus the oracle often chooses the terminal bullish burst immediately before the later drop. It does NOT wait for a clean bearish reversal confirmation.

## Earliest future-good reversal

74 / 138 Fridays have at least one future-good reversal point.
- median earliest future-good point: **20m**
- discovery median: 25m
- validation median: 15m

Again, this is future-labelled and not directly deployable.

### F5.8 conclusion

There is no stable causal signature that identifies the exact ex-post top. The best theoretical pivot often occurs while current observable price action still looks bullish.

---

# F5.9 — Causal Sequential Reversal Router

Script: `btc_temporal_friday15_f59_causal_reversal_router.py`

140 compact causal rules were tested using first-fire sequential execution.

Two predeclared mechanism families:
1. **EXHAUSTION** — positive BUY progress + terminal range/volume/buyer burst.
2. **CONFIRMATION** — useful MFE followed by giveback + negative return / seller-flow confirmation.

For every signal, two alternatives were measured:
- EXIT_ONLY: close BUY at actual signal open.
- REVERSE: close BUY and open fixed SHORT 0.7/0.7/180m.

A reversal candidate was only acceptable in discovery when:
- REVERSE beats the original parent,
- REVERSE beats EXIT_ONLY,
- standalone SHORT legs are net profitable,
- at least 5 actions occur.

Results:
- discovery reversal candidates: **0**
- strict discovery+validation cross-positive reversals: **0**
- strict cross-positive EXIT_ONLY rules: **0**

### F5.9 conclusion

Neither terminal-burst detection nor delayed bearish confirmation converts oracle reversal capacity into a causal economic router.

---

# F5.10 — SHORT Geometry Sensitivity

Script: `btc_temporal_friday15_f510_reversal_geometry_sensitivity.py`

To determine whether F5.9 failed only because the fixed SHORT geometry was unsuitable, the exact same causal trigger families were retested with four broad SHORT shapes:

1. TP0.7 / SL0.7 / hold180m
2. TP1.0 / SL0.7 / hold240m
3. TP1.3 / SL0.7 / hold360m
4. TP1.5 / SL0.5 / hold360m

Results for **every geometry**:
- discovery candidates: **0**
- cross-positive candidates: **0**

### F5.10 conclusion

The failure is not explained by SHORT TP/SL geometry. The bottleneck is causal identification/timing of the reversal state.

---

# Final scientific verdict

The user's hypothesis is economically meaningful:

> Many Friday15 BUY losses really do contain a later opposite-direction move large enough that an ideally timed BUY->SHORT reversal would materially improve performance.

But the strongest evidence says:

> **The optimum reversal point is visible ex-post but not reliably identifiable ex-ante from the tested price-path, range/volume, taker-flow, giveback, and simple structural features.**

The oracle commonly wants to reverse while observable market state is still in a final bullish expansion. Waiting for bearish confirmation comes too late or creates too many false reversals; trying to anticipate the top from expansion also does not survive causal economics.

Therefore do NOT implement a Friday "reverse at optimal pivot" rule from F5.7-F5.10.

This does not invalidate the broader idea of dynamic direction switching. It means the next justified direction would require a qualitatively different information source or state representation, for example:
- order-book / liquidation / positioning transition data available at the exact live timestamp,
- an online state-change model trained only on prior Fridays,
- or using the existing regime detector as a prior and asking for reversal confirmation only inside defensive regimes.

Do not expand thresholds/features on the same 138-Friday sample merely to force a positive router.

F5.4/F5.5 selective PROTECT and A6.x regime-risk lineage remain separate and are not replaced by this rejected reversal router.

**Live BBC remains untouched.**
