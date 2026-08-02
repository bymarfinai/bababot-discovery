"""
BBC Account Monitor — called every candle close to check exchange state.
Auto-fixes missing SL/TP, detects orphans, cross-checks D1 trade log.
"""

import os
import requests as req
from datetime import datetime, timezone

_WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")


def check_account_health(client, acct_name, bot_state):
    """Run all health checks for one account. Auto-fix missing SL/TP."""
    from baret_live import _log, _send_telegram, _place_sl_tp

    alerts = []
    fixes = []

    # Get configs for SL/TP percentages
    from bbc_live_endpoint import BBC_FALLBACK, _fetch_bbc_configs_from_d1
    try:
        configs = _fetch_bbc_configs_from_d1()
    except Exception:
        configs = dict(BBC_FALLBACK)

    # 1. Check all open positions — fix missing SL/TP
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

            # Auto-fix missing SL/TP
            if not has_sl or not has_tp:
                cfg = configs.get(symbol, BBC_FALLBACK.get(symbol))
                if cfg and entry > 0:
                    sl_pct = cfg.get("sl_pct", 0.015)
                    tp_pct = cfg.get("tp_pct", 0.013)

                    if side == "LONG":
                        sl_price = entry * (1 - sl_pct)
                        tp_price = entry * (1 + tp_pct)
                    else:
                        sl_price = entry * (1 + sl_pct)
                        tp_price = entry * (1 - tp_pct)

                    if not has_sl and not has_tp:
                        result = _place_sl_tp(client, symbol, side, sl_price, tp_price)
                        fixes.append(f"🔧 {symbol} {side} — placed SL @ ${sl_price:.4f} + TP @ ${tp_price:.4f}")
                    elif not has_sl:
                        close_side = "SELL" if side == "LONG" else "BUY"
                        client.place_algo_order(symbol, close_side, "STOP_MARKET", sl_price)
                        fixes.append(f"🔧 {symbol} {side} — placed SL @ ${sl_price:.4f}")
                    elif not has_tp:
                        close_side = "SELL" if side == "LONG" else "BUY"
                        client.place_algo_order(symbol, close_side, "TAKE_PROFIT_MARKET", tp_price)
                        fixes.append(f"🔧 {symbol} {side} — placed TP @ ${tp_price:.4f}")
                else:
                    if not has_sl:
                        alerts.append(f"⚠️ {symbol} {side} @ ${entry:.4f} — NO SL (no config to auto-fix)")
                    if not has_tp:
                        alerts.append(f"⚠️ {symbol} {side} @ ${entry:.4f} — NO TP (no config to auto-fix)")

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

        for symbol in configs.keys():
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
                    alerts.append(f"📋 {missing} trade(s) on exchange but NOT in D1 log (last 6h) — run /bbc-live/sync-trades to fix")
            except Exception:
                pass
    except Exception as e:
        _log(f"[MONITOR] ❌ Trade cross-check error: {e}")

    # Report
    if fixes:
        fix_msg = f"🔧 *AUTO-FIX — {acct_name}*\n" + "\n".join(fixes)
        _log(f"[MONITOR] {len(fixes)} fix(es) applied for {acct_name}")
        _send_telegram(fix_msg)

    if alerts:
        alert_msg = f"🚨 *ACCOUNT MONITOR — {acct_name}*\n" + "\n".join(alerts)
        _log(f"[MONITOR] {len(alerts)} alert(s) for {acct_name}")
        _send_telegram(alert_msg)

    if not fixes and not alerts:
        _log(f"[MONITOR] ✅ {acct_name} healthy")

    return {"fixes": fixes, "alerts": alerts}
