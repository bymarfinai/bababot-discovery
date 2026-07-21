# BabaBot BBC — Single Source of Truth v20
## Updated: 2026-07-21

## CRITICAL: BBC LIVE STUCK — NEEDS DEBUG

### Issue
- `bbc_live.py` exists and running (`thread_alive: true`)
- But `cycle_count: 0` after 12+ hours
- Thread likely stuck in wait loop or crashed silently after Railway redeploy
- Need to debug: `_bbc_live_loop`, `at_boundary()`, `_fetch_candles()`

### BBC Live Engine
- File: `bbc_live.py` (SEPARATE from `baret_live.py`)
- NOT inside baret_live — completely independent engine
- Uses BBC state machine (BULL/BEAR/SIDEWAYS) from `mode3_bbc/switcher.py`

## CURRENT STATE

### Infrastructure
- **Repo**: `bymarfinai/bababot-discovery` (private)
- **Railway**: `https://web-production-b6a05.up.railway.app`
- **MCP**: `https://bababot-mcp.bymarfinai.workers.dev` (v2.7, 54 tools)
- **Dashboard**: Cloudflare Pages `bababot-dashboard-v2`

### BBC Engine v2.5 CLEAN (Backtest)
```
TF: 1h main, 15m MTF entry
EMA: 20 default (sweepable 5-50, EMA7 best)
BULL: TP 1.3%, SL 1.3%, body 0.5, MTF 15m ON
BEAR: TP 1.3%, SL 1.3%, body 0.6, MTF 15m ON
SW:   TP 1.5%, SL wick, body 0.6, MTF 15m ON
Direct transition: ON
Trailing EMA: available (sweepable)
Entry: $10 × 50x = $500 notional
```

### Recommended LIVE Configs (from full sweep, B+B WR ≥65%)
| Pair | EMA | TP | SL | Body B/R | B+B WR | PnL (925d) |
|---|---|---|---|---|---|---|
| SOL | 7 | 1.3% | 1.5% | 0.7/0.7 | 76.6% | $2,562 |
| ETH | 7 | 1.3% | 1.5% | 0.5/0.6 | 69.9% | $1,790 |
| BNB | 7 | 1.3% | 2.0% | 0.6/0.7 | 75.5% | $1,463 |
| DOGE | 7 | 1.3% | 1.5% | 0.7/0.5 | 71.8% | $1,108 |
| BTC | 7 | 1.3% | 1.3% | 0.7/0.7 | 66.2% | $947 |
| **TOTAL** | | | | | **~72%** | **$7,870** |

NOTE: "win_rate" in sweep DB = TOTAL WR (incl SW ~29%). BULL+BEAR WR is higher.
To get B+B WR: calculate from bull_wr × bull_trades + bear_wr × bear_trades.

### Sweep Results
- 11,200 results in DB (5 pairs × 2,240 configs each)
- All complete, queryable via `/mode3_bbc/sweep/results`
- Job ID: `0021d3e6254c`

### Key Strategy Insights
- Strategy is **reversal/mean-reversion** at EMA
- Counter-trend entries have HIGHER WR (don't filter them!)
- 4H directional filter DOESN'T WORK (tested, removed)
- 4H as BONUS entry layer WORKS (+$3,762, 75.5% WR)
- WR control via TP/SL ratio: lower TP = higher WR
- SL wider than TP = better for this strategy (gives room to bounce)
- Avg trade duration: 6.0h (median 3h)
- Funding rate impact: ~3.6% of PnL

### Files
- `mode3_bbc/config.py` — v2.5 clean config
- `mode3_bbc/switcher.py` — v2.5 clean state machine
- `mode3_bbc/__init__.py` — exports
- `mode3_bbc_endpoint.py` — backtest API (all params sweepable)
- `bbc_sweep_endpoint.py` — sweep batch + DB + results API
- `bbc_live.py` — BBC LIVE ENGINE (stuck, needs debug)
- `baret_live.py` — original Deret Statistik live (NOT BBC)
- `app.py` — all endpoints mounted

### Dashboard
- BBC in Pipeline 1 dropdown (SL/TP, Tick Clustering, BBC Discovery)
- BBCSweepPanel: presets, quick backtest, equity chart, sweep table
- TabNav: Lucide icons (no emoji)
- api.ts: cleaned 737→480 lines + 6 BBC functions
- 8 unused components identified for deletion

## PENDING
1. **DEBUG BBC LIVE** — fix stuck loop, get cycles running
2. **TradingView chart** — lightweight-charts with candle + trade markers
3. **Add remaining pairs** — ETH/BNB/DOGE/BTC to live configs
4. **Delete 8 dead components** — 1,914 lines dead code
5. **Missing pair data** — AVAX/XRP/LINK/PEPE not in DB yet
