"""Limit Order at EMA Simulation — Proper, no look-ahead.

GET /mode3_bbc/limit_sim?symbol=SOLUSDT&days=925&ema_period=7&tp_pct=0.013&sl_pct=0.02

Rules:
1. State machine runs on 1H candle CLOSE (EMA reclaim/reject, no MTF)
2. After candle N closes and state = BULL → place LIMIT BUY at EMA(N) for candle N+1
3. Candle N+1: if low <= EMA(N) → FILLED at EMA(N) price
4. If NOT filled → cancel, recalculate EMA(N+1), place new limit for N+2
5. If filled → track position on candle N+2, N+3, etc. (NOT same candle as fill)
6. Same-candle fill: conservative — only check TP/SL on NEXT candles
7. TP/SL: if both hit same candle → SL wins (pessimistic)
8. One position at a time
"""
import os
import sqlite3
import numpy as np
from fastapi import APIRouter, Query
from datetime import datetime

router = APIRouter(prefix="/mode3_bbc", tags=["bbc_limit_sim"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _load_candles(symbol, timeframe, days):
    conn = sqlite3.connect(DB_PATH)
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    start_ts = now_ms - (days * 86400 * 1000)
    cur = conn.cursor()
    cur.execute(
        "SELECT open_time, open, high, low, close, volume FROM klines "
        "WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC",
        (symbol, timeframe, start_ts, now_ms))
    rows = cur.fetchall()
    conn.close()
    return rows


def _compute_ema(closes, period):
    ema = np.zeros(len(closes))
    ema[0] = closes[0]
    k = 2.0 / (period + 1)
    for i in range(1, len(closes)):
        ema[i] = closes[i] * k + ema[i - 1] * (1 - k)
    return ema


@router.get("/limit_sim")
def limit_order_sim(
    symbol: str = Query("SOLUSDT"),
    days: int = Query(925, ge=1, le=1500),
    ema_period: int = Query(7, ge=3, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    body_ratio_min: float = Query(0.5, ge=0.0, le=1.0),
    fee_pct: float = Query(0.0015),
    entry_usd: float = Query(10.0),
    leverage: float = Query(50.0),
    fill_on_same_candle_tp: bool = Query(False),  # conservative: False = TP checked NEXT candle only
):
    """
    Proper limit order at EMA simulation.
    
    Timeline per candle:
      Candle N closes → state update → IF state valid → place limit for candle N+1
      Candle N+1 → check if low/high touches EMA → filled at EMA
      If filled: check TP/SL on candle N+2+ (or N+1 if fill_on_same_candle_tp=True)
    """
    rows = _load_candles(symbol, "1h", days)
    if len(rows) < ema_period + 10:
        return {"error": f"Not enough candles: {len(rows)}"}

    closes = np.array([r[4] for r in rows], dtype=float)
    highs = np.array([r[2] for r in rows], dtype=float)
    lows = np.array([r[3] for r in rows], dtype=float)
    opens = np.array([r[1] for r in rows], dtype=float)
    times = [r[0] for r in rows]
    ema = _compute_ema(closes, ema_period)

    notional = entry_usd * leverage
    n = len(rows)

    # State machine: simple EMA-based
    # BULL: close > EMA AND bullish candle (close > open) AND body ratio pass
    # BEAR: close < EMA AND bearish candle (close < open) AND body ratio pass
    # State changes on candle close
    state = "NONE"  # NONE until first signal
    
    # Track everything
    trades = []
    position = None  # {side, entry_price, entry_bar, tp_level, sl_level, filled_bar}
    pending_limit = None  # {side, price, bar_placed, valid_for_bar}
    
    orders_placed = 0
    orders_filled = 0
    orders_cancelled = 0
    same_candle_both_hit = 0
    
    # Warmup EMA
    warmup = max(ema_period * 2, 50)
    
    for i in range(warmup, n):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        ema_val = ema[i]
        prev_ema = ema[i - 1] if i > 0 else ema_val
        bar_range = h - l
        body = abs(c - o)
        body_ratio = body / bar_range if bar_range > 0 else 0
        
        # ── STEP 1: Check pending limit order fill ──
        if pending_limit is not None and position is None:
            lmt = pending_limit
            if lmt["valid_for_bar"] == i:
                filled = False
                if lmt["side"] == "LONG" and l <= lmt["price"]:
                    filled = True
                elif lmt["side"] == "SHORT" and h >= lmt["price"]:
                    filled = True
                
                if filled:
                    orders_filled += 1
                    entry_price = lmt["price"]
                    if lmt["side"] == "LONG":
                        tp_level = entry_price * (1 + tp_pct)
                        sl_level = entry_price * (1 - sl_pct)
                    else:
                        tp_level = entry_price * (1 - tp_pct)
                        sl_level = entry_price * (1 + sl_pct)
                    
                    position = {
                        "side": lmt["side"],
                        "entry_price": entry_price,
                        "entry_bar": i,
                        "filled_bar": i,
                        "tp_level": tp_level,
                        "sl_level": sl_level,
                        "peak_high": h,
                        "trough_low": l,
                        "state_at_entry": state,
                    }
                    
                    # Check TP/SL on SAME candle as fill?
                    if fill_on_same_candle_tp:
                        # Check TP/SL on this candle (AFTER fill point)
                        if lmt["side"] == "LONG":
                            hit_sl = l <= sl_level  # already true if l < sl
                            hit_tp = h >= tp_level
                        else:
                            hit_sl = h >= sl_level
                            hit_tp = l <= tp_level
                        
                        if hit_sl and hit_tp:
                            same_candle_both_hit += 1
                            # Pessimistic: SL wins
                            pnl_pct = -sl_pct - fee_pct
                            pnl_usd = pnl_pct * notional
                            trades.append({
                                "side": lmt["side"], "entry_price": entry_price,
                                "exit_price": sl_level, "entry_bar": i, "exit_bar": i,
                                "exit_type": "SL", "pnl_pct": round(pnl_pct * 100, 3),
                                "pnl_usd": round(pnl_usd, 2), "state": state,
                                "same_candle_fill_exit": True,
                            })
                            position = None
                        elif hit_sl:
                            pnl_pct = -sl_pct - fee_pct
                            pnl_usd = pnl_pct * notional
                            trades.append({
                                "side": lmt["side"], "entry_price": entry_price,
                                "exit_price": sl_level, "entry_bar": i, "exit_bar": i,
                                "exit_type": "SL", "pnl_pct": round(pnl_pct * 100, 3),
                                "pnl_usd": round(pnl_usd, 2), "state": state,
                            })
                            position = None
                        elif hit_tp:
                            pnl_pct = tp_pct - fee_pct
                            pnl_usd = pnl_pct * notional
                            trades.append({
                                "side": lmt["side"], "entry_price": entry_price,
                                "exit_price": tp_level, "entry_bar": i, "exit_bar": i,
                                "exit_type": "TP", "pnl_pct": round(pnl_pct * 100, 3),
                                "pnl_usd": round(pnl_usd, 2), "state": state,
                            })
                            position = None
                else:
                    orders_cancelled += 1
                
                pending_limit = None
        
        # ── STEP 2: Check TP/SL for open position (from PREVIOUS candle fill) ──
        if position is not None and position["filled_bar"] < i:
            pos = position
            pos["peak_high"] = max(pos["peak_high"], h)
            pos["trough_low"] = min(pos["trough_low"], l)
            
            if pos["side"] == "LONG":
                hit_sl = l <= pos["sl_level"]
                hit_tp = h >= pos["tp_level"]
            else:
                hit_sl = h >= pos["sl_level"]
                hit_tp = l <= pos["tp_level"]
            
            if hit_sl and hit_tp:
                same_candle_both_hit += 1
                # Pessimistic: SL wins
                pnl_pct = -sl_pct - fee_pct
                pnl_usd = pnl_pct * notional
                trades.append({
                    "side": pos["side"], "entry_price": pos["entry_price"],
                    "exit_price": pos["sl_level"], "entry_bar": pos["entry_bar"],
                    "exit_bar": i, "exit_type": "SL",
                    "pnl_pct": round(pnl_pct * 100, 3), "pnl_usd": round(pnl_usd, 2),
                    "state": pos["state_at_entry"],
                })
                position = None
            elif hit_sl:
                pnl_pct = -sl_pct - fee_pct
                pnl_usd = pnl_pct * notional
                trades.append({
                    "side": pos["side"], "entry_price": pos["entry_price"],
                    "exit_price": pos["sl_level"], "entry_bar": pos["entry_bar"],
                    "exit_bar": i, "exit_type": "SL",
                    "pnl_pct": round(pnl_pct * 100, 3), "pnl_usd": round(pnl_usd, 2),
                    "state": pos["state_at_entry"],
                })
                position = None
            elif hit_tp:
                pnl_pct = tp_pct - fee_pct
                pnl_usd = pnl_pct * notional
                trades.append({
                    "side": pos["side"], "entry_price": pos["entry_price"],
                    "exit_price": pos["tp_level"], "entry_bar": pos["entry_bar"],
                    "exit_bar": i, "exit_type": "TP",
                    "pnl_pct": round(pnl_pct * 100, 3), "pnl_usd": round(pnl_usd, 2),
                    "state": pos["state_at_entry"],
                })
                position = None
        
        # ── STEP 3: Update state on candle close ──
        is_bull_signal = (l <= ema_val) and (c > ema_val) and (c > o) and (body_ratio >= body_ratio_min)
        is_bear_signal = (h >= ema_val) and (c < ema_val) and (c < o) and (body_ratio >= body_ratio_min)
        
        if is_bull_signal:
            state = "BULL"
        elif is_bear_signal:
            state = "BEAR"
        # If neither signal, keep previous state
        
        # ── STEP 4: Place limit order for NEXT candle (if no position) ──
        if position is None and state in ("BULL", "BEAR"):
            ema_now = ema_val  # EMA at candle N close
            if state == "BULL":
                pending_limit = {
                    "side": "LONG",
                    "price": ema_now,
                    "bar_placed": i,
                    "valid_for_bar": i + 1,  # only valid for next candle
                }
            else:
                pending_limit = {
                    "side": "SHORT",
                    "price": ema_now,
                    "bar_placed": i,
                    "valid_for_bar": i + 1,
                }
            orders_placed += 1
    
    # ── RESULTS ──
    total = len(trades)
    wins = [t for t in trades if t["pnl_usd"] > 0]
    losses = [t for t in trades if t["pnl_usd"] <= 0]
    total_pnl = sum(t["pnl_usd"] for t in trades)
    wr = round(100 * len(wins) / total, 2) if total else 0
    
    # Per-side breakdown
    bull_trades = [t for t in trades if t["side"] == "LONG"]
    bear_trades = [t for t in trades if t["side"] == "SHORT"]
    bull_wins = [t for t in bull_trades if t["pnl_usd"] > 0]
    bear_wins = [t for t in bear_trades if t["pnl_usd"] > 0]
    
    # Equity curve for drawdown
    equity = 0; peak = 0; max_dd = 0; max_streak = 0; streak = 0
    for t in trades:
        equity += t["pnl_usd"]
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > max_dd: max_dd = dd
        if t["pnl_usd"] <= 0: streak += 1; max_streak = max(max_streak, streak)
        else: streak = 0
    
    fill_rate = round(100 * orders_filled / orders_placed, 1) if orders_placed else 0
    
    return {
        "symbol": symbol,
        "days": days,
        "candles": len(rows),
        "ema_period": ema_period,
        "tp_pct": tp_pct,
        "sl_pct": sl_pct,
        "body_ratio_min": body_ratio_min,
        "fill_on_same_candle_tp": fill_on_same_candle_tp,
        "orders": {
            "placed": orders_placed,
            "filled": orders_filled,
            "cancelled": orders_cancelled,
            "fill_rate_pct": fill_rate,
        },
        "summary": {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": wr,
            "total_pnl_usd": round(total_pnl, 2),
            "max_drawdown_usd": round(max_dd, 2),
            "max_loss_streak": max_streak,
            "same_candle_both_hit": same_candle_both_hit,
        },
        "per_side": {
            "LONG": {
                "count": len(bull_trades),
                "wr_pct": round(100 * len(bull_wins) / len(bull_trades), 2) if bull_trades else 0,
                "pnl_usd": round(sum(t["pnl_usd"] for t in bull_trades), 2),
            },
            "SHORT": {
                "count": len(bear_trades),
                "wr_pct": round(100 * len(bear_wins) / len(bear_trades), 2) if bear_trades else 0,
                "pnl_usd": round(sum(t["pnl_usd"] for t in bear_trades), 2),
            },
        },
        "trades": trades[-20:],  # last 20 trades for inspection
    }
