"""
BBC Account Monitor — background watchdog that periodically checks exchange state
and alerts on anomalies (missing SL/TP, orphan positions, unlogged trades).

Runs as a daemon thread alongside the BBC live bot.
"""

import time
import threading
import os
import requests as req
from datetime import datetime, timezone

_WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")
_CHECK_INTERVAL = 300  # 5 minutes
_monitor_threads = {}


def _send_alert(msg):
    """Send Telegram alert for anomalies."""
    try:
        from baret_live import _send_telegram, _log
        _log(f"[MONITOR] {msg}")
        _send_telegram(f"🚨 *ACCOUNT MONITOR*\n{msg}")
    except Exception:
        pass


def _check_account(client, acct_name, bot_state):
    """Single health check cycle for one account."""
    alerts = []

    # 1. Check all open positions have SL/TP
    try:
        positions = client.get_all_positions()
        for p in positions:
            symbol = p["symbol"]
            amt = float(p.get("positionAmt", 0))
            if amt == 0:
                continue
            side = "LONG" if amt > 0 else "SHORT"
            entry = float(p.get("entryPrice", 0))
            unrealized = float(p.get("unRealizedProfit", 0))

            algo_orders = client.get_open_algo_orders(symbol)
            has_sl = False
            has_tp = False
            if isinstance(algo_orders, dict):
                algo_orders = algo_orders.get("orders", [])
            if isinstance(algo_orders, list):
                for ao in algo_orders:
                    if ao.get("type") == "STOP_MARKET":
                        has_sl = True
                    elif ao.get("type") == "TAKE_PROFIT_MARKET":
                        has_tp = True

            if not has_sl:
                alerts.append(f"⚠️ {symbol} {side} @ ${entry:.4f} — NO STOP LOSS!")
            if not has_tp:
                alerts.append(f"⚠️ {symbol} {side} @ ${entry:.4f} — NO TAKE PROFIT!")

            # Check if bot is tracking
            if bot_state:
                bot_positions = bot_state.get("positions", {})
                if symbol not in bot_positions:
                    alerts.append(f"👻 {symbol} {side} @ ${entry:.4f} — ORPHAN (not tracked by bot)")
    except Exception as e:
        alerts.append(f"❌ Position check failed: {e}")

    # 2. Cross-check recent trades: exchange vs D1
    try:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        lookback_6h = 6 * 60 * 60 * 1000
        exchange_exit_count = 0

        from bbc_live_endpoint import BBC_FALLBACK
        for symbol in BBC_FALLBACK.keys():
            try:
                trades = client.api_get("/fapi/v1/userTrades", {
                    "symbol": symbol,
                    "startTime": now_ms - lookback_6h,
                    "limit": 100,
                }, signed=True)
                if isinstance(trades, list):
                    for t in trades:
                        if abs(float(t.get("realizedPnl", 0))) > 0.0001:
                            exchange_exit_count += 1
            except Exception:
                pass

        if exchange_exit_count > 0:
            try:
                r = req.get(f"{_WORKER_URL}/bot/trade-log?period=24h", timeout=10)
                d1_trades = r.json().get("trades", [])
                d1_count = len([t for t in d1_trades if acct_name in (t.get("notes") or "")])
                if exchange_exit_count > d1_count:
                    missing = exchange_exit_count - d1_count
                    alerts.append(f"📋 {missing} trade(s) in exchange but NOT in D1 log (last 6h)")
            except Exception:
                pass
    except Exception:
        pass

    if alerts:
        header = f"*Account: {acct_name}*\n"
        _send_alert(header + "\n".join(alerts))

    return alerts


def _monitor_loop(account_id, client, acct_name, bot_ref):
    """Background loop that checks account health every N minutes."""
    try:
        from baret_live import _log
        _log(f"[MONITOR] Started for {acct_name} (every {_CHECK_INTERVAL}s)")
    except Exception:
        pass

    while True:
        bot = bot_ref()
        if bot is None or not bot.get("running", False):
            break

        try:
            _check_account(client, acct_name, bot.get("state"))
        except Exception as e:
            try:
                from baret_live import _log
                _log(f"[MONITOR] ❌ Check failed for {acct_name}: {e}")
            except Exception:
                pass

        time.sleep(_CHECK_INTERVAL)

    try:
        from baret_live import _log
        _log(f"[MONITOR] Stopped for {acct_name}")
    except Exception:
        pass


def start_monitor(account_id, client, acct_name, bot_ref):
    """Start background monitor for an account.

    Args:
        account_id: account ID
        client: ExchangeClient instance
        acct_name: human-readable account name
        bot_ref: callable that returns bot dict (for checking running state)
    """
    if account_id in _monitor_threads:
        t = _monitor_threads[account_id]
        if t.is_alive():
            return

    t = threading.Thread(
        target=_monitor_loop,
        args=(account_id, client, acct_name, bot_ref),
        daemon=True,
    )
    t.start()
    _monitor_threads[account_id] = t


def stop_monitor(account_id):
    """Stop is handled by bot_ref() returning not-running."""
    _monitor_threads.pop(account_id, None)
