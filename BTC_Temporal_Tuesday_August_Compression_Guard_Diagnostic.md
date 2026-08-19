# Tuesday August Compression Guard Diagnostic

**Status: COMPLETE — post-hoc August-motivated diagnostic; live BBC untouched.**

- Frozen D Q25 range6: **1.397%**; range24: **3.536%**.

| Candidate WAIT guard | Aug hits | D skip N | D delta | V skip N | V delta | Full skip N | Full delta | Keep coverage | Cross-slice? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| LOW_RANGE6 | 3/3 | 21 | $+3.17 | 23 | $-32.25 | 44 | $-29.08 | 68.3% | NO |
| LOW_RANGE24 | 3/3 | 21 | $-7.74 | 27 | $-26.11 | 48 | $-33.85 | 65.5% | NO |
| DUAL_COMPRESSION | 3/3 | 11 | $+6.75 | 14 | $-14.77 | 25 | $-8.02 | 82.0% | NO |
| BEARISH_SATURATION | 3/3 | 17 | $-12.11 | 19 | $-10.75 | 36 | $-22.86 | 74.1% | NO |
| DUAL_COMP_PLUS_TAKER_SELL | 3/3 | 5 | $+11.94 | 9 | $+1.30 | 14 | $+13.24 | 89.9% | YES |
| DUAL_COMP_PLUS_EMA_BEAR | 3/3 | 6 | $-4.81 | 9 | $-4.53 | 15 | $-9.34 | 89.2% | NO |
| DUAL_COMP_PLUS_BEARISH_SATURATION | 3/3 | 3 | $+5.42 | 6 | $+2.72 | 9 | $+8.14 | 93.5% | YES |

## Diagnostic interpretation
- Best candidate that catches all three August failures and improves both historical chronology slices: **DUAL_COMP_PLUS_TAKER_SELL**.
- Historical WAIT delta: D **$+11.94**, V **$+1.30**, full **$+13.24**.
- Retains **89.9%** of Tuesday trades.
- This is suitable only as a **frozen shadow guard** because August motivated the conjunction.

## Guardrail
All compound gates are motivated after observing August, so they are post-hoc diagnostics. Even a D/V-positive result is only a shadow-guard candidate. Freeze without further tuning and require future Tuesdays before live use.
