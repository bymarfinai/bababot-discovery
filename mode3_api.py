"""
mode3_regime_api.py — FastAPI endpoints untuk Mode 3 Regime engine
==================================================================

Wraps mode3_regime module ke HTTP endpoints:
- GET  /mode3/regime/health         — check module loaded
- POST /mode3/regime/analyze        — analyze regime state at latest candle
- POST /mode3/regime/backtest       — sync backtest 1 pair (returns full stats)
- POST /mode3/regime/backtest-async — async backtest (returns job_id)
- POST /mode3/regime/sweep          — async parameter sweep
- GET  /mode3/regime/job/{job_id}   — poll job status
- GET  /mode3/regime/jobs           — list all jobs

Author: BabaBot team
Version: 1.0.0
"""

from __future__ import annotations
import sqlite3
import time
import uuid
import threading
import traceback
import gc
from typing import Optional
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mode3_regime import (
    RegimeConfig, StateMachineConfig, ClassifierConfig,
    BacktestConfig, SweepGrid, SweepConfig,
    run_regime_backtest, run_sweep,
    classify_regime_series, run_state_machine,
    SMState, Regime,
)


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

DB_PATH = Path(__file__).parent / "market_data.db"

router = APIRouter(prefix="/mode3/regime", tags=["mode3_regime"])

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════

def _load_klines(symbol: str, timeframe: str, days: int) -> tuple[np.ndarray, ...]:
    """Load klines dari SQLite db. Returns (open_times, opens, highs, lows, closes, volumes)."""
    if not DB_PATH.exists():
        raise HTTPException(500, f"DB not found at {DB_PATH}")

    cutoff_ms = int((time.time() - days * 86400) * 1000)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT open_time, open, high, low, close, volume "
            "FROM klines WHERE symbol = ? AND timeframe = ? AND open_time >= ? "
            "ORDER BY open_time ASC",
            (symbol, timeframe, cutoff_ms),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(
            404,
            f"No data for {symbol} {timeframe} in last {days} days",
        )

    arr = np.array(rows, dtype=float)
    return (
        arr[:, 0].astype(np.int64),  # open_time
        arr[:, 1],  # open
        arr[:, 2],  # high
        arr[:, 3],  # low
        arr[:, 4],  # close
        arr[:, 5],  # volume
    )


def _apply_config_overrides(bt_cfg: BacktestConfig, req: dict) -> BacktestConfig:
    """Apply optional overrides dari request body ke BacktestConfig."""
    import copy
    cfg = copy.copy(bt_cfg)
    for field_name in [
        "position_usd", "leverage", "fee_pct", "slippage_pct",
        "max_hold_candles", "sl_atr_multiplier",
        "tp1_ratio", "tp2_ratio", "tp3_ratio",
        "trailing_atr_multiplier",
        "max_consecutive_losses", "max_drawdown_pct",
    ]:
        val = req.get(field_name)
        if val is not None:
            setattr(cfg, field_name, val)
    return cfg


# ═════════════════════════════════════════════════════════════
# REQUEST MODELS
# ═════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(30, ge=1, le=365)


class BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(1825, ge=30, le=3650)

    # Optional overrides
    position_usd: Optional[float] = None
    leverage: Optional[float] = None
    fee_pct: Optional[float] = None
    slippage_pct: Optional[float] = None
    max_hold_candles: Optional[int] = None
    sl_atr_multiplier: Optional[float] = None
    tp1_ratio: Optional[float] = None
    tp2_ratio: Optional[float] = None
    tp3_ratio: Optional[float] = None
    trailing_atr_multiplier: Optional[float] = None
    max_consecutive_losses: Optional[int] = None
    max_drawdown_pct: Optional[float] = None


class SweepRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "1h"
    days: int = Field(1825, ge=30, le=3650)

    # Sweep grid (empty = pakai default)
    range_max_width_pct: list[float] = Field(default_factory=list)
    va_percentage: list[float] = Field(default_factory=list)
    reclaim_buffer_pct: list[float] = Field(default_factory=list)
    reclaim_volume_multiplier: list[float] = Field(default_factory=list)
    sl_atr_multiplier: list[float] = Field(default_factory=list)
    tp1_ratio: list[float] = Field(default_factory=list)
    max_hold_candles: list[int] = Field(default_factory=list)
    trailing_atr_multiplier: list[float] = Field(default_factory=list)

    # Sweep config
    train_split: float = Field(0.7, ge=0.5, le=0.9)
    top_n: int = Field(10, ge=1, le=50)
    target_trades_per_day: float = Field(2.5, ge=0.1, le=20.0)
    min_trades_train: int = Field(20, ge=1)


