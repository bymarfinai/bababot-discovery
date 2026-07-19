"""
FastAPI Router for live trading fixes + BBC live mode.
Mount in app.py: app.include_router(live_fixes_router)
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/baret-live/exchange-positions")
def api_exchange_positions(account_id: int = None):
    """Get actual positions from Binance exchange — bypasses bot state."""
    from live_fixes.integrate import get_exchange_positions
    return get_exchange_positions(account_id)


@router.post("/baret-live/close-position")
def api_close_position(symbol: str, account_id: int = None):
    """Emergency close a position from dashboard."""
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
    """Emergency close ALL positions."""
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
    """Start BBC live trading."""
    from bbc_live import start_bbc_live
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    overrides = {}
    if tp_pct > 0:
        overrides["tp_pct"] = tp_pct / 100  # convert from % to decimal
    if sl_pct > 0:
        overrides["sl_pct"] = sl_pct / 100
    if ema_period > 0:
        overrides["ema_period"] = ema_period
    return start_bbc_live(symbol_list, timeframe, position_usd, leverage,
                          overrides or None)


@router.get("/bbc-live/stop")
def api_bbc_stop():
    """Stop BBC live trading."""
    from bbc_live import stop_bbc_live
    return stop_bbc_live()


@router.get("/bbc-live/status")
def api_bbc_status():
    """Get BBC live status."""
    from bbc_live import bbc_live_status
    return bbc_live_status()
