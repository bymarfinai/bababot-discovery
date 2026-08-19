# Market Hunter MH0 — Cross-Sectional Backtest

**Research-only. Live systems untouched.**

Frozen window end-exclusive: `2026-08-19T00:00:00+00:00`
Requested universe: **56** symbols; usable data: **56**.

Primary: causal 1h cross-sectional composite rank → top-1 → next-1h-open entry. Cost 0.15%. Sequential control uses TP/SL 1.3%/1.3%, max 6h.

## 90 days

### Independent hourly opportunities

| Selector | N | 6h positive | 6h net exp | 6h PF |
|---|---:|---:|---:|---:|
| composite | 2154 | 42.85% | $-0.4971 | 0.907 |
| momentum | 2154 | 41.55% | $-1.4523 | 0.791 |
| random | 2154 | 43.22% | $-0.3699 | 0.890 |

### Single-position sequential TP/SL execution

| Selector | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| composite | 915 | 44.04% | $-1115.88 | $-1.2195 | 0.661 | $1127.09 |
| momentum | 1281 | 42.15% | $-2143.68 | $-1.6734 | 0.587 | $2168.93 |
| random | 633 | 46.60% | $-440.96 | $-0.6966 | 0.764 | $456.05 |

## 120 days

### Independent hourly opportunities

| Selector | N | 6h positive | 6h net exp | 6h PF |
|---|---:|---:|---:|---:|
| composite | 2874 | 42.48% | $-0.5242 | 0.909 |
| momentum | 2874 | 42.00% | $-1.6913 | 0.783 |
| random | 2874 | 43.04% | $-0.4709 | 0.862 |

### Single-position sequential TP/SL execution

| Selector | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| composite | 1214 | 43.74% | $-1561.13 | $-1.2859 | 0.645 | $1582.34 |
| momentum | 1805 | 40.89% | $-3367.90 | $-1.8659 | 0.553 | $3376.40 |
| random | 814 | 45.95% | $-704.65 | $-0.8657 | 0.713 | $719.54 |

## 365 days

### Independent hourly opportunities

| Selector | N | 6h positive | 6h net exp | 6h PF |
|---|---:|---:|---:|---:|
| composite | 8753 | 43.46% | $-0.6668 | 0.887 |
| momentum | 8753 | 44.30% | $-0.4844 | 0.934 |
| random | 8753 | 45.00% | $-0.6419 | 0.839 |

### Single-position sequential TP/SL execution

| Selector | Trades | WR | PnL | Exp/trade | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| composite | 3713 | 44.52% | $-4764.95 | $-1.2833 | 0.648 | $4788.39 |
| momentum | 5124 | 42.33% | $-8645.61 | $-1.6873 | 0.586 | $8665.61 |
| random | 2685 | 47.90% | $-1855.09 | $-0.6909 | 0.776 | $1944.76 |

## 365d composite attribution

### Side

| Side | Trades | WR | PnL | PF |
|---|---:|---:|---:|---:|
| LONG | 2427 | 41.99% | $-3984.92 | 0.575 |
| SHORT | 1286 | 49.30% | $-780.04 | 0.812 |

### Top pair contributions

| Pair | PnL | Trades |
|---|---:|---:|
| GALAUSDT | $20.00 | 8 |
| OPUSDT | $9.73 | 55 |
| DOGEUSDT | $3.08 | 67 |
| KAIAUSDT | $-0.50 | 18 |
| BNBUSDT | $-6.56 | 104 |
| APEUSDT | $-10.09 | 13 |
| RUNEUSDT | $-10.25 | 5 |
| JUPUSDT | $-10.50 | 14 |
| LDOUSDT | $-10.55 | 46 |
| SANDUSDT | $-14.75 | 11 |
| MANAUSDT | $-16.00 | 4 |
| STXUSDT | $-16.00 | 4 |

## Chronological blocks — composite sequential

| Block | Trades | WR | PnL | PF | 6h net exp (independent-selected rows within block) |
|---|---:|---:|---:|---:|---:|
| B1 | 907 | 42.34% | $-1460.33 | 0.580 | $-1.5437 |
| B2 | 967 | 46.12% | $-1128.90 | 0.676 | $-1.2174 |
| B3 | 913 | 45.35% | $-1055.10 | 0.674 | $0.0853 |
| B4 | 926 | 44.17% | $-1120.62 | 0.663 | $-0.0545 |

## Coverage

- Median eligible contracts/hour: **55.0**
- Median liquid contracts/hour: **28.0**
- Composite decision timestamps: **8753**

## Frozen verdict

**REJECT_MH0_LIVE_CANDIDATE**

Composite failed one or more preregistered feasibility gates (365d 6h net exp=-0.6667593125273852, sequential exp=-1.2833167129311471, PF=0.6476091266710928, positive blocks=0/4, concentration=0.610). No tuning follows automatically.

MH0 uses a survivorship-screened preregistered symbol list. Even a KEEP only earns a stricter delist-aware MH1; it never authorizes live trading.