# ═════════════════════════════════════════════════════════════
# ENDPOINTS
# ═════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Check kalau module loaded."""
    return {
        "ok": True,
        "module": "mode3_regime",
        "version": "0.5.0",
        "engine_features": [
            "anchored_vah_val",
            "5_line_value_area",
            "state_machine_3way_confirmation",
            "continuation_vs_reversal_classifier",
            "3_mode_entry",
            "3_tier_partial_tp",
            "circuit_breakers",
            "walk_forward_sweep",
        ],
        "db_exists": DB_PATH.exists(),
    }


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Analyze current regime state at latest candle."""
    try:
        open_times, opens, highs, lows, closes, volumes = _load_klines(
            req.symbol, req.timeframe, req.days,
        )
    except HTTPException as e:
        return {"ok": False, "error": e.detail}

    n = len(closes)
    if n < 100:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    regime_cfg = RegimeConfig()
    sm_cfg = StateMachineConfig()

    warmup = min(100, n // 3)
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)
    ms_list = run_state_machine(highs, lows, closes, volumes, regime_states, sm_cfg, warmup=warmup)

    # Latest state
    latest_regime = regime_states[-1]
    latest_ms = ms_list[-1]

    va = latest_regime.current_va
    va_dict = None
    if va is not None:
        va_dict = {
            "vah": round(va.vah, 2),
            "val": round(va.val, 2),
            "poc": round(va.poc, 2),
            "vwap": round(va.vwap, 2),
            "vwap_upper": round(va.vwap_upper, 2),
            "vwap_lower": round(va.vwap_lower, 2),
            "is_anchored": va.is_anchored,
        }

    # Regime distribution across full history
    regime_counts: dict[str, int] = {}
    for s in regime_states:
        regime_counts[s.regime.value] = regime_counts.get(s.regime.value, 0) + 1

    # Recent entry signals (last 100 candle)
    recent_signals = []
    for i in range(max(0, n - 100), n):
        ms = ms_list[i]
        if ms.sm_state in (SMState.ENTER_LONG, SMState.ENTER_SHORT):
            recent_signals.append({
                "idx": i,
                "candle_idx_from_end": n - 1 - i,
                "side": "long" if ms.sm_state == SMState.ENTER_LONG else "short",
                "reason": ms.reason,
                "context": ms.bot_context.value,
                "price": round(float(closes[i]), 2),
            })

    return {
        "ok": True,
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "total_candles": n,
        "current_price": round(float(closes[-1]), 2),
        "current_regime": latest_regime.regime.value,
        "regime_confidence": round(latest_regime.confidence, 3),
        "prior_regime": latest_regime.prior_regime.value,
        "current_state": latest_ms.sm_state.value,
        "bot_context": latest_ms.bot_context.value,
        "value_area": va_dict,
        "regime_distribution": regime_counts,
        "recent_signals_count": len(recent_signals),
        "recent_signals": recent_signals[-10:],  # Last 10 only
    }


@router.post("/backtest")
async def backtest_sync(req: BacktestRequest):
    """Full backtest sync — returns stats + trades summary."""
    try:
        open_times, opens, highs, lows, closes, volumes = _load_klines(
            req.symbol, req.timeframe, req.days,
        )
    except HTTPException as e:
        return {"ok": False, "error": e.detail}

    n = len(closes)
    if n < 200:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    bt_cfg = _apply_config_overrides(BacktestConfig(), req.dict(exclude_none=True))

    try:
        result = run_regime_backtest(
            highs, lows, closes, volumes,
            cfg=bt_cfg,
            warmup=min(100, n // 3),
        )
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
            "breakeven": s.breakeven,
            "win_rate": round(s.win_rate, 4),
            "trades_per_day": round(s.trades_per_day, 3),
            "total_pnl_net": round(s.total_pnl_net, 2),
            "total_pnl_gross": round(s.total_pnl_gross, 2),
            "total_fees": round(s.total_fees, 2),
            "avg_win_usd": round(s.avg_win_usd, 2),
            "avg_loss_usd": round(s.avg_loss_usd, 2),
            "max_drawdown_usd": round(s.max_drawdown_usd, 2),
            "max_drawdown_pct": round(s.max_drawdown_pct, 4),
            "range_trades": s.range_trades,
            "retest_trades": s.retest_trades,
            "trend_trades": s.trend_trades,
            "range_wr": round(s.range_wr, 4),
            "retest_wr": round(s.retest_wr, 4),
            "trend_wr": round(s.trend_wr, 4),
            "exit_by_reason": s.exit_by_reason,
        },
        "config_used": {
            "position_usd": bt_cfg.position_usd,
            "leverage": bt_cfg.leverage,
            "fee_pct": bt_cfg.fee_pct,
            "slippage_pct": bt_cfg.slippage_pct,
            "sl_atr_multiplier": bt_cfg.sl_atr_multiplier,
            "tp_ratios": [bt_cfg.tp1_ratio, bt_cfg.tp2_ratio, bt_cfg.tp3_ratio],
            "max_hold_candles": bt_cfg.max_hold_candles,
        },
    }


# ─── Async sweep job ─────────────────────────────────────────

def _run_sweep_job(job_id: str, req: SweepRequest):
    """Background thread untuk sweep job."""
    try:
        _update_job(job_id, {"status": "loading_data", "progress": 0})

        open_times, opens, highs, lows, closes, volumes = _load_klines(
            req.symbol, req.timeframe, req.days,
        )

        _update_job(job_id, {"status": "running", "progress": 5})

        # Build grid dari request
        grid = SweepGrid(
            range_max_width_pct=req.range_max_width_pct,
            va_percentage=req.va_percentage,
            reclaim_buffer_pct=req.reclaim_buffer_pct,
            reclaim_volume_multiplier=req.reclaim_volume_multiplier,
            sl_atr_multiplier=req.sl_atr_multiplier,
            tp1_ratio=req.tp1_ratio,
            max_hold_candles=req.max_hold_candles,
            trailing_atr_multiplier=req.trailing_atr_multiplier,
        )

        sweep_cfg = SweepConfig(
            train_split=req.train_split,
            top_n=req.top_n,
            target_trades_per_day=req.target_trades_per_day,
            min_trades_train=req.min_trades_train,
        )

        def progress_cb(current, total, result):
            pct = int(5 + 90 * current / total)
            _update_job(job_id, {"progress": pct, "current": current, "total": total})

        summary = run_sweep(
            highs, lows, closes, volumes,
            grid=grid, sweep_cfg=sweep_cfg,
            progress_callback=progress_cb,
        )

        # Serialize top configs
        top_serialized = []
        for r in summary.top_configs:
            top_serialized.append({
                "config_id": r.config_id,
                "params": r.params,
                "train": {
                    "trades": r.train_trades,
                    "wr": round(r.train_wr, 4),
                    "pnl": round(r.train_pnl, 2),
                    "trades_per_day": round(r.train_trades_per_day, 3),
                    "max_dd_pct": round(r.train_max_dd, 4),
                },
                "test": {
                    "trades": r.test_trades,
                    "wr": round(r.test_wr, 4),
                    "pnl": round(r.test_pnl, 2),
                    "trades_per_day": round(r.test_trades_per_day, 3),
                    "max_dd_pct": round(r.test_max_dd, 4),
                },
                "train_score": round(r.train_score, 4),
                "test_score": round(r.test_score, 4),
                "overfitting_ratio": round(r.overfitting_ratio, 3),
            })

        _update_job(job_id, {
            "status": "done",
            "progress": 100,
            "runtime_sec": round(summary.runtime_sec, 2),
            "total_configs": summary.total_configs,
            "completed_configs": summary.completed_configs,
            "skipped_configs": summary.skipped_configs,
            "top_configs": top_serialized,
        })

    except Exception as e:
        traceback.print_exc()
        _update_job(job_id, {"status": "error", "error": str(e)})
    finally:
        # Memory cleanup
        try:
            del highs
            del lows
            del closes
            del volumes
        except NameError:
            pass
        gc.collect()


def _update_job(job_id: str, updates: dict):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(updates)
            _JOBS[job_id]["updated_at"] = time.time()


@router.post("/sweep")
async def sweep_async(req: SweepRequest):
    """Start async parameter sweep. Returns job_id, poll via /job/{job_id}."""
    job_id = uuid.uuid4().hex[:8]

    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "kind": "sweep",
            "status": "queued",
            "progress": 0,
            "symbol": req.symbol,
            "timeframe": req.timeframe,
            "days": req.days,
            "started_at": time.time(),
            "updated_at": time.time(),
        }

    # Spawn thread
    thread = threading.Thread(
        target=_run_sweep_job,
        args=(job_id, req),
        daemon=True,
    )
    thread.start()

    return {
        "ok": True,
        "job_id": job_id,
        "poll_url": f"/mode3/regime/job/{job_id}",
        "message": "Sweep started, poll job status for results.",
    }


@router.get("/job/{job_id}")
async def job_status(job_id: str):
    with _JOBS_LOCK:
        if job_id not in _JOBS:
            return {"ok": False, "error": "job not found"}
        return {"ok": True, **_JOBS[job_id]}


@router.get("/jobs")
async def list_jobs():
    with _JOBS_LOCK:
        jobs = list(_JOBS.values())
    jobs.sort(key=lambda j: j.get("started_at", 0), reverse=True)
    return {"ok": True, "count": len(jobs), "jobs": jobs[:20]}


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            del _JOBS[job_id]
            gc.collect()
            return {"ok": True, "deleted": job_id}
    return {"ok": False, "error": "job not found"}
