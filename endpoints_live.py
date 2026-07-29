"""Baret Live + Ultron + Baret Discovery + Exchange Positions endpoints."""
import os
import requests as req
from fastapi import APIRouter
from baret_bot import start_baret, stop_baret, baret_status, get_baret_log
from baret_live import (start_baret_live, stop_baret_live, baret_live_status,
    get_baret_live_log, close_position, close_all_positions,
    start_account_bot, stop_account_bot, account_bot_status, _account_bots,
    ExchangeClient, WORKER_URL, _cancel_sl_tp)
from ultron_engine import (ultron_status, get_ultron_log, manual_analyze,
    clear_pair_skip, clear_hour_skip, clear_buffer_adjustment)
from shared import DB_PATH

router = APIRouter()


# ══════════════════════════════════════════════
# HELPER: create ExchangeClient from D1 account
# ══════════════════════════════════════════════

def _get_client_for_account(account_id: int):
    """Create ExchangeClient from D1 credentials. Works even if bot is not running."""
    # Try running bots first (faster, no D1 roundtrip)
    bot = _account_bots.get(account_id)
    if bot and bot.get("client"):
        return bot["client"], None
    try:
        from bbc_live_endpoint import _bbc_account_bots
        bbc_bot = _bbc_account_bots.get(account_id)
        if bbc_bot and bbc_bot.get("client"):
            return bbc_bot["client"], None
    except:
        pass
    
    # Create fresh client from D1
    try:
        r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
        acct = next((a for a in r.json().get("accounts", []) if a["id"] == account_id), None)
        if not acct:
            return None, f"Account {account_id} not found"
        api_key = os.environ.get(acct.get("env_key_name", ""), "")
        api_secret = os.environ.get(acct.get("env_secret_name", ""), "")
        if not api_key or not api_secret:
            return None, f"API keys not found: {acct.get('env_key_name', '')}"
        return ExchangeClient(acct["base_url"], api_key, api_secret, acct.get("leverage", 50)), None
    except Exception as e:
        return None, str(e)


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
    """Close position(s). Works even if bot is not running."""
    client = None
    if account_id:
        client, err = _get_client_for_account(int(account_id))
        if err:
            return {"ok": False, "error": err}
    if symbol:
        return close_position(symbol, client=client)
    return close_all_positions(client=client)

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
    """Fetch real exchange positions from ALL trading accounts (or specific one)."""
    try:
        r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
        accounts = r.json().get("accounts", [])
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch accounts: {e}"}

    if account_id is not None:
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
                p = {
                    "symbol": pos.get("symbol", ""),
                    "side": "LONG" if amt > 0 else "SHORT",
                    "size": abs(amt),
                    "entry_price": float(pos.get("entryPrice", 0)),
                    "mark_price": float(pos.get("markPrice", 0)),
                    "unrealized_pnl": round(float(pos.get("unRealizedProfit", 0)), 4),
                    "leverage": int(pos.get("leverage", 0)),
                    "margin": round(float(pos.get("isolatedMargin", 0) or pos.get("initialMargin", 0)), 4),
                    "account_name": acct["name"],
                    "account_id": acct["id"],
                    "tracked_by_bot": False,
                }
                # Check if tracked by running bot
                bot = _account_bots.get(acct["id"])
                if bot and bot.get("running"):
                    p["tracked_by_bot"] = True
                try:
                    from bbc_live_endpoint import _bbc_account_bots
                    bbc_bot = _bbc_account_bots.get(acct["id"])
                    if bbc_bot and bbc_bot.get("running"):
                        p["tracked_by_bot"] = True
                except:
                    pass
                acct_positions.append(p)
                all_positions.append(p)
            per_account[acct["name"]] = {"positions": acct_positions, "count": len(acct_positions)}
        except Exception as e:
            per_account[acct["name"]] = {"error": str(e), "positions": []}

    return {
        "ok": True,
        "positions": all_positions,
        "count": len(all_positions),
        "per_account": per_account,
        "accounts_checked": len(accounts),
    }


# ══════════════════════════════════════════════
# CLOSE POSITION PER ACCOUNT (works without bot running)
# ══════════════════════════════════════════════

@router.post("/baret-live/close-position")
def close_position_per_account(symbol: str, account_id: int):
    """Close a specific position on a specific account. Works without bot running."""
    client, err = _get_client_for_account(account_id)
    if err:
        return {"ok": False, "error": err}
    try:
        # Cancel SL/TP algo orders first
        _cancel_sl_tp(client, symbol)
        # Get current position
        pos = client.get_position(symbol)
        if not pos or float(pos.get("positionAmt", 0)) == 0:
            return {"ok": True, "message": f"No position for {symbol} on account {account_id}"}
        amt = abs(float(pos["positionAmt"]))
        side = "SELL" if float(pos["positionAmt"]) > 0 else "BUY"
        client.place_market_close(symbol, side, amt)
        return {"ok": True, "message": f"Closed {symbol} {side} {amt} on account {account_id}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/baret-live/close-all-account")
def close_all_per_account(account_id: int):
    """Close ALL positions on a specific account. Works without bot running."""
    client, err = _get_client_for_account(account_id)
    if err:
        return {"ok": False, "error": err}
    try:
        positions = client.get_all_positions() or []
        closed = []
        for pos in positions:
            amt = float(pos.get("positionAmt", 0))
            if amt == 0:
                continue
            symbol = pos["symbol"]
            _cancel_sl_tp(client, symbol)
            side = "SELL" if amt > 0 else "BUY"
            client.place_market_close(symbol, side, abs(amt))
            closed.append(symbol)
        return {"ok": True, "closed": closed, "count": len(closed)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
