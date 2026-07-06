"""
mode3_regime_api.py — API untuk Mode 3 Regime v0.6 engine
"""

from __future__ import annotations
import sqlite3
import time
import traceback
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mode3_regime import (
    Regime, RegimeConfig, RegimeState, classify_regime_series,
    Transition, TransitionConfig, classify_transitions,
    MicroEvent, Bias, MicroEventConfig, BiasConfig,
    detect_micro_events, compute_bias_series,
    EntrySide, EntryMode, EntryConfig, generate_entry_signals,
    BacktestConfig, run_backtest, TPScheme,
    SidewaysConfig, SidewaysBTConfig, run_sideways_backtest,
)


DB_PATH = Path("/app/data/market_data.db")
if not DB_PATH.exists():
    for _c in [Path(__file__).parent / "data" / "market_data.db",
               Path(__file__).parent / "market_data.db"]:
        if _c.exists():
            DB_PATH = _c
            break

router = APIRouter(prefix="/mode3/regime", tags=["mode3_regime"])


def _load_klines(symbol: str, timeframe: str, days: int):
    if not DB_PATH.exists():
        raise HTTPException(500, f"DB not found at {DB_PATH}")

    cutoff_ms = int((time.time() - days * 86400) * 1000)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT open_time, open, high, low, close, volume "
            "FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? "
            "ORDER BY open_time ASC",
            (symbol, timeframe, cutoff_ms),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(404, f"No data for {symbol} {timeframe} in {days} days")

    arr = np.array(rows, dtype=float)
    return arr[:, 0].astype(np.int64), arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4], arr[:, 5]


