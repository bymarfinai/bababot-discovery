"""
FastAPI Router for live trading fixes.
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
