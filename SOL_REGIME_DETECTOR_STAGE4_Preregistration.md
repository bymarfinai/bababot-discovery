# SOL Regime Detector — Stage 4 Hysteresis / Transition Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 4 converts the valid Stage-3 raw score stream into a causal state machine with:
- one incumbent regime: BULL / BEAR / SIDEWAYS
- hysteresis
- persistence-confirmed switching
- fast switching only for strong score displacement
- explicit transition_flag
- final confidence

Stage 4 uses 2023-2024 raw scores only. No 2025/2026 rows, forward returns, TP/SL, trade outcomes, MFE/MAE, or strategy performance are used.

## Frozen state machine

### Startup
- First finite Stage-3 provisional class seeds the incumbent regime.
- No backfilling or future confirmation is allowed.

### Normal regime switch
A challenger may replace the incumbent only if:
1. challenger is the raw provisional winner for **3 consecutive completed 1H bars**, and
2. the raw top-vs-second score margin is at least **0.08 on every bar in that challenger streak**.

### Fast switch
A challenger may replace the incumbent after **2 consecutive completed 1H bars** only if:
1. challenger is the raw provisional winner on both bars, and
2. challenger score exceeds incumbent score by at least **0.18 on every bar in that streak**.

Fast switching is allowed for any regime pair, including direct BULL↔BEAR, but only under the frozen strong-displacement rule.

### Transition flag
transition_flag = true if any applies:
- raw provisional regime differs from incumbent,
- raw score margin < 0.08,
- incumbent score < 0.45,
- a challenger streak is currently active.

transition_flag is a flag only; it is not a fourth regime.

### Confidence
Let:
- I = incumbent regime score
- A = I - max(other two regime scores)
- normalized incumbent advantage = clip01(0.5 + A / 0.30)

Then:
- base confidence = 0.70*I + 0.30*normalized incumbent advantage
- if transition_flag=true, final confidence = 0.70 * base confidence
- otherwise final confidence = base confidence
- clip final confidence to [0,1]

## Frozen outputs
For every valid 1H bar:
- final_regime
- transition_flag
- final_confidence
- regime_duration_hours
- challenger_regime
- challenger_streak
- switch_event
- switch_reason
- incumbent_score
- incumbent_advantage
- raw provisional regime / raw scores retained for audit transparency

## Mandatory Stage-4 audits
1. Stage-3 status must be VALID.
2. Output contains only 2023-2024 rows.
3. final_regime contains only BULL / BEAR / SIDEWAYS.
4. transition_flag is separate from final_regime.
5. final_confidence is always in [0,1].
6. Prefix-causality replay at frozen checkpoints matches the full-run state exactly.
7. Every emitted switch satisfies either NORMAL_3BAR or FAST_2BAR rule.
8. No future/outcome/TP/SL/MFE/MAE fields exist.
9. Each final regime occupies at least 5% of valid DEV rows.
10. transition_flag share must be between 5% and 60%.
11. Total final regime switches must be <=70% of raw provisional switches.
12. One-bar final regime runs must be <=10% of final runs.
13. Median final regime duration must not be lower than raw provisional median for any of the three regimes.

Stage 4 passes only if all mandatory audits pass.
