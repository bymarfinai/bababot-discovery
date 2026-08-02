"""
BBC Live Trading Endpoints — FastAPI router for BBC live control.

v2.1: Per-pair configs loaded FULLY from D1 (ema, body ratios, TP, SL).
      Account status returns full pair states + positions.
"""

import os
import threading
import traceback
from datetime import datetime, timezone
import requests as req
from fastapi import APIRouter

from bbc_live import start_bbc_live, stop_bbc_live, bbc_live_status, _bbc_live_loop
from bbc_account_monitor import start_monitor, stop_monitor
from baret_live import (
    ExchangeClient, _log, _send_telegram, _cancel_sl_tp,
    _get_default_client, _account_bots, close_position, close_all_positions,
    WORKER_URL,
)

# Fix: BBC trades logged with 'bbc_live_' notes prefix (not 'baret_live_')
import bbc_live as _bbc_mod
from bbc_trade_logger import _log_trade_to_d1 as _bbc_logger
_bbc_mod._log_trade_to_d1 = _bbc_logger

router = APIRouter()

BBC_FALLBACK = {
    "SOLUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.7},
    "ETHUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.5, "bear_body_ratio_min": 0.6},
    "BNBUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.020, "bull_body_ratio_min": 0.6, "bear_body_ratio_min": 0.7},
    "DOGEUSDT": {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.015, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.5},
    "BTCUSDT":  {"ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.013, "bull_body_ratio_min": 0.7, "bear_body_ratio_min": 0.7},
}


def _fetch_bbc_configs_from_d1():
    config_overrides = {}
    try:
        r = req.get(f"{WORKER_URL}/custom-configs/list?live_only=true", timeout=15)
        all_configs = r.json().get("configs", [])
        bbc_configs = [c for c in all_configs if c.get("mode") == "bbc"]
    except Exception as e:
        _log(f"[BBC] ⚠️ Failed to fetch D1 configs: {e}, using fallback")
        return dict(BBC_FALLBACK)
    if not bbc_configs:
        _log("[BBC] ⚠️ No BBC configs in D1, using fallback defaults")
        return dict(BBC_FALLBACK)
    for c in bbc_configs:
        symbol = c["symbol"]
        fallback = BBC_FALLBACK.get(symbol, {"ema_period": 7, "bull_body_ratio_min": 0.5, "bear_body_ratio_min": 0.6, "tp_pct": 0.013, "sl_pct": 0.015})
        tp_raw = float(c["tp_pct"]) if c.get("tp_pct") is not None else None
        sl_raw = float(c["sl_pct"]) if c.get("sl_pct") is not None else None
        config_overrides[symbol] = {
            "ema_period": int(c["ema_period"]) if c.get("ema_period") else fallback["ema_period"],
            "tp_pct": round(tp_raw / 100, 6) if tp_raw and tp_raw > 0.1 else (tp_raw or fallback["tp_pct"]),
            "sl_pct": round(sl_raw / 100, 6) if sl_raw and sl_raw > 0.1 else (sl_raw or fallback["sl_pct"]),
            "bull_body_ratio_min": float(c["bull_body_ratio_min"]) if c.get("bull_body_ratio_min") is not None else fallback["bull_body_ratio_min"],
            "bear_body_ratio_min": float(c["bear_body_ratio_min"]) if c.get("bear_body_ratio_min") is not None else fallback["bear_body_ratio_min"],
        }
        cfg = config_overrides[symbol]
        _log(f"[BBC] 📋 {symbol}: EMA={cfg['ema_period']} TP={cfg['tp_pct']*100:.1f}% SL={cfg['sl_pct']*100:.1f}% "
             f"BullBody={cfg['bull_body_ratio_min']} BearBody={cfg['bear_body_ratio_min']}")
    _log(f"[BBC] 📊 {len(config_overrides)} pair configs loaded from D1")
    return config_overrides


@router.get("/bbc-live/start")
def bbc_live_start(position_usd: float = 1.0, leverage: int = 50):
    config_overrides = _fetch_bbc_configs_from_d1()
    symbols = list(config_overrides.keys())
    return start_bbc_live(symbols=symbols, timeframe="1h",
        position_usd=position_usd, leverage=leverage, config_overrides=config_overrides)

@router.get("/bbc-live/stop")
def bbc_live_stop():
    return stop_bbc_live()

@router.get("/bbc-live/status")
def bbc_live_status_endpoint():
    return bbc_live_status()


# ══════════════════════════════════════════════
# MULTI-ACCOUNT BBC
# ══════════════════════════════════════════════

_bbc_account_bots = {}


def _bbc_account_loop(account_id, client, account_info):
    bot = _bbc_account_bots.get(account_id)
    if not bot: return
    acct_name = account_info.get("name", f"BBC-{account_id}")
    position_usd = account_info.get("position_usd", 1)
    leverage = account_info.get("leverage", 50)
    client.leverage = leverage
    config_overrides = _fetch_bbc_configs_from_d1()
    symbols = list(config_overrides.keys()) if config_overrides else ["SOLUSDT", "ETHUSDT", "BTCUSDT", "BNBUSDT"]
    try:
        _bbc_live_loop(symbols=symbols, timeframe="1h",
            position_usd=position_usd, leverage=leverage,
            config_overrides=config_overrides,
            client=client, state=bot["state"],
            running_check=lambda: bot["running"], acct_name=acct_name)
    except Exception as e:
        _log(f"[{acct_name}] ❌ BBC CRASH: {e}")
        _log(f"[{acct_name}] {traceback.format_exc()}")
    bot["running"] = False


@router.get("/bbc-live/start-account")
def bbc_live_start_account(account_id: int = 0):
    if account_id in _bbc_account_bots and _bbc_account_bots[account_id].get("running"):
        return {"ok": True, "message": f"BBC account {account_id} already running"}
    try:
        r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
        accounts = r.json().get("accounts", [])
        account = next((a for a in accounts if a["id"] == account_id), None)
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch account: {e}"}
    if not account:
        return {"ok": False, "error": f"Account {account_id} not found"}
    api_key = os.environ.get(account["env_key_name"], "")
    api_secret = os.environ.get(account["env_secret_name"], "")
    if not api_key or not api_secret:
        return {"ok": False, "error": f"API keys not found: {account['env_key_name']}"}
    client = ExchangeClient(account["base_url"], api_key, api_secret, account.get("leverage", 50))
    bot_state = {"mode": "bbc", "pairs": {}, "cycle_count": 0, "last_cycle": None,
        "started_at": None, "active_pairs": [], "positions": {}, "error": None}
    _bbc_account_bots[account_id] = {
        "running": True, "state": bot_state, "client": client, "account": account, "thread": None}
    t = threading.Thread(target=_bbc_account_loop, args=(account_id, client, account), daemon=True)
    _bbc_account_bots[account_id]["thread"] = t
    t.start()
    # Start background health monitor
    acct_name = account.get("name", f"BBC-{account_id}")
    start_monitor(account_id, client, acct_name, lambda: _bbc_account_bots.get(account_id))
    return {"ok": True, "message": f"BBC started for '{acct_name}', ${account.get('position_usd', 1)}×{account.get('leverage', 50)}x (monitor ON)"}


@router.get("/bbc-live/stop-account")
def bbc_live_stop_account(account_id: int = 0):
    bot = _bbc_account_bots.get(account_id)
    if not bot or not bot.get("running"):
        return {"ok": True, "message": f"BBC account {account_id} not running"}
    bot["running"] = False
    stop_monitor(account_id)
    _log(f"[BBC-{account_id}] Stop signal sent")
    return {"ok": True, "message": f"BBC account {account_id} stopping... (monitor OFF)"}


@router.get("/bbc-live/account-status")
def bbc_live_account_status(account_id: int = None):
    """Get BBC account status with FULL pair states and positions."""
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if not bot:
            return {"ok": True, "running": False, "account_id": account_id}
        return {"ok": True, "account_id": account_id, "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "state": bot["state"], "account_name": bot["account"].get("name", "")}

    # ALL accounts — include full state with pair info
    result = {}
    for aid, bot in _bbc_account_bots.items():
        state = bot["state"]
        # Extract pair states for dashboard
        pair_states = {}
        for sym, ps in state.get("pairs", {}).items():
            if hasattr(ps, "switcher"):
                pair_states[sym] = {
                    "state": ps.switcher.state if ps.switcher else "—",
                    "position": {
                        "side": ps.switcher.position.side,
                        "entry_price": ps.switcher.position.entry_price,
                        "tool": ps.switcher.position.tool,
                    } if ps.switcher and ps.switcher.position else None,
                }
            elif isinstance(ps, dict):
                pair_states[sym] = ps
            else:
                pair_states[sym] = {"state": "—", "position": None}

        result[aid] = {
            "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "account_name": bot["account"].get("name", ""),
            "pairs": bot["state"].get("active_pairs", []),
            "pair_states": pair_states,
            "cycle": state.get("cycle_count", 0),
            "positions": state.get("positions", {}),
            "position_count": len(state.get("positions", {})),
        }
    return {"ok": True, "accounts": result}


@router.get("/bbc-live/configs")
def bbc_live_configs():
    d1_configs = _fetch_bbc_configs_from_d1()
    return {"ok": True, "configs": {sym: {"active": cfg, "recommended": BBC_FALLBACK.get(sym, {}),
        "match": cfg == BBC_FALLBACK.get(sym) if sym in BBC_FALLBACK else None}
        for sym, cfg in d1_configs.items()}}

@router.post("/bbc-live/close")
def bbc_close_position(symbol: str = None, account_id: int = None):
    client = None
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if bot: client = bot.get("client")
    if symbol: return close_position(symbol, client=client)
    return close_all_positions(client=client)

@router.post("/bbc-live/close-all")
def bbc_close_all(account_id: int = None):
    client = None
    if account_id is not None:
        bot = _bbc_account_bots.get(account_id)
        if bot: client = bot.get("client")
    return close_all_positions(client=client)


def _get_client_for_account(account_id):
    """Get or create ExchangeClient for an account. Returns (client, acct_name) or raises."""
    bot = _bbc_account_bots.get(account_id)
    if bot and bot.get("client"):
        return bot["client"], bot["account"].get("name", f"Account-{account_id}")
    r = req.get(f"{WORKER_URL}/trading-accounts/list", timeout=10)
    accounts = r.json().get("accounts", [])
    account = next((a for a in accounts if a["id"] == account_id), None)
    if not account:
        raise ValueError(f"Account {account_id} not found")
    api_key = os.environ.get(account["env_key_name"], "")
    api_secret = os.environ.get(account["env_secret_name"], "")
    if not api_key or not api_secret:
        raise ValueError(f"API keys not found: {account['env_key_name']}")
    client = ExchangeClient(account["base_url"], api_key, api_secret, account.get("leverage", 50))
    return client, account.get("name", f"Account-{account_id}")


@router.get("/bbc-live/account-health")
def bbc_account_health(account_id: int = 0):
    """Full account health check: positions, SL/TP orders, balance, cross-check with bot state."""
    try:
        client, acct_name = _get_client_for_account(account_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # 1. All open positions from exchange
    positions = client.get_all_positions()
    position_list = []
    for p in positions:
        symbol = p["symbol"]
        amt = float(p.get("positionAmt", 0))
        entry = float(p.get("entryPrice", 0))
        mark = float(p.get("markPrice", 0))
        unrealized_pnl = float(p.get("unRealizedProfit", 0))
        leverage = int(p.get("leverage", 0))
        liq_price = float(p.get("liquidationPrice", 0))
        side = "LONG" if amt > 0 else "SHORT"

        # Check if this position has SL/TP algo orders
        algo_orders = client.get_open_algo_orders(symbol)
        has_sl = False
        has_tp = False
        sl_price = None
        tp_price = None
        if isinstance(algo_orders, dict):
            algo_orders = algo_orders.get("orders", [])
        if isinstance(algo_orders, list):
            for ao in algo_orders:
                if ao.get("type") == "STOP_MARKET":
                    has_sl = True
                    sl_price = float(ao.get("triggerPrice", 0))
                elif ao.get("type") == "TAKE_PROFIT_MARKET":
                    has_tp = True
                    tp_price = float(ao.get("triggerPrice", 0))

        # Check if bot is tracking this position
        bot = _bbc_account_bots.get(account_id)
        bot_tracking = False
        if bot and bot.get("state"):
            bot_positions = bot["state"].get("positions", {})
            bot_tracking = symbol in bot_positions

        warnings = []
        if not has_sl:
            warnings.append("NO_SL")
        if not has_tp:
            warnings.append("NO_TP")
        if not bot_tracking:
            warnings.append("NOT_TRACKED_BY_BOT")

        position_list.append({
            "symbol": symbol,
            "side": side,
            "size": abs(amt),
            "entry_price": entry,
            "mark_price": mark,
            "unrealized_pnl": round(unrealized_pnl, 4),
            "leverage": leverage,
            "liquidation_price": liq_price,
            "has_sl": has_sl, "sl_price": sl_price,
            "has_tp": has_tp, "tp_price": tp_price,
            "bot_tracking": bot_tracking,
            "warnings": warnings if warnings else None,
        })

    # 2. Account balance
    balance_info = {}
    try:
        balances = client.api_get("/fapi/v2/balance", signed=True)
        if isinstance(balances, list):
            usdt = next((b for b in balances if b["asset"] == "USDT"), None)
            if usdt:
                balance_info = {
                    "total": round(float(usdt.get("balance", 0)), 4),
                    "available": round(float(usdt.get("availableBalance", 0)), 4),
                    "unrealized_pnl": round(float(usdt.get("crossUnPnl", 0)), 4),
                }
    except Exception:
        pass

    # 3. Recent trade history from exchange (last 24h)
    recent_pnl = 0
    recent_trades_count = 0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    lookback_24h = 24 * 60 * 60 * 1000
    for symbol in list(BBC_FALLBACK.keys()):
        try:
            trades = client.api_get("/fapi/v1/userTrades", {
                "symbol": symbol,
                "startTime": now_ms - lookback_24h,
                "limit": 100,
            }, signed=True)
            if isinstance(trades, list):
                for t in trades:
                    rpnl = float(t.get("realizedPnl", 0))
                    commission = float(t.get("commission", 0))
                    recent_pnl += rpnl - commission
                    if abs(rpnl) > 0.0001:
                        recent_trades_count += 1
        except Exception:
            pass

    # 4. Cross-check with D1 trade log
    d1_mismatch = []
    try:
        r = req.get(f"{WORKER_URL}/bot/trade-log?period=24h", timeout=10)
        d1_trades = r.json().get("trades", [])
        d1_count = len([t for t in d1_trades if acct_name in (t.get("notes") or "")])
        if recent_trades_count > 0 and d1_count < recent_trades_count:
            d1_mismatch.append(f"Exchange has {recent_trades_count} exits in 24h but D1 only has {d1_count} for {acct_name}")
    except Exception:
        pass

    return {
        "ok": True,
        "account": acct_name,
        "account_id": account_id,
        "balance": balance_info,
        "positions": position_list,
        "position_count": len(position_list),
        "pnl_24h": round(recent_pnl, 4),
        "exits_24h": recent_trades_count,
        "d1_warnings": d1_mismatch if d1_mismatch else None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/bbc-live/sync-trades")
def bbc_sync_trades(account_id: int = 0, days: int = 7):
    """Pull trade history from Binance, cross-check with D1, log any missing trades."""
    try:
        client, acct_name = _get_client_for_account(account_id)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    # Get existing D1 trades for dedup
    try:
        r = req.get(f"{WORKER_URL}/bot/trade-log?period={'30d' if days <= 30 else 'all'}", timeout=15)
        d1_trades = r.json().get("trades", [])
    except Exception:
        d1_trades = []

    # Build set of existing trades for matching (entry_time + symbol + side)
    existing = set()
    for t in d1_trades:
        key = (t.get("symbol", ""), t.get("side", ""), t.get("entry_price", 0))
        existing.add(key)

    symbols = list(BBC_FALLBACK.keys())
    lookback_ms = days * 24 * 60 * 60 * 1000
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    synced = []
    errors = []

    for symbol in symbols:
        try:
            trades = client.api_get("/fapi/v1/userTrades", {
                "symbol": symbol,
                "startTime": now_ms - lookback_ms,
                "limit": 500,
            }, signed=True)

            if not isinstance(trades, list) or not trades:
                continue

            entry_fills = []
            exit_fills = []
            for t in trades:
                rpnl = float(t.get("realizedPnl", 0))
                if abs(rpnl) > 0.0001:
                    exit_fills.append(t)
                else:
                    entry_fills.append(t)

            if not exit_fills:
                continue

            # Group exit fills by time proximity (within 2s = same exit)
            exit_groups = []
            current_group = [exit_fills[0]]
            for i in range(1, len(exit_fills)):
                if exit_fills[i]["time"] - exit_fills[i - 1]["time"] < 2000:
                    current_group.append(exit_fills[i])
                else:
                    exit_groups.append(current_group)
                    current_group = [exit_fills[i]]
            exit_groups.append(current_group)

            for group in exit_groups:
                total_qty = sum(float(t["qty"]) for t in group)
                total_rpnl = sum(float(t["realizedPnl"]) for t in group)
                avg_exit_price = sum(float(t["price"]) * float(t["qty"]) for t in group) / total_qty if total_qty > 0 else 0
                exit_time_ms = group[-1]["time"]
                exit_time = datetime.fromtimestamp(exit_time_ms / 1000, tz=timezone.utc).isoformat()

                exit_side = group[0]["side"]
                position_side = "SHORT" if exit_side == "BUY" else "LONG"

                # Find matching entries
                matching_entries = [t for t in entry_fills
                                    if t["side"] != exit_side and t["time"] < exit_time_ms]
                if matching_entries:
                    matching_entries.sort(key=lambda t: t["time"], reverse=True)
                    entry_qty = 0
                    entry_price_sum = 0
                    entry_time_ms = matching_entries[0]["time"]
                    for t in matching_entries:
                        q = float(t["qty"])
                        entry_qty += q
                        entry_price_sum += float(t["price"]) * q
                        entry_time_ms = min(entry_time_ms, t["time"])
                        if entry_qty >= total_qty * 0.95:
                            break
                    avg_entry_price = entry_price_sum / entry_qty if entry_qty > 0 else avg_exit_price
                    entry_time = datetime.fromtimestamp(entry_time_ms / 1000, tz=timezone.utc).isoformat()
                else:
                    avg_entry_price = avg_exit_price
                    entry_time = exit_time

                # Check if already in D1
                dedup_key = (symbol, position_side, round(avg_entry_price, 2))
                already_logged = dedup_key in existing

                if position_side == "LONG":
                    pnl_pct = (avg_exit_price - avg_entry_price) / avg_entry_price * 100
                else:
                    pnl_pct = (avg_entry_price - avg_exit_price) / avg_entry_price * 100

                commission = sum(float(t.get("commission", 0)) for t in group)
                net_pnl = total_rpnl - commission
                exit_reason = "TP" if total_rpnl > 0 else "SL"

                trade_record = {
                    "symbol": symbol, "side": position_side,
                    "entry_price": round(avg_entry_price, 4),
                    "exit_price": round(avg_exit_price, 4),
                    "entry_time": entry_time, "exit_time": exit_time,
                    "pnl_dollar": round(net_pnl, 4), "pnl_pct": round(pnl_pct, 2),
                    "exit_reason": exit_reason, "already_in_d1": already_logged,
                }

                if not already_logged:
                    from bbc_trade_logger import _log_trade_to_d1
                    _log_trade_to_d1(
                        symbol, "1h", position_side,
                        avg_entry_price, avg_exit_price,
                        entry_time, exit_time,
                        0, 0, net_pnl, pnl_pct,
                        f"{exit_reason}_SYNCED", acct_name,
                    )
                    trade_record["action"] = "SYNCED_TO_D1"
                else:
                    trade_record["action"] = "ALREADY_EXISTS"

                synced.append(trade_record)

        except Exception as e:
            errors.append({"symbol": symbol, "error": str(e)})

    new_count = sum(1 for t in synced if t["action"] == "SYNCED_TO_D1")
    existing_count = sum(1 for t in synced if t["action"] == "ALREADY_EXISTS")

    return {
        "ok": True,
        "account": acct_name,
        "days_scanned": days,
        "total_exchange_trades": len(synced),
        "already_in_d1": existing_count,
        "newly_synced": new_count,
        "trades": synced,
        "errors": errors if errors else None,
    }
