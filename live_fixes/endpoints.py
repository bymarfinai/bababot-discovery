"""
FastAPI Router for live trading fixes + BBC live mode + Sweep All + BBC Configs.
Mount in app.py: app.include_router(live_fixes_router)
"""

import threading
import time
import json
import os
import traceback
import requests
from datetime import datetime, timezone
from fastapi import APIRouter, Request

router = APIRouter()

WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")

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
# BBC LIVE CONFIGS
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

_load_bbc_configs()


def _get_bbc_symbols():
    """Get BBC pairs: D1 custom-configs (primary) > local JSON (fallback) > BTCUSDT."""
    try:
        r = requests.get(f"{WORKER_URL}/custom-configs/list?live_only=true", timeout=10)
        configs = r.json().get("configs", [])
        symbols = [c["symbol"] for c in configs if c.get("mode") == "bbc"]
        if symbols:
            return symbols
    except:
        pass
    if _bbc_configs:
        return [c["symbol"] for c in _bbc_configs]
    return ["BTCUSDT"]


@router.get("/bbc-live/configs")
def api_bbc_configs():
    return {"ok": True, "configs": _bbc_configs, "count": len(_bbc_configs)}

@router.post("/bbc-live/configs/add")
async def api_bbc_config_add(request: Request):
    data = await request.json()
    symbol = data.get("symbol", "").upper()
    if not symbol:
        return {"ok": False, "error": "symbol required"}
    config = {
        "symbol": symbol, "ema_period": data.get("ema_period", 7),
        "tp_pct": data.get("tp_pct", 1.0), "sl_pct": data.get("sl_pct", 1.0),
        "win_rate": data.get("win_rate", 0), "total_pnl": data.get("total_pnl", 0),
        "total_trades": data.get("total_trades", 0), "source": "sweep",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != symbol]
    _bbc_configs.append(config)
    _save_bbc_configs()
    return {"ok": True, "config": config, "total": len(_bbc_configs)}

@router.delete("/bbc-live/configs/remove")
def api_bbc_config_remove(symbol: str):
    symbol = symbol.upper()
    before = len(_bbc_configs)
    _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != symbol]
    _save_bbc_configs()
    return {"ok": True, "removed": before - len(_bbc_configs), "total": len(_bbc_configs)}

