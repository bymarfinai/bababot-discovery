"""
Exchange Position Monitor — Direct Binance query + orphan detection.

Functions to be imported into baret_live.py:
- _reconcile_exchange_positions: detect orphan/ghost positions
- get_exchange_positions: direct Binance query for dashboard
"""

import time
from datetime import datetime, timezone


def _reconcile_exchange_positions(client, state, configs, prefix, acct_name,
                                  _log_fn=None, _send_telegram_fn=None,
                                  _cancel_sl_tp_fn=None, _get_price_fn=None,
                                  _log_trade_to_d1_fn=None):
    """Reconcile bot state with actual exchange positions.
    
    Detects:
    1. Orphan positions (on exchange, not in bot state) -> auto-close + alert
    2. Ghost positions (in bot state, not on exchange) -> cleanup state
    
    Called every cycle to prevent position leaks.
    """
    _log = _log_fn or (lambda msg: print(f"[Reconcile] {msg}"))
    _send_telegram = _send_telegram_fn or (lambda msg: None)
    _cancel_sl_tp = _cancel_sl_tp_fn or (lambda c, s: None)
    _get_price = _get_price_fn or (lambda s: 0)
    _log_trade_to_d1 = _log_trade_to_d1_fn or (lambda *a, **k: None)

    try:
        exchange_positions = client.get_all_positions()
        exchange_symbols = {p["symbol"] for p in exchange_positions}
        tracked_symbols = set(state.get("positions", {}).keys())

        # Case 1: Orphan (exchange has it, bot doesn't track it)
        for pos in exchange_positions:
            symbol = pos["symbol"]
            if symbol not in tracked_symbols:
                amt = float(pos.get("positionAmt", 0))
                entry_price = float(pos.get("entryPrice", 0))
                side = "LONG" if amt > 0 else "SHORT"
                unrealized_pnl = float(pos.get("unRealizedProfit", 0))

                _log(f"{prefix}  ORPHAN DETECTED: {symbol} {side} qty={abs(amt)} entry=${entry_price:.4f} uPnL=${unrealized_pnl:.2f}")
                _send_telegram(
                    f"*ORPHAN POSITION DETECTED*\n"
                    f"{symbol} {side}\n"
                    f"Entry: ${entry_price:.4f}\n"
                    f"Qty: {abs(amt)}\n"
                    f"Unrealized PnL: ${unrealized_pnl:.2f}\n"
                    f"Auto-closing..."
                )

                try:
                    client.cancel_all_orders(symbol)
                    _cancel_sl_tp(client, symbol)
                    close_side = "SELL" if amt > 0 else "BUY"
                    client.place_market_close(symbol, close_side, abs(amt))
                    time.sleep(1)

                    verify = client.get_position(symbol)
                    if verify and abs(float(verify.get("positionAmt", 0))) > 0:
                        _log(f"{prefix}  ORPHAN {symbol}: auto-close FAILED, still open!")
                        _send_telegram(f"ORPHAN {symbol} auto-close FAILED! Close manually on Binance!")
                    else:
                        cp = _get_price(symbol)
                        _log(f"{prefix}  ORPHAN {symbol}: auto-closed @ ~${cp:.4f}")
                        _send_telegram(f"Orphan {symbol} closed @ ~${cp:.4f}")

                        cfg_tf = next((c.get("timeframe", "1h") for c in configs if c["symbol"] == symbol), "1h")
                        pnl_pct = ((cp - entry_price) / entry_price * 100) if side == "LONG" else ((entry_price - cp) / entry_price * 100) if entry_price > 0 and cp > 0 else 0
                        pnl_dollar = unrealized_pnl
                        _log_trade_to_d1(symbol, cfg_tf, side, entry_price, cp,
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                            0, 0, pnl_dollar, pnl_pct, "ORPHAN_CLOSE", acct_name)

                except Exception as e:
                    _log(f"{prefix}  ORPHAN {symbol} close error: {e}")
                    _send_telegram(f"ORPHAN {symbol} close error: {e}\nClose manually!")

        # Case 2: Ghost (bot tracks it, but exchange is flat)
        for symbol in list(tracked_symbols):
            if symbol not in exchange_symbols:
                pos_info = state["positions"].get(symbol)
                if pos_info:
                    _log(f"{prefix}  GHOST DETECTED: {symbol} in bot state but NOT on exchange - cleaning up")
                    cp = _get_price(symbol)
                    if cp > 0 and pos_info.get("entry", 0) > 0:
                        entry = pos_info["entry"]
                        side = pos_info["side"]
                        pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                        _log(f"{prefix}  GHOST {symbol} {side}: estimated exit ~${cp:.4f}, PnL ~{pnl_pct:+.2f}%")

                    state["positions"].pop(symbol, None)
                    state.get("pending_orders", {}).pop(symbol, None)

    except Exception as e:
        _log(f"{prefix}  Reconciliation error: {e}")


def get_exchange_positions(client_fn, baret_state, account_bots, account_id=None):
    """Get actual positions from Binance exchange.
    Independent of bot state - always shows truth.
    
    Args:
        client_fn: callable that returns default ExchangeClient
        baret_state: _baret_live_state dict
        account_bots: _account_bots dict
        account_id: optional specific account
    """
    results = []

    if account_id:
        account_id = int(account_id)
        bot = account_bots.get(account_id)
        if bot and bot.get("client"):
            client = bot["client"]
            acct_name = bot["account"].get("name", f"Account-{account_id}")
        else:
            return {"ok": False, "error": f"Account {account_id} not found or not started"}
    else:
        client = client_fn()
        acct_name = "Demo"

    try:
        positions = client.get_all_positions()
        for p in positions:
            symbol = p["symbol"]
            amt = float(p.get("positionAmt", 0))
            entry_price = float(p.get("entryPrice", 0))
            mark_price = float(p.get("markPrice", 0))
            unrealized_pnl = float(p.get("unRealizedProfit", 0))
            leverage_val = int(p.get("leverage", 0))
            side = "LONG" if amt > 0 else "SHORT"

            tracked = baret_state.get("positions", {}).get(symbol)
            if account_id:
                bot = account_bots.get(account_id)
                tracked = bot["state"].get("positions", {}).get(symbol) if bot else None

            results.append({
                "symbol": symbol,
                "side": side,
                "qty": abs(amt),
                "entry_price": entry_price,
                "mark_price": mark_price,
                "unrealized_pnl": unrealized_pnl,
                "leverage": leverage_val,
                "tracked_by_bot": tracked is not None,
                "bot_tp": tracked.get("tp") if tracked else None,
                "bot_sl": tracked.get("sl") if tracked else None,
                "bot_hold_candles": tracked.get("hold_candles") if tracked else None,
                "account": acct_name,
            })

    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "positions": results, "count": len(results), "account": acct_name}
