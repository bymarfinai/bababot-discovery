"""
BBC Live Trading Endpoints — FastAPI router for BBC live control.

v2.0: Per-pair configs loaded FULLY from D1 (ema, body ratios, TP, SL).
      BBC_RECOMMENDED only used as fallback if D1 is empty.

Endpoints:
  GET /bbc-live/start       — Start BBC live (all pairs from D1)
  GET /bbc-live/stop        — Stop BBC live
  GET /bbc-live/status      — Get BBC live status + per-pair state
  GET /bbc-live/start-account — Start BBC for specific trading account
  GET /bbc-live/stop-account  — Stop BBC for specific trading account
  POST /bbc-live/close      — Close specific BBC position
  POST /bbc-live/close-all  — Close all BBC positions
"""

import os
import threading
import traceback
import requests as req
from fastapi import APIRouter

from bbc_live import start_bbc_live, stop_bbc_live, bbc_live_status, _bbc_live_loop
from baret_live import (
    ExchangeClient, _log, _send_telegram, _cancel_sl_tp,
    _get_default_client, _account_bots, close_position, close_all_positions,
    WORKER_URL,
)

router = APIRouter()

# ══════════════════════════════════════════════
# FALLBACK ONLY — used when D1 has no BBC configs at all
# ══════════════════════════════════════════════

BBC_FALLBACK = {
    "SOLUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.7},
    "ETHUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.5, "bear_body_ratio_min": 0.6},
    "BNBUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.020, "bull_body_ratio_min": 0.6, "bear_body_ratio_min": 0.7},
    "DOGEUSDT": {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.5},
    "BTCUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.013, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.7},
}


def _fetch_bbc_configs_from_d1():
    """Fetch BBC configs from D1 custom_configs — ALL fields including ema, body ratios.
    
    D1 now stores: symbol, tp_pct, sl_pct, ema_period, bull_body_ratio_min, bear_body_ratio_min
    TP/SL in D1 are percentages (e.g. 1.3), config needs decimals (e.g. 0.013).
    
    Returns: dict of {symbol: {ema_period, tp_pct, sl_pct, bull_body_ratio_min, bear_body_ratio_min}}
    """
    config_overrides = {}
    
    try:
        r = req.get(f"{WORKER_URL}/custom-configs/list?live_only=true", timeout=15)
        all_configs = r.json().get("configs", [])
        bbc_configs = [c for c in all_configs if c.get("mode") == "bbc"]
    except Exception as e:
        _log(f"[BBC] ⚠️ Failed to fetch D1 configs: {e}, using fallback")
        return dict(BBC_FALLBACK)
    
    if not bbc_configs:
        _log("[BBC] ⚠️ No BBC configs in D1, using fallback defaults")
        return dict(BBC_FALLBACK)
    
    for c in bbc_configs:
        symbol = c["symbol"]
        fallback = BBC_FALLBACK.get(symbol, {"ema_period": 7, "bull_body_ratio_min": 0.5, "bear_body_ratio_min": 0.6, "tp_pct": 0.013, "sl_pct": 0.015})
        
        # Read ALL fields from D1, fallback only for missing fields
        tp_raw = float(c["tp_pct"]) if c.get("tp_pct") is not None else None
        sl_raw = float(c["sl_pct"]) if c.get("sl_pct") is not None else None
        
        config_overrides[symbol] = {
            "ema_period": int(c["ema_period"]) if c.get("ema_period") else fallback["ema_period"],
            "tp_pct": round(tp_raw / 100, 6) if tp_raw and tp_raw > 0.1 else (tp_raw or fallback["tp_pct"]),
            "sl_pct": round(sl_raw / 100, 6) if sl_raw and sl_raw > 0.1 else (sl_raw or fallback["sl_pct"]),
            "bull_body_ratio_min": float(c["bull_body_ratio_min"]) if c.get("bull_body_ratio_min") is not None else fallback["bull_body_ratio_min"],
            "bear_body_ratio_min": float(c["bear_body_ratio_min"]) if c.get("bear_body_ratio_min") is not None else fallback["bear_body_ratio_min"],
        }
        
        cfg = config_overrides[symbol]
        _log(f"[BBC] 📋 {symbol}: EMA={cfg['ema_period']} TP={cfg['tp_pct']*100:.1f}% SL={cfg['sl_pct']*100:.1f}% "
             f"BullBody={cfg['bull_body_ratio_min']} BearBody={cfg['bear_body_ratio_min']}")
    
    _log(f"[BBC] 📊 {len(config_overrides)} pair configs loaded from D1")
    return config_overrides


# ══════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════

