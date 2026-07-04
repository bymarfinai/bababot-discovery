"""
mode3_api.py v1.2 — Direct import + dynamic feature detection

Fix vs v1.1:
- Import langsung dari mode3_drc (no v1_1 suffix confusion)
- Dynamic detection: cek apakah v1.1 features (KDTree, context caching) tersedia
- Version label yang akurat: '1.1-kdtree' / '1.1-brute' / '1.0-brute'
"""

from __future__ import annotations
import os, time, uuid, json, threading, traceback
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import core engine (v1.0 or v1.1 — same filename)
from mode3_drc import (
    DRCConfig, backtest, load_klines, compute_btc_returns,
)

# Detect v1.1 features dynamically
try:
    from mode3_drc import build_pair_context, backtest_with_context
    _V11_FEATURES = True
except ImportError:
    build_pair_context = None
    backtest_with_context = None
    _V11_FEATURES = False

# Detect KDTree availability
try:
    from mode3_drc import _KDTREE_AVAILABLE
except ImportError:
    _KDTREE_AVAILABLE = False

# Compose version label
if _V11_FEATURES and _KDTREE_AVAILABLE:
    _ENGINE_VERSION = "1.1-kdtree"
elif _V11_FEATURES:
    _ENGINE_VERSION = "1.1-brute"
else:
    _ENGINE_VERSION = "1.0-brute"


DB_PATH = os.environ.get("DB_PATH", "market_data.db")

_JOBS: dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_MAX_JOBS_KEPT = 100

router = APIRouter(prefix="/mode3", tags=["mode3"])


PRESETS = {
    "strict": dict(
        knn_min_confidence=0.70, ensemble_min_confidence=0.60,
        ensemble_min_agree=4, joint_confidence_min=0.75, joint_gap_min=0.50,
    ),
    "medium": dict(
        knn_min_confidence=0.60, ensemble_min_confidence=0.55,
        ensemble_min_agree=3, joint_confidence_min=0.65, joint_gap_min=0.30,
    ),
    "loose": dict(
        knn_min_confidence=0.55, ensemble_min_confidence=0.52,
        ensemble_min_agree=2, joint_confidence_min=0.60, joint_gap_min=0.20,
    ),
}


class Mode3BacktestRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    days: int = 1825
    tp_pct: float = 0.004
    preset: str = "strict"
    sl_atr_mult: float = 1.2
    include_trades: bool = False


class Mode3BacktestBatchRequest(BaseModel):
    pairs: list[str]
    timeframe: str = "15m"
    days: int = 1825
    tp_options: list[float] = [0.003, 0.004, 0.005]
    preset: str = "strict"
    sl_atr_mult: float = 1.2
    include_trades: bool = False


def _new_job(kind, params):
    job_id = str(uuid.uuid4())[:8]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id, "kind": kind, "params": params,
            "status": "pending", "progress": 0.0, "current_task": "",
            "started_at": None, "finished_at": None,
            "results": [], "error": None, "created_at": time.time(),
        }
        if len(_JOBS) > _MAX_JOBS_KEPT:
            oldest = sorted(_JOBS.keys(), key=lambda k: _JOBS[k]["created_at"])
            for k in oldest[:len(_JOBS) - _MAX_JOBS_KEPT]:
                del _JOBS[k]
    return job_id


def _update_job(job_id, **kwargs):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(kwargs)


def _get_job(job_id):
    with _JOBS_LOCK:
        return _JOBS.get(job_id, {}).copy() if job_id in _JOBS else None


@router.get("/health")
def health():
    import sqlite3
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        pairs = cur.execute(
            "SELECT symbol, COUNT(*) as n FROM klines WHERE timeframe='15m' GROUP BY symbol ORDER BY n DESC"
        ).fetchall()
        conn.close()
    except Exception as e:
        return {"ok": False, "error": str(e), "db_path": DB_PATH}
    return {
        "ok": True,
        "mode": "Mode 3 DRC",
        "engine_version": _ENGINE_VERSION,
        "v11_features_loaded": _V11_FEATURES,
        "kdtree_available": _KDTREE_AVAILABLE,
        "presets_available": list(PRESETS.keys()),
        "tp_options_default": [0.003, 0.004, 0.005],
        "db_path": DB_PATH,
        "pairs_15m": [{"symbol": p[0], "candles": p[1]} for p in pairs],
        "active_jobs": len([j for j in _JOBS.values() if j["status"] == "running"]),
        "total_jobs_kept": len(_JOBS),
    }


@router.post("/backtest")
def backtest_sync(req: Mode3BacktestRequest):
    if req.preset not in PRESETS:
        raise HTTPException(400, f"Invalid preset. Use: {list(PRESETS.keys())}")
    try:
        data = load_klines(DB_PATH, req.symbol, req.timeframe, days=req.days)
    except Exception as e:
        raise HTTPException(404, f"No data: {e}")

    btc_r = None
    if req.symbol != "BTCUSDT":
        btc_r = compute_btc_returns(DB_PATH, req.timeframe)

    cfg = DRCConfig(
        symbol=req.symbol, timeframe=req.timeframe, days=req.days,
        sl_atr_mult=req.sl_atr_mult, **PRESETS[req.preset],
    )
    t0 = time.time()
    r = backtest(data, cfg, tp_pct=req.tp_pct, btc_returns=btc_r)
    r["runtime_sec"] = round(time.time() - t0, 1)
    r["preset"] = req.preset
    r["engine_version"] = _ENGINE_VERSION
    if not req.include_trades:
        r.pop("trades_list", None)
    return r


