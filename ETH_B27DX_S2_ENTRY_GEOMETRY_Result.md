# ETH B27DX — S2 Native Entry Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen native structure: **R300 / X360**, execution clocks **05:00, 09:00, 10:00, 16:00 UTC**. Only LONG retrace entry fraction varies. Target E20 and completed-close invalidation F35 remain frozen.

## Entry-fraction summary

| Entry | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Supported |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| F95 | 0/4 | - | 67.5% | 0.98 | 62.6% | 1.12 | 63.7% | 0.87 | - | - | NO |
| F90 | 1/4 | 16:00 | 66.5% | 1.07 | 61.9% | 1.29 | 66.1% | 1.11 | 56.7% | 1.35 | NO |
| F85 | 4/4 | 05:00,09:00,10:00,16:00 | 65.4% | 1.17 | 64.6% | 1.43 | 63.7% | 1.14 | 64.6% | 1.25 | YES |
| F80 | 3/4 | 05:00,09:00,10:00 | 61.7% | 1.22 | 59.3% | 1.66 | 63.3% | 1.26 | 64.7% | 1.38 | YES |
| F75 | 3/4 | 05:00,09:00,10:00 | 61.3% | 1.29 | 62.0% | 1.71 | 60.5% | 1.42 | 62.7% | 1.47 | YES |
| F70 | 2/4 | 09:00,10:00 | 57.2% | 1.26 | 63.1% | 1.80 | 58.4% | 1.52 | 60.6% | 1.70 | YES |
| F65 | 1/4 | 10:00 | 58.9% | 1.34 | 58.3% | 1.83 | 50.0% | 1.52 | 50.0% | 1.60 | NO |
| F60 | 1/4 | 10:00 | 55.2% | 1.42 | 59.0% | 2.21 | 50.0% | 1.79 | 47.4% | 1.88 | NO |

## Robust clock × entry pairs

| Entry | Clock |
|---:|---:|
| F90 | 16:00 |
| F85 | 05:00 |
| F85 | 09:00 |
| F85 | 10:00 |
| F85 | 16:00 |
| F80 | 05:00 |
| F80 | 09:00 |
| F80 | 10:00 |
| F75 | 05:00 |
| F75 | 09:00 |
| F75 | 10:00 |
| F70 | 09:00 |
| F70 | 10:00 |
| F65 | 10:00 |
| F60 | 10:00 |

## Supported entry-family runs

- Run 1: **F85 → F80 → F75 → F70** (4 adjacent fractions).

## BTC final benchmark diagnostic

- BTC B27DX LONG: **WR 71.9%, PF 2.22, expectancy +$1.26/trade**.
- S2 does not require BTC-level economics yet because E20/F35 exits are intentionally frozen.
- Final ETH acceptance remains contingent on BTC-level or better quality after target/invalidation and portfolio-lock calibration.

## Decision

**Status: ETH_S2_NATIVE_ENTRY_FAMILY_SUPPORTED**

- No TP, stop, runner, leverage, lifecycle, or live-code changes were made.
