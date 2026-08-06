"""Filtered EMA Reclaim — V0-V4 progressive filters, MTF OFF, 1H close entry.

V0: Baseline EMA reclaim (same as BBC MTF OFF)
V1: V0 + EMA slope positive
V2: V1 + trend structure (higher high / higher low)
V3: V2 + room to resistance (distance to swing high > TP)
V4: V3 + follow-through (next candle confirms)

GET /filtered_reclaim/backtest?symbol=SOLUSDT&days=971&version=2&ema_fast=7&ema_slow=20
"""
import os, sqlite3, numpy as np
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter(prefix="/filtered_reclaim", tags=["filtered_reclaim"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def _load(symbol, tf, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute("SELECT open_time,open,high,low,close,volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (symbol, tf, start, now_ms))
    rows = cur.fetchall(); conn.close(); return rows

def _ema(c, p):
    e = np.zeros(len(c)); e[0] = c[0]; k = 2.0/(p+1)
    for i in range(1, len(c)): e[i] = c[i]*k + e[i-1]*(1-k)
    return e

def _atr(h, l, c, period=14):
    n = len(h); atr = np.zeros(n)
    for i in range(1, n):
        tr = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
        if i < period: atr[i] = atr[i-1] + (tr - atr[i-1]) / i
        else: atr[i] = atr[i-1] + (tr - atr[i-1]) / period
    return atr

@router.get("/backtest")
def filtered_reclaim_backtest(
    symbol: str = Query("SOLUSDT"), days: int = Query(971, ge=1, le=1500),
    version: int = Query(0, ge=0, le=4),
    ema_fast: int = Query(7, ge=3, le=50),
    ema_slow: int = Query(20, ge=5, le=200),
    tp_pct: float = Query(0.015, ge=0.001, le=0.10),
    sl_pct: float = Query(0.015, ge=0.001, le=0.10),
    body_ratio_min: float = Query(0.0, ge=0.0, le=1.0),
    fee_pct: float = Query(0.0015),
    entry_usd: float = Query(10.0), leverage: float = Query(50.0),
    slope_lookback: int = Query(3, ge=1, le=10),
    structure_lookback: int = Query(5, ge=3, le=20),
    pullback_max_atr: float = Query(0.5, ge=0.0, le=3.0),
    use_wick_exit: bool = Query(True),
):
    rows = _load(symbol, "1h", days)
    if len(rows) < max(ema_fast, ema_slow) + 60: return {"error": f"Not enough: {len(rows)}"}

    O = np.array([r[1] for r in rows], dtype=float)
    H = np.array([r[2] for r in rows], dtype=float)
    L = np.array([r[3] for r in rows], dtype=float)
    C = np.array([r[4] for r in rows], dtype=float)
    T = [r[0] for r in rows]

    ema_f = _ema(C, ema_fast)
    ema_s = _ema(C, ema_slow)
    atr = _atr(H, L, C, 14)

    notional = entry_usd * leverage
    warmup = max(ema_slow * 2, 60)
    n = len(rows)

    trades = []; position = None
    filter_stats = {"total_signals": 0, "slope_blocked": 0, "structure_blocked": 0,
                    "room_blocked": 0, "followthrough_blocked": 0, "passed": 0}

    i = warmup
    while i < n:
        o, h, l, c = O[i], H[i], L[i], C[i]
        ef = ema_f[i]; es = ema_s[i]
        br = h - l; body = abs(c - o); body_r = body / br if br > 0 else 0

        # TP/SL check
        if position is not None:
            if position["side"] == "LONG":
                hit_sl = (l if use_wick_exit else c) <= position["sl"]
                hit_tp = (h if use_wick_exit else c) >= position["tp"]
            else:
                hit_sl = (h if use_wick_exit else c) >= position["sl"]
                hit_tp = (l if use_wick_exit else c) <= position["tp"]
            if hit_sl:
                pnl = -sl_pct - fee_pct
                trades.append({"side": position["side"], "entry": round(position["entry"],4), "exit_type": "SL", "pnl_pct": round(pnl*100,3), "pnl_usd": round(pnl*notional,2), "entry_bar": position["bar"], "exit_bar": i, "version": position.get("ver","")})
                position = None; i += 1; continue
            elif hit_tp:
                pnl = tp_pct - fee_pct
                trades.append({"side": position["side"], "entry": round(position["entry"],4), "exit_type": "TP", "pnl_pct": round(pnl*100,3), "pnl_usd": round(pnl*notional,2), "entry_bar": position["bar"], "exit_bar": i, "version": position.get("ver","")})
                position = None; i += 1; continue

        if position is None:
            is_bull = (l <= ef) and (c > ef) and (c > o)
            is_bear = (h >= ef) and (c < ef) and (c < o)
            if body_ratio_min > 0 and body_r < body_ratio_min: is_bull = False; is_bear = False

            if is_bull or is_bear:
                filter_stats["total_signals"] += 1
                side = "LONG" if is_bull else "SHORT"
                ver = "V0"

                # V1: EMA SLOPE
                if version >= 1 and i >= slope_lookback:
                    if side == "LONG":
                        ok = (ema_f[i] > ema_f[i-slope_lookback]) and (ema_s[i] > ema_s[i-slope_lookback])
                    else:
                        ok = (ema_f[i] < ema_f[i-slope_lookback]) and (ema_s[i] < ema_s[i-slope_lookback])
                    if not ok: filter_stats["slope_blocked"] += 1; i += 1; continue
                    ver = "V1"

                # V2: TREND STRUCTURE
                if version >= 2 and i >= structure_lookback:
                    rh = H[i-structure_lookback:i+1]; rl = L[i-structure_lookback:i+1]
                    if side == "LONG":
                        ok = (H[i] >= np.percentile(rh, 50)) and (L[i] >= np.min(rl[:-1]))
                    else:
                        ok = (L[i] <= np.percentile(rl, 50)) and (H[i] <= np.max(rh[:-1]))
                    if not ok: filter_stats["structure_blocked"] += 1; i += 1; continue
                    ver = "V2"

                # V3: ROOM TO RESISTANCE
                if version >= 3 and i >= 20:
                    if side == "LONG":
                        swing_hi = np.max(H[i-20:i])
                        room = (swing_hi - c) / c
                    else:
                        swing_lo = np.min(L[i-20:i])
                        room = (c - swing_lo) / c
                    if room < tp_pct + fee_pct: filter_stats["room_blocked"] += 1; i += 1; continue
                    ver = "V3"

                # V4: FOLLOW-THROUGH
                if version >= 4:
                    if i + 1 >= n: i += 1; continue
                    o1, h1, l1, c1 = O[i+1], H[i+1], L[i+1], C[i+1]
                    if side == "LONG":
                        ok = (c1 > ema_f[i+1]) and (h1 > h)
                    else:
                        ok = (c1 < ema_f[i+1]) and (l1 < l)
                    if not ok: filter_stats["followthrough_blocked"] += 1; i += 1; continue
                    c = c1; i += 1
                    ver = "V4"

                entry_price = c
                if side == "LONG":
                    tp_l = entry_price*(1+tp_pct); sl_l = entry_price*(1-sl_pct)
                else:
                    tp_l = entry_price*(1-tp_pct); sl_l = entry_price*(1+sl_pct)
                position = {"side": side, "entry": entry_price, "bar": i, "tp": tp_l, "sl": sl_l, "ver": ver}
                filter_stats["passed"] += 1

        i += 1

    total = len(trades); wins = [t for t in trades if t["pnl_usd"]>0]
    total_pnl = sum(t["pnl_usd"] for t in trades)
    wr = round(100*len(wins)/total,2) if total else 0
    longs = [t for t in trades if t["side"]=="LONG"]; shorts = [t for t in trades if t["side"]=="SHORT"]
    lw = [t for t in longs if t["pnl_usd"]>0]; sw = [t for t in shorts if t["pnl_usd"]>0]
    eq=0;pk=0;mdd=0;ms=0;cs=0
    for t in trades:
        eq+=t["pnl_usd"]
        if eq>pk:pk=eq
        dd=pk-eq
        if dd>mdd:mdd=dd
        if t["pnl_usd"]<=0:cs+=1;ms=max(ms,cs)
        else:cs=0

    return {
        "symbol": symbol, "days": days, "candles": len(rows), "version": f"V{version}",
        "config": {"ema_fast": ema_fast, "ema_slow": ema_slow, "tp_pct": tp_pct, "sl_pct": sl_pct, "body_ratio_min": body_ratio_min, "fee_pct": fee_pct, "slope_lookback": slope_lookback, "structure_lookback": structure_lookback, "notional": notional},
        "filter_stats": filter_stats,
        "summary": {"total_trades": total, "wins": len(wins), "losses": total-len(wins), "win_rate_pct": wr, "total_pnl_usd": round(total_pnl,2), "max_drawdown_usd": round(mdd,2), "max_loss_streak": ms},
        "per_side": {"LONG": {"count": len(longs), "wr_pct": round(100*len(lw)/len(longs),2) if longs else 0, "pnl_usd": round(sum(t["pnl_usd"] for t in longs),2)}, "SHORT": {"count": len(shorts), "wr_pct": round(100*len(sw)/len(shorts),2) if shorts else 0, "pnl_usd": round(sum(t["pnl_usd"] for t in shorts),2)}},
        "trades": trades[-20:],
    }
