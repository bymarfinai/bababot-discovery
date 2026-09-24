# SOL Leg MAE / Exit Geometry V6 — Verified Result

Run ID: 35956489234
Head SHA: 8e7e547673ad97c11256b33f0dbd486d8959b9c0
Status: SUCCESS
Artifact ID: 10790244730
Price coverage: 99.76977%

Parents:
- NEW_LONG_BUILD rising edge
- ABSORPTION_RELEASE rising edge

All tested exits preserve TP >= 1% and reward:risk >= 1:1.

## MAE before eventual target, stop ignored (diagnostic only)

### NEW_LONG_BUILD
L2:
- 2023 p25/p50/p75/p90 = 0.37 / 0.93 / 1.89 / 3.14%
- 2024 = 0.38 / 0.91 / 1.93 / 3.27%
- 2025 = 0.35 / 0.87 / 1.69 / 2.83%
- 2026 = 0.29 / 0.71 / 1.38 / 2.19%

L3:
- 2023 = 0.51 / 1.30 / 2.62 / 4.46%
- 2024 = 0.54 / 1.35 / 2.80 / 4.84%
- 2025 = 0.50 / 1.18 / 2.33 / 3.85%
- 2026 = 0.40 / 0.95 / 1.87 / 3.22%

L5:
- 2023 = 0.72 / 1.71 / 3.46 / 5.92%
- 2024 = 0.69 / 1.70 / 3.33 / 5.41%
- 2025 = 0.60 / 1.41 / 2.67 / 4.58%
- 2026 = 0.51 / 1.13 / 2.32 / 4.29%

### ABSORPTION_RELEASE
L2:
- 2023 = 0.40 / 0.98 / 1.98 / 3.24%
- 2024 = 0.37 / 0.91 / 1.97 / 3.25%
- 2025 = 0.38 / 0.92 / 1.75 / 2.94%
- 2026 = 0.30 / 0.71 / 1.28 / 2.17%

L3:
- 2023 = 0.56 / 1.38 / 2.67 / 4.63%
- 2024 = 0.51 / 1.29 / 2.76 / 4.74%
- 2025 = 0.53 / 1.24 / 2.43 / 4.06%
- 2026 = 0.45 / 0.96 / 1.92 / 3.38%

L5:
- 2023 = 0.75 / 1.74 / 3.39 / 5.89%
- 2024 = 0.65 / 1.64 / 3.28 / 5.30%
- 2025 = 0.65 / 1.56 / 2.84 / 4.80%
- 2026 = 0.52 / 1.24 / 2.55 / 4.37%

Interpretation of MAE:
- For L2, a 1% stop is around the median adverse excursion of eventual winners; roughly half of eventual L2 target hits can dip around or beyond 1% first.
- For L3, median MAE is about 1.0-1.4%, so SL1 is clearly too tight for a large share of eventual target hits.
- For L5, median MAE is about 1.1-1.7% and p75 about 2.3-3.5%; a 1% stop is materially too tight.

## 2024-selected RR-valid SL frozen transfer

No state/target had any positive 2024 SL candidate.

Best frontier in every family was the widest RR=1:1 stop:
- L2 NEW_LONG_BUILD TP2/SL2: 2024 WR47.7%, exp -0.192%, weekly -4.88%; 2025 exp -0.170%; 2026 exp -0.178%.
- L2 ABSORPTION_RELEASE TP2/SL2: 2024 WR47.9%, exp -0.184%; 2025 -0.224%; 2026 -0.197%.
- L3 NEW_LONG_BUILD TP3/SL3: 2024 WR47.4%, exp -0.242%; 2025 -0.150%; 2026 -0.328%.
- L3 ABSORPTION_RELEASE TP3/SL3: 2024 WR46.9%, exp -0.286%; 2025 -0.185%; 2026 -0.367%.
- L5 NEW_LONG_BUILD TP5/SL5: 2024 WR46.6%, exp -0.134%; 2025 -0.266%; 2026 -0.335%.
- L5 ABSORPTION_RELEASE TP5/SL5: 2024 WR46.8%, exp -0.095%; 2025 -0.317%; 2026 -0.455%.

Conclusion:
The 1% stop was indeed too tight for many valid multi-percent legs, but widening the stop within RR>=1 does not create a positive strategy. The dominant remaining problem is low per-signal precision / false ignition episodes. Broad derivatives state covers many true legs but also fires on too many non-winning episodes.

VERDICT: NO_EXIT_GEOMETRY_GATE_PASS_V6__FALSE_IGNITION_REMAINS
