"""
BabaBot — Baret Live Trading (Demo)
Predicted range entry: limit orders at predicted extremes + buffer.
Supports: baret (single), baret_dca (L1+L2), baret_marfin (close filter).

Uses Binance Demo API (testnet) for order placement.
Data from OKX (cloud-accessible).
"""

import os
import time
import hmac
import hashlib
import threading
import numpy as np
import requests as req
from datetime import datetime, timezone
from collections import deque
from urllib.parse import urlencode

# ── Config ──
TESTNET_URL = os.environ.get("BINANCE_TESTNET_URL", "https://demo-fapi.binance.com")
TESTNET_KEY = os.environ.get("BINANCE_TESTNET_KEY", "")
TESTNET_SECRET = os.environ.get("BINANCE_TESTNET_SECRET", "")
WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_ID", "888366328")
LEVERAGE = int(os.environ.get("LEVERAGE", "50"))

# ── State ──
_baret_live_running = False
_baret_live_thread = None
_baret_live_log = deque(maxlen=500)
_baret_live_state = {
    "active_pairs": [],
    "positions": {},
    "pending_orders": {},
    "cycle_count": 0,
    "last_cycle": None,
    "mode": "baret",
    "started_at": None,
}

# ── Logging ──
def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _baret_live_log.append(entry)
    print(f"[BaretLive] {entry}")


