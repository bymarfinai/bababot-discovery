# SOL Structure-Specific Native Trigger V2 — Preregistration

## Objective
Test a second, materially different entry trigger native to each already-frozen SOL structural setup. This experiment does **not** redefine the underlying structures and does not tune TP/SL, hours, indicators, regime filters, or trigger thresholds after observing results.

## Frozen data and evaluation
- Symbol/timeframe: SOLUSDT 5m.
- Structural contexts: reuse `detect_setups()` from `sol_structure_trigger_matrix_v1.py` exactly.
- Evaluation universe: 2020-2024.
- 2025+ remains CLOSED.
- Long only.
- Entry: next 5m open after the causal trigger bar closes.
- Diagnostic exit: fixed +60m from entry.
- Round-trip cost: 0.15%.
- $500 notional for PnL reporting.
- Trigger observation window: maximum 12 completed 5m bars / 60 minutes after setup completion.
- A structure invalidates before entry when a completed close violates the setup's frozen invalidation level.

## Frozen native trigger V2 definitions

### 1. SWEEP_RECLAIM -> RECLAIM_CANDLE_HIGH_BREAK
The structure is already complete on the frozen sweep/reclaim setup bar. Freeze that setup bar's high as the trigger level. During the next 12 completed 5m bars, while no completed close loses the swept/reclaimed anchor level, trigger on the first completed close strictly above the setup/reclaim candle high.

### 2. HL_SETUP -> FIRST_POST_HL_SWING_HIGH_BREAK
The HL structure is already complete when its pivot low is causally confirmed. After setup completion, identify the first new causal pivot high (same frozen 2-left/2-right pivot definition used by the library) whose pivot occurs after the HL pivot. Once that pivot high is confirmed and while no completed close loses the HL price, trigger on the first later completed close strictly above that post-HL swing-high price. The full process must occur within the frozen 12-bar window.

### 3. BREAKOUT_PULLBACK_SETUP -> PULLBACK_PIVOT_HIGH_BREAK
The breakout/pullback structure is already complete when the frozen pullback pivot low is causally confirmed. Freeze the **high of the pullback pivot-low candle itself** (`secondary_pivot_i`) as the trigger level. During the next 12 completed bars, while no completed close loses the frozen breakout level, trigger on the first completed close strictly above that pullback-pivot candle high.

### 4. FAILED_BREAKDOWN_RECLAIM -> RECLAIM_CANDLE_HIGH_BREAK
The failed-breakdown structure is already complete on its frozen reclaim bar. Freeze that reclaim/setup candle high as the trigger level. During the next 12 completed bars, while no completed close loses the reclaimed breakdown level, trigger on the first completed close strictly above the reclaim candle high.

## Output per detector
For each exact structure + native-trigger pair report:
- setup count,
- triggered trade count / conversion rate,
- trigger delay,
- WR at +60m,
- net expectancy after cost,
- PF,
- PnL,
- max drawdown,
- max loss streak,
- clean-up-impulse incidence,
- median MFE, MAE, MFE/|MAE|,
- yearly 2020/21/22/23/24 economics.

## Frozen promotion gates
A detector advances to characterization only if **all** hold:
1. N >= 100.
2. Pooled +60m net expectancy > 0.
3. Pooled PF >= 1.15.
4. Positive PnL in >= 4 of 5 years.
5. Median MFE/|MAE| >= 1.20.

`REJECTED_AS_DEFINED` rejects only this exact trigger for that frozen structure. No rescue on 2020-2024 by changing trigger window, structure levels, hours, indicators, regime filters, TP, SL, or adding confirmation after results.
