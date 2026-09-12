# ETH R4b — Stage G 2026 Failure Decomposition

**DIAGNOSTIC ONLY. FIVE FROZEN H04 CELLS. NO RESELECTION, RETUNING, OR REGIME-GATE PROMOTION.**

Dataset cutoff frozen to Stage E: **2026-08-25T23:55:00+00:00**. Coverage **100.0000%**.
Pre-entry features end one 5m bar before entry. Forward returns are outcome-side diagnostics only.
Stage G status: **Q2_FAILURE_DECOMPOSED__MONTHLY_CONCENTRATION_CONFIRMED__PREENTRY_SHIFT_PRESENT__FOLLOWTHROUGH_SHIFT_PRESENT**.
Months where all 5 frozen cells are weak (Exp<0 and PF<1): **2026-05, 2026-06**.
Months where all 5 frozen cells are positive (Exp>0 and PF>1): **2026-02**.

## Canonical LB240/H360 monthly localization

| Month | N | WR | Net | Exp | PF | PreRet1H | PreRet4H | RV1H | ATR1H | TrendEff4H | Fwd1H | Fwd2H |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-01 | 3 | 100.00% | $+8.52 | $+2.84 | NA | -0.02% | -1.71% | 0.56% | 0.26% | 0.220 | 0.38% | 0.23% |
| 2026-02 | 10 | 80.00% | $+29.19 | $+2.92 | 2.720 | -0.52% | -1.83% | 0.95% | 0.41% | 0.208 | 0.24% | 0.38% |
| 2026-03 | 5 | 20.00% | $-5.97 | $-1.19 | 0.660 | -0.10% | -1.83% | 0.28% | 0.19% | 0.242 | -0.60% | -0.26% |
| 2026-04 | 0 | NA | $+0.00 | NA | NA | NA | NA | NA | NA | NA | NA | NA |
| 2026-05 | 13 | 15.38% | $-43.48 | $-3.34 | 0.028 | -0.16% | -1.13% | 0.37% | 0.17% | 0.329 | -0.13% | -0.08% |
| 2026-06 | 11 | 27.27% | $-46.65 | $-4.24 | 0.153 | -0.27% | -1.40% | 0.70% | 0.30% | 0.157 | -0.22% | 0.25% |
| 2026-07 | 3 | 0.00% | $-11.32 | $-3.77 | 0.000 | -0.46% | -1.53% | 0.55% | 0.20% | 0.280 | -0.01% | 0.09% |
| 2026-08 | 2 | 100.00% | $+12.38 | $+6.19 | NA | -0.28% | -1.17% | 0.45% | 0.21% | 0.195 | -0.27% | 0.35% |

## Cross-cell phase feature shifts

| Feature | Role | Q1 median | Q2 median | Q3 median | Same-direction cells | Relative Q2 shift vs flanks |
|---|---|---:|---:|---:|---:|---:|
| fwd_ret_60 | follow_through | 0.00238 | -0.00006 | 0.00334 | 5/5 | -1.021 |
| fwd_ret_120 | follow_through | 0.00233 | 0.00002 | 0.00485 | 5/5 | -0.997 |
| pre_ret_60 | pre_entry | -0.00375 | -0.00305 | -0.00359 | 0/5 | 0.324 |
| rv_60 | pre_entry | 0.00650 | 0.00492 | 0.00552 | 5/5 | -0.271 |
| atr_pct_60 | pre_entry | 0.00339 | 0.00214 | 0.00241 | 5/5 | -0.261 |
| atr_pct_240 | pre_entry | 0.00393 | 0.00276 | 0.00337 | 3/5 | -0.249 |
| trend_eff_240 | pre_entry | 0.19184 | 0.18705 | 0.14186 | 3/5 | 0.121 |
| rv_240 | pre_entry | 0.01648 | 0.01347 | 0.01387 | 3/5 | -0.110 |
| pre_ret_240 | pre_entry | -0.01581 | -0.01229 | -0.00936 | 1/5 | 0.024 |
| disp_240 | pre_entry | 0.96476 | 0.87699 | 0.74979 | 3/5 | 0.023 |
| disp_60 | pre_entry | 0.68915 | 0.77329 | 0.67817 | 2/5 | 0.011 |

## Diagnostic readout

- Strongest consistent pre-entry Q2 shifts (>=4/5 cells): **rv_60, atr_pct_60**.
- Outcome-side follow-through shifts: **fwd_ret_60, fwd_ret_120**.
- These rankings are descriptive failure signatures only. They are not thresholds and cannot be converted into a live filter without a new preregistered validation stage.
- Stage D 2025 remains the final untouched full-year OOS result. Stage E/F/G remain current-regime diagnostics.
- No hour, character rule, lookback, hold, entry, TP/SL, or risk rule changed in Stage G.
