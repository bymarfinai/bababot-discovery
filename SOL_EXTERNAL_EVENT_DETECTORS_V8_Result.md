# SOL External Event Detectors V8 — Verified Result

Authoritative run: 35966476994
Head SHA: 6209db43cb9dca2a940c2ed0a4207333aad500cb
Artifact ID: 10794826156
Status: SUCCESS

External event families transplanted and benchmarked:
- CUSUM_UP
- DIRECTIONAL_CHANGE_UP
- PAGE_HINKLEY_UP
- BOCD_UP

Protocol:
- completed 15m trigger, next 15m open;
- standalone EVENT_ONLY and EVENT_IN_NEW_LONG_STATE context modes;
- exits all satisfy TP>=1% and RR>=1:1;
- one active position;
- 0.15% RT cost;
- parameters/context/exit selected by calendar 2023 only;
- 2024 validation, 2025/2026 frozen diagnostic transfer.

Frozen 2023-selected family candidates:
- CUSUM alpha=1 + NEW_LONG_STATE, TP3/SL3: 2023 47.6% WR, 2.08/day, +0.068% exp; 2024 42.4%, 1.93/day, -0.194%; 2025 41.8%, 1.82/day, -0.145%; 2026 31.3%, 1.46/day, -0.249%.
- Directional Change theta=0.50% + NEW_LONG_STATE, TP3/SL3: 2023 45.3%, 1.25/day, +0.034%; 2024 40.5%, 1.29/day, -0.236%; 2025 40.5%, 1.21/day, -0.111%; 2026 31.8%, 1.01/day, -0.031%.
- Page-Hinkley delta=.05/lambda=5 EVENT_ONLY, TP2/SL2: 2023 52.1%, 1.18/day, +0.058%; 2024 46.0%, 1.26/day, -0.225%; 2025 48.5%, 1.24/day, -0.136%; 2026 40.8%, 1.08/day, -0.175%.
- BOCD hazard=1/96 + NEW_LONG_STATE, TP2/SL2: 2023 53.1%, 0.57/day, +0.028%; 2024 46.7%, 0.54/day, -0.198%; 2025 47.3%, 0.51/day, -0.193%; 2026 38.9%, 0.46/day, -0.204%.

Full-grid 2024 frontier at >=1 executed trade/day:
- Directional Change theta=1.50% + NEW_LONG_STATE, TP1/SL1: 52.90% WR, 1.32/day, -0.089% exp/trade.
- No configuration in the entire 324-config V8 grid simultaneously had >=1/day and positive expectancy in 2024.
- No 2024 configuration approached 65% or 70% WR at >=1/day.

Interpretation:
External event-sampling/change-point algorithms successfully change WHEN the market is sampled, but none separates SOL long winners from losers at the required strength. Directional Change is the best 2024 event-only architecture among this family, yet remains around 53% WR and negative after cost.

The external-repo hypothesis has therefore been tested directly. Copying more variants of CUSUM, DC, Page-Hinkley, or BOCD is not justified by this evidence.

VERDICT: NO_EXTERNAL_EVENT_GATE_PASS_V8