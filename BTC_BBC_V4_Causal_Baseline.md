# BBC V4 — Strict Causal Live Baseline

**Research-only. Live BBC files and exchange execution are untouched.**

Frozen end-exclusive: `2026-08-19T00:00:00+00:00`

Primary V4 definition: completed 1H signal → **entry at next 1H open**; MTF 15m disabled; SIDEWAYS skipped; EMA7; TP/SL 1.3%/1.3%; bull body ≥0.5; bear body ≥0.6; 0.15% modeled round-trip cost.

The `close_proxy` control books the just-completed 1H close and exists only to quantify execution-timing sensitivity.

## 90 days

| Mode | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| close_proxy | 400 | 47.5% | $-430.00 | $-1.0750 | 0.718 | $534.50 |
| next_open_strict | 401 | 48.63% | $-372.25 | $-0.9283 | 0.751 | $482.75 |

Timing delta (next-open minus close): PnL **$+57.75**, WR **+1.13 pp**, expectancy **$+0.1467/trade**.

### Next-open by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 77 | 51.95% | $-38.25 | 0.857 | $85.50 |
| ETHUSDT | 106 | 48.11% | $-105.50 | 0.735 | $157.75 |
| SOLUSDT | 130 | 46.92% | $-149.50 | 0.701 | $188.75 |
| BNBUSDT | 88 | 48.86% | $-79.00 | 0.758 | $115.75 |

## 120 days

| Mode | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| close_proxy | 516 | 47.29% | $-569.00 | $-1.1027 | 0.711 | $667.50 |
| next_open_strict | 519 | 48.17% | $-512.75 | $-0.9880 | 0.737 | $610.00 |

Timing delta (next-open minus close): PnL **$+56.25**, WR **+0.88 pp**, expectancy **$+0.1147/trade**.

### Next-open by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 102 | 52.94% | $-37.50 | 0.892 | $93.00 |
| ETHUSDT | 137 | 47.45% | $-148.25 | 0.716 | $207.75 |
| SOLUSDT | 168 | 45.83% | $-217.00 | 0.671 | $259.00 |
| BNBUSDT | 112 | 48.21% | $-110.00 | 0.738 | $138.50 |

## 971 days

| Mode | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| close_proxy | 5639 | 49.87% | $-4326.75 | $-0.7673 | 0.789 | $4428.50 |
| next_open_strict | 5652 | 50.04% | $-4213.00 | $-0.7454 | 0.794 | $4320.75 |

Timing delta (next-open minus close): PnL **$+113.75**, WR **+0.17 pp**, expectancy **$+0.0219/trade**.

### Next-open by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 1076 | 51.95% | $-534.00 | 0.858 | $634.50 |
| ETHUSDT | 1424 | 50.42% | $-990.00 | 0.807 | $1081.00 |
| SOLUSDT | 1868 | 48.55% | $-1752.00 | 0.749 | $1787.00 |
| BNBUSDT | 1284 | 50.16% | $-937.00 | 0.798 | $968.00 |

## Interpretation rule

Do not tune thresholds from this run. First determine whether the strict next-open baseline remains economically positive and reasonably stable across 90d, 120d, 971d, pairs, and chronological blocks. Only then open a separately preregistered improvement study.
