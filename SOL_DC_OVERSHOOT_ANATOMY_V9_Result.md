# SOL DC Overshoot Anatomy V9 — Verified Result

Authoritative run: 36083549009
Head SHA: 39f60f642a0dbdd68f32d46fe7b0020c42dc26e9
Artifact ID: 10842462465
Status: SUCCESS

Frozen event: Directional Change upturn theta 0.50% inside causal NEW_LONG_BUILD context.
Eligible cycles across 2023-2024: 1,880.

Base rates:
- OS1: 2023 38.98%, 2024 37.60%, 2 stable separators.
- OS2: 2023 16.48%, 2024 13.70%, 5 stable separators.
- OS3: 2023 8.64%, 2024 5.70%, 10 stable separators.

Strongest OS3 stable separators:
- ret1 / price_ret15: SMD +0.594 (2023), +0.785 (2024); AUC 0.625 / 0.618.
- up_amp_pct / excess_pct: SMD +0.584 / +0.719; AUC 0.623 / 0.578.
- ATR%: SMD +0.314 / +0.779; AUC 0.606 / 0.624.
- ret4 / price_ret1h: SMD +0.347 / +0.462.
- bars_trough_confirm: SMD -0.309 / -0.322.
- bars_peak_trough: SMD -0.265 / -0.424.

Interpretation:
Large overshoots are rare, but successful OS2/OS3 events are not anatomically identical to failures. Stronger immediate momentum, larger/faster DC confirmation, higher volatility, and shorter confirmation/pre-swing durations separate successful overshoots with the same direction in both 2023 and 2024.

VERDICT: ANATOMY_GATE_PASS__os2__os3