def _run_batch_job(job_id, req: Mode3BacktestBatchRequest):
    try:
        _update_job(job_id, status="running", started_at=time.time())
        btc_r = compute_btc_returns(DB_PATH, req.timeframe)
        total = len(req.pairs) * len(req.tp_options)
        done = 0
        results = []

        for symbol in req.pairs:
            try:
                data = load_klines(DB_PATH, symbol, req.timeframe, days=req.days)
            except Exception as e:
                results.append({
                    "symbol": symbol, "error": f"load_failed: {e}",
                    "timeframe": req.timeframe, "preset": req.preset,
                })
                done += len(req.tp_options)
                _update_job(job_id, progress=round(done/total*100, 1))
                continue

            cfg = DRCConfig(
                symbol=symbol, timeframe=req.timeframe, days=req.days,
                sl_atr_mult=req.sl_atr_mult, **PRESETS[req.preset],
            )

            # ── OPTIMIZATION v1.1: Build heavy context ONCE per pair ──
            ctx = None
            if _V11_FEATURES:
                _update_job(job_id, current_task=f"{symbol} building context (features + KDTree)")
                try:
                    ctx = build_pair_context(
                        data, cfg,
                        btc_returns=btc_r if symbol != "BTCUSDT" else None,
                    )
                except Exception as e:
                    results.append({"symbol": symbol, "error": f"context_failed: {e}"})
                    done += len(req.tp_options)
                    _update_job(job_id, progress=round(done/total*100, 1))
                    continue

            # Sweep TP options (reuse context)
            for tp in req.tp_options:
                _update_job(
                    job_id,
                    current_task=f"{symbol} TF={req.timeframe} TP={tp*100:.2f}%",
                )
                t0 = time.time()
                if ctx is not None and backtest_with_context is not None:
                    r = backtest_with_context(ctx, cfg, tp_pct=tp)
                else:
                    r = backtest(
                        data, cfg, tp_pct=tp,
                        btc_returns=btc_r if symbol != "BTCUSDT" else None,
                    )
                r["runtime_sec"] = round(time.time() - t0, 1)
                r["preset"] = req.preset
                r["engine_version"] = _ENGINE_VERSION
                if not req.include_trades:
                    r.pop("trades_list", None)
                results.append(r)
                done += 1
                _update_job(
                    job_id,
                    progress=round(done/total*100, 1),
                    results=results,
                )

        candidates = [
            {
                "symbol": r.get("symbol"), "timeframe": r.get("timeframe"),
                "tp_pct": r.get("tp_pct"), "wr": r.get("wr"),
                "trades": r.get("trades"),
                "profit_per_day": r.get("profit_per_day"),
                "preset": req.preset,
            }
            for r in results
            if r.get("wr", 0) >= 75 and r.get("trades", 0) >= 30
            and r.get("profit_per_day", 0) > 0
        ]

        _update_job(
            job_id, status="done", progress=100.0,
            finished_at=time.time(), results=results,
            summary={
                "engine_version": _ENGINE_VERSION,
                "total_backtests": len(results),
                "candidates_count": len(candidates),
                "candidates": candidates,
            },
        )
    except Exception as e:
        _update_job(
            job_id, status="error",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            finished_at=time.time(),
        )


@router.post("/backtest-async")
def backtest_async(req: Mode3BacktestBatchRequest):
    if req.preset not in PRESETS:
        raise HTTPException(400, f"Invalid preset. Use: {list(PRESETS.keys())}")
    if not req.pairs:
        raise HTTPException(400, "pairs list cannot be empty")
    job_id = _new_job("batch", req.dict())
    threading.Thread(
        target=_run_batch_job, args=(job_id, req),
        daemon=True, name=f"mode3-job-{job_id}",
    ).start()
    return {
        "ok": True, "job_id": job_id,
        "engine": _ENGINE_VERSION,
        "estimated_backtests": len(req.pairs) * len(req.tp_options),
        "estimated_runtime_min": round(
            len(req.pairs) * (2 if _KDTREE_AVAILABLE else 15) +
            len(req.pairs) * (len(req.tp_options)-1) * (0.3 if _V11_FEATURES else 15), 1
        ),
        "poll_url": f"/mode3/job/{job_id}",
    }


@router.get("/job/{job_id}")
def get_job(job_id: str, include_results: bool = False, include_trades: bool = False):
    job = _get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    out = {
        "job_id": job["job_id"], "kind": job["kind"],
        "status": job["status"], "progress": job["progress"],
        "current_task": job["current_task"],
        "started_at": job["started_at"], "finished_at": job["finished_at"],
        "error": job.get("error"),
        "runtime_sec": (
            (job["finished_at"] - job["started_at"])
            if job["started_at"] and job["finished_at"] else None
        ),
    }
    if job.get("summary"): out["summary"] = job["summary"]
    if include_results:
        results = job.get("results", [])
        if not include_trades:
            results = [
                {k: v for k, v in r.items() if k != "trades_list"}
                for r in results
            ]
        out["results"] = results
    return out


@router.get("/jobs")
def list_jobs(status: Optional[str] = None, limit: int = 20):
    with _JOBS_LOCK:
        jobs = list(_JOBS.values())
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    return {
        "engine_version": _ENGINE_VERSION,
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j["job_id"], "kind": j["kind"],
                "status": j["status"], "progress": j["progress"],
                "current_task": j["current_task"],
                "created_at": j["created_at"],
                "started_at": j["started_at"], "finished_at": j["finished_at"],
                "n_pairs": len(j["params"].get("pairs", [])) if j["kind"] == "batch" else 1,
            }
            for j in jobs[:limit]
        ],
    }


@router.delete("/job/{job_id}")
def delete_job(job_id: str):
    with _JOBS_LOCK:
        if job_id in _JOBS:
            _JOBS[job_id]["status"] = "cancelled"
            del _JOBS[job_id]
            return {"ok": True, "job_id": job_id, "deleted": True}
    raise HTTPException(404, "Not found")