@router.get("/bbc-live/configs/auto-pick")
def api_bbc_auto_pick(min_wr: float = 65, limit: int = 8):
    port = os.environ.get("PORT", "8000")
    base = f"http://127.0.0.1:{port}"
    try:
        r = requests.get(f"{base}/mode3_bbc/sweep/results?min_wr={min_wr}&sort_by=total_pnl&limit=500", timeout=30).json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    results = r.get("results", [])
    if not results:
        return {"ok": False, "error": f"No results with WR >= {min_wr}%"}
    picked = {}
    for res in results:
        sym = res["symbol"]
        if sym not in picked:
            picked[sym] = {
                "symbol": sym, "ema_period": res.get("ema_period", 7),
                "tp_pct": res["tp_pct"] * 100 if res["tp_pct"] < 1 else res["tp_pct"],
                "sl_pct": res["sl_pct"] * 100 if res["sl_pct"] < 1 else res["sl_pct"],
                "win_rate": res["win_rate"], "total_pnl": res["total_pnl"],
                "total_trades": res["total_trades"], "source": "auto-pick",
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
        if len(picked) >= limit:
            break
    for cfg in picked.values():
        _bbc_configs[:] = [c for c in _bbc_configs if c["symbol"] != cfg["symbol"]]
        _bbc_configs.append(cfg)
    _save_bbc_configs()
    return {"ok": True, "picked": list(picked.values()), "total_configs": len(_bbc_configs)}


# ══════════════════════════════════════════════
# BBC GLOBAL ENDPOINTS
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
    for aid, bot in _bbc_account_bots.items():
        bot["running"] = False
    return stop_bbc_live()

@router.get("/bbc-live/status")
def api_bbc_status():
    from bbc_live import bbc_live_status
    global_status = bbc_live_status()
    acct_statuses = {}
    for aid, bot in _bbc_account_bots.items():
        acct_statuses[aid] = {
            "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "account_name": bot["account"].get("name", ""),
            "pairs": bot["state"].get("active_pairs", []),
            "cycle_count": bot["state"].get("cycle_count", 0),
            "last_cycle": bot["state"].get("last_cycle"),
            "positions": bot["state"].get("positions", {}),
            "pairs_state": bot["state"].get("pairs", {}),
            "error": bot["state"].get("error"),
        }
    global_status["account_bots"] = acct_statuses
    return global_status

# ══════════════════════════════════════════════
# BBC PER-ACCOUNT SYSTEM
# ══════════════════════════════════════════════

_bbc_account_bots = {}

def _bbc_account_loop(account_id, client, account_info):
    from bbc_live import _bbc_live_loop
    from baret_live import _log
    bot = _bbc_account_bots.get(account_id)
    if not bot:
        return
    acct_name = account_info.get("name", f"Account-{account_id}")
    position_usd = account_info.get("position_usd", 10)
    leverage = account_info.get("leverage", 50)
    client.leverage = leverage
    symbols = _get_bbc_symbols()
    overrides = {}
    if _bbc_configs:
        cfg = _bbc_configs[0]
        if cfg.get("tp_pct"): overrides["tp_pct"] = cfg["tp_pct"] / 100 if cfg["tp_pct"] > 1 else cfg["tp_pct"]
        if cfg.get("sl_pct"): overrides["sl_pct"] = cfg["sl_pct"] / 100 if cfg["sl_pct"] > 1 else cfg["sl_pct"]
        if cfg.get("ema_period"): overrides["ema_period"] = cfg["ema_period"]
    try:
        _bbc_live_loop(
            symbols=symbols, timeframe="1h",
            position_usd=position_usd, leverage=leverage,
            config_overrides=overrides or None,
            client=client, state=bot["state"],
            running_check=lambda: bot["running"],
            acct_name=acct_name,
        )
    except Exception as e:
        _log(f"[BBC {acct_name}] CRASH: {e}")
        _log(f"[BBC {acct_name}] {traceback.format_exc()}")
    bot["running"] = False
    try:
        requests.post(f"{WORKER_URL}/trading-accounts/update-status",
                      json={"id": account_id, "status": "stopped"}, timeout=10)
    except:
        pass

@router.get("/bbc-live/start-account")
def api_bbc_start_account(account_id: int):
    from baret_live import ExchangeClient
    account_id = int(account_id)
    if account_id in _bbc_account_bots and _bbc_account_bots[account_id].get("running"):
        return {"ok": True, "message": f"BBC account {account_id} already running"}
    try:
        r = requests.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
        accounts = r.json().get("accounts", [])
        account = next((a for a in accounts if a["id"] == account_id), None)
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch account: {e}"}
    if not account:
        return {"ok": False, "error": f"Account {account_id} not found"}
    api_key = os.environ.get(account["env_key_name"], "")
    api_secret = os.environ.get(account["env_secret_name"], "")
    if not api_key or not api_secret:
        return {"ok": False, "error": f"API keys not found: {account['env_key_name']}"}
    client = ExchangeClient(account["base_url"], api_key, api_secret, account.get("leverage", 50))
    symbols = _get_bbc_symbols()
    bot_state = {
        "mode": "bbc", "active_pairs": symbols, "pairs": {},
        "positions": {}, "cycle_count": 0, "last_cycle": None,
        "started_at": None, "error": None,
    }
    _bbc_account_bots[account_id] = {
        "running": True, "state": bot_state,
        "client": client, "account": account, "thread": None,
    }
    t = threading.Thread(target=_bbc_account_loop, args=(account_id, client, account), daemon=True)
    _bbc_account_bots[account_id]["thread"] = t
    t.start()
    try:
        requests.post(f"{WORKER_URL}/trading-accounts/update-status",
                      json={"id": account_id, "status": "running"}, timeout=10)
    except:
        pass
    return {"ok": True, "message": f"BBC started for '{account['name']}', pairs: {', '.join(symbols)}, ${account['position_usd']}x{account['leverage']}x"}

@router.get("/bbc-live/stop-account")
def api_bbc_stop_account(account_id: int):
    account_id = int(account_id)
    bot = _bbc_account_bots.get(account_id)
    if not bot or not bot.get("running"):
        return {"ok": True, "message": f"BBC account {account_id} not running"}
    bot["running"] = False
    try:
        requests.post(f"{WORKER_URL}/trading-accounts/update-status",
                      json={"id": account_id, "status": "stopped"}, timeout=10)
    except:
        pass
    return {"ok": True, "message": f"BBC account {account_id} stopping..."}

# ══════════════════════════════════════════════
# BBC POSITION MANAGEMENT
# ══════════════════════════════════════════════

@router.get("/bbc-live/positions")
def api_bbc_positions(account_id: int = None):
    """Get open positions + open orders from BBC account bot's Binance client."""
    results = {}
    for aid, bot in _bbc_account_bots.items():
        if account_id and int(account_id) != int(aid):
            continue
        if not bot.get("client"):
            continue
        client = bot["client"]
        acct_name = bot["account"].get("name", f"Account-{aid}")
        try:
            positions = client.api_get("/fapi/v2/positionRisk")
            open_pos = []
            for p in positions:
                amt = float(p.get("positionAmt", 0))
                if amt != 0:
                    open_pos.append({
                        "symbol": p["symbol"],
                        "side": "LONG" if amt > 0 else "SHORT",
                        "qty": abs(amt),
                        "entry": float(p.get("entryPrice", 0)),
                        "pnl": float(p.get("unRealizedProfit", 0)),
                        "leverage": p.get("leverage"),
                        "mark_price": float(p.get("markPrice", 0)),
                    })
            orders = client.api_get("/fapi/v1/openOrders")
            results[aid] = {
                "account_name": acct_name,
                "positions": open_pos,
                "open_orders": [{"symbol": o["symbol"], "side": o["side"], "type": o["type"],
                                 "price": o.get("stopPrice") or o.get("price"),
                                 "orderId": o["orderId"]} for o in orders],
            }
        except Exception as e:
            results[aid] = {"account_name": acct_name, "error": str(e)}
    return {"ok": True, "accounts": results}

@router.get("/bbc-live/cancel-orders")
def api_bbc_cancel_orders(account_id: int, symbol: str = ""):
    """Cancel all open orders for a symbol on BBC account."""
    bot = _bbc_account_bots.get(int(account_id))
    if not bot or not bot.get("client"):
        return {"ok": False, "error": f"Account {account_id} not available"}
    client = bot["client"]
    try:
        if symbol:
            symbol = symbol.upper()
            client.cancel_all_orders(symbol)
            from baret_live import _cancel_sl_tp
            _cancel_sl_tp(client, symbol)
            return {"ok": True, "message": f"Cancelled all orders for {symbol}"}
        else:
            for sym in bot["state"].get("active_pairs", []):
                try:
                    client.cancel_all_orders(sym)
                    from baret_live import _cancel_sl_tp
                    _cancel_sl_tp(client, sym)
                except:
                    pass
            return {"ok": True, "message": "Cancelled all orders"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/bbc-live/place-sltp")
def api_bbc_place_sltp(account_id: int, symbol: str, sl: float, tp: float):
    """Place SL/TP for an existing position."""
    bot = _bbc_account_bots.get(int(account_id))
    if not bot or not bot.get("client"):
        return {"ok": False, "error": f"Account {account_id} not available"}
    client = bot["client"]
    symbol = symbol.upper()
    try:
        pos = client.get_position(symbol)
        if not pos or float(pos.get("positionAmt", 0)) == 0:
            return {"ok": False, "error": f"No open position for {symbol}"}
        amt = float(pos["positionAmt"])
        side = "LONG" if amt > 0 else "SHORT"
        from baret_live import _place_sl_tp
        result = _place_sl_tp(client, symbol, side, sl, tp)
        return {"ok": True, "symbol": symbol, "side": side, "sl": sl, "tp": tp, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ══════════════════════════════════════════════
# SWEEP ALL
# ══════════════════════════════════════════════

_sweep_all_state = {"running": False, "job_id": None, "completed": 0, "total": 0, "results_added": 0, "started_at": None, "errors": 0, "last_batch_at": None, "log": []}
_sweep_all_thread = None
_sweep_all_stop = False

def _sweep_log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    _sweep_all_state["log"].append(f"[{ts}] {msg}")
    if len(_sweep_all_state["log"]) > 50:
        _sweep_all_state["log"] = _sweep_all_state["log"][-50:]
    print(f"[SweepAll] {msg}")

def _sweep_all_worker(job_id, batch_size=20):
    global _sweep_all_stop
    port = os.environ.get("PORT", "8000")
    base = f"http://127.0.0.1:{port}"
    _sweep_all_state.update({"running": True, "job_id": job_id, "started_at": datetime.now(timezone.utc).isoformat(), "errors": 0, "results_added": 0, "log": []})
    try:
        r = requests.get(f"{base}/mode3_bbc/sweep/status/{job_id}", timeout=10).json()
        _sweep_all_state["total"] = r.get("total", 0)
        _sweep_all_state["completed"] = r.get("completed", 0)
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
            if r.get("status") == "completed" or _sweep_all_state["completed"] >= _sweep_all_state["total"]:
                _sweep_log(f"COMPLETED! {_sweep_all_state['completed']} combos")
                break
        except Exception as e:
            consecutive_errors += 1
            _sweep_all_state["errors"] += 1
            if consecutive_errors >= 5:
                break
            time.sleep(3)
    _sweep_all_state["running"] = False
    _sweep_all_stop = False

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