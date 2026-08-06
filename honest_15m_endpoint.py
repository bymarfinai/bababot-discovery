"""Honest 15m Entry — NO look-ahead.

1H state machine detects BULL/BEAR.
After signal, monitor 15m candles in SUBSEQUENT hours (not same hour).
Entry at first 15m EMA reclaim/reject close. TP/SL tracked from next 15m bar.

GET /honest_15m/backtest?symbol=SOLUSDT&days=971&ema_1h=7&ema_15m=20&tp_pct=0.015&sl_pct=0.015
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter(prefix="/honest_15m", tags=["honest_15m"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load_candles(symbol, timeframe, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ts = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time, open, high, low, close, volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (symbol, timeframe, start_ts, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(closes, period):
    ema = np.zeros(len(closes)); ema[0] = closes[0]; k = 2.0 / (period + 1)
    for i in range(1, len(closes)): ema[i] = closes[i] * k + ema[i-1] * (1-k)
    return ema

@router.get("/backtest")
def honest_15m_backtest(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=1, le=1500),
    ema_1h: int = Query(7, ge=3, le=100), ema_15m: int = Query(20, ge=3, le=100),
    tp_pct: float = Query(0.015, ge=0.001, le=0.10), sl_pct: float = Query(0.015, ge=0.001, le=0.10),
    body_ratio_min: float = Query(0.0, ge=0.0, le=1.0),
    fee_pct: float = Query(0.0015), entry_usd: float = Query(10.0), leverage: float = Query(50.0),
    max_wait_hours: int = Query(4, ge=1, le=24), use_wick_exit: bool = Query(True),
):
    rows_1h = _load_candles(symbol, "1h", days)
    rows_15m = _load_candles(symbol, "15m", days)
    if len(rows_1h) < ema_1h + 10: return {"error": f"Not enough 1H: {len(rows_1h)}"}
    if len(rows_15m) < ema_15m + 10: return {"error": f"Not enough 15m: {len(rows_15m)}"}

    closes_1h = np.array([r[4] for r in rows_1h], dtype=float)
    opens_1h = np.array([r[1] for r in rows_1h], dtype=float)
    highs_1h = np.array([r[2] for r in rows_1h], dtype=float)
    lows_1h = np.array([r[3] for r in rows_1h], dtype=float)
    times_1h = [r[0] for r in rows_1h]
    ema_1h_s = _ema(closes_1h, ema_1h)

    closes_15m = np.array([r[4] for r in rows_15m], dtype=float)
    opens_15m = np.array([r[1] for r in rows_15m], dtype=float)
    highs_15m = np.array([r[2] for r in rows_15m], dtype=float)
    lows_15m = np.array([r[3] for r in rows_15m], dtype=float)
    times_15m = [r[0] for r in rows_15m]
    ema_15m_s = _ema(closes_15m, ema_15m)
    idx_15m = {t: i for i, t in enumerate(times_15m)}

    notional = entry_usd * leverage; warmup = max(ema_1h * 2, 50)
    trades = []; position = None; pending = None
    stats = {"signals_fired": 0, "signals_filled": 0, "signals_expired": 0, "bull_signals": 0, "bear_signals": 0, "wait_bars": []}

    for i in range(warmup, len(rows_1h)):
        o, h, l, c = opens_1h[i], highs_1h[i], lows_1h[i], closes_1h[i]
        ema_val = ema_1h_s[i]; t_1h = times_1h[i]
        br = h - l; body = abs(c - o); body_r = body / br if br > 0 else 0
        M = 15 * 60 * 1000

        # TP/SL check on 15m bars
        if position is not None:
            for k in range(4):
                t15 = t_1h + k * M; j = idx_15m.get(t15)
                if j is None: continue
                # Skip the entry candle itself
                if t15 <= position["entry_time"]: continue
                h15, l15 = highs_15m[j], lows_15m[j]
                if position["side"] == "LONG":
                    hit_sl = l15 <= position["sl"]; hit_tp = h15 >= position["tp"]
                else:
                    hit_sl = h15 >= position["sl"]; hit_tp = l15 <= position["tp"]
                if hit_sl:
                    pnl = -sl_pct - fee_pct
                    trades.append({"side": position["side"], "entry_price": round(position["entry_price"],4), "exit_type": "SL", "pnl_pct": round(pnl*100,3), "pnl_usd": round(pnl*notional,2), "wait_bars_15m": position.get("wait_bars",0)})
                    position = None; break
                elif hit_tp:
                    pnl = tp_pct - fee_pct
                    trades.append({"side": position["side"], "entry_price": round(position["entry_price"],4), "exit_type": "TP", "pnl_pct": round(pnl*100,3), "pnl_usd": round(pnl*notional,2), "wait_bars_15m": position.get("wait_bars",0)})
                    position = None; break

        # Pending signal check
        if pending is not None and position is None:
            if t_1h > pending["wait_until"]:
                stats["signals_expired"] += 1; pending = None
            else:
                for k in range(4):
                    t15 = t_1h + k * M; j = idx_15m.get(t15)
                    if j is None: continue
                    if t15 < pending["start_time"]: continue
                    o15, h15, l15, c15 = opens_15m[j], highs_15m[j], lows_15m[j], closes_15m[j]
                    ema15 = ema_15m_s[j]
                    if pending["side"] == "LONG":
                        reclaim = (l15 <= ema15) and (c15 > ema15) and (c15 > o15)
                    else:
                        reclaim = (h15 >= ema15) and (c15 < ema15) and (c15 < o15)
                    if reclaim:
                        ep = c15; wb = max(0, (t15 - pending["start_time"]) // M)
                        if pending["side"] == "LONG":
                            tp_l = ep * (1 + tp_pct); sl_l = ep * (1 - sl_pct)
                        else:
                            tp_l = ep * (1 - tp_pct); sl_l = ep * (1 + sl_pct)
                        position = {"side": pending["side"], "entry_price": ep, "entry_time": t15, "tp": tp_l, "sl": sl_l, "signal_bar": pending["signal_bar"], "wait_bars": wb}
                        stats["signals_filled"] += 1; stats["wait_bars"].append(wb); pending = None; break

        # New 1H signal
        if position is None and pending is None:
            is_bull = (l <= ema_val) and (c > ema_val) and (c > o)
            is_bear = (h >= ema_val) and (c < ema_val) and (c < o)
            if body_ratio_min > 0 and body_r < body_ratio_min: is_bull = False; is_bear = False
            if is_bull:
                pending = {"side": "LONG", "signal_bar": i, "start_time": t_1h + 3600*1000, "wait_until": t_1h + (max_wait_hours+1)*3600*1000}
                stats["signals_fired"] += 1; stats["bull_signals"] += 1
            elif is_bear:
                pending = {"side": "SHORT", "signal_bar": i, "start_time": t_1h + 3600*1000, "wait_until": t_1h + (max_wait_hours+1)*3600*1000}
                stats["signals_fired"] += 1; stats["bear_signals"] += 1

    total = len(trades); wins = [t for t in trades if t["pnl_usd"] > 0]; losses = [t for t in trades if t["pnl_usd"] <= 0]
    total_pnl = sum(t["pnl_usd"] for t in trades); wr = round(100*len(wins)/total, 2) if total else 0
    longs = [t for t in trades if t["side"]=="LONG"]; shorts = [t for t in trades if t["side"]=="SHORT"]
    lw = [t for t in longs if t["pnl_usd"]>0]; sw = [t for t in shorts if t["pnl_usd"]>0]
    eq = 0; pk = 0; mdd = 0; ms = 0; cs = 0
    for t in trades:
        eq += t["pnl_usd"]
        if eq > pk: pk = eq
        dd = pk - eq
        if dd > mdd: mdd = dd
        if t["pnl_usd"] <= 0: cs += 1; ms = max(ms, cs)
        else: cs = 0
    avg_w = round(sum(stats["wait_bars"])/len(stats["wait_bars"]),1) if stats["wait_bars"] else 0
    fr = round(100*stats["signals_filled"]/stats["signals_fired"],1) if stats["signals_fired"] else 0

    return {
        "symbol": symbol, "days": days, "candles_1h": len(rows_1h), "candles_15m": len(rows_15m),
        "config": {"ema_1h": ema_1h, "ema_15m": ema_15m, "tp_pct": tp_pct, "sl_pct": sl_pct, "body_ratio_min": body_ratio_min, "fee_pct": fee_pct, "max_wait_hours": max_wait_hours, "notional": notional},
        "signal_stats": {"total_signals": stats["signals_fired"], "bull": stats["bull_signals"], "bear": stats["bear_signals"], "filled": stats["signals_filled"], "expired": stats["signals_expired"], "fill_rate_pct": fr, "avg_wait_bars_15m": avg_w, "avg_wait_minutes": round(avg_w*15,0)},
        "summary": {"total_trades": total, "wins": len(wins), "losses": len(losses), "win_rate_pct": wr, "total_pnl_usd": round(total_pnl,2), "max_drawdown_usd": round(mdd,2), "max_loss_streak": ms},
        "per_side": {"LONG": {"count": len(longs), "wr_pct": round(100*len(lw)/len(longs),2) if longs else 0, "pnl_usd": round(sum(t["pnl_usd"] for t in longs),2)}, "SHORT": {"count": len(shorts), "wr_pct": round(100*len(sw)/len(shorts),2) if shorts else 0, "pnl_usd": round(sum(t["pnl_usd"] for t in shorts),2)}},
        "trades": trades[-20:],
    }
