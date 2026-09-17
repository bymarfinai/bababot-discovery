# SOL Structure × Trigger Matrix V1 — Result

- Data coverage: **99.769767%**
- Structural setups detected: **50748**
- Triggered trade records across 12 combinations: **48249**
- Evaluation: **2020-2024**; **2025+ remained CLOSED**.
- A structure is context only; entry occurs only after a frozen post-structure trigger.
- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% round-trip cost.

## Structure × trigger scorecard

| Structure | Trigger | Setup N | Trigger N | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SWEEP_RECLAIM | MICRO_BOS | 13601 | 2691 | 19.79% | 40.54% | -0.0980% | 0.796 | $-1318.99 | $1508.48 | 12.08% | 0.977 | 20m | 2/5 | REJECTED_AS_DEFINED |
| SWEEP_RECLAIM | BULLISH_DISPLACEMENT | 13601 | 4387 | 32.25% | 41.65% | -0.1143% | 0.768 | $-2507.53 | $2644.67 | 11.51% | 0.967 | 10m | 0/5 | REJECTED_AS_DEFINED |
| SWEEP_RECLAIM | PULLBACK_RESUME | 13601 | 3521 | 25.89% | 41.21% | -0.1275% | 0.736 | $-2244.58 | $2507.60 | 10.99% | 0.939 | 20m | 1/5 | REJECTED_AS_DEFINED |
| HL_SETUP | MICRO_BOS | 26411 | 7150 | 27.07% | 39.85% | -0.1327% | 0.745 | $-4745.73 | $5065.81 | 12.94% | 0.914 | 25m | 0/5 | REJECTED_AS_DEFINED |
| HL_SETUP | BULLISH_DISPLACEMENT | 26411 | 10481 | 39.68% | 40.69% | -0.1309% | 0.750 | $-6859.20 | $7632.81 | 13.53% | 0.978 | 10m | 0/5 | REJECTED_AS_DEFINED |
| HL_SETUP | PULLBACK_RESUME | 26411 | 11217 | 42.47% | 39.89% | -0.1330% | 0.735 | $-7461.23 | $7998.18 | 11.90% | 0.928 | 20m | 0/5 | REJECTED_AS_DEFINED |
| BREAKOUT_PULLBACK_SETUP | MICRO_BOS | 2025 | 506 | 24.99% | 43.08% | -0.0778% | 0.851 | $-196.90 | $272.26 | 15.42% | 0.988 | 25m | 1/5 | REJECTED_AS_DEFINED |
| BREAKOUT_PULLBACK_SETUP | BULLISH_DISPLACEMENT | 2025 | 788 | 38.91% | 41.12% | -0.1660% | 0.688 | $-654.17 | $654.17 | 14.47% | 0.959 | 10m | 0/5 | REJECTED_AS_DEFINED |
| BREAKOUT_PULLBACK_SETUP | PULLBACK_RESUME | 2025 | 808 | 39.90% | 42.95% | -0.0827% | 0.826 | $-334.09 | $406.63 | 13.00% | 0.984 | 20m | 1/5 | REJECTED_AS_DEFINED |
| FAILED_BREAKDOWN_RECLAIM | MICRO_BOS | 8711 | 1737 | 19.94% | 40.99% | -0.1212% | 0.756 | $-1053.02 | $1083.79 | 11.34% | 0.977 | 20m | 0/5 | REJECTED_AS_DEFINED |
| FAILED_BREAKDOWN_RECLAIM | BULLISH_DISPLACEMENT | 8711 | 2610 | 29.96% | 43.72% | -0.0784% | 0.832 | $-1023.09 | $1190.25 | 12.49% | 1.118 | 10m | 1/5 | REJECTED_AS_DEFINED |
| FAILED_BREAKDOWN_RECLAIM | PULLBACK_RESUME | 8711 | 2353 | 27.01% | 41.99% | -0.1057% | 0.778 | $-1243.36 | $1276.70 | 10.88% | 1.031 | 20m | 0/5 | REJECTED_AS_DEFINED |

## Passing combinations

- **NONE**

## Best diagnostics, not promotions

- Best fixed +60m expectancy: **BREAKOUT_PULLBACK_SETUP × MICRO_BOS = -0.0778%**, PF 0.851, N 506.
- Highest WR60: **FAILED_BREAKDOWN_RECLAIM × BULLISH_DISPLACEMENT = 43.72%**, expectancy -0.0784%, PF 0.832, N 2610.
- Highest median MFE/MAE: **FAILED_BREAKDOWN_RECLAIM × BULLISH_DISPLACEMENT = 1.118**, still below the frozen 1.20 gate and economically negative.
- No combination had positive expectancy.
- No combination had PF >= 1.15.
- No combination had positive PnL in >=4/5 years.

## Interpretation

The experiment confirms the architectural separation between **structure** and **entry trigger**, but these three generic post-structure triggers do not yet create a viable SOL LONG entry for the four tested contexts.

This does **not** invalidate the structures themselves. It rejects only these exact structure×trigger pairs as defined.

Do not rescue these pairs on 2020-2024 by changing trigger thresholds/window, structure rules, hours, indicators, regime filters, TP or SL. Move to a different explicitly defined trigger family or a more structure-native trigger.

Authoritative workflow run: `35210279745`
Artifact: `10491419682`
Artifact digest: `sha256:00f3332a4c992e3022f9a5958e97e81dff2856c233b32063c66ff23bbe5cface`

# VERDICT: PASSING_COMBOS=NONE
