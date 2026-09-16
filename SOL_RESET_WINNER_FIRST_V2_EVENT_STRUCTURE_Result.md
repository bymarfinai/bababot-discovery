# SOL Reset — Winner-First V2 Event-Relative Structure Result

- Data coverage: **99.769767%**
- Research opportunities: **149912**
- OOS opportunities 2022-2024: **104532**
- OOS selected LONG entries: **0**
- OOS baseline clean-winner rate: **10.83%**
- Selected clean-winner precision: **n/a**
- Precision lift: **n/a**
- Selected family keys: **0**
- Representation: ordered pivot/sweep/displacement event stream; no raw candle-position path matching.
- 2025+ reference_validation remained CLOSED.

## Fixed +60m diagnostic

- ALL OOS expectancy: **-0.1435%**
- ALL OOS PF: **0.672**
- No family passed the frozen training eligibility gate, therefore no OOS LONG entries were permitted.

## Year stability

| Year | All N | Baseline clean | Selected |
|---:|---:|---:|---:|
| 2022 | 34360 | 10.77% | 0 |
| 2023 | 35040 | 10.71% | 0 |
| 2024 | 35132 | 11.01% | 0 |

## Training-eligible family transfer

- No training family passed the frozen eligibility gate.

## Gate audit

- FAIL — `selected_oos_n_ge_100`
- FAIL — `clean_winner_precision_lift_ge_1_50x`
- FAIL — `fixed60_expectancy_positive`
- FAIL — `fixed60_pf_ge_1_15`
- FAIL — `positive_pnl_years_ge_2_of_3`
- FAIL — `median_mfe_mae_ratio_ge_1_25`
- FAIL — `distinct_selected_family_keys_ge_2`

# VERDICT: WINNER_FIRST_V2_NOT_READY

Do not rescue this exact event representation by sweeping pivot order, sweep lookback, displacement thresholds, event slots, family count/radius/support, winner barriers, precursor length, hours, horizon, TP or SL on 2022-2024.

Authoritative workflow run: `35054147278`
Artifact: `10429987867`
Artifact digest: `sha256:2ff6585d13f0c427e1592c7c30b8001cc0e7ebef7421c36526c9ec9650114e41`
