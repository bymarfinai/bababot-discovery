"""
Live Fixes Integration — Monkey-patch baret_live.py at startup.

Usage in app.py:
    import live_fixes.integrate  # patches baret_live automatically

This avoids modifying the 67KB baret_live.py file directly.
All fixes are applied via function replacement at import time.
"""

import time
import baret_live
from baret_live import (
    _log, _send_telegram, _fmt_price, _get_price, _cancel_sl_tp,
    _log_trade_to_d1, _log_analytics_to_d1,
    _baret_live_state, _baret_live_running, _baret_live_thread,
    _account_bots, _get_default_client,
)
from datetime import datetime, timezone


# ══════════════════════════════════════════════
# FIX 1: _place_sl_tp with retry 3x + Telegram alert
# ══════════════════════════════════════════════

def _place_sl_tp_v2(client, symbol, position_side, sl_price, tp_price, max_retries=3):
    """Place SL and TP via algoOrder with retry. Telegram alert on total failure."""
    close_side = "SELL" if position_side == "LONG" else "BUY"
    results = {}

    for label, algo_type, price in [("SL", "STOP_MARKET", sl_price), ("TP", "TAKE_PROFIT_MARKET", tp_price)]:
        for attempt in range(1, max_retries + 1):
            try:
                r = client.place_algo_order(symbol, close_side, algo_type, price)
                if r.get("algoId"):
                    results[label.lower()] = r
                    break
                _log(f"    ⚠️ {label} attempt {attempt}/{max_retries} failed: {r.get('msg', r)}")
                if attempt < max_retries:
                    time.sleep(1)
            except Exception as e:
                _log(f"    ⚠️ {label} attempt {attempt}/{max_retries} error: {e}")
                if attempt < max_retries:
                    time.sleep(1)

        if label.lower() not in results:
            _log(f"    🚨 CRITICAL: {label} FAILED after {max_retries} attempts for {symbol}!")
            _send_telegram(
                f"🚨 *CRITICAL: {label} FAILED*\n"
                f"{symbol} {position_side}\n"
                f"{label} @ ${_fmt_price(symbol, price)}\n"
                f"⚠️ Position {'UNPROTECTED' if label == 'SL' else 'no TP'}! Close manually!"
            )
            results[label.lower()] = {"error": f"Failed after {max_retries} attempts"}

    return results


# Apply patch
baret_live._place_sl_tp = _place_sl_tp_v2
_log("[LiveFixes] ✅ FIX 1: _place_sl_tp patched with retry 3x + Telegram alert")


# ══════════════════════════════════════════════
# FIX 2: Exchange reconciliation
# ══════════════════════════════════════════════

def _reconcile_exchange_positions(client, state, configs, prefix, acct_name):
    """Detect orphan/ghost positions and auto-close/cleanup."""
    try:
        exchange_positions = client.get_all_positions()
        exchange_symbols = {p["symbol"] for p in exchange_positions}
        tracked_symbols = set(state.get("positions", {}).keys())

        # Orphan: on exchange but not tracked
        for pos in exchange_positions:
            symbol = pos["symbol"]
            if symbol not in tracked_symbols:
                amt = float(pos.get("positionAmt", 0))
                entry_price = float(pos.get("entryPrice", 0))
                side = "LONG" if amt > 0 else "SHORT"
                upnl = float(pos.get("unRealizedProfit", 0))

                _log(f"{prefix}  🚨 ORPHAN: {symbol} {side} qty={abs(amt)} entry=${entry_price:.4f} uPnL=${upnl:.2f}")
                _send_telegram(f"🚨 *ORPHAN DETECTED*\n{symbol} {side}\nEntry: ${entry_price:.4f}\nQty: {abs(amt)}\nuPnL: ${upnl:.2f}\nAuto-closing...")

                try:
                    client.cancel_all_orders(symbol)
                    _cancel_sl_tp(client, symbol)
                    close_side = "SELL" if amt > 0 else "BUY"
                    client.place_market_close(symbol, close_side, abs(amt))
                    time.sleep(1)
                    verify = client.get_position(symbol)
                    if verify and abs(float(verify.get("positionAmt", 0))) > 0:
                        _log(f"{prefix}  ❌ ORPHAN {symbol}: close FAILED!")
                        _send_telegram(f"❌ ORPHAN {symbol} close FAILED! Manual close needed!")
                    else:
                        cp = _get_price(symbol)
                        _log(f"{prefix}  ✅ ORPHAN {symbol}: closed @ ~${cp:.4f}")
                        _send_telegram(f"✅ Orphan {symbol} closed @ ~${cp:.4f}")
                        cfg_tf = next((c.get("timeframe", "1h") for c in configs if c["symbol"] == symbol), "1h")
                        pnl_pct = ((cp - entry_price) / entry_price * 100) if side == "LONG" else ((entry_price - cp) / entry_price * 100) if entry_price > 0 and cp > 0 else 0
                        _log_trade_to_d1(symbol, cfg_tf, side, entry_price, cp,
                            datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
                            0, 0, upnl, pnl_pct, "ORPHAN_CLOSE", acct_name)
                except Exception as e:
                    _log(f"{prefix}  ❌ ORPHAN {symbol} error: {e}")
                    _send_telegram(f"❌ ORPHAN {symbol} error: {e}")

        # Ghost: tracked but not on exchange
        for symbol in list(tracked_symbols):
            if symbol not in exchange_symbols:
                pos_info = state["positions"].get(symbol)
                if pos_info:
                    _log(f"{prefix}  👻 GHOST: {symbol} in state but not on exchange — cleanup")
                    cp = _get_price(symbol)
                    if cp > 0 and pos_info.get("entry", 0) > 0:
                        entry = pos_info["entry"]
                        side = pos_info["side"]
                        pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                        _log(f"{prefix}  👻 {symbol} {side}: ~${cp:.4f}, PnL ~{pnl_pct:+.2f}%")
                    state["positions"].pop(symbol, None)
                    state.get("pending_orders", {}).pop(symbol, None)

    except Exception as e:
        _log(f"{prefix}  ⚠️ Reconcile error: {e}")


