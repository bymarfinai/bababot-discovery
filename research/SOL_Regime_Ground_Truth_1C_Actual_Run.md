# SOL Regime Ground Truth 1C — Actual Run

Source: Binance USDS-M Futures, SOLUSDT 1H  
Coverage: 2023-12-02 00:00 UTC → 2026-09-25 11:00 UTC  
Candles: 24,684  
Detected hourly gaps: 0

Thresholds fitted on DEV 2023-2024 only, then frozen:
- scale 4H: 0.9839058824
- scale 8H: 1.4145306028
- scale 12H: 1.7947203627
- scale 24H: 2.6297278164
- direction_abs_q60: 1.1008168496
- direction_abs_q30: 0.4730911847
- path_eff_q55: 0.3239784290
- path_eff_q35: 0.2471253535

## DEV 2023-2024
n=9,504
- BULL: 1,664 (17.51%); median returns 4H +1.8651%, 8H +3.1110%, 12H +3.9736%, 24H +4.9387%
- BEAR: 1,351 (14.22%); median returns 4H -1.8720%, 8H -3.0718%, 12H -3.6013%, 24H -4.4098%
- SIDEWAYS: 2,025 (21.31%); median returns 4H -0.0065%, 8H +0.0206%, 12H -0.0158%, 24H -0.0982%
- TRANSITION: 4,464 (46.97%); median returns 4H -0.0164%, 8H -0.0169%, 12H -0.0917%, 24H +0.0204%
- persistence: 59.30%
- acceptance: PASS

## VAL 2025
n=8,760
- BULL: 1,399 (15.97%); median returns 4H +1.7220%, 8H +2.9620%, 12H +3.6653%, 24H +4.5226%
- BEAR: 1,368 (15.62%); median returns 4H -1.7417%, 8H -3.0489%, 12H -3.7591%, 24H -4.2690%
- SIDEWAYS: 1,840 (21.00%); median returns 4H -0.0138%, 8H +0.0409%, 12H +0.0240%, 24H -0.0145%
- TRANSITION: 4,153 (47.41%); median returns 4H +0.0387%, 8H -0.0613%, 12H -0.0517%, 24H -0.1276%
- persistence: 62.03%
- acceptance: PASS

## OOS 2026 YTD
n=6,396
- BULL: 706 (11.04%); median returns 4H +1.6291%, 8H +2.7517%, 12H +3.3548%, 24H +4.1763%
- BEAR: 717 (11.21%); median returns 4H -1.5931%, 8H -2.4709%, 12H -3.0209%, 24H -3.9953%
- SIDEWAYS: 1,578 (24.67%); median returns 4H -0.0117%, 8H +0.0133%, 12H -0.0239%, 24H +0.0785%
- TRANSITION: 3,395 (53.08%); median returns 4H +0.0133%, 8H -0.0248%, 12H -0.0676%, 24H +0.0513%
- persistence: 64.89%
- acceptance: PASS

Acceptance checks in all three periods:
- BULL median forward return positive at 4H/8H/12H/24H: PASS
- BEAR median forward return negative at 4H/8H/12H/24H: PASS
- Ordered 24H return BULL > SIDEWAYS > BEAR: PASS
- All four states non-empty: PASS

Important: this is future-informed ground truth for research labels, NOT a live detector and NOT a trading signal.
