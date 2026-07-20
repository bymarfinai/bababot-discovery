"""
FastAPI Router for live trading fixes + BBC live mode + Sweep All + BBC Configs.
Mount in app.py: app.include_router(live_fixes_router)
"""

import threading
import time
import json
import os
import requests
from datetime import datetime, timezone
from fastapi import APIRouter, Request

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
    # Load saved configs and merge overrides
    overrides = {}
    if tp_pct > 0: overrides["tp_pct"] = tp_pct / 100
    if sl_pct > 0: overrides["sl_pct"] = sl_pct / 100
    if ema_period > 0: overrides["ema_period"] = ema_period
    # Per-pair configs from saved BBC configs
    per_pair = {}
    for cfg in _bbc_configs:
        s = cfg["symbol"]
        per_pair[s] = {
            "tp_pct": cfg["tp_pct"] / 100 if cfg["tp_pct"] > 1 else cfg["tp_pct"],
            "sl_pct": cfg["sl_pct"] / 100 if cfg["sl_pct"] > 1 else cfg["sl_pct"],
            "ema_period": cfg.get("ema_period", 7),
        }
    return start_bbc_live(symbol_list, timeframe, position_usd, leverage,
                          overrides or None)

@router.get("/bbc-live/stop")
def api_bbc_stop():
    from bbc_live import stop_bbc_live
    return stop_bbc_live()

@router.get("/bbc-live/status")
def api_bbc_status():
    from bbc_live import bbc_live_status
    return bbc_live_status()

# ══════════════════════════════════════════════
# BBC LIVE CONFIGS — save sweep winners for live trading
# Persisted to JSON file (survives restart)
# ══════════════════════════════════════════════

_BBC_CONFIG_FILE = "/app/data/bbc_live_configs.json"
_bbc_configs = []

def _load_bbc_configs():
    global _bbc_configs
    try:
        if os.path.exists(_BBC_CONFIG_FILE):
            with open(_BBC_CONFIG_FILE) as f:
                _bbc_configs = json.load(f)
    except:
        _bbc_configs = []

def _save_bbc_configs():
    try:
        os.makedirs(os.path.dirname(_BBC_CONFIG_FILE), exist_ok=True)
        with open(_BBC_CONFIG_FILE, "w") as f:
            json.dump(_bbc_configs, f, indent=2)
    except Exception as e:
        print(f"[BBCConfig] Save error: {e}")

# Load on import
_load_bbc_configs()


@router.get("/bbc-live/configs")
def api_bbc_configs():
    """Get all saved BBC live configs."""
    return {"ok": True, "configs": _bbc_configs, "count": len(_bbc_configs)}


@router.post("/bbc-live/configs/add")
async def api_bbc_config_add(request: Request):
    """Save a sweep result as BBC live config."""
    data = await request.json()
    symbol = data.get("symbol", "").upper()
    if not symbol:
        return {"ok": False, "error": "symbol required"}

    config = {
        "symbol": symbol,
        "ema_period": data.get("ema_period", 7),
        "tp_pct": data.get("tp_pct", 1.0),
        "sl_pct": data.get("sl_pct", 1.0),
        "win_rate": data.get("win_rate", 0),
        "total_pnl": data.get("total_pnl", 0),
        "total_trades": data.get("total_trades", 0),
        "source": "sweep",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    # Replace if same symbol exists
    _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != symbol]
    _bbc_configs.append(config)
    _save_bbc_configs()

    return {"ok": True, "config": config, "total": len(_bbc_configs)}


@router.delete("/bbc-live/configs/remove")
def api_bbc_config_remove(symbol: str):
    """Remove a BBC live config."""
    symbol = symbol.upper()
    before = len(_bbc_configs)
    _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != symbol]
    _save_bbc_configs()
    return {"ok": True, "removed": before - len(_bbc_configs), "total": len(_bbc_configs)}


@router.get("/bbc-live/configs/auto-pick")
def api_bbc_auto_pick(min_wr: float = 65, limit: int = 8):
    """Auto-pick best config per pair from sweep results (WR >= min_wr)."""
    import os
    port = os.environ.get("PORT", "8000")
    base = f"http://127.0.0.1:{port}"

    # Get all results sorted by PnL
    try:
        r = requests.get(f"{base}/mode3_bbc/sweep/results?min_wr={min_wr}&sort_by=total_pnl&limit=500", timeout=30).json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

    results = r.get("results", [])
    if not results:
        return {"ok": False, "error": f"No results with WR >= {min_wr}%"}

    # Pick best per symbol
    picked = {}
    for res in results:
        sym = res["symbol"]
        if sym not in picked:
            picked[sym] = {
                "symbol": sym,
                "ema_period": res.get("ema_period", 7),
                "tp_pct": res["tp_pct"] * 100 if res["tp_pct"] < 1 else res["tp_pct"],
                "sl_pct": res["sl_pct"] * 100 if res["sl_pct"] < 1 else res["sl_pct"],
                "win_rate": res["win_rate"],
                "total_pnl": res["total_pnl"],
                "total_trades": res["total_trades"],
                "source": "auto-pick",
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
        if len(picked) >= limit:
            break

    # Save all
    for cfg in picked.values():
        _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != cfg["symbol"]]
        _bbc_configs.append(cfg)
    _save_bbc_configs()

    return {"ok": True, "picked": list(picked.values()), "total_configs": len(_bbc_configs)}


# ══════════════════════════════════════════════
# SWEEP ALL — background worker on Railway
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
    port = os.environ.get("PORT", "8000")
    base = f"http://127.0.0.1:{port}"

    _sweep_all_state.update({
        "running": True, "job_id": job_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "errors": 0, "results_added": 0, "log": [],
    })

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