# Patch: inject reconciliation into the main loop
# We wrap _baret_live_loop to add reconciliation at cycle start
_original_loop = baret_live._baret_live_loop

def _patched_baret_live_loop(*args, **kwargs):
    """Patched loop that adds reconciliation. We monkey-patch _monitor_positions instead
    since it's called every poll cycle, making reconciliation more frequent."""
    return _original_loop(*args, **kwargs)

# Better approach: patch _monitor_positions to also reconcile periodically
_original_monitor = baret_live._monitor_positions
_last_reconcile = [0]  # timestamp of last reconciliation

def _patched_monitor_positions(client, configs, state, prefix, acct_name, last_debug_ref):
    """Monitor with periodic reconciliation (every 5 minutes)."""
    # Run original monitor
    _original_monitor(client, configs, state, prefix, acct_name, last_debug_ref)
    
    # Reconcile every 5 minutes
    now = time.time()
    if now - _last_reconcile[0] > 300:  # 5 min
        _reconcile_exchange_positions(client, state, configs, prefix, acct_name)
        _last_reconcile[0] = now

baret_live._monitor_positions = _patched_monitor_positions
_log("[LiveFixes] ✅ FIX 2: Exchange reconciliation patched (every 5 min)")


# ══════════════════════════════════════════════
# FIX 3: baret_live_status with enriched data
# ══════════════════════════════════════════════

def _patched_baret_live_status():
    """Enhanced status with current prices, unrealized PnL, progress."""
    base = {
        "ok": True,
        "running": baret_live._baret_live_running,
        "thread_alive": baret_live._baret_live_thread.is_alive() if baret_live._baret_live_thread else False,
        **baret_live._baret_live_state,
    }

    enriched = {}
    for symbol, pos in baret_live._baret_live_state.get("positions", {}).items():
        p = dict(pos)
        try:
            cp = _get_price(symbol)
            if cp > 0 and pos.get("entry", 0) > 0:
                entry = pos["entry"]
                side = pos["side"]
                p["current_price"] = cp
                p["unrealized_pnl_pct"] = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                p["unrealized_pnl_usd"] = p["unrealized_pnl_pct"] / 100 * entry * pos.get("qty", 0)
                tp, sl = pos.get("tp", 0), pos.get("sl", 0)
                if side == "LONG" and tp > entry and entry > sl:
                    p["progress"] = min(1.0, (cp - entry) / (tp - entry)) if cp >= entry else max(-1.0, -(entry - cp) / (entry - sl))
                elif side == "SHORT" and entry > tp and sl > entry:
                    p["progress"] = min(1.0, (entry - cp) / (entry - tp)) if cp <= entry else max(-1.0, -(cp - entry) / (sl - entry))
                else:
                    p["progress"] = 0
        except:
            pass
        enriched[symbol] = p

    base["positions"] = enriched
    return base

baret_live.baret_live_status = _patched_baret_live_status
_log("[LiveFixes] ✅ FIX 3: baret_live_status patched with unrealized PnL + progress")


# ══════════════════════════════════════════════
# FIX 4: get_exchange_positions (new function)
# ══════════════════════════════════════════════

def get_exchange_positions(account_id=None):
    """Direct Binance query — bypasses bot state entirely."""
    results = []
    if account_id:
        account_id = int(account_id)
        bot = baret_live._account_bots.get(account_id)
        if bot and bot.get("client"):
            client = bot["client"]
            acct_name = bot["account"].get("name", f"Account-{account_id}")
        else:
            return {"ok": False, "error": f"Account {account_id} not found or not started"}
    else:
        client = _get_default_client()
        acct_name = "Demo"

    try:
        positions = client.get_all_positions()
        for p in positions:
            symbol = p["symbol"]
            amt = float(p.get("positionAmt", 0))
            side = "LONG" if amt > 0 else "SHORT"
            entry_price = float(p.get("entryPrice", 0))
            mark_price = float(p.get("markPrice", 0))

            tracked = baret_live._baret_live_state.get("positions", {}).get(symbol)
            if account_id:
                bot = baret_live._account_bots.get(account_id)
                tracked = bot["state"].get("positions", {}).get(symbol) if bot else None

            results.append({
                "symbol": symbol, "side": side, "qty": abs(amt),
                "entry_price": entry_price, "mark_price": mark_price,
                "unrealized_pnl": float(p.get("unRealizedProfit", 0)),
                "leverage": int(p.get("leverage", 0)),
                "tracked_by_bot": tracked is not None,
                "bot_tp": tracked.get("tp") if tracked else None,
                "bot_sl": tracked.get("sl") if tracked else None,
                "bot_hold_candles": tracked.get("hold_candles") if tracked else None,
                "account": acct_name,
            })
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "positions": results, "count": len(results), "account": acct_name}

# Export for app.py
baret_live.get_exchange_positions = get_exchange_positions
_log("[LiveFixes] ✅ FIX 4: get_exchange_positions added")

_log("[LiveFixes] ═══ ALL 4 CRITICAL FIXES APPLIED ═══")
