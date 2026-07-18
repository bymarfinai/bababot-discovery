# BabaBot BBC — Single Source of Truth v19
## Updated: 2026-07-18

## CURRENT STATE

### BBC Engine v2.5 CLEAN
- **Repo**: `bymarfinai/bababot-discovery` (private)
- **Railway**: `https://web-production-b6a05.up.railway.app`
- **MCP**: `https://bababot-mcp.bymarfinai.workers.dev` (v2.7, 54 tools)
- **Dashboard**: Cloudflare Pages `bababot-dashboard-v2`

### Config v2.5 (locked)
```
TF: 1h main, 15m MTF entry
EMA: 20 (sweepable 5-50)
BULL: TP 1.3%, SL 1.3%, body 0.5, MTF 15m ON
BEAR: TP 1.3%, SL 1.3%, body 0.6, MTF 15m ON
SW:   TP 1.5%, SL wick, body 0.6, MTF 15m ON
VA:   50 candle window, 85/15 percentile
Direct transition: ON
Trailing EMA: available but OFF by default (sweepable)
Entry: $10 × 50x leverage = $500 notional
Fees: 0.1% roundtrip + 0.05% slippage
```

### Best Configs Discovered (925 days, 4 pairs BTC/ETH/BNB/SOL)
| Config | EMA | TP | SL | Trades | B+B WR | Total PnL |
|---|---|---|---|---|---|---|
| v2.3 baseline | 20 | 1.3% | 1.3% | 3,740 | 66.6% | $3,918 |
| **EMA7 TP0.9% (WR 75%)** | 7 | 0.9% | 1.3% | 5,296 | 74.7% | $5,197 |
| **EMA7 TP1.0% (WR 72%)** | 7 | 1.0% | 1.3% | 5,103 | 72.0% | $5,352 |
| **EMA7 TP1.3% (max PnL)** | 7 | 1.3% | 1.3% | 4,689 | 65.4% | $6,060 |
| 1H+4H combined | 20+4H7 | 1.3%+2% | 1.3% | ~4,550 | 75.5% 4H | $7,669 |
| EMA7+Trail5+cap5% | 7 | trail | 1.3% | 7,860 | 40.3% | $8,381 |
| 4H EMA7 TP2% only | 7(4H) | 2.0% | 1.3% | 1,365 | 77.3% | $6,957 |

### Per Pair (v2.3 EMA20 TP1.3%)
| Pair | Trades | WR | PnL |
|---|---|---|---|
| SOL | 1,054 | 63.0% | $1,751 |
| ETH | 937 | 56.9% | $950 |
| BNB | 914 | 53.7% | $649 |
| BTC | 831 | 51.9% | $563 |

### Key Strategy Insights
- Strategy is **reversal/mean-reversion** based at EMA
- Counter-trend entries (BULL during death cross) have HIGHER WR
- 4H directional filter DOESN'T WORK (blocks profitable counter entries)
- 4H as BONUS entry layer WORKS (+$3,762, 75.5% WR, no position overlap)
- WR control via TP/SL ratio: lower TP = higher WR (TP 0.9% → 74.7% WR)
- Trailing EMA exit: max PnL $8,381 but WR drops to 40%
- Avg trade duration: 6.0h (median 3h), funding rate impact ~3.6%

### What Was Explored But DIDN'T Work
- 4H EMA filter (blocks profitable counter-trend entries)
- 4H EMA slope filter (no consistent pattern)
- POC breakout entry (WR 44% but PnL negative)
- SW EMA distance filter (+$36 max, negligible)
- Dual MA crossover filter (counter entries win MORE)
- Funding rate / OI (couldn't access Binance API from sandbox)
- Move-to-BE trailing (kills trend winners)

## FILES & SHAS

### Backend (Railway)
- `mode3_bbc/config.py` — v2.5 clean, no 4H filter
- `mode3_bbc/switcher.py` — v2.5 clean, trailing EMA available
- `mode3_bbc/__init__.py` — exports
- `mode3_bbc_endpoint.py` — v2.5 clean, all params sweepable
- `bbc_sweep_endpoint.py` — batch sweep + DB + filterable results
- `app.py` — BBC + sweep endpoints mounted

### MCP (Cloudflare)
- `mcp-server/src/index.ts` — v2.7, 54 tools including 6 BBC tools
- BBC tools: bbc_backtest, bbc_presets, bbc_sweep_start, bbc_sweep_run, bbc_sweep_status, bbc_sweep_results

### Frontend (Cloudflare Pages)
- `src/app/App.tsx` — BBC as P1 sub-mode (dropdown: SL/TP, Tick, BBC)
- `src/app/components/BBCSweepPanel.tsx` — sweep panel with presets + equity chart
- `src/app/components/TabNav.tsx` — Lucide icons (no emoji), 7 tabs
- `src/app/api.ts` — cleaned (737→480 lines), 57 functions + 6 BBC

### Sweep Job
- Job ID: `0021d3e6254c` (8,960 combos, 15 processed)
- DB table: `bbc_sweep_results`

## COMPLETED STEPS
1. ✅ BBC engine v2.0-v2.5 (config, switcher, endpoint)
2. ✅ Sweep endpoint + DB storage
3. ✅ Dashboard BBC panel (P1 sub-mode, presets, equity chart)
4. ✅ MCP v2.7 (54 tools, 6 BBC)
5. ✅ UI/UX audit (emoji→Lucide, api cleanup, dead code identified)

## PENDING STEPS
6. **TradingView/Lightweight Charts** — candlestick + trade markers + EMA overlay
   - Need: `npm install lightweight-charts`
   - Need: backend endpoint returning OHLCV candle data (currently only returns trades)
   - Need: frontend component with chart + trade markers
7. **Live bot implementation** — BBC state machine in baret_live
   - Need: "Save to Live" button from sweep results
   - Need: BBC state machine running on live tick data
8. **Full sweep run** — process all 8,960 combos
   - Via dashboard "Run Batch" button or MCP bbc_sweep_run
9. **Delete 8 unused components** (1,914 lines dead code)
   - BaretModePanel, DCAModePanel, P2ValidationPanel, P3PortfolioPanel
   - MultiPeriodView, StrategyDrillDown, EquityCurve, PortfolioCalculator
