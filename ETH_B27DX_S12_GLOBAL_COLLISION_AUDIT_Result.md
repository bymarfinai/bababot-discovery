# ETH B27DX — S12 Global Collision / One-Position Audit — Result

ETH raw 5m coverage: **100.0000%**.

Frozen portfolio under audit: **S10 hybrid** — 05:00 fixed E25 · 09:00 fixed E25 · 10:00 E10 profit-lock runner · 16:00 fixed E25.

- S10 source audit: **PASS**.
- Exact S10 one-position decision parity: **PASS**.

## Global one-position anatomy

- Candidates: **575**.
- Accepted: **478**.
- Blocked while another ETH position was open: **97 (16.9%)**.
- Exact same-entry tie groups: **68**; alternatives blocked by same-entry tie: **65**.
- Blocked candidates standalone outcome: **65 wins / 32 losses / 0 flat**. These are counterfactual diagnostics only.

## Collision matrix

| Active blocker | Later blocked clock | Blocked N | Standalone wins | Standalone net |
|---:|---:|---:|---:|---:|
| 05:00 | 09:00 | 8 | 4 | -8.83 |
| 05:00 | 10:00 | 4 | 4 | 11.91 |
| 09:00 | 05:00 | 3 | 1 | 0.42 |
| 09:00 | 10:00 | 8 | 3 | -16.59 |
| 10:00 | 05:00 | 1 | 1 | 0.18 |
| 10:00 | 09:00 | 73 | 52 | 56.94 |

## Blocked candidate standalone quality by blocked clock

| Blocked clock | N | WR | PF | Exp | Net | 5bps PF | 5bps Net |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 05:00 | 4 | 50.0% | 1.18 | 0.15 | 0.59 | 0.75 | -1.16 |
| 09:00 | 81 | 69.1% | 1.37 | 0.59 | 48.11 | 1.14 | 19.39 |
| 10:00 | 12 | 58.3% | 0.80 | -0.39 | -4.68 | 0.59 | -10.68 |

## Accepted holding time by clock

| Clock | N | Median hold | Mean hold | P75 hold | WR | PF | Exp | Net |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 05:00 | 101 | 140.0m | 149.5m | 215.0m | 62.4% | 1.71 | 1.00 | 101.35 |
| 09:00 | 90 | 115.0m | 141.2m | 222.5m | 62.2% | 1.30 | 0.67 | 60.14 |
| 10:00 | 164 | 85.0m | 103.3m | 135.0m | 71.3% | 1.78 | 1.05 | 172.01 |
| 16:00 | 123 | 170.0m | 182.6m | 282.5m | 58.5% | 1.21 | 0.51 | 63.22 |

## How close blocked signals were to portfolio becoming free

| Remaining until blocker exit | N | Standalone wins | Standalone net |
|---|---:|---:|---:|
| <=5m | 2 | 1 | -5.48 |
| 5-15m | 1 | 1 | 2.40 |
| 15-30m | 20 | 14 | 12.11 |
| 30-60m | 16 | 13 | 24.26 |
| >60m | 58 | 36 | 10.73 |

## Accepted positions that blocked the most later signals

| Clock | Entry | Exit | Hold | Signals blocked | Trade PnL |
|---:|---|---|---:|---:|---:|
| 05:00 | 2025-02-10 06:00:00+00:00 | 2025-02-10 11:00:00+00:00 | 300.0m | 2 | 2.18 |
| 05:00 | 2021-02-01 07:10:00+00:00 | 2021-02-01 11:00:00+00:00 | 230.0m | 2 | 3.77 |
| 05:00 | 2022-06-02 07:35:00+00:00 | 2022-06-02 11:00:00+00:00 | 205.0m | 2 | 0.23 |
| 05:00 | 2020-05-06 08:40:00+00:00 | 2020-05-06 11:00:00+00:00 | 140.0m | 2 | 3.92 |
| 10:00 | 2023-01-02 10:35:00+00:00 | 2023-01-02 16:00:00+00:00 | 325.0m | 1 | 0.47 |
| 05:00 | 2024-06-25 05:40:00+00:00 | 2024-06-25 11:00:00+00:00 | 320.0m | 1 | -0.79 |
| 10:00 | 2025-04-29 10:40:00+00:00 | 2025-04-29 16:00:00+00:00 | 320.0m | 1 | -3.22 |
| 09:00 | 2023-12-04 09:50:00+00:00 | 2023-12-04 14:30:00+00:00 | 280.0m | 1 | -8.14 |
| 10:00 | 2023-03-23 10:55:00+00:00 | 2023-03-23 15:25:00+00:00 | 270.0m | 1 | 23.96 |
| 05:00 | 2022-04-20 06:15:00+00:00 | 2022-04-20 10:30:00+00:00 | 255.0m | 1 | 2.84 |

## Interpretation guardrail

- Blocked-candidate PnL is **not executable portfolio PnL** and is never added to S10 results.
- S12 does **not** change clock priority, tie-break, entry, exit, runner, or live configuration.
- Any collision rule suggested by this anatomy requires a new preregistered causal experiment.

## Decision

**Status: ETH_S12_GLOBAL_COLLISION_AUDIT_VALID**
