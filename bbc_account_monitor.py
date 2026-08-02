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
                    otype = ao.get("type") or ao.get("algoOrderType") or ao.get("origType") or ""
                    if otype in ("STOP_MARKET", "STOP"):
                        has_sl = True
                    elif otype in ("TAKE_PROFIT_MARKET", "TAKE_PROFIT"):
                        has_tp = True
            else:
                _log(f"[MONITOR] ⚠️ Unexpected algo_orders response for {symbol}: {type(algo_orders)} — {str(algo_orders)[:200]}")

            if has_sl and has_tp:
                continue

            # Auto-fix missing SL/TP
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

                if has_sl or has_tp:
                    try:
                        client.cancel_all_algo_orders(symbol)
                    except Exception:
                        pass

                result = _place_sl_tp(client, symbol, side, sl_price, tp_price)
                fixes.append(f"🔧 {symbol} {side} — placed SL @ ${sl_price:.4f} + TP @ ${tp_price:.4f}")
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

    # 2. Auto-sync: pull exchange trades (last 6h), backfill any missing from D1
    try:
        from bbc_trade_logger import _log_trade_to_d1

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        lookback_6h = 24 * 60 * 60 * 1000

        # Fetch D1 trades for dedup
        d1_trades = []
        try:
            r = req.get(f"{_WORKER_URL}/bot/trade-log?period=24h", timeout=10)
            d1_trades = r.json().get("trades", [])
        except Exception:
            pass

        # Build dedup key set from D1: (symbol, approx_exit_time_hour, side)
        d1_keys = set()
        for t in d1_trades:
            if acct_name not in (t.get("notes") or ""):
                continue
            exit_str = t.get("exit_time") or ""
            d1_keys.add((t.get("symbol"), exit_str[:16], t.get("side")))

        for symbol in configs.keys():
            try:
                exchange_trades = client.api_get("/fapi/v1/userTrades", {
                    "symbol": symbol,
                    "startTime": now_ms - lookback_6h,
                    "limit": 100,
                }, signed=True)
                if not isinstance(exchange_trades, list):
                    continue

                # Split into entry and exit fills
                entry_fills = []
                exit_fills = []
                for t in exchange_trades:
                    rpnl = float(t.get("realizedPnl", 0))
                    if abs(rpnl) > 0.0001:
                        exit_fills.append(t)
                    else:
                        entry_fills.append(t)

                if not exit_fills:
                    continue

                # Group exit fills by time proximity (within 1s = same exit)
                exit_groups = []
                current_group = [exit_fills[0]]
                for i in range(1, len(exit_fills)):
                    if exit_fills[i]["time"] - exit_fills[i-1]["time"] < 1000:
                        current_group.append(exit_fills[i])
                    else:
                        exit_groups.append(current_group)
                        current_group = [exit_fills[i]]
                exit_groups.append(current_group)

                for group in exit_groups:
                    total_qty = sum(float(t["qty"]) for t in group)
                    total_rpnl = sum(float(t["realizedPnl"]) for t in group)
                    avg_exit = sum(float(t["price"]) * float(t["qty"]) for t in group) / total_qty if total_qty else 0
                    exit_time_ms = group[-1]["time"]
                    exit_time = datetime.fromtimestamp(exit_time_ms / 1000, tz=timezone.utc).isoformat()
                    exit_side = group[0]["side"]
                    pos_side = "SHORT" if exit_side == "BUY" else "LONG"

                    # Dedup: skip if already in D1
                    dedup_key = (symbol, exit_time[:16], pos_side)
                    if dedup_key in d1_keys:
                        continue

                    # Find matching entry fills
                    matching = [t for t in entry_fills if t["side"] != exit_side and t["time"] < exit_time_ms]
                    if matching:
                        matching.sort(key=lambda t: t["time"], reverse=True)
                        eq = 0
                        ep_sum = 0
                        entry_time_ms = matching[0]["time"]
                        for t in matching:
                            q = float(t["qty"])
                            eq += q
                            ep_sum += float(t["price"]) * q
                            entry_time_ms = min(entry_time_ms, t["time"])
                            if eq >= total_qty * 0.95:
                                break
                        avg_entry = ep_sum / eq if eq else avg_exit
                        entry_time = datetime.fromtimestamp(entry_time_ms / 1000, tz=timezone.utc).isoformat()
                    else:
                        avg_entry = avg_exit
                        entry_time = exit_time

                    pnl_pct = ((avg_exit - avg_entry) / avg_entry * 100) if pos_side == "LONG" else ((avg_entry - avg_exit) / avg_entry * 100) if avg_entry > 0 else 0
                    commission = sum(float(t.get("commission", 0)) for t in group)
                    net_pnl = total_rpnl - commission
                    exit_reason = "TP_SYNCED" if total_rpnl > 0 else "SL_SYNCED"

                    cfg = configs.get(symbol, BBC_FALLBACK.get(symbol, {}))
                    _log_trade_to_d1(
                        symbol, "1h", pos_side, avg_entry, avg_exit,
                        entry_time, exit_time,
                        cfg.get("sl_pct", 0) * 100, cfg.get("tp_pct", 0) * 100,
                        net_pnl, pnl_pct, exit_reason, acct_name
                    )
                    emoji = "🎯" if "TP" in exit_reason else "🛑"
                    fixes.append(f"📋 {emoji} SYNCED {symbol} {pos_side} {exit_reason} | Entry ${avg_entry:.4f} → Exit ${avg_exit:.4f} | PnL ${net_pnl:+.4f}")
                    _log(f"[MONITOR] 📋 AUTO-SYNCED: {symbol} {pos_side} {exit_reason} PnL=${net_pnl:+.4f}")

            except Exception as e:
                _log(f"[MONITOR] ⚠️ Sync error {symbol}: {e}")
    except Exception as e:
        _log(f"[MONITOR] ❌ Trade sync error: {e}")

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
