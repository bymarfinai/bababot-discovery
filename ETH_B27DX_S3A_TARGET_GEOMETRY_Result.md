# ETH B27DX — S3A Native Target Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen: R300/X360, entry **F80**, invalidation **F35**, clocks **05:00, 09:00, 10:00, 16:00 UTC**. Only target extension varies.

## Target summary

| Target | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Supported |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| E05 | 1/4 | 10:00 | 67.3% | 1.04 | 71.4% | 1.48 | 66.5% | 0.97 | 72.5% | 1.22 | NO |
| E10 | 2/4 | 09:00,10:00 | 65.0% | 1.15 | 67.8% | 1.67 | 65.5% | 1.07 | 70.7% | 1.38 | YES |
| E15 | 2/4 | 05:00,09:00 | 61.7% | 1.07 | 62.2% | 1.67 | 63.3% | 1.10 | 67.0% | 1.37 | YES |
| E20 | 3/4 | 05:00,09:00,10:00 | 61.7% | 1.22 | 59.3% | 1.66 | 63.3% | 1.26 | 64.7% | 1.38 | YES |
| E25 | 2/4 | 05:00,09:00 | 59.2% | 1.20 | 57.2% | 1.70 | 60.0% | 1.31 | 61.8% | 1.48 | YES |
| E30 | 2/4 | 05:00,09:00 | 57.4% | 1.21 | 57.2% | 1.62 | 57.1% | 1.24 | 60.7% | 1.45 | YES |
| E35 | 3/4 | 05:00,09:00,10:00 | 57.4% | 1.33 | 55.5% | 1.65 | 55.0% | 1.24 | 57.8% | 1.44 | YES |
| E40 | 3/4 | 05:00,09:00,10:00 | 56.4% | 1.27 | 55.0% | 1.65 | 53.9% | 1.26 | 56.9% | 1.41 | YES |

## Robust clock × target pairs

| Target | Clock |
|---:|---:|
| E05 | 10:00 |
| E10 | 09:00 |
| E10 | 10:00 |
| E15 | 05:00 |
| E15 | 09:00 |
| E20 | 05:00 |
| E20 | 09:00 |
| E20 | 10:00 |
| E25 | 05:00 |
| E25 | 09:00 |
| E30 | 05:00 |
| E30 | 09:00 |
| E35 | 05:00 |
| E35 | 09:00 |
| E35 | 10:00 |
| E40 | 05:00 |
| E40 | 09:00 |
| E40 | 10:00 |

## Supported target-family runs

- Run 1: **E10 → E15 → E20 → E25 → E30 → E35 → E40** (7 adjacent targets).

## BTC benchmark diagnostic

- BTC B27DX LONG final: WR 71.9%, PF 2.22, expectancy +$1.26/trade.
- Target-family promotion is topology-based, not benchmark-maximization.

## Decision

**Status: ETH_S3A_NATIVE_TARGET_FAMILY_SUPPORTED**

- No stop, runner, leverage, lifecycle, clock, or live-code changes were made.
