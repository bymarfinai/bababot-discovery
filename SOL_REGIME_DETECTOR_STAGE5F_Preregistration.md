# SOL Regime Detector — Stage 5F Failure Forensics Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 5F diagnoses where directional information is lost between early causal movement evidence and the final Stage-4 regime state.

This is **forensics only**:
- no Stage-2 feature definition is changed,
- no Stage-3 score is changed,
- no Stage-4 hysteresis rule is changed,
- no threshold is selected from future outcomes,
- no 2025/2026 data are used.

## DEV boundary
- Event detection: 2023-01-01 through 2024-12-31.
- Future labeling: SOLUSDT perpetual futures 5m, entirely within the same 2023-2024 boundary.
- Entry/reference price: next 1H open = Stage-2/3/4 `decision_time`.
- Future ±1% first-hit horizons: 6H, 12H, 24H.
- Same-5m +1% and -1% touch = AMBIGUOUS.
- Events whose full requested horizon crosses 2025-01-01 are excluded for that horizon.

## Frozen causal milestones

All milestones are generated without looking forward.

### M0 — IMPULSE_START
Natural early directional displacement marker, not a regime label.

Let:
`impulse3 = h1_ret_3 / h1_atr_norm`.

BULL event:
- impulse3 >= +1.00,
- previous completed 1H impulse3 < +1.00,
- h1_ema20_slope3_atr > 0.

BEAR event:
- impulse3 <= -1.00,
- previous completed 1H impulse3 > -1.00,
- h1_ema20_slope3_atr < 0.

### M1 — STRUCTURE_BREAK
BULL event:
- `h1_break_above_last_high == True`,
- previous completed 1H value was False.

BEAR event is symmetric for `h1_break_below_last_low`.

### M2 — STRUCTURE_CONFIRM
BULL event:
- causal Stage-2 `h1_structure_state` changes into `BULL_SEQ`.

BEAR:
- state changes into `BEAR_SEQ`.

### M3 — RAW_SCORE_SWITCH
BULL event:
- Stage-3 `provisional_regime` changes into BULL from another provisional class.

BEAR is symmetric.

### M4 — FINAL_SWITCH
BULL/BEAR event:
- Stage-4 `switch_event == True`,
- `switch_reason` is NORMAL_3BAR or FAST_2BAR,
- final regime is BULL or BEAR.
- STARTUP_SEED is excluded.

## Frozen forensic measurements

For every milestone and side:

### Already-consumed move
From Stage-2 causal features at the event bar:
- aligned pre-3H return = h1_ret_3 × side_sign
- aligned pre-6H return = h1_ret_6 × side_sign
- aligned pre-12H return = h1_ret_12 × side_sign
- aligned pre-24H return = h1_ret_24 × side_sign

where BULL sign=+1 and BEAR sign=-1.

### Future directional quality
At 6H, 12H, 24H:
- aligned ±1% first-hit rate among resolved outcomes,
- aligned forward return,
- aligned MFE / adverse excursion.

### Temporal robustness
24H aligned first-hit rate is reported separately for:
- 2023-H1
- 2023-H2
- 2024-H1
- 2024-H2

## Event-chain latency

For every M4 FINAL_SWITCH, Stage 5F looks backward **up to 72 hours**, same side only, and records the most recent preceding:
- M3 RAW_SCORE_SWITCH,
- M2 STRUCTURE_CONFIRM,
- M1 STRUCTURE_BREAK,
- M0 IMPULSE_START.

This linkage is diagnostic only and never changes event labels.

Report:
- median M0→M4 delay,
- M1→M4,
- M2→M4,
- M3→M4,
- share of M4 switches with each preceding milestone found within 72H.

## Frozen forensic interpretations

### LATENCY_HYPOTHESIS_SUPPORTED
Only if ALL are true:
1. At least one of M0/M1/M2 has combined Bull+Bear 24H aligned first-hit rate at least **5 percentage points** above M4.
2. The same early milestone beats M4 in at least **3 of 4** half-year blocks on combined aligned hit-rate.
3. Median same-side delay from that milestone to M4 is >0 hours among linked chains.
4. M4 median aligned pre-6H return is greater than the early milestone's median aligned pre-6H return.
5. M4 median aligned future-24H return is lower than the early milestone's.

### DIRECTIONAL_FEATURES_WEAK
If no milestone M0-M4 reaches **55% combined aligned 24H first-hit** and no early milestone beats M4 by at least 5pp.

### EDGE_LOSS_AT_<STEP>
If the latency hypothesis is supported, identify the **largest consecutive decline** in combined 24H aligned hit-rate among:
M0→M1→M2→M3→M4.
This is a forensic localization, not an authorization to tune that step.

## Mandatory technical audits
1. Stage-5 status is REGIME_VALIDATION_FAILED (forensics only after failure).
2. Stage-2 feature rows, Stage-3 scores, and Stage-4 states are consumed unchanged.
3. 5m DEV coverage >=99.5%.
4. No event/future window used crosses 2025-01-01.
5. No milestone definition references future fields.
6. Same-5m ambiguous first-hit share <=2% for every milestone×side at 24H.
7. Each milestone has at least 200 combined BULL+BEAR eligible 24H events.
