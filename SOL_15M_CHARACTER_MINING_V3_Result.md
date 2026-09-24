# SOL 15M Character Mining V3 — Result

Run: 35949766849
Head: 44d2b24d11fb4019a7cbf165bff2eab5524851e7
5m coverage: 99.76977%

Frozen economics:
- TP +1.0%
- SL -1.0%
- RR 1:1
- round-trip cost 0.15%
- notional USD500
- one active position

Data:
- train 2023: 35,039 rows
- validation 2024: 35,129 rows
- reference 2025: 35,022 rows
- reference 2026: 22,752 rows

Selected from 2024 only:
- Random Forest depth 8
- min leaf 150
- score quantile 0.750
- threshold 0.521577

Frozen transfer:
- 2024: 2,394 trades, 50.92% WR, 6.541/day, -0.1316% net expectancy/trade, -USD1,575.50
- 2025: 2,067 trades, 51.43% WR, 5.663/day, -0.1215% net expectancy/trade, -USD1,255.25
- 2026: 885 trades, 48.47% WR, 3.734/day, -0.1724% net expectancy/trade, -USD762.72

Top predictors:
1. h4_ret6
2. h4_ema_slope
3. h1_ret24
4. h1_loc72
5. h4_dist_ema
6. atr_pct
7. h4_ret3
8. h1_ema_slope
9. h4_ret1
10. h1_dist_ema
11. loc96
12. dist_high32

Interpretation:
The selected learned character heavily favors positive HTF momentum and high range location, but it does not separate TP-before-SL outcomes at RR 1:1. Transfer remains approximately coin-flip and negative after fees.

VERDICT: NO_FULL_PASS__LEARNED_CHARACTER_FRONTIER
