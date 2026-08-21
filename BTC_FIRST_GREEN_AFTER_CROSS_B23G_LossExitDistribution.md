# B23G Losing-Trade Exit Distribution

5m source rows: **698,112**; coverage: **100.0000%**.

This is post-result forensic diagnostics only. It does not alter B23G rules. A losing trade is any trade with gross return <= 0. The trigger zone is measured on the completed same-timeframe candle that caused the next-open exit.

Zone definitions: ABOVE_EMA20 = close >= EMA20 > EMA50; BETWEEN_EMA20_EMA50 = EMA20 > close >= EMA50; BELOW_EMA50 = EMA20 > EMA50 and close < EMA50; EMA20_BELOW_EMA50 = EMA20 < EMA50.

## Main partitions combined (External + Development + Reference Validation)

| TF | Losing trades | Above EMA20 | Between EMA20/50 | Below EMA50 | EMA20 below EMA50 |
|---|---:|---:|---:|---:|---:|
| 5m | 4628 | 0 (0.00%) | 2585 (55.86%) | 2012 (43.47%) | 31 (0.67%) |
| 15m | 1444 | 0 (0.00%) | 784 (54.29%) | 652 (45.15%) | 8 (0.55%) |
| 1h | 335 | 0 (0.00%) | 174 (51.94%) | 158 (47.16%) | 3 (0.90%) |
| 4h | 77 | 0 (0.00%) | 30 (38.96%) | 47 (61.04%) | 0 (0.00%) |

## Reference Validation only

| TF | Losing trades | Above EMA20 | Between EMA20/50 | Below EMA50 | EMA20 below EMA50 |
|---|---:|---:|---:|---:|---:|
| 5m | 1073 | 0 (0.00%) | 595 (55.45%) | 470 (43.80%) | 8 (0.75%) |
| 15m | 328 | 0 (0.00%) | 181 (55.18%) | 146 (44.51%) | 1 (0.30%) |
| 1h | 82 | 0 (0.00%) | 39 (47.56%) | 43 (52.44%) | 0 (0.00%) |
| 4h | 19 | 0 (0.00%) | 6 (31.58%) | 13 (68.42%) | 0 (0.00%) |

## Exit-reason distribution, main partitions combined

| TF | Deterioration cut | Reversal cut | Bear-cross cut | Force close |
|---|---:|---:|---:|---:|
| 5m | 2585 (55.86%) | 2043 (44.14%) | 0 (0.00%) | 0 (0.00%) |
| 15m | 784 (54.29%) | 660 (45.71%) | 0 (0.00%) | 0 (0.00%) |
| 1h | 174 (51.94%) | 161 (48.06%) | 0 (0.00%) | 0 (0.00%) |
| 4h | 30 (38.96%) | 47 (61.04%) | 0 (0.00%) | 0 (0.00%) |