@router.get("/bbc-live/start")
def bbc_live_start(position_usd: float = 1.0, leverage: int = 50):
    """Start BBC live trading with per-pair configs from D1."""
    config_overrides = _fetch_bbc_configs_from_d1()
    symbols = list(config_overrides.keys())
    
    return start_bbc_live(
        symbols=symbols, timeframe="1h",
        position_usd=position_usd, leverage=leverage,
        config_overrides=config_overrides,
    )


@router.get("/bbc-live/stop")
def bbc_live_stop():
    return stop_bbc_live()


@router.get("/bbc-live/status")
def bbc_live_status_endpoint():
    return bbc_live_status()


# ══════════════════════════════════════════════
# MULTI-ACCOUNT BBC
# ══════════════════════════════════════════════

_bbc_account_bots = {}


def _bbc_account_loop(account_id, client, account_info):
    bot = _bbc_account_bots.get(account_id)
    if not bot:
        return
    
    acct_name = account_info.get("name", f"BBC-{account_id}")
    position_usd = account_info.get("position_usd", 1)
    leverage = account_info.get("leverage", 50)
    client.leverage = leverage
    
    config_overrides = _fetch_bbc_configs_from_d1()
    symbols = list(config_overrides.keys()) if config_overrides else ["SOLUSDT", "ETHUSDT", "BTCUSDT", "BNBUSDT"]
    
    try:
        _bbc_live_loop(
            symbols=symbols, timeframe="1h",
            position_usd=position_usd, leverage=leverage,
            config_overrides=config_overrides,
            client=client, state=bot["state"],
            running_check=lambda: bot["running"],
            acct_name=acct_name,
        )
    except Exception as e:
        _log(f"[{acct_name}] ❌ BBC CRASH: {e}")
        _log(f"[{acct_name}] {traceback.format_exc()}")
    bot["running"] = False


@router.get("/bbc-live/start-account")
def bbc_live_start_account(account_id: int = 0):
    if account_id in _bbc_account_bots and _bbc_account_bots[account_id].get("running"):
        return {"ok": True, "message": f"BBC account {account_id} already running"}
    
    try:
        r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
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
    
    bot_state = {"mode": "bbc", "pairs": {}, "cycle_count": 0, "last_cycle": None,
        "started_at": None, "active_pairs": [], "positions": {}, "error": None}
    
    _bbc_account_bots[account_id] = {
        "running": True, "state": bot_state, "client": client, "account": account, "thread": None,
    }
    
    t = threading.Thread(target=_bbc_account_loop, args=(account_id, client, account), daemon=True)
    _bbc_account_bots[account_id]["thread"] = t
    t.start()
    
    return {"ok": True, "message": f"BBC started for '{account['name']}', ${account.get('position_usd', 1)}×{account.get('leverage', 50)}x"}


@router.get("/bbc-live/stop-account")
def bbc_live_stop_account(account_id: int = 0):
    bot = _bbc_account_bots.get(account_id)
    if not bot or not bot.get("running"):
        return {"ok": True, "message": f"BBC account {account_id} not running"}
    bot["running"] = False
    _log(f"[BBC-{account_id}] Stop signal sent")
    return {"ok": True, "message": f"BBC account {account_id} stopping..."}


@router.get("/bbc-live/account-status")
def bbc_live_account_status(account_id: int = None):
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if not bot:
            return {"ok": True, "running": False, "account_id": account_id}
        return {"ok": True, "account_id": account_id, "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "state": bot["state"], "account_name": bot["account"].get("name", "")}
    
    result = {}
    for aid, bot in _bbc_account_bots.items():
        result[aid] = {"running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "account_name": bot["account"].get("name", ""),
            "pairs": bot["state"].get("active_pairs", []),
            "cycle": bot["state"].get("cycle_count", 0),
            "positions": len(bot["state"].get("positions", {}))}
    return {"ok": True, "accounts": result}


@router.get("/bbc-live/configs")
def bbc_live_configs():
    """Show current BBC configs from D1 vs fallback."""
    d1_configs = _fetch_bbc_configs_from_d1()
    return {"ok": True, "configs": {sym: {"active": cfg, "recommended": BBC_FALLBACK.get(sym, {}),
        "match": cfg == BBC_FALLBACK.get(sym) if sym in BBC_FALLBACK else None}
        for sym, cfg in d1_configs.items()}}


@router.post("/bbc-live/close")
def bbc_close_position(symbol: str = None, account_id: int = None):
    client = None
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if bot: client = bot.get("client")
    if symbol: return close_position(symbol, client=client)
    return close_all_positions(client=client)


@router.post("/bbc-live/close-all")
def bbc_close_all(account_id: int = None):
    client = None
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if bot: client = bot.get("client")
    return close_all_positions(client=client)