class AnalyzeReq(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(30, ge=1, le=365)


class BacktestReq(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(1825, ge=30, le=3650)
    position_usd: Optional[float] = None
    leverage: Optional[float] = None
    sl_atr_mult: Optional[float] = None
    max_hold_candles: Optional[int] = None

    # TP scheme
    tp_scheme: Optional[str] = None  # "levels" or "percentage"
    tp1_pct: Optional[float] = None
    tp2_pct: Optional[float] = None
    tp3_pct: Optional[float] = None
    tp1_ratio: Optional[float] = None
    tp2_ratio: Optional[float] = None
    tp3_ratio: Optional[float] = None


class SidewaysBTReq(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(1825, ge=30, le=3650)

    # Strategy params
    range_max_width_pct: Optional[float] = None
    touch_tolerance: Optional[float] = None
    volume_multiplier: Optional[float] = None
    cooldown_bars: Optional[int] = None

    # Backtest params
    sl_pct_from_level: Optional[float] = None
    tp1_ratio: Optional[float] = None
    tp2_ratio: Optional[float] = None
    tp3_ratio: Optional[float] = None
    max_hold_candles: Optional[int] = None


@router.post("/sideways_backtest")
async def sideways_backtest(req: SidewaysBTReq):
    """Backtest Sideways Tektok strategy standalone."""
    try:
        _, _, highs, lows, closes, volumes = _load_klines(req.symbol, req.timeframe, req.days)
    except HTTPException as e:
        return {"ok": False, "error": e.detail}

    n = len(closes)
    if n < 200:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    strat_cfg = SidewaysConfig()
    for f in ["range_max_width_pct", "touch_tolerance", "volume_multiplier", "cooldown_bars"]:
        v = getattr(req, f, None)
        if v is not None:
            setattr(strat_cfg, f, v)

    bt_cfg = SidewaysBTConfig()
    for f in ["sl_pct_from_level", "tp1_ratio", "tp2_ratio", "tp3_ratio", "max_hold_candles"]:
        v = getattr(req, f, None)
        if v is not None:
            setattr(bt_cfg, f, v)

    try:
        result = run_sideways_backtest(highs, lows, closes, volumes, bt_cfg, strategy_cfg=strat_cfg, warmup=min(100, n // 3))
    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

    if result.error:
        return {"ok": False, "error": result.error}

    s = result.stats
    return {
        "ok": True,
        "strategy": "sideways_tektok_v0.1",
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "days": req.days,
        "runtime_sec": round(s.runtime_sec, 2),
        "total_candles": s.total_candles,
        "stats": {
            "total_trades": s.total_trades,
            "wins": s.wins,
            "losses": s.losses,
            "win_rate": round(s.win_rate, 4),
            "trades_per_day": round(s.trades_per_day, 3),
            "total_pnl_net": round(s.total_pnl_net, 2),
            "avg_win": round(s.avg_win, 2),
            "avg_loss": round(s.avg_loss, 2),
            "max_drawdown_pct": round(s.max_drawdown_pct, 4),
            "tp1_hit_rate": round(s.tp1_hit_rate, 4),
            "tp2_hit_rate": round(s.tp2_hit_rate, 4),
            "tp3_hit_rate": round(s.tp3_hit_rate, 4),
            "exit_by_reason": s.exit_by_reason,
            "by_regime": s.by_regime,
            "by_mode": s.by_mode,
        },
        "sample_trades": [
            {
                "entry_idx": t.entry_idx, "exit_idx": t.exit_idx,
                "side": t.side, "mode": t.mode, "reason": t.reason, "regime": t.regime,
                "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
                "sl": round(t.sl_price, 2), "tp1": round(t.tp1_price, 2), "tp3": round(t.tp3_price, 2),
                "tp1_hit": t.tp1_hit, "tp2_hit": t.tp2_hit, "tp3_hit": t.tp3_hit,
                "pnl_net": round(t.pnl_net, 2),
                "exit_reason": t.exit_reason,
            }
            for t in result.trades[:20]
        ],
    }
async def health():
    return {
        "ok": True,
        "module": "mode3_regime",
        "version": "0.6.0",
        "architecture": "3-layer: Regime + Transition + MicroEvent + Bias",
        "features": [
            "4_regime_detector",
            "continuation_vs_reversal",
            "6_micro_event",
            "bias_filter_responsive_exit",
            "adaptive_entry_per_regime",
            "bull_pullback_ema20",
            "bear_failed_rally_ema20",
            "range_bounce_reject",
        ],
        "db_exists": DB_PATH.exists(),
    }


@router.post("/analyze")
async def analyze(req: AnalyzeReq):
    try:
        _, _, highs, lows, closes, volumes = _load_klines(req.symbol, req.timeframe, req.days)
    except HTTPException as e:
        return {"ok": False, "error": e.detail}

    n = len(closes)
    if n < 100:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    warmup = min(80, n // 3)
    rs_list = classify_regime_series(highs, lows, closes, volumes, RegimeConfig(), warmup=warmup)
    events = detect_micro_events(highs, lows, closes, volumes, rs_list, MicroEventConfig())
    biases = compute_bias_series(highs, lows, closes, volumes, rs_list, BiasConfig())
    signals = generate_entry_signals(highs, lows, closes, rs_list, events, biases, EntryConfig())

    latest = rs_list[-1]
    latest_bias = biases[-1]

    regime_counts, bias_counts, event_counts = {}, {}, {}
    for s in rs_list:
        regime_counts[s.regime.value] = regime_counts.get(s.regime.value, 0) + 1
    for b in biases:
        bias_counts[b.value] = bias_counts.get(b.value, 0) + 1
    for e in events:
        if e != MicroEvent.NONE:
            event_counts[e.value] = event_counts.get(e.value, 0) + 1

    return {
        "ok": True,
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "total_candles": n,
        "current_price": round(float(closes[-1]), 2),
        "current_regime": latest.regime.value,
        "regime_confidence": round(latest.confidence, 3),
        "current_bias": latest_bias.value,
        "ema_fast": round(latest.ema_fast, 2),
        "ema_slow": round(latest.ema_slow, 2),
        "ema_diff_pct": round(latest.ema_diff_pct * 100, 3),
        "value_area": {
            "vah": round(latest.vah, 2),
            "val": round(latest.val, 2),
            "poc": round(latest.poc, 2),
            "range_position": round(latest.range_position, 3),
            "is_range": latest.is_range,
        },
        "regime_distribution": regime_counts,
        "bias_distribution": bias_counts,
        "event_counts": event_counts,
        "total_signals": len(signals),
        "recent_signals": [
            {
                "idx": s.idx,
                "candle_from_end": n - 1 - s.idx,
                "side": s.side.value,
                "mode": s.mode.value,
                "reason": s.reason,
                "regime": s.regime,
                "bias": s.bias,
                "price": round(s.price, 2),
            }
            for s in signals[-10:]
        ],
    }


@router.post("/backtest")
async def backtest(req: BacktestReq):
    try:
        _, _, highs, lows, closes, volumes = _load_klines(req.symbol, req.timeframe, req.days)
    except HTTPException as e:
        return {"ok": False, "error": e.detail}

    n = len(closes)
    if n < 200:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    cfg = BacktestConfig()
    for field_name in ["position_usd", "leverage", "sl_atr_mult", "max_hold_candles",
                        "tp1_pct", "tp2_pct", "tp3_pct",
                        "tp1_ratio", "tp2_ratio", "tp3_ratio"]:
        val = getattr(req, field_name, None)
        if val is not None:
            setattr(cfg, field_name, val)

    # TP scheme
    if req.tp_scheme is not None:
        if req.tp_scheme.lower() == "percentage":
            cfg.tp_scheme = TPScheme.PERCENTAGE
        else:
            cfg.tp_scheme = TPScheme.LEVELS

    try:
        result = run_backtest(highs, lows, closes, volumes, cfg, warmup=min(100, n // 3))
    except Exception as e:
        traceback.print_exc()
        return {"ok": False, "error": str(e)}

    if result.error:
        return {"ok": False, "error": result.error}

    s = result.stats
    return {
        "ok": True,
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "days": req.days,
        "runtime_sec": round(s.runtime_sec, 2),
        "total_candles": s.total_candles,
        "stats": {
            "total_trades": s.total_trades,
            "wins": s.wins,
            "losses": s.losses,
            "win_rate": round(s.win_rate, 4),
            "trades_per_day": round(s.trades_per_day, 3),
            "total_pnl_net": round(s.total_pnl_net, 2),
            "avg_win": round(s.avg_win, 2),
            "avg_loss": round(s.avg_loss, 2),
            "max_drawdown_pct": round(s.max_drawdown_pct, 4),
            "exit_by_reason": s.exit_by_reason,
            "by_regime": s.by_regime,
            "by_mode": s.by_mode,
            "tp1_hit_rate": round(s.tp1_hit_rate, 4),
            "tp2_hit_rate": round(s.tp2_hit_rate, 4),
            "tp3_hit_rate": round(s.tp3_hit_rate, 4),
        },
        "sample_trades": [
            {
                "entry_idx": t.entry_idx,
                "exit_idx": t.exit_idx,
                "side": t.side,
                "mode": t.mode,
                "reason": t.reason,
                "regime": t.regime,
                "bias": t.bias,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "pnl_net": round(t.pnl_net, 2),
                "exit_reason": t.exit_reason,
            }
            for t in result.trades[:20]
        ],
    }
