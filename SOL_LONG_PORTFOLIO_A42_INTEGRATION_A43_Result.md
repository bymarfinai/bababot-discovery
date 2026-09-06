# SOL LONG Three-Zone Portfolio + A42 Integration Audit — A43 Result

Frozen A24 component ledger + frozen A42 CENTRAL `G_MAE145`; A25 component-trade/day/week/DD conventions preserved.

A42 recovery rows integrated: **28**. Exact parent reconciliation: **28/28**. Duplicate recovery parent: **False**. Duplicate frozen parent key: **False**. Critical null: **False**.

## Baseline vs +A42

| Scope | Trades B→A | Episodes B→A | WR B→A | PF B→A | Net B→A | 5bps WR B→A | 5bps PF B→A | 5bps Net B→A | DD B→A | 5bps DD B→A | Loss streak B→A | 5bps loss streak B→A | Day+ B→A | 5bps Day+ B→A | Week+ B→A | 5bps Week+ B→A | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 2043→2055 | 1827→1827 | 40.04%→40.29% | 1.27→1.27 | $1069.20→$1096.76 | 39.26%→39.51% | 1.13→1.13 | $558.45→$583.01 | $162.79→$162.79 | $201.11→$201.11 | 20→13 | 20→13 | 51.03%→51.35% | 49.40%→49.73% | 55.70%→56.33% | 50.00%→50.63% | NO |
| external | 931→940 | 806→806 | 37.59%→37.98% | 1.61→1.62 | $1407.88→$1450.62 | 37.27%→37.66% | 1.48→1.49 | $1175.13→$1215.62 | $167.06→$167.06 | $183.81→$183.81 | 13→13 | 13→13 | 52.25%→52.75% | 51.50%→52.00% | 72.06%→69.12% | 63.24%→61.76% | NO |
| reference_validation | 1113→1120 | 974→974 | 40.25%→40.36% | 1.35→1.36 | $562.75→$575.12 | 39.26%→39.38% | 1.16→1.17 | $284.50→$295.12 | $77.28→$77.28 | $105.63→$105.63 | 17→17 | 17→17 | 51.13%→51.54% | 50.10%→50.31% | 65.06%→63.86% | 54.22%→55.42% | NO |
| pooled | 4087→4115 | 3607→3607 | 39.54%→39.78% | 1.38→1.39 | $3039.83→$3122.50 | 38.81%→39.05% | 1.24→1.24 | $2018.08→$2093.75 | $167.06→$167.06 | $201.11→$201.11 | 20→17 | 20→17 | 51.33%→51.71% | 50.06%→50.39% | 61.89%→61.24% | 53.75%→54.07% | NO |

## Gate failures

- **development:** dd_stress_not_worse
- **external:** week_rate_raw_not_worse, week_rate_stress_not_worse
- **reference_validation:** week_rate_raw_not_worse
- **pooled:** week_rate_raw_not_worse

## Net contribution by frozen habitat/component

| Partition | Habitat | Component | N | Raw Net | 5bps Net |
|---|---|---|---:|---:|---:|
| development | 03UTC_PARENT | PARENT | 609 | $281.47 | $129.22 |
| development | 15UTC_A42_RECOVERY | A42_G_MAE145 | 12 | $27.56 | $24.56 |
| development | 15UTC_PARENT | PARENT | 601 | $338.91 | $188.66 |
| development | 18UTC_MATURE | PARENT | 617 | $314.06 | $159.81 |
| development | 18UTC_MATURE | REC_H2 | 216 | $134.76 | $80.76 |
| external | 03UTC_PARENT | PARENT | 252 | $527.66 | $464.66 |
| external | 15UTC_A42_RECOVERY | A42_G_MAE145 | 9 | $42.74 | $40.49 |
| external | 15UTC_PARENT | PARENT | 281 | $419.82 | $349.57 |
| external | 18UTC_MATURE | PARENT | 273 | $347.53 | $279.28 |
| external | 18UTC_MATURE | REC_H2 | 125 | $112.87 | $81.62 |
| reference_validation | 03UTC_PARENT | PARENT | 320 | $171.50 | $91.50 |
| reference_validation | 15UTC_A42_RECOVERY | A42_G_MAE145 | 7 | $12.37 | $10.62 |
| reference_validation | 15UTC_PARENT | PARENT | 337 | $263.33 | $179.08 |
| reference_validation | 18UTC_MATURE | PARENT | 317 | $81.96 | $2.71 |
| reference_validation | 18UTC_MATURE | REC_H2 | 139 | $45.96 | $11.21 |
| pooled | 03UTC_PARENT | PARENT | 1181 | $980.63 | $685.38 |
| pooled | 15UTC_A42_RECOVERY | A42_G_MAE145 | 28 | $82.67 | $75.67 |
| pooled | 15UTC_PARENT | PARENT | 1219 | $1022.06 | $717.31 |
| pooled | 18UTC_MATURE | PARENT | 1207 | $743.55 | $441.80 |
| pooled | 18UTC_MATURE | REC_H2 | 480 | $293.59 | $173.59 |

**Status: `SOL_LONG_PORTFOLIO_A42_INTEGRATION_A43_NOT_SUPPORTED`**

No thresholds or OOS coordinates were changed. Research only; live Baba Bot remains unchanged.
