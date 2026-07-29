"""Baret Live + Ultron + Baret Discovery + Exchange Positions endpoints."""
import os
import requests as req
from fastapi import APIRouter
from baret_bot import start_baret, stop_baret, baret_status, get_baret_log
from baret_live import (start_baret_live, stop_baret_live, baret_live_status,
    get_baret_live_log, close_position, close_all_positions,
    start_account_bot, stop_account_bot, account_bot_status, _account_bots,
    ExchangeClient, WORKER_URL)
from ultron_engine import (ultron_status, get_ultron_log, manual_analyze,
    clear_pair_skip, clear_hour_skip, clear_buffer_adjustment)
from shared import DB_PATH

router = APIRouter()

# ── Baret Discovery ──
@router.get("/baret/start")
def baret_start_endpoint(mode: str = "baret", timeframes: str = ""):
    tfs = [t.strip() for t in timeframes.split(",") if t.strip()] or None
    return start_baret(DB_PATH, mode=mode, timeframes=tfs)

@router.get("/baret/stop")
def baret_stop_endpoint():
    return stop_baret()

@router.get("/baret/status")
def baret_status_endpoint():
    return baret_status()

@router.get("/baret/log")
def baret_log_endpoint(limit: int = 200):
    return {"ok": True, "log": get_baret_log(limit)}

# ── Baret Live ──
@router.get("/baret-live/start")
def baret_live_start(mode: str = "baret", position_usd: float = 10.0, min_wr: float = 75.0,
    max_dd: float = 20.0, min_ppd: float = 0.0, leverage: int = 50, max_bh: float = 100.0,
    buffer: float = None, tp: float = None, sl: float = None, sort_by: str = "profit",
    use_custom_configs: bool = False):
    return start_baret_live(mode=mode, position_usd=position_usd, min_wr=min_wr,
        max_dd=max_dd, min_ppd=min_ppd, leverage=leverage, max_bh=max_bh,
        buffer=buffer, tp=tp, sl=sl, sort_by=sort_by, use_custom_configs=use_custom_configs)

@router.get("/baret-live/stop")
def baret_live_stop():
    return stop_baret_live()

@router.get("/baret-live/status")
def baret_live_status_endpoint():
    return baret_live_status()

@router.get("/baret-live/log")
def baret_live_log_endpoint(limit: int = 200):
    return {"ok": True, "log": get_baret_live_log(limit)}

@router.get("/baret-live/close")
def baret_live_close(symbol: str = None, account_id: int = None):
    if account_id:
        bot = _account_bots.get(int(account_id))
        if not bot:
            return {"ok": False, "error": f"Account {account_id} not found or not running"}
        client = bot.get("client")
        if symbol:
            return close_position(symbol, client=client)
        return close_all_positions(client=client)
    if symbol:
        return close_position(symbol)
    return close_all_positions()

@router.get("/baret-live/start-account")
def baret_live_start_account(account_id: int = 0, mode: str = "baret_dca"):
    return start_account_bot(account_id, mode=mode)

@router.get("/baret-live/stop-account")
def baret_live_stop_account(account_id: int = 0):
    return stop_account_bot(account_id)

@router.get("/baret-live/account-status")
def baret_live_account_status(account_id: int = None):
    return account_bot_status(account_id)


# ══════════════════════════════════════════════
# EXCHANGE POSITIONS — checks ALL trading accounts
# ══════════════════════════════════════════════

@router.get("/baret-live/exchange-positions")
def exchange_positions(account_id: int = None):
    """Fetch real exchange positions from ALL trading accounts (or specific one).
    
    No account_id → checks ALL accounts and merges results.
    With account_id → checks only that account.
    """
    try:
        # Fetch trading accounts from D1
        r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
        accounts = r.json().get("accounts", [])
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch accounts: {e}"}

    if account_id is not None:
        # Single account
        accounts = [a for a in accounts if a["id"] == account_id]
        if not accounts:
            return {"ok": False, "error": f"Account {account_id} not found"}

    all_positions = []
    per_account = {}

    for acct in accounts:
        api_key = os.environ.get(acct.get("env_key_name", ""), "")
        api_secret = os.environ.get(acct.get("env_secret_name", ""), "")
        if not api_key or not api_secret:
            per_account[acct["name"]] = {"error": "API keys not found", "positions": []}
            continue

        try:
            client = ExchangeClient(acct["base_url"], api_key, api_secret, acct.get("leverage", 50))
            positions = client.get_all_positions() or []
            
            acct_positions = []
            for pos in positions:
                amt = float(pos.get("positionAmt", 0))
                if amt == 0:
                    continue
                entry = float(pos.get("entryPrice", 0))
                mark = float(pos.get("markPrice", 0))
                side = "LONG" if amt > 0 else "SHORT"
                pnl = float(pos.get("unRealizedProfit", 0))
                
                p = {
                    "symbol": pos.get("symbol", ""),
                    "side": side,
                    "size": abs(amt),
                    "entry_price": entry,
                    "mark_price": mark,
                    "unrealized_pnl": round(pnl, 4),
                    "leverage": int(pos.get("leverage", 0)),
                    "margin": round(float(pos.get("isolatedMargin", 0) or pos.get("initialMargin", 0)), 4),
                    "account_name": acct["name"],
                    "account_id": acct["id"],
                    "tracked_by_bot": False,  # Will be updated below
                }
                acct_positions.append(p)
                all_positions.append(p)
            
            per_account[acct["name"]] = {"positions": acct_positions, "count": len(acct_positions)}
        except Exception as e:
            per_account[acct["name"]] = {"error": str(e), "positions": []}

    # Check if positions are tracked by running bots
    for p in all_positions:
        aid = p["account_id"]
        sym = p["symbol"]
        # Check baret account bots
        bot = _account_bots.get(aid)
        if bot and bot.get("running"):
            p["tracked_by_bot"] = True
        # Check BBC account bots
        try:
            from bbc_live_endpoint import _bbc_account_bots
            bbc_bot = _bbc_account_bots.get(aid)
            if bbc_bot and bbc_bot.get("running"):
                p["tracked_by_bot"] = True
        except:
            pass

    return {
        "ok": True,
        "positions": all_positions,
        "count": len(all_positions),
        "per_account": per_account,
        "accounts_checked": len(accounts),
    }


# ── Ultron ──
@router.get("/ultron/status")
def ultron_status_endpoint():
    return ultron_status()

@router.get("/ultron/log")
def ultron_log_endpoint(limit: int = 100):
    return {"ok": True, "log": get_ultron_log(limit)}

@router.post("/ultron/analyze")
def ultron_analyze_endpoint():
    return manual_analyze()

@router.post("/ultron/clear-skip")
def ultron_clear_skip(symbol: str = None, hour: int = None):
    if symbol:
        clear_pair_skip(symbol)
        return {"ok": True, "message": f"Pair skip cleared: {symbol}"}
    if hour is not None:
        clear_hour_skip(hour)
        return {"ok": True, "message": f"Hour skip cleared: {hour}"}
    return {"ok": False, "error": "Provide symbol or hour"}

@router.post("/ultron/clear-buffer")
def ultron_clear_buffer(symbol: str = ""):
    clear_buffer_adjustment(symbol)
    return {"ok": True, "message": f"Buffer adjustment cleared: {symbol}"}