# ── Exchange API ──
def _sign(params):
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 10000
    qs = urlencode(params)
    sig = hmac.new(TESTNET_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
    return qs + f"&signature={sig}"


def _api_post(path, params):
    headers = {"X-MBX-APIKEY": TESTNET_KEY}
    body = _sign(params)
    r = req.post(f"{TESTNET_URL}{path}", data=body, headers=headers, timeout=10)
    return r.json()


def _api_get(path, params=None, signed=False):
    headers = {"X-MBX-APIKEY": TESTNET_KEY}
    if signed:
        qs = _sign(params or {})
        r = req.get(f"{TESTNET_URL}{path}?{qs}", headers=headers, timeout=10)
    else:
        r = req.get(f"{TESTNET_URL}{path}", params=params, headers=headers, timeout=10)
    return r.json()


def _api_delete(path, params):
    headers = {"X-MBX-APIKEY": TESTNET_KEY}
    body = _sign(params)
    r = req.delete(f"{TESTNET_URL}{path}?{body}", headers=headers, timeout=10)
    return r.json()


def _set_leverage(symbol):
    try:
        _api_post("/fapi/v1/leverage", {"symbol": symbol, "leverage": LEVERAGE})
    except:
        pass


def _place_limit_order(symbol, side, price, qty):
    """Place a limit order. Returns order dict with orderId."""
    try:
        result = _api_post("/fapi/v1/order", {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "price": f"{price:.6f}",
            "quantity": f"{qty:.4f}",
            "timeInForce": "GTC",
        })
        if "orderId" in result:
            _log(f"  📋 Limit {side} {symbol} @ ${price:.4f} qty={qty:.4f} → orderId={result['orderId']}")
        else:
            _log(f"  ❌ Limit order failed: {result.get('msg', result)}")
        return result
    except Exception as e:
        _log(f"  ❌ Order error: {e}")
        return {"error": str(e)}


def _place_market_close(symbol, side, qty):
    """Close position with market order."""
    try:
        close_side = "SELL" if side == "BUY" else "BUY"
        result = _api_post("/fapi/v1/order", {
            "symbol": symbol,
            "side": close_side,
            "type": "MARKET",
            "quantity": f"{qty:.4f}",
        })
        return result
    except Exception as e:
        return {"error": str(e)}


def _place_sl_tp(symbol, side, sl_price, tp_price):
    """Place SL and TP orders for an open position."""
    close_side = "SELL" if side == "BUY" else "BUY"
    results = {}
    try:
        results["sl"] = _api_post("/fapi/v1/order", {
            "symbol": symbol, "side": close_side,
            "type": "STOP_MARKET",
            "stopPrice": f"{sl_price:.6f}",
            "closePosition": "true",
        })
    except Exception as e:
        results["sl"] = {"error": str(e)}
    try:
        results["tp"] = _api_post("/fapi/v1/order", {
            "symbol": symbol, "side": close_side,
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": f"{tp_price:.6f}",
            "closePosition": "true",
        })
    except Exception as e:
        results["tp"] = {"error": str(e)}
    return results


def _cancel_order(symbol, order_id):
    try:
        return _api_delete("/fapi/v1/order", {"symbol": symbol, "orderId": order_id})
    except:
        return {}


def _cancel_all_orders(symbol):
    try:
        return _api_delete("/fapi/v1/allOpenOrders", {"symbol": symbol})
    except:
        return {}


def _get_open_orders(symbol):
    try:
        return _api_get("/fapi/v1/openOrders", {"symbol": symbol}, signed=True)
    except:
        return []


def _get_position(symbol):
    try:
        positions = _api_get("/fapi/v2/positionRisk", signed=True)
        for p in positions:
            if p["symbol"] == symbol and float(p.get("positionAmt", 0)) != 0:
                return p
    except:
        pass
    return None


# ── OKX Data ──
OKX_TF_MAP = {"4h": "4H", "1h": "1H"}

def _fetch_candles(symbol, tf="4h", limit=15):
    """Fetch candles from OKX."""
    inst = symbol.replace("USDT", "-USDT-SWAP")
    bar = OKX_TF_MAP.get(tf, "4H")
    try:
        r = req.get("https://www.okx.com/api/v5/market/candles",
                     params={"instId": inst, "bar": bar, "limit": limit}, timeout=10)
        data = r.json().get("data", [])
        candles = []
        for c in reversed(data):
            candles.append({
                "open": float(c[1]), "high": float(c[2]),
                "low": float(c[3]), "close": float(c[4]),
                "time": int(c[0]),
            })
        return candles
    except Exception as e:
        _log(f"  ❌ OKX fetch error: {e}")
        return []


def _get_price(symbol):
    """Get current price from OKX."""
    inst = symbol.replace("USDT", "-USDT-SWAP")
    try:
        r = req.get("https://www.okx.com/api/v5/market/ticker",
                     params={"instId": inst}, timeout=5)
        return float(r.json()["data"][0]["last"])
    except:
        return 0


# ── Predicted Range Calculation ──
def _calculate_predicted_range(candles, window=10):
    """Calculate predicted high/low/close for next candle using Deret Statistik."""
    if len(candles) < window + 1:
        return None

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    h_ratios = [highs[i] / highs[i-1] for i in range(1, len(highs)) if highs[i-1] > 0]
    l_ratios = [lows[i] / lows[i-1] for i in range(1, len(lows)) if lows[i-1] > 0]
    c_ratios = [closes[i] / closes[i-1] for i in range(1, len(closes)) if closes[i-1] > 0]

    if len(h_ratios) < window:
        return None

    avg_h = sum(h_ratios[-window:]) / window
    avg_l = sum(l_ratios[-window:]) / window
    avg_c = sum(c_ratios[-window:]) / window

    return {
        "pred_high": highs[-1] * avg_h,
        "pred_low": lows[-1] * avg_l,
        "pred_close": closes[-1] * avg_c,
        "current_price": closes[-1],
    }


# ── Baret Config from D1 (same source as Dashboard recommendations) ──
def _fetch_baret_configs(mode="baret", min_wr=75.0, max_dd=20.0, min_ppd=0.0):
    """Fetch best config per pair from D1, applying same filters as Dashboard."""
    try:
        r = req.get(f"{WORKER_URL}/baret/results?mode={mode}", timeout=15)
        results = r.json().get("results", [])
    except:
        _log("⚠️ Failed to fetch configs from D1, using fallback")
        results = []

    if not results:
        _log("⚠️ No D1 data, using fallback defaults")
        return [
            {"symbol": "SOLUSDT", "buffer_pct": 0.8, "tp_pct": 1.5, "sl_pct": 0.3, "window": 10, "buffer2_pct": 1.0, "close_filter_pct": 0.3},
            {"symbol": "AVAXUSDT", "buffer_pct": 0.8, "tp_pct": 1.5, "sl_pct": 0.3, "window": 10, "buffer2_pct": 1.0, "close_filter_pct": 0.3},
            {"symbol": "DOGEUSDT", "buffer_pct": 1.0, "tp_pct": 1.5, "sl_pct": 0.3, "window": 10, "buffer2_pct": 1.0, "close_filter_pct": 0.3},
        ]

    # Filter by user criteria (same as Dashboard)
    filtered = [r for r in results if 
        r["win_rate"] >= min_wr and 
        r["max_drawdown"] <= max_dd and
        r["profit_per_day"] >= min_ppd
    ]

    # Pick best per pair (highest profit/day that passes filter)
    best = {}
    for r in filtered:
        pair = r["symbol"]
        if pair not in best or r["profit_per_day"] > best[pair]["profit_per_day"]:
            best[pair] = r

    configs = []
    for pair, r in sorted(best.items(), key=lambda x: -x[1]["profit_per_day"]):
        configs.append({
            "symbol": pair,
            "buffer_pct": r.get("buffer1_pct", 0.8),
            "tp_pct": r.get("tp_pct", 1.5),
            "sl_pct": r.get("sl_pct", 0.3),
            "window": r.get("window", 10),
            "buffer2_pct": r.get("buffer2_pct", 1.0),
            "close_filter_pct": r.get("close_filter_pct", 0.3),
            "win_rate": r.get("win_rate", 0),
            "profit_per_day": r.get("profit_per_day", 0),
            "max_drawdown": r.get("max_drawdown", 0),
        })
        _log(f"  📋 {pair}: buf={r.get('buffer1_pct')}% TP={r.get('tp_pct')}% SL={r.get('sl_pct')}% WR={r.get('win_rate'):.1f}% DD={r.get('max_drawdown'):.1f}%")

    _log(f"  📊 {len(configs)} pairs loaded from D1 (WR≥{min_wr}% DD≤{max_dd}%)")
    return configs


# ── Quantity Calculation ──
def _calc_quantity(symbol, price, position_usd=10.0):
    """Calculate order quantity based on position size and price."""
    notional = position_usd * LEVERAGE
    qty = notional / price
    # Round to appropriate decimals based on pair
    if "BTC" in symbol:
        return round(qty, 3)
    elif "ETH" in symbol:
        return round(qty, 3)
    else:
        return round(qty, 1)


# ── Telegram ──
def _send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        req.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                 json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass


# ── Main Trading Loop ──
def _baret_live_loop(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0, min_ppd=0.0):
    """Main Baret live trading loop. Runs every 4h candle cycle."""
    global _baret_live_running, _baret_live_state

    if not TESTNET_KEY or not TESTNET_SECRET:
        _log("❌ BINANCE_TESTNET_KEY/SECRET not set. Cannot trade.")
        _baret_live_running = False
        return

    _baret_live_state["mode"] = mode
    _baret_live_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _baret_live_state["filters"] = {"min_wr": min_wr, "max_dd": max_dd, "min_ppd": min_ppd}
    configs = _fetch_baret_configs(mode=mode, min_wr=min_wr, max_dd=max_dd, min_ppd=min_ppd)
    _baret_live_state["active_pairs"] = [c["symbol"] for c in configs]

    _log(f"═══ BARET LIVE STARTED ═══ mode={mode}, {len(configs)} pairs, ${position_usd}/trade")
    _send_telegram(f"📐 *BARET LIVE STARTED*\nMode: {mode}\nPairs: {', '.join(c['symbol'] for c in configs)}\nPosition: ${position_usd}")

    # Set leverage for all pairs
    for cfg in configs:
        _set_leverage(cfg["symbol"])

    cycle = 0
    while _baret_live_running:
        cycle += 1
        _baret_live_state["cycle_count"] = cycle
        _baret_live_state["last_cycle"] = datetime.now(timezone.utc).isoformat()

        _log(f"═══ CYCLE {cycle} ═══")

        for cfg in configs:
            if not _baret_live_running:
                break

            symbol = cfg["symbol"]
            buffer_pct = cfg["buffer_pct"]
            tp_pct = cfg["tp_pct"]
            sl_pct = cfg["sl_pct"]
            window = cfg.get("window", 10)

            try:
                # 1. Cancel any existing open orders for this pair
                _cancel_all_orders(symbol)

                # 2. Check if already in position
                pos = _get_position(symbol)
                if pos:
                    _log(f"  ⏩ {symbol}: already in position ({pos.get('positionSide','?')} {pos.get('positionAmt','?')}), skipping")
                    continue

                # 3. Fetch candles + calculate predicted range
                candles = _fetch_candles(symbol, "4h", window + 5)
                if not candles:
                    _log(f"  ⚠️ {symbol}: no candle data")
                    continue

                pred = _calculate_predicted_range(candles, window)
                if not pred:
                    _log(f"  ⚠️ {symbol}: insufficient data for prediction")
                    continue

                pred_high = pred["pred_high"]
                pred_low = pred["pred_low"]
                pred_close = pred["pred_close"]
                current = pred["current_price"]

                # 4. Close filter (baret_marfin mode)
                if mode == "baret_marfin":
                    close_filter = cfg.get("close_filter_pct", 0.3)
                    close_gap_long = (pred_close - pred_low) / pred_low * 100 if pred_low > 0 else 0
                    close_gap_short = (pred_high - pred_close) / pred_high * 100 if pred_high > 0 else 0
                    if close_gap_long < close_filter and close_gap_short < close_filter:
                        _log(f"  ⏩ {symbol}: close filter skip (gap L={close_gap_long:.2f}% S={close_gap_short:.2f}% < {close_filter}%)")
                        continue

                # 5. Calculate entry levels
                long_entry = pred_low * (1 - buffer_pct / 100)
                short_entry = pred_high * (1 + buffer_pct / 100)

                qty = _calc_quantity(symbol, current, position_usd)

                _log(f"  📐 {symbol}: pred_range ${pred_low:.4f}-${pred_high:.4f}, current=${current:.4f}")
                _log(f"     LONG entry=${long_entry:.4f}, SHORT entry=${short_entry:.4f}, qty={qty}")

                # 6. Place limit orders (both sides)
                long_order = _place_limit_order(symbol, "BUY", long_entry, qty)
                short_order = _place_limit_order(symbol, "SELL", short_entry, qty)

                # Track pending orders
                _baret_live_state["pending_orders"][symbol] = {
                    "long_id": long_order.get("orderId"),
                    "short_id": short_order.get("orderId"),
                    "long_entry": long_entry,
                    "short_entry": short_entry,
                    "tp_pct": tp_pct,
                    "sl_pct": sl_pct,
                    "qty": qty,
                    "placed_at": datetime.now(timezone.utc).isoformat(),
                }

                # 7. DCA: place L2 orders (baret_dca mode)
                if mode == "baret_dca":
                    buf2 = cfg.get("buffer2_pct", 1.0)
                    long_l2 = long_entry * (1 - buf2 / 100)
                    short_l2 = short_entry * (1 + buf2 / 100)
                    _place_limit_order(symbol, "BUY", long_l2, qty)
                    _place_limit_order(symbol, "SELL", short_l2, qty)
                    _log(f"     DCA L2: LONG=${long_l2:.4f}, SHORT=${short_l2:.4f}")

            except Exception as e:
                _log(f"  ❌ {symbol} error: {e}")

        # 8. Monitor fills for 4 hours (check every 30s)
        _log(f"  ⏳ Monitoring fills for 4h (check every 30s)...")
        checks = 0
        max_checks = 480  # 4h × 60min × 2 checks/min = 480
        
        while _baret_live_running and checks < max_checks:
            time.sleep(30)
            checks += 1

            for cfg in configs:
                if not _baret_live_running:
                    break
                symbol = cfg["symbol"]
                pending = _baret_live_state["pending_orders"].get(symbol)
                if not pending:
                    continue

                # Check if position opened (order filled)
                pos = _get_position(symbol)
                if pos and float(pos.get("positionAmt", 0)) != 0:
                    amt = float(pos["positionAmt"])
                    entry_price = float(pos.get("entryPrice", 0))
                    side = "LONG" if amt > 0 else "SHORT"

                    # Cancel remaining orders
                    _cancel_all_orders(symbol)

                    # Calculate TP/SL from entry
                    if side == "LONG":
                        tp_price = entry_price * (1 + pending["tp_pct"] / 100)
                        sl_price = entry_price * (1 - pending["sl_pct"] / 100)
                    else:
                        tp_price = entry_price * (1 - pending["tp_pct"] / 100)
                        sl_price = entry_price * (1 + pending["sl_pct"] / 100)

                    order_side = "BUY" if amt > 0 else "SELL"
                    _place_sl_tp(symbol, order_side, sl_price, tp_price)

                    _log(f"  ✅ {symbol} {side} FILLED @ ${entry_price:.4f} → TP=${tp_price:.4f} SL=${sl_price:.4f}")
                    _send_telegram(f"📐 *BARET ENTRY*\n{symbol} {side} @ ${entry_price:.4f}\nTP: ${tp_price:.4f}\nSL: ${sl_price:.4f}")

                    # Save trade to D1
                    try:
                        req.post(f"{WORKER_URL}/bot/trade-log", json={
                            "symbol": symbol, "side": side, "entry_price": entry_price,
                            "tp_price": tp_price, "sl_price": sl_price,
                            "source": f"baret_{mode}", "status": "open",
                        }, timeout=10)
                    except:
                        pass

                    # Remove from pending
                    del _baret_live_state["pending_orders"][symbol]
                    _baret_live_state["positions"][symbol] = {
                        "side": side, "entry": entry_price,
                        "tp": tp_price, "sl": sl_price,
                    }

            # Log progress every 5 minutes
            if checks % 10 == 0:
                pending_count = len(_baret_live_state["pending_orders"])
                pos_count = len(_baret_live_state["positions"])
                _log(f"  ⏳ Check {checks}/{max_checks} — {pending_count} pending, {pos_count} positions")

        # 9. End of candle: cancel all unfilled orders
        for cfg in configs:
            symbol = cfg["symbol"]
            if symbol in _baret_live_state["pending_orders"]:
                _cancel_all_orders(symbol)
                _log(f"  🗑 {symbol}: unfilled orders cancelled (candle close)")
                del _baret_live_state["pending_orders"][symbol]

        # Check positions that closed (TP/SL hit)
        for symbol in list(_baret_live_state["positions"].keys()):
            pos = _get_position(symbol)
            if not pos or float(pos.get("positionAmt", 0)) == 0:
                saved = _baret_live_state["positions"].pop(symbol)
                _log(f"  📊 {symbol}: position closed (TP/SL hit)")

        _log(f"═══ CYCLE {cycle} DONE ═══ Next cycle in 10s")
        time.sleep(10)

    _log("═══ BARET LIVE STOPPED ═══")
    _baret_live_running = False


# ── Public API ──

def start_baret_live(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0, min_ppd=0.0):
    global _baret_live_running, _baret_live_thread
    if _baret_live_running:
        return {"ok": True, "message": "Already running", "state": _baret_live_state}
    _baret_live_running = True
    _baret_live_thread = threading.Thread(
        target=_baret_live_loop, args=(mode, position_usd, min_wr, max_dd, min_ppd), daemon=True
    )
    _baret_live_thread.start()
    return {"ok": True, "message": f"Baret live started, mode={mode}, ${position_usd}/trade, WR≥{min_wr}% DD≤{max_dd}%"}


def stop_baret_live():
    global _baret_live_running
    _baret_live_running = False
    return {"ok": True, "message": "Baret live stopped"}


def baret_live_status():
    return {
        "ok": True,
        "running": _baret_live_running,
        "thread_alive": _baret_live_thread.is_alive() if _baret_live_thread else False,
        **_baret_live_state,
    }


def get_baret_live_log(limit=200):
    return list(_baret_live_log)[-limit:]
