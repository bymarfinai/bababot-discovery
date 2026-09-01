# ETH B27DX — S3B Native Invalidation Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen: R300/X360, entry **F80**, target **E25**, clocks **05:00, 09:00, 10:00, 16:00 UTC**. Only completed-close invalidation varies.

## Invalidation summary

| Stop | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Robust-major Exp | Supported |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| F60 | 1/4 | 05:00 | 39.3% | 0.78 | 43.4% | 1.36 | 43.2% | 1.09 | 48.3% | 1.40 | 0.68 | NO |
| F55 | 1/4 | 05:00 | 46.6% | 0.92 | 47.8% | 1.33 | 47.5% | 1.07 | 51.7% | 1.40 | 0.53 | NO |
| F50 | 1/4 | 05:00 | 52.5% | 1.03 | 51.3% | 1.54 | 52.1% | 1.17 | 56.9% | 1.53 | 0.83 | NO |
| F45 | 2/4 | 05:00,09:00 | 55.8% | 1.09 | 53.2% | 1.61 | 53.6% | 1.29 | 57.9% | 1.37 | 0.52 | YES |
| F40 | 1/4 | 05:00 | 57.7% | 1.12 | 55.0% | 1.61 | 57.1% | 1.26 | 58.6% | 1.51 | 0.69 | NO |
| F35 | 2/4 | 05:00,09:00 | 59.2% | 1.20 | 57.2% | 1.70 | 60.0% | 1.31 | 61.8% | 1.48 | 0.67 | YES |
| F30 | 1/4 | 05:00 | 59.2% | 1.15 | 57.2% | 1.64 | 62.2% | 1.28 | 58.6% | 1.41 | 0.61 | NO |
| F25 | 1/4 | 05:00 | 61.1% | 1.09 | 57.2% | 1.59 | 65.5% | 1.33 | 60.3% | 1.43 | 0.64 | NO |
| F20 | 2/4 | 05:00,09:00 | 61.5% | 1.10 | 58.1% | 1.54 | 66.5% | 1.33 | 63.2% | 1.52 | 0.70 | YES |
| F15 | 2/4 | 05:00,09:00 | 62.5% | 1.14 | 58.1% | 1.53 | 68.7% | 1.45 | 63.2% | 1.51 | 0.70 | YES |

## Robust clock × invalidation pairs

| Stop | Clock |
|---:|---:|
| F60 | 05:00 |
| F55 | 05:00 |
| F50 | 05:00 |
| F45 | 05:00 |
| F45 | 09:00 |
| F40 | 05:00 |
| F35 | 05:00 |
| F35 | 09:00 |
| F30 | 05:00 |
| F25 | 05:00 |
| F20 | 05:00 |
| F20 | 09:00 |
| F15 | 05:00 |
| F15 | 09:00 |

## Supported invalidation-family runs

- Run 1: **F45** (1 adjacent stops).
- Run 2: **F35** (1 adjacent stops).
- Run 3: **F20 → F15** (2 adjacent stops).

## BTC benchmark diagnostic

- BTC B27DX LONG final: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.
- S3B promotion is topology-based, not benchmark-maximization.

## Decision

**Status: ETH_S3B_NATIVE_INVALIDATION_FAMILY_SUPPORTED**

- No entry, target, runner, leverage, lifecycle, clock, or live-code changes were made.
