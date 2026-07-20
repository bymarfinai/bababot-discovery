"""
FastAPI Router for live trading fixes + BBC live mode + Sweep All.
Mount in app.py: app.include_router(live_fixes_router)
"""

import threading
import time
import requests
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()

# ══════════════════════════════════════════════
# EXCHANGE POSITION ENDPOINTS
# ══════════════════════════════════════════════

@router.get("/baret-live/exchange-positions")
def api_exchange_positions(account_id: int = None):
    from live_fixes.integrate import get_exchange_positions
    return get_exchange_positions(account_id)

@router.post("/baret-live/close-position")
def api_close_position(symbol: str, account_id: int = None):
    import baret_live
    symbol = symbol.upper()
    if account_id:
        account_id = int(account_id)
        bot = baret_live._account_bots.get(account_id)
        if bot and bot.get("client"):
            result = baret_live.close_position(symbol, client=bot["client"])
            if bot.get("state"):
                bot["state"].get("positions", {}).pop(symbol, None)
                bot["state"].get("pending_orders", {}).pop(symbol, None)
            return result
        return {"ok": False, "error": f"Account {account_id} client not available"}
    return baret_live.close_position(symbol)

@router.post("/baret-live/close-all")
def api_close_all(account_id: int = None):
    import baret_live
    if account_id:
        account_id = int(account_id)
        bot = baret_live._account_bots.get(account_id)
        if bot and bot.get("client"):
            result = baret_live.close_all_positions(client=bot["client"])
            if bot.get("state"):
                bot["state"]["positions"] = {}
                bot["state"]["pending_orders"] = {}
            return result
        return {"ok": False, "error": f"Account {account_id} client not available"}
    return baret_live.close_all_positions()

# ══════════════════════════════════════════════
# BBC LIVE ENDPOINTS
# ══════════════════════════════════════════════

@router.get("/bbc-live/start")
def api_bbc_start(symbols: str = "BTCUSDT", timeframe: str = "1h",
                  position_usd: float = 10.0, leverage: int = 50,
                  tp_pct: float = 0, sl_pct: float = 0, ema_period: int = 0):
    from bbc_live import start_bbc_live
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    overrides = {}
    if tp_pct > 0: overrides["tp_pct"] = tp_pct / 100
    if sl_pct > 0: overrides["sl_pct"] = sl_pct / 100
    if ema_period > 0: overrides["ema_period"] = ema_period
    return start_bbc_live(symbol_list, timeframe, position_usd, leverage, overrides or None)

@router.get("/bbc-live/stop")
def api_bbc_stop():
    from bbc_live import stop_bbc_live
    return stop_bbc_live()

@router.get("/bbc-live/status")
def api_bbc_status():
    from bbc_live import bbc_live_status
    return bbc_live_status()

# ══════════════════════════════════════════════
# SWEEP ALL — background worker on Railway
# Calls local HTTP endpoints (avoids import issues)
# ══════════════════════════════════════════════

_sweep_all_state = {
    "running": False,
    "job_id": None,
    "completed": 0,
    "total": 0,
    "results_added": 0,
    "started_at": None,
    "errors": 0,
    "last_batch_at": None,
    "log": [],
}
_sweep_all_thread = None
_sweep_all_stop = False

def _sweep_log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _sweep_all_state["log"].append(entry)
    if len(_sweep_all_state["log"]) > 50:
        _sweep_all_state["log"] = _sweep_all_state["log"][-50:]
    print(f"[SweepAll] {msg}")

def _sweep_all_worker(job_id, batch_size=20):
    global _sweep_all_stop
    import os
    port = os.environ.get("PORT", "8000")
    base = f"http://127.0.0.1:{port}"

    _sweep_all_state.update({
        "running": True, "job_id": job_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "errors": 0, "results_added": 0, "log": [],
    })

    # Get initial status
    try:
        r = requests.get(f"{base}/mode3_bbc/sweep/status/{job_id}", timeout=10).json()
        _sweep_all_state["total"] = r.get("total", 0)
        _sweep_all_state["completed"] = r.get("completed", 0)
        _sweep_log(f"Started: {_sweep_all_state['completed']}/{_sweep_all_state['total']} combos")
    except Exception as e:
        _sweep_log(f"Initial status failed: {e}")

    consecutive_errors = 0

    while not _sweep_all_stop:
        try:
            r = requests.get(f"{base}/mode3_bbc/sweep/run/{job_id}?batch_size={batch_size}", timeout=120).json()
            _sweep_all_state["completed"] = r.get("completed", 0)
            _sweep_all_state["total"] = r.get("total", 0)
            _sweep_all_state["results_added"] += r.get("results_added", 0)
            _sweep_all_state["last_batch_at"] = datetime.now(timezone.utc).isoformat()
            consecutive_errors = 0

            pct = round(_sweep_all_state["completed"] / max(_sweep_all_state["total"], 1) * 100, 1)
            if _sweep_all_state["completed"] % 100 < batch_size:
                _sweep_log(f"{_sweep_all_state['completed']}/{_sweep_all_state['total']} ({pct}%) | +{r.get('results_added', 0)} results this batch")

            if r.get("status") == "completed" or _sweep_all_state["completed"] >= _sweep_all_state["total"]:
                _sweep_log(f"✅ COMPLETED! {_sweep_all_state['completed']} combos, {_sweep_all_state['results_added']} total results")
                break

        except Exception as e:
            consecutive_errors += 1
            _sweep_all_state["errors"] += 1
            _sweep_log(f"❌ Batch error ({consecutive_errors}/5): {e}")
            if consecutive_errors >= 5:
                _sweep_log("STOPPED: too many consecutive errors")
                break
            time.sleep(3)

    _sweep_all_state["running"] = False
    _sweep_all_stop = False
    _sweep_log("Worker finished")

@router.get("/sweep-all/start")
def api_sweep_all_start(job_id: str, batch_size: int = 20):
    global _sweep_all_thread, _sweep_all_stop
    if _sweep_all_state["running"]:
        return {"ok": True, "message": "Already running", **_sweep_all_state}
    _sweep_all_stop = False
    _sweep_all_thread = threading.Thread(target=_sweep_all_worker, args=(job_id, batch_size), daemon=True)
    _sweep_all_thread.start()
    return {"ok": True, "message": f"Sweep-all started for job {job_id}"}

@router.get("/sweep-all/stop")
def api_sweep_all_stop():
    global _sweep_all_stop
    _sweep_all_stop = True
    return {"ok": True, "message": "Stop signal sent"}

@router.get("/sweep-all/status")
def api_sweep_all_status():
    return {"ok": True, **_sweep_all_state, "thread_alive": _sweep_all_thread.is_alive() if _sweep_all_thread else False}
