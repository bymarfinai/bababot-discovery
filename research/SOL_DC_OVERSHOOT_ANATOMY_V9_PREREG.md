# SOL DC Overshoot Anatomy V9 — Preregistration

## Frozen parent event
- Directional Change upturn confirmation with theta = 0.50%.
- Event is eligible only when causal NEW_LONG_BUILD context is active at the completed 15m confirmation close.
- Theta/context are frozen from the V8 2023-selected Directional Change family candidate.

## Overshoot cycle
- DC state is tracked causally on completed 15m closes.
- For each eligible upturn confirmation, the cycle ends at the next causal downturn confirmation under the same theta.
- Trading reference entry = next 15m open after upturn confirmation.
- Overshoot MFE is measured from that entry until the next downturn-confirmation close.
- Labels: OS1, OS2, OS3 = whether +1%, +2%, +3% is touched before the cycle ends.
- Future cycle information is used only for labels, never as a feature.

## Causal anatomy features at upturn confirmation
- DC trough-to-confirmation amplitude and excess above theta;
- bars/minutes from trough to confirmation;
- preceding downswing amplitude and duration when available;
- path efficiency from trough to confirmation;
- confirmation candle body, range, close-location, wick geometry;
- 15m returns over 1/2/4/8/16 bars;
- ATR %, range/ATR, EMA20 distance/slope;
- 4/8/16-bar compression;
- volume burst if available;
- causal derivatives-state descriptors already available before entry: OI 1h/4h regime z, top-vs-global positioning z, top-account z, taker-flow z, quote-burst z, funding z, 60m taker imbalance.

## Partitions
- Anatomy discovery: 2023.
- Stability check: 2024.
- 2025/2026 remain untouched in V9.

## Stable-separator gate
For each OS1/OS2/OS3 label, a feature is a stable differentiator only if:
- same SMD sign in 2023 and 2024;
- abs(SMD) >= 0.15 in both years;
- orientation-free ROC AUC >= 0.55 in both years.

V9 passes anatomy gate if at least 3 stable differentiators exist for any one overshoot target and that target has >=500 eligible events in both 2023 and 2024.

If V9 passes, proceed to V10 detector with only the stable V9 feature family plus frozen baseline controls.
If V9 fails, stop the DC-overshoot branch before detector optimization.