# BNB B42-S4 — Historical Derivatives Information Result

**Status: BNB_B42_S4_NO_DERIVATIVES_DISCRIMINATORY_EDGE**

Signature: `a3579f84325796b19489e4b11ba1b9f86d7484e6f2795aa162c1d068c1ff7e0a`

## Archive audit

- Metrics archive files found: **1711/1711**.
- Metrics rows: **492,631**; first **2021-12-20 00:00:00+00:00**; last **2026-08-26 23:55:00+00:00**.
- Metrics mapped fields: `{"count_long_short_ratio": "count_long_short_ratio", "count_toptrader_long_short_ratio": "count_toptrader_long_short_ratio", "sum_open_interest": "sum_open_interest", "sum_open_interest_value": "sum_open_interest_value", "sum_taker_long_short_vol_ratio": "sum_taker_long_short_vol_ratio", "sum_toptrader_long_short_ratio": "sum_toptrader_long_short_ratio"}`.
- Premium rows: **163,872**.
- Funding rows: **5,205**.

## Coverage

| Feature | DEV N | REF N | DEV cov | REF cov | Eligible |
|---|---:|---:|---:|---:|---|
| oi_level_log | 210242 | 115574 | 99.91% | 99.99% | YES |
| oi_change_15m | 210274 | 115582 | 99.92% | 100.00% | YES |
| oi_change_60m | 210282 | 115586 | 99.93% | 100.00% | YES |
| oi_change_240m | 210306 | 115586 | 99.94% | 100.00% | YES |
| oi_value_change_60m | 210282 | 115586 | 99.93% | 100.00% | YES |
| oi_value_change_240m | 210306 | 115586 | 99.94% | 100.00% | YES |
| directional_global_account_log_ratio | 206768 | 115574 | 98.26% | 99.99% | YES |
| directional_top_account_log_ratio | 149174 | 115552 | 70.89% | 99.97% | NO |
| directional_top_position_log_ratio | 149174 | 115576 | 70.89% | 99.99% | NO |
| directional_taker_log_ratio | 185780 | 115586 | 88.29% | 100.00% | NO |
| taker_change_60m | 185746 | 115586 | 88.27% | 100.00% | NO |
| premium_close | 210056 | 115398 | 99.82% | 99.84% | YES |
| premium_z_7d | 210056 | 115398 | 99.82% | 99.84% | YES |
| premium_change_60m | 210056 | 115398 | 99.82% | 99.84% | YES |
| directional_premium | 210056 | 115398 | 99.82% | 99.84% | YES |
| directional_premium_z_7d | 210056 | 115398 | 99.82% | 99.84% | YES |
| directional_premium_change_60m | 210056 | 115398 | 99.82% | 99.84% | YES |
| latest_funding | 210432 | 115586 | 100.00% | 100.00% | YES |
| directional_funding | 210432 | 115586 | 100.00% | 100.00% | YES |

## Discrimination

| Feature | Orient | DEV AUC | REF AUC | Years >=.53 | Nominate |
|---|---:|---:|---:|---:|---|
| directional_premium_z_7d | -1 | **0.501** | **0.516** | 0 | NO |
| directional_global_account_log_ratio | -1 | **0.518** | **0.513** | 0 | NO |
| premium_close | -1 | **0.512** | **0.510** | 1 | NO |
| latest_funding | -1 | **0.507** | **0.509** | 0 | NO |
| premium_z_7d | -1 | **0.503** | **0.506** | 0 | NO |
| directional_funding | +1 | **0.501** | **0.503** | 0 | NO |
| oi_change_15m | +1 | **0.501** | **0.503** | 0 | NO |
| oi_value_change_60m | +1 | **0.501** | **0.502** | 0 | NO |
| directional_premium | +1 | **0.501** | **0.501** | 0 | NO |
| premium_change_60m | -1 | **0.501** | **0.501** | 0 | NO |
| oi_value_change_240m | -1 | **0.501** | **0.498** | 0 | NO |
| oi_change_60m | -1 | **0.500** | **0.497** | 0 | NO |
| directional_premium_change_60m | -1 | **0.504** | **0.496** | 0 | NO |
| oi_change_240m | -1 | **0.500** | **0.495** | 0 | NO |
| oi_level_log | -1 | **0.526** | **0.486** | 1 | NO |

## Decision
**BNB_B42_S4_NO_DERIVATIVES_DISCRIMINATORY_EDGE**

No S4 derivatives feature is eligible for promotion under the frozen gates; do not hyperopt these same features to force S5.
