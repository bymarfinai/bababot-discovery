# ETH B27DX — S4A Native Runner Arm Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen: R300/X360, F80 entry, pre-arm F35 close invalidation, BTC-style causal N+2 one-step-behind runner architecture. Only arm threshold varies.

## Arm summary

| Arm | Robust clocks | Labels | Dev WR | Dev PF | Ext WR | Ext PF | Val WR | Val PF | Robust-major WR | Robust-major PF | Robust-major exp | Max LS | Supported |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| E10 | 1/4 | 09:00 | 61.6% | 1.12 | 66.9% | 1.71 | 63.3% | 0.93 | 64.6% | 1.60 | 0.73 | 4 | NO |
| E15 | 1/4 | 09:00 | 60.2% | 1.01 | 61.3% | 1.67 | 61.1% | 1.01 | 65.6% | 1.59 | 0.73 | 4 | NO |
| E20 | 1/4 | 09:00 | 60.2% | 1.12 | 58.4% | 1.57 | 60.0% | 1.10 | 63.5% | 1.42 | 0.61 | 4 | NO |
| E25 | 2/4 | 05:00,09:00 | 57.7% | 1.12 | 55.5% | 1.69 | 57.5% | 1.24 | 60.6% | 1.35 | 0.49 | 5 | YES |
| E30 | 2/4 | 05:00,09:00 | 56.9% | 1.22 | 55.5% | 1.58 | 54.3% | 1.13 | 58.7% | 1.41 | 0.62 | 5 | YES |
| E35 | 2/4 | 05:00,09:00 | 56.0% | 1.26 | 55.0% | 1.59 | 52.5% | 0.98 | 56.3% | 1.41 | 0.58 | 7 | YES |
| E40 | 2/4 | 05:00,09:00 | 55.9% | 1.27 | 55.0% | 1.58 | 50.4% | 1.04 | 56.2% | 1.48 | 0.68 | 7 | YES |

## Robust clock × arm pairs

| Arm | Clock |
|---:|---:|
| E10 | 09:00 |
| E15 | 09:00 |
| E20 | 09:00 |
| E25 | 05:00 |
| E25 | 09:00 |
| E30 | 05:00 |
| E30 | 09:00 |
| E35 | 05:00 |
| E35 | 09:00 |
| E40 | 05:00 |
| E40 | 09:00 |

## Supported arm-family runs

- Run 1: **E25 → E30 → E35 → E40** (4 adjacent arms).

## BTC benchmark diagnostic

- BTC B27DX LONG final: WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3.
- Arm promotion remains topology-based; final acceptance requires portfolio locking and stress.

## Decision

**Status: ETH_S4A_NATIVE_RUNNER_ARM_FAMILY_SUPPORTED**

- No live BBC changes.
