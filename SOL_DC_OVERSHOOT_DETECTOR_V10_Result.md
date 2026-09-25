# SOL DC Overshoot Detector V10 — Verified Result

Authoritative run: 36083805943
Head SHA: 31b728fdeada9857d0125c41a10697fc873abc61
Artifact ID: 10843093106
Status: SUCCESS

Frozen parent:
- Directional Change upturn theta 0.50%
- causal NEW_LONG_BUILD context
- V9 stable anatomy only

V10 target-matched execution:
- OS2 -> TP2 / SL2 / RR1:1 / 24h max hold
- OS3 -> TP3 / SL3 / RR1:1 / 24h max hold
- 0.15% RT cost
- one active position

Frozen transfer:
- OS2 RF q=0.50:
  - 2024: 369 trades, 51.76% WR, 1.008/day, -0.020% exp/trade, -0.14% mean weekly.
  - 2025: 355 trades, 48.45% WR, 0.973/day, -0.140% exp/trade, -0.94% mean weekly.
  - 2026: 162 trades, 44.44% WR, 0.684/day, -0.199% exp/trade, -0.92% mean weekly.
- OS3 TREE q=0.50:
  - 2024: 472 trades, 40.47% WR, 1.290/day, -0.236% exp/trade, -2.11% mean weekly.
  - 2025: 440 trades, 40.45% WR, 1.205/day, -0.111% exp/trade, -0.93% mean weekly.
  - 2026: 239 trades, 31.80% WR, 1.008/day, -0.031% exp/trade, -0.21% mean weekly.

Interpretation:
V9 showed genuine statistical anatomy differences between large overshoots and failures, especially for OS3. However, those differences are not strong enough to yield a high-precision executable detector at the required >=1 trade/day frequency. OS2 barely preserves frequency in 2024 but remains negative and degrades in 2025/2026. OS3 is materially weaker.

Stop rule:
V10 detector gate failed for both OS2 and OS3. V11 entry/exit optimization and V12 final robustness are NOT authorized, because optimizing execution on a detector without a validated edge would be post-hoc curve fitting.

VERDICT: NO_V10_DETECTOR_GATE_PASS__STOP_BEFORE_V11