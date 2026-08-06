"""V4 Frozen Entry Sweep — C1 from ChatGPT verification framework.

1. Run FilteredSwitcher V4 once → extract all entry candidates
2. Freeze entry stream (bar, side, price)  
3. Sweep TP/SL independently on each entry against subsequent candles
4. No one-position blocking during sweep (entries evaluated independently)
5. TP/SL tracking starts from entry_bar + 1 (no same-bar exit)

GET /filtered_switcher/v4_sweep?symbol=SOLUSDT&days=971
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Position
from filtered_switcher_endpoint import FilteredSwitcher, _load, _ema, _compute_va

router_sweep = APIRouter(prefix="/filtered_switcher", tags=["filtered_switcher_sweep"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

@router_sweep.get("/v4_sweep")
def v4_frozen_sweep(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=1, le=1500),
    ema_period: int = Query(7), ema_slow: int = Query(20),
    bull_body: float = Query(0.5), bear_body: float = Query(0.6),
    fee_pct: float = Query(0.001), slippage_pct: float = Query(0.0005),
    slope_lb: int = Query(3), struct_lb: int = Query(5),
    ref_tp: float = Query(0.013), ref_sl: float = Query(0.013),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_period, ema_slow) + 60:
        return {"error": f"Not enough candles: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    V = np.array([r[5] for r in rows], dtype=float)
    n = len(rows)

    ema_f = _ema(C, ema_period); ema_s = _ema(C, ema_slow)
    vahs, vals, pocs = _compute_va(H.tolist(), L.tolist(), C.tolist(), V.tolist(), 50)

    # Step 1: Run V4 with reference TP/SL to get entry stream
    cfg = Mode3BBCConfig()
    cfg.ema_period = ema_period; cfg.tp_pct = ref_tp; cfg.sl_pct = ref_sl
    cfg.bull_body_ratio_min = bull_body; cfg.bear_body_ratio_min = bear_body
    cfg.bull_mtf_15m_enabled = False; cfg.bear_mtf_15m_enabled = False
    cfg.sideways_mtf_15m_enabled = False; cfg.enable_sideways_trades = False
    cfg.direct_transition_enabled = True
    cfg.fee_pct_roundtrip = fee_pct; cfg.slippage_pct = slippage_pct

    sw = FilteredSwitcher(cfg, version=4,
        ema_fast_s=ema_f, ema_slow_s=ema_s, all_H=H, all_L=L, all_C=C,
        slope_lb=slope_lb, struct_lb=struct_lb,
        tp_for_room=ref_tp, fee_for_room=fee_pct+slippage_pct)

    for i in range(n):
        sw.process_candle(i, O[i], H[i], L[i], C[i], ema_f[i], vahs[i], vals[i], pocs[i])

    # Extract frozen entries from V4 trades
    entries = []
    for t in sw.trades:
        entries.append({
            "bar": t.entry_bar, "side": t.side, "tool": t.tool,
            "price": t.entry_price, "trigger": t.entry_trigger,
        })

    # Step 2: Sweep TP/SL on frozen entries
    cost = fee_pct + slippage_pct
    notional = 10.0 * 50.0  # $500
    tp_range = [0.008, 0.010, 0.013, 0.015, 0.020, 0.025, 0.030]
    sl_range = [0.010, 0.013, 0.015, 0.020, 0.025]

    results = []
    for tp in tp_range:
        for sl in sl_range:
            trades_out = []
            for e in entries:
                entry_bar = e["bar"]
                entry_price = e["price"]
                side = e["side"]

                if side == "LONG":
                    tp_level = entry_price * (1 + tp)
                    sl_level = entry_price * (1 - sl)
                else:
                    tp_level = entry_price * (1 - tp)
                    sl_level = entry_price * (1 + sl)

                outcome = None
                exit_bar = None
                for j in range(entry_bar + 1, min(entry_bar + 200, n)):
                    hj = H[j]; lj = L[j]
                    if side == "LONG":
                        hit_sl = lj <= sl_level
                        hit_tp = hj >= tp_level
                    else:
                        hit_sl = hj >= sl_level
                        hit_tp = lj <= tp_level
                    if hit_sl:
                        outcome = "SL"; exit_bar = j; break
                    elif hit_tp:
                        outcome = "TP"; exit_bar = j; break

                if outcome is None:
                    outcome = "EXPIRE"; exit_bar = min(entry_bar + 200, n - 1)

                if outcome == "TP":
                    pnl = tp - cost
                elif outcome == "SL":
                    pnl = -(sl + cost)
                else:
                    last_c = C[exit_bar]
                    if side == "LONG":
                        pnl = (last_c - entry_price) / entry_price - cost
                    else:
                        pnl = (entry_price - last_c) / entry_price - cost

                trades_out.append({
                    "side": side, "tool": e["tool"], "outcome": outcome,
                    "pnl_usd": round(pnl * notional, 2),
                    "hold_bars": exit_bar - entry_bar,
                })

            total = len(trades_out)
            wins = sum(1 for t in trades_out if t["pnl_usd"] > 0)
            total_pnl = sum(t["pnl_usd"] for t in trades_out)
            wr = round(100 * wins / total, 2) if total else 0

            # Per side
            longs = [t for t in trades_out if t["side"] == "LONG"]
            shorts = [t for t in trades_out if t["side"] == "SHORT"]
            l_wins = sum(1 for t in longs if t["pnl_usd"] > 0)
            s_wins = sum(1 for t in shorts if t["pnl_usd"] > 0)

            # Per tool
            bulls = [t for t in trades_out if t["tool"] == "BULL"]
            bears = [t for t in trades_out if t["tool"] == "BEAR"]
            bu_wins = sum(1 for t in bulls if t["pnl_usd"] > 0)
            be_wins = sum(1 for t in bears if t["pnl_usd"] > 0)

            # Drawdown
            eq = 0; pk = 0; mdd = 0; ms = 0; cs = 0
            for t in trades_out:
                eq += t["pnl_usd"]
                if eq > pk: pk = eq
                dd = pk - eq
                if dd > mdd: mdd = dd
                if t["pnl_usd"] <= 0: cs += 1; ms = max(ms, cs)
                else: cs = 0

            # Exit breakdown
            eb = {}
            for t in trades_out:
                eb[t["outcome"]] = eb.get(t["outcome"], 0) + 1

            # BE WR
            w_val = tp - cost; l_val = sl + cost
            be_wr = round(100 * l_val / (w_val + l_val), 1)

            results.append({
                "tp_pct": tp, "sl_pct": sl, "be_wr": be_wr,
                "trades": total, "wr": wr, "pnl": round(total_pnl, 2),
                "expectancy": round(total_pnl / total, 3) if total else 0,
                "max_dd": round(mdd, 2), "max_ls": ms,
                "exit_breakdown": eb,
                "bull": {"count": len(bulls), "wr": round(100*bu_wins/len(bulls),1) if bulls else 0, "pnl": round(sum(t["pnl_usd"] for t in bulls),2)},
                "bear": {"count": len(bears), "wr": round(100*be_wins/len(bears),1) if bears else 0, "pnl": round(sum(t["pnl_usd"] for t in bears),2)},
                "long": {"count": len(longs), "wr": round(100*l_wins/len(longs),1) if longs else 0, "pnl": round(sum(t["pnl_usd"] for t in longs),2)},
                "short": {"count": len(shorts), "wr": round(100*s_wins/len(shorts),1) if shorts else 0, "pnl": round(sum(t["pnl_usd"] for t in shorts),2)},
            })

    # Sort by PnL
    results.sort(key=lambda x: x["pnl"], reverse=True)

    return {
        "symbol": symbol, "days": days, "candles": n,
        "frozen_entries": len(entries),
        "frozen_entry_breakdown": {
            "BULL": sum(1 for e in entries if e["tool"] == "BULL"),
            "BEAR": sum(1 for e in entries if e["tool"] == "BEAR"),
        },
        "sweep_configs": len(results),
        "feasibility": {
            "entries": len(entries),
            "notional": notional,
            "max_profit_all_win_tp1.3": round(len(entries) * (0.013 - cost) * notional, 0),
            "max_profit_all_win_tp2.0": round(len(entries) * (0.020 - cost) * notional, 0),
            "max_profit_all_win_tp3.0": round(len(entries) * (0.030 - cost) * notional, 0),
        },
        "results": results,
    }
