"""
BBC Account Monitor — called every candle close to check exchange state
and alert on anomalies (missing SL/TP, orphan positions, unlogged trades).
"""

import os
import requests as req
from datetime import datetime, timezone

_WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")


def check_account_health(client, acct_name, bot_state):
    """Run all health checks for one account. Called at end of each candle cycle."""
    from baret_live import _log, _send_telegram

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
            bot_positions = bot_state.get("positions", {})
            if symbol not in bot_positions:
                alerts.append(f"👻 {symbol} {side} @ ${entry:.4f} — ORPHAN (not tracked by bot)")
    except Exception as e:
        _log(f"[MONITOR] ❌ Position check error: {e}")

    # 2. Cross-check recent trades: exchange vs D1 (last 6h)
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
                    alerts.append(f"📋 {missing} trade(s) on exchange but NOT in D1 log (last 6h)")
            except Exception:
                pass
    except Exception as e:
        _log(f"[MONITOR] ❌ Trade cross-check error: {e}")

    # Send alerts if any
    if alerts:
        msg = f"🚨 *ACCOUNT MONITOR — {acct_name}*\n" + "\n".join(alerts)
        _log(f"[MONITOR] {len(alerts)} alert(s) for {acct_name}")
        _send_telegram(msg)
    else:
        _log(f"[MONITOR] ✅ {acct_name} healthy")

    return alerts
