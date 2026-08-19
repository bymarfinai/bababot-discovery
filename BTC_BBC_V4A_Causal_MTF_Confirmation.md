# BBC V4-A — Causal Post-Close 15m Confirmation

**Research-only. No live files or orders are touched.**

End-exclusive: `2026-08-19T00:00:00+00:00`

Signal: completed 1H EMA7 reclaim/reject. V4-A waits for EMA20 confirmation during the next hour and enters at the following 15m open. Confirmation on 15m #4 is not tradable and expires.

## 90 days

| Mode | Trades | WR | PnL | Exp/trade | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| next_1h_open | 668 | 45.51% | $-882.13 | $-1.3205 | 0.664 | $892.25 |
| mtf_confirm | 217 | 46.54% | $-249.52 | $-1.1499 | 0.699 | $289.75 |

MTF delta: PnL **$+632.61**, WR **+1.03 pp**, expectancy **$+0.1706/trade**, trade count **-451**.

### MTF confirmation by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 48 | 50.0% | $-36.00 | 0.793 | $69.00 |
| ETHUSDT | 55 | 43.64% | $-82.10 | 0.627 | $94.85 |
| SOLUSDT | 60 | 41.67% | $-110.00 | 0.567 | $125.75 |
| BNBUSDT | 54 | 51.85% | $-21.42 | 0.883 | $64.50 |

## 120 days

| Mode | Trades | WR | PnL | Exp/trade | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| next_1h_open | 844 | 46.56% | $-1001.13 | $-1.1862 | 0.693 | $1046.75 |
| mtf_confirm | 280 | 49.64% | $-212.27 | $-0.7581 | 0.79 | $290.00 |

MTF delta: PnL **$+788.86**, WR **+3.08 pp**, expectancy **$+0.4281/trade**, trade count **-564**.

### MTF confirmation by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 65 | 58.46% | $+22.75 | 1.116 | $69.00 |
| ETHUSDT | 72 | 47.22% | $-75.35 | 0.722 | $94.85 |
| SOLUSDT | 76 | 44.74% | $-109.00 | 0.642 | $133.25 |
| BNBUSDT | 67 | 49.25% | $-50.67 | 0.789 | $89.50 |

## 971 days

| Mode | Trades | WR | PnL | Exp/trade | PF | DD |
|---|---:|---:|---:|---:|---:|---:|
| next_1h_open | 9700 | 51.01% | $-5992.13 | $-0.6177 | 0.826 | $6019.50 |
| mtf_confirm | 2711 | 49.58% | $-2172.02 | $-0.8012 | 0.781 | $2236.75 |

MTF delta: PnL **$+3820.11**, WR **-1.43 pp**, expectancy **$-0.1835/trade**, trade count **-6989**.

### MTF confirmation by pair

| Pair | Trades | WR | PnL | PF | DD |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 575 | 50.26% | $-411.75 | 0.801 | $477.75 |
| ETHUSDT | 673 | 50.82% | $-428.60 | 0.821 | $428.60 |
| SOLUSDT | 796 | 49.37% | $-662.00 | 0.773 | $683.50 |
| BNBUSDT | 667 | 47.98% | $-669.67 | 0.733 | $725.75 |

## Decision rule

No threshold sweep follows automatically. KEEP as a live-candidate research branch only if causal MTF materially improves economics and is not dependent on one pair or one recent window; otherwise REJECT this concept.
