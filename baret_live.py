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


# ── Symbol Precision Rules (Binance Futures) ──
PRECISION = {
    "BTCUSDT":       {"price": 1, "qty": 3},
    "ETHUSDT":       {"price": 2, "qty": 3},
    "SOLUSDT":       {"price": 2, "qty": 1},
    "AVAXUSDT":      {"price": 3, "qty": 0},
    "DOGEUSDT":      {"price": 5, "qty": 0},
    "XRPUSDT":       {"price": 4, "qty": 1},
    "LINKUSDT":      {"price": 3, "qty": 1},
    "1000PEPEUSDT":  {"price": 7, "qty": 0},
}

def _fmt_price(symbol, price):
    d = PRECISION.get(symbol, {"price": 4})["price"]
    return f"{price:.{d}f}"

def _fmt_qty(symbol, qty):
    d = PRECISION.get(symbol, {"qty": 1})["qty"]
    return f"{qty:.{d}f}"
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
            "price": _fmt_price(symbol, price),
            "quantity": _fmt_qty(symbol, qty),
            "timeInForce": "GTC",
        })
        if "orderId" in result:
            _log(f"  📋 Limit {side} {symbol} @ ${_fmt_price(symbol, price)} qty={_fmt_qty(symbol, qty)} → orderId={result['orderId']}")
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
            "quantity": _fmt_qty(symbol, qty),
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
        _log(f"    SL order: {results['sl'].get('orderId', results['sl'].get('msg', 'UNKNOWN'))}")
    except Exception as e:
        results["sl"] = {"error": str(e)}
        _log(f"    SL error: {e}")
    try:
        results["tp"] = _api_post("/fapi/v1/order", {
            "symbol": symbol, "side": close_side,
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": f"{tp_price:.6f}",
            "closePosition": "true",
        })
        _log(f"    TP order: {results['tp'].get('orderId', results['tp'].get('msg', 'UNKNOWN'))}")
    except Exception as e:
        results["tp"] = {"error": str(e)}
        _log(f"    TP error: {e}")
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
OKX_TF_MAP = {"4h": "4H", "1h": "1H", "15m": "15m"}

def _fetch_candles(symbol, tf="4h", limit=15):
    """Fetch candles from OKX."""
    # Handle special symbol mappings
    okx_symbol = symbol.replace("1000PEPEUSDT", "PEPE-USDT-SWAP").replace("USDT", "-USDT-SWAP")
    if "1000PEPE" in symbol:
        okx_symbol = "PEPE-USDT-SWAP"
    else:
        okx_symbol = symbol.replace("USDT", "-USDT-SWAP")
    bar = OKX_TF_MAP.get(tf, "4H")
    try:
        r = req.get("https://www.okx.com/api/v5/market/candles",
                     params={"instId": okx_symbol, "bar": bar, "limit": limit}, timeout=10)
        data = r.json().get("data", [])
        candles = []
        for c in reversed(data):
            candles.append({
                "open": float(c[1]), "high": float(c[2]),
                "low": float(c[3]), "close": float(c[4]),
                "time": int(c[0]),
            })
        # Drop last candle — it's still OPEN (incomplete)
        if candles:
            candles = candles[:-1]
        return candles
    except Exception as e:
        _log(f"  ❌ OKX fetch error: {e}")
        return []


def _get_price(symbol):
    """Get current price from OKX."""
    if "1000PEPE" in symbol:
        inst = "PEPE-USDT-SWAP"
    else:
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


# ── Custom Configs from D1 (per-pair custom settings) ──
def _fetch_custom_configs(mode="baret"):
    """Fetch custom configs from D1 where live_enabled=true."""
    try:
        r = req.get(f"{WORKER_URL}/custom-configs/list?live_only=true", timeout=15)
        all_configs = r.json().get("configs", [])
    except:
        _log("⚠️ Failed to fetch custom configs from D1")
        return []

    # Filter by mode
    filtered = [c for c in all_configs if c.get("mode", "baret") == mode]

    if not filtered:
        return []

    configs = []
    for c in filtered:
        configs.append({
            "symbol": c["symbol"],
            "timeframe": c.get("timeframe", "4h"),
            "buffer_pct": c.get("buffer1_pct", 0.8),
            "tp_pct": c.get("tp_pct", 1.5),
            "sl_pct": c.get("sl_pct", 0.3),
            "window": c.get("window", 10),
            "buffer2_pct": c.get("buffer2_pct", 1.0),
            "close_filter_pct": c.get("close_filter_pct", 0.3),
            "win_rate": c.get("win_rate", 0),
            "profit_per_day": c.get("profit_per_day", 0),
            "max_drawdown": c.get("max_drawdown", 0),
        })
        _log(f"  📋 [CUSTOM] {c['symbol']} {c.get('timeframe','4h')}: buf={c.get('buffer1_pct')}% TP={c.get('tp_pct')}% SL={c.get('sl_pct')}% WR={c.get('win_rate', 0):.1f}%")

    SKIP_PAIRS = {"1000PEPEUSDT"}
    configs = [c for c in configs if c["symbol"] not in SKIP_PAIRS]
    _log(f"  📊 {len(configs)} custom configs loaded from D1 (mode={mode})")
    return configs


# ── Baret Config from D1 (same source as Dashboard recommendations) ──
def _fetch_baret_configs(mode="baret", min_wr=75.0, max_dd=20.0, min_ppd=0.0, max_bh=100.0, buffer=None, tp=None, sl=None, sort_by="profit", position_usd=100.0):
    """Fetch best config per pair from D1, applying EXACT same filters as Dashboard.
    Dashboard scales profit: ppd_scaled = ppd_raw * position_usd / 100
    min_ppd filter applies on scaled value (same as dashboard).
    """
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

    # Scale profit same as Dashboard: ppd_scaled = ppd_raw * position_usd / 100
    scale = position_usd / 100.0

    # Filter by user criteria (EXACT same as Dashboard)
    filtered = [r for r in results if 
        r["win_rate"] >= min_wr and 
        r["max_drawdown"] <= max_dd and
        (r["profit_per_day"] * scale) >= min_ppd and
        (r.get("both_hit_pct") is None or r.get("both_hit_pct", 0) <= max_bh) and
        (buffer is None or r.get("buffer1_pct") == buffer) and
        (tp is None or r.get("tp_pct") == tp) and
        (sl is None or r.get("sl_pct") == sl)
    ]

    # Pick best per pair based on sort criteria
    best = {}
    for r in filtered:
        pair = r["symbol"]
        if pair not in best:
            best[pair] = r
        elif sort_by == "wr" and r["win_rate"] > best[pair]["win_rate"]:
            best[pair] = r
        elif sort_by == "safe" and r["max_drawdown"] < best[pair]["max_drawdown"]:
            best[pair] = r
        elif sort_by == "profit" and r["profit_per_day"] > best[pair]["profit_per_day"]:
            best[pair] = r

    # Sort final list
    if sort_by == "wr":
        sorted_pairs = sorted(best.items(), key=lambda x: -x[1]["win_rate"])
    elif sort_by == "safe":
        sorted_pairs = sorted(best.items(), key=lambda x: x[1]["max_drawdown"])
    else:
        sorted_pairs = sorted(best.items(), key=lambda x: -x[1]["profit_per_day"])

    configs = []
    for pair, r in sorted_pairs:
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
        ppd_scaled = r.get("profit_per_day", 0) * scale
        _log(f"  📋 {pair}: buf={r.get('buffer1_pct')}% TP={r.get('tp_pct')}% SL={r.get('sl_pct')}% WR={r.get('win_rate'):.1f}% DD={r.get('max_drawdown'):.1f}% ${ppd_scaled:.2f}/day")

    # Exclude pairs with known issues
    SKIP_PAIRS = {"1000PEPEUSDT"}
    configs = [c for c in configs if c["symbol"] not in SKIP_PAIRS]
    
    _log(f"  📊 {len(configs)} pairs loaded from D1 (WR≥{min_wr}% DD≤{max_dd}% BH≤{max_bh}% PPD≥${min_ppd} sort={sort_by})")
    return configs


# ── Quantity Calculation ──
def _calc_quantity(symbol, price, position_usd=10.0):
    """Calculate order quantity based on position size and price."""
    notional = position_usd * LEVERAGE
    qty = notional / price
    d = PRECISION.get(symbol, {"qty": 1})["qty"]
    return round(qty, d)


# ── Telegram ──
def _send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        _log("⚠️ TELEGRAM_BOT_TOKEN not set, skip notification")
        return
    try:
        # Use HTML or no parse_mode to avoid Markdown underscore issues (baret_dca etc)
        resp = req.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                 json={"chat_id": ADMIN_CHAT_ID, "text": msg}, timeout=5)
        if resp.status_code != 200:
            _log(f"⚠️ Telegram send failed: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        _log(f"⚠️ Telegram error: {e}")


# ── Main Trading Loop ──
def _baret_live_loop(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0, min_ppd=0.0, leverage=50, max_bh=100.0, buffer=None, tp=None, sl=None, sort_by="profit", use_custom_configs=False):
    """Main Baret live trading loop. Supports 15m/1h/4h candle cycles."""
    global _baret_live_running, _baret_live_state, LEVERAGE
    LEVERAGE = leverage

    if not TESTNET_KEY or not TESTNET_SECRET:
        _log("❌ BINANCE_TESTNET_KEY/SECRET not set. Cannot trade.")
        _baret_live_running = False
        return

    _baret_live_state["mode"] = mode
    _baret_live_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _baret_live_state["filters"] = {"min_wr": min_wr, "max_dd": max_dd, "min_ppd": min_ppd, "max_bh": max_bh, "buffer": buffer, "tp": tp, "sl": sl, "sort_by": sort_by}
    # Try custom configs first, fallback to sweep-based configs
    configs = []
    if use_custom_configs:
        configs = _fetch_custom_configs(mode=mode)
    if not configs:
        configs = _fetch_baret_configs(mode=mode, min_wr=min_wr, max_dd=max_dd, min_ppd=min_ppd, max_bh=max_bh, buffer=buffer, tp=tp, sl=sl, sort_by=sort_by, position_usd=position_usd)
    _baret_live_state["active_pairs"] = [c["symbol"] for c in configs]

    # Determine shortest timeframe from configs for candle sync
    tf_minutes = {"15m": 15, "1h": 60, "4h": 240}
    all_tfs = set(c.get("timeframe", "4h") for c in configs)
    shortest_tf = min(all_tfs, key=lambda t: tf_minutes.get(t, 240))
    interval_min = tf_minutes.get(shortest_tf, 240)
    _log(f"═══ BARET LIVE STARTED ═══ mode={mode}, {len(configs)} pairs, ${position_usd}/trade, TFs: {all_tfs}, cycle={interval_min}min")
    _send_telegram(f"📐 *BARET LIVE STARTED*\nMode: {mode}\nPairs: {', '.join(c['symbol'] for c in configs)}\nPosition: ${position_usd}\nCycle: {interval_min}min")

    # Set leverage for all pairs
    for cfg in configs:
        _set_leverage(cfg["symbol"])

    # Helper: next candle boundary for a given interval
    def _next_boundary(now, interval):
        """Calculate next candle close time for given interval in minutes."""
        from datetime import timedelta as td
        epoch = datetime(2020, 1, 1, tzinfo=timezone.utc)
        elapsed = (now - epoch).total_seconds()
        interval_sec = interval * 60
        current_boundary = epoch + td(seconds=(elapsed // interval_sec) * interval_sec)
        next_b = current_boundary + td(seconds=interval_sec)
        return next_b

    def _at_boundary(now, interval):
        """Check if we're within 2 minutes after a candle boundary."""
        from datetime import timedelta as td
        epoch = datetime(2020, 1, 1, tzinfo=timezone.utc)
        elapsed = (now - epoch).total_seconds()
        interval_sec = interval * 60
        since_boundary = elapsed % interval_sec
        return since_boundary < 120  # within 2 minutes

    # Poll interval based on shortest TF
    poll_sec = 10 if interval_min <= 15 else 20 if interval_min <= 60 else 30

    cycle = 0
    while _baret_live_running:
        # ── Wait for next candle close ──
        now = datetime.now(timezone.utc)
        
        if not _at_boundary(now, interval_min):
            next_close = _next_boundary(now, interval_min)
            wait_secs = max(0, (next_close - now).total_seconds()) + 5  # +5s buffer
            _log(f"  ⏰ Waiting for {shortest_tf} candle close at {next_close.strftime('%H:%M')} UTC ({int(wait_secs//60)} min)")
            while wait_secs > 0 and _baret_live_running:
                time.sleep(min(poll_sec, wait_secs))
                wait_secs -= 30
                # Monitor existing positions for TP/SL while waiting
                for sym in list(_baret_live_state["positions"].keys()):
                    pos_info = _baret_live_state["positions"][sym]
                    cp = _get_price(sym)
                    if cp <= 0:
                        continue
                    side, tp, sl = pos_info["side"], pos_info["tp"], pos_info["sl"]
                    entry, qty = pos_info["entry"], pos_info.get("qty", 0)
                    hit = None
                    if side == "LONG" and cp >= tp: hit = "TP"
                    elif side == "LONG" and cp <= sl: hit = "SL"
                    elif side == "SHORT" and cp <= tp: hit = "TP"
                    elif side == "SHORT" and cp >= sl: hit = "SL"
                    if hit:
                        _cancel_all_orders(sym)
                        ex_pos = _get_position(sym)
                        if ex_pos:
                            cq = abs(float(ex_pos.get("positionAmt", 0)))
                            if cq > 0:
                                _place_market_close(sym, "BUY" if side == "LONG" else "SELL", cq)
                        pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                        pnl_dollar = pnl_pct / 100 * entry * qty
                        _log(f"  {'🎯' if hit == 'TP' else '🛑'} {sym} {side} {hit} @ ${cp:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_dollar:+.2f})")
                        _send_telegram(f"{'🎯' if hit == 'TP' else '🛑'} *{sym} {side} {hit}*\nEntry: ${entry:.4f}\nExit: ${cp:.4f}\nPnL: {pnl_pct:+.2f}%")
                        try:
                            cfg_tf = next((c.get("timeframe", "4h") for c in configs if c["symbol"] == sym), "15m")
                            req.post(f"{WORKER_URL}/bot/trade-log", json={
                                "strategy_id": 0, "symbol": sym, "timeframe": cfg_tf, "side": side,
                                "entry_price": entry, "exit_price": cp,
                                "entry_time": pos_data.get("filled_at", datetime.now(timezone.utc).isoformat()),
                                "exit_time": datetime.now(timezone.utc).isoformat(),
                                "sl_pct": None, "tp_pct": None,
                                "pnl_dollar": pnl_dollar, "pnl_pct": pnl_pct, "exit_reason": hit,
                                "regime_at_entry": None, "minimax_entry_verdict": None,
                                "minimax_exit_verdict": None, "minimax_adjustments": None,
                                "bars_held": None, "max_favorable": None, "max_adverse": None,
                                "backtest_wr": None, "notes": "baret_live",
                            }, timeout=10)
                        except:
                            pass
                        del _baret_live_state["positions"][sym]
        
        if not _baret_live_running:
            break

        # ── Candle just closed — start new cycle ──
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
                cfg_tf = cfg.get("timeframe", "4h")
                candles = _fetch_candles(symbol, cfg_tf, window + 5)
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
                    long_l2_order = _place_limit_order(symbol, "BUY", long_l2, qty)
                    short_l2_order = _place_limit_order(symbol, "SELL", short_l2, qty)
                    _baret_live_state["pending_orders"][symbol]["long_l2_id"] = long_l2_order.get("orderId")
                    _baret_live_state["pending_orders"][symbol]["short_l2_id"] = short_l2_order.get("orderId")
                    _baret_live_state["pending_orders"][symbol]["long_l2_entry"] = long_l2
                    _baret_live_state["pending_orders"][symbol]["short_l2_entry"] = short_l2
                    _log(f"     DCA L2: LONG=${long_l2:.4f}, SHORT=${short_l2:.4f}")

            except Exception as e:
                _log(f"  ❌ {symbol} error: {e}")

        # 8. Monitor fills until next candle close (check every 30s)
        _log(f"  ⏳ Monitoring fills until next {shortest_tf} candle close...")
        now_m = datetime.now(timezone.utc)
        monitor_until = _next_boundary(now_m, interval_min)
        
        _log(f"  📊 Monitor until {monitor_until.strftime('%Y-%m-%d %H:%M')} UTC ({int((monitor_until - now_m).total_seconds() // 60)} min)")
        
        while _baret_live_running and datetime.now(timezone.utc) < monitor_until:
            time.sleep(poll_sec)

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
                    existing_pos = _baret_live_state["positions"].get(symbol)

                    if existing_pos and mode == "baret_dca":
                        # ── DCA UPDATE: check if L2 filled (qty increased) ──
                        old_qty = existing_pos.get("qty", 0)
                        if abs(amt) > old_qty * 1.3:
                            # L2 filled! Binance auto-averaged entry price
                            _cancel_all_orders(symbol)
                            if side == "LONG":
                                tp_price = entry_price * (1 + pending["tp_pct"] / 100)
                                sl_price = entry_price * (1 - pending["sl_pct"] / 100)
                            else:
                                tp_price = entry_price * (1 - pending["tp_pct"] / 100)
                                sl_price = entry_price * (1 + pending["sl_pct"] / 100)
                            order_side = "BUY" if amt > 0 else "SELL"
                            _place_sl_tp(symbol, order_side, sl_price, tp_price)
                            _log(f"  🔄 {symbol} DCA L2 FILLED → avg entry ${entry_price:.4f} → TP=${tp_price:.4f} SL=${sl_price:.4f}")
                            _send_telegram(f"🔄 DCA L2 FILLED\n{symbol} {side} avg entry ${entry_price:.4f}\nTP: ${tp_price:.4f} SL: ${sl_price:.4f}")
                            existing_pos["entry"] = entry_price
                            existing_pos["tp"] = tp_price
                            existing_pos["sl"] = sl_price
                            existing_pos["qty"] = abs(amt)
                            existing_pos["dca_filled"] = True
                            if symbol in _baret_live_state["pending_orders"]:
                                del _baret_live_state["pending_orders"][symbol]

                    elif not existing_pos:
                        # ── NEW FILL (L1) ──
                        if mode == "baret_dca" and pending:
                            # DCA mode: cancel opposite side only, keep same-side L2
                            if side == "LONG":
                                # Cancel SHORT L1 + SHORT L2, keep LONG L2
                                if pending.get("short_id"):
                                    try: _cancel_order(symbol, pending["short_id"])
                                    except: pass
                                if pending.get("short_l2_id"):
                                    try: _cancel_order(symbol, pending["short_l2_id"])
                                    except: pass
                                _log(f"     DCA: cancelled SHORT orders, LONG L2 still active")
                            else:
                                # Cancel LONG L1 + LONG L2, keep SHORT L2
                                if pending.get("long_id"):
                                    try: _cancel_order(symbol, pending["long_id"])
                                    except: pass
                                if pending.get("long_l2_id"):
                                    try: _cancel_order(symbol, pending["long_l2_id"])
                                    except: pass
                                _log(f"     DCA: cancelled LONG orders, SHORT L2 still active")
                        else:
                            # Standard baret: cancel everything
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

                        dca_label = " (L1, L2 pending)" if mode == "baret_dca" else ""
                        _log(f"  ✅ {symbol} {side} FILLED @ ${entry_price:.4f} → TP=${tp_price:.4f} SL=${sl_price:.4f}{dca_label}")
                        _send_telegram(f"📐 BARET ENTRY{dca_label}\n{symbol} {side} @ ${entry_price:.4f}\nTP: ${tp_price:.4f}\nSL: ${sl_price:.4f}")

                        try:
                            cfg_tf = cfg.get("timeframe", "15m")
                            req.post(f"{WORKER_URL}/bot/trade-log", json={
                                "strategy_id": 0, "symbol": symbol, "timeframe": cfg_tf, "side": side,
                                "entry_price": entry_price, "exit_price": None,
                                "entry_time": datetime.now(timezone.utc).isoformat(), "exit_time": None,
                                "sl_pct": cfg.get("sl_pct"), "tp_pct": cfg.get("tp_pct"),
                                "pnl_dollar": None, "pnl_pct": None, "exit_reason": None,
                                "regime_at_entry": None, "minimax_entry_verdict": None,
                                "minimax_exit_verdict": None, "minimax_adjustments": None,
                                "bars_held": None, "max_favorable": None, "max_adverse": None,
                                "backtest_wr": None, "notes": "baret_live",
                            }, timeout=10)
                        except:
                            pass

                        # Don't delete pending in DCA mode (L2 still active)
                        if mode != "baret_dca":
                            del _baret_live_state["pending_orders"][symbol]
                        _baret_live_state["positions"][symbol] = {
                            "side": side, "entry": entry_price,
                            "tp": tp_price, "sl": sl_price,
                            "qty": abs(amt),
                            "dca_filled": False,
                            "filled_at": datetime.now(timezone.utc).isoformat(),
                        }
            
            # Monitor TP/SL for open positions
            for sym in list(_baret_live_state["positions"].keys()):
                if not _baret_live_running:
                    break
                pos_info = _baret_live_state["positions"][sym]
                current_price = _get_price(sym)
                if current_price <= 0:
                    continue
                
                side = pos_info["side"]
                tp = pos_info["tp"]
                sl = pos_info["sl"]
                entry = pos_info["entry"]
                qty = pos_info.get("qty", 0)
                
                hit = None
                if side == "LONG":
                    if current_price >= tp: hit = "TP"
                    elif current_price <= sl: hit = "SL"
                elif side == "SHORT":
                    if current_price <= tp: hit = "TP"
                    elif current_price >= sl: hit = "SL"
                
                if hit:
                    _cancel_all_orders(sym)
                    ex_pos = _get_position(sym)
                    if ex_pos:
                        close_qty = abs(float(ex_pos.get("positionAmt", 0)))
                        if close_qty > 0:
                            _place_market_close(sym, "BUY" if side == "LONG" else "SELL", close_qty)
                    
                    pnl_pct = ((current_price - entry) / entry * 100) if side == "LONG" else ((entry - current_price) / entry * 100)
                    pnl_dollar = pnl_pct / 100 * entry * qty
                    
                    _log(f"  {'🎯' if hit == 'TP' else '🛑'} {sym} {side} {hit} @ ${current_price:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_dollar:+.2f})")
                    _send_telegram(f"{'🎯' if hit == 'TP' else '🛑'} *{sym} {side} {hit}*\nEntry: ${entry:.4f}\nExit: ${current_price:.4f}\nPnL: {pnl_pct:+.2f}%")
                    
                    try:
                        cfg_tf = next((c.get("timeframe", "4h") for c in configs if c["symbol"] == sym), "15m")
                        req.post(f"{WORKER_URL}/bot/trade-log", json={
                            "strategy_id": 0, "symbol": sym, "timeframe": cfg_tf, "side": side,
                            "entry_price": entry, "exit_price": current_price,
                            "entry_time": pos_data.get("filled_at", datetime.now(timezone.utc).isoformat()),
                            "exit_time": datetime.now(timezone.utc).isoformat(),
                            "sl_pct": None, "tp_pct": None,
                            "pnl_dollar": pnl_dollar, "pnl_pct": pnl_pct, "exit_reason": hit,
                            "regime_at_entry": None, "minimax_entry_verdict": None,
                            "minimax_exit_verdict": None, "minimax_adjustments": None,
                            "bars_held": None, "max_favorable": None, "max_adverse": None,
                            "backtest_wr": None, "notes": "baret_live",
                        }, timeout=10)
                    except:
                        pass
                    
                    del _baret_live_state["positions"][sym]
        # 9. Candle close: cancel all unfilled orders
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

        _log(f"═══ CYCLE {cycle} DONE ═══")
        time.sleep(5)  # Small delay, then immediately recalculate (candle just closed)

    _log("═══ BARET LIVE STOPPED ═══")
    _baret_live_running = False


# ── Public API ──

def start_baret_live(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0, min_ppd=0.0, leverage=50, max_bh=100.0, buffer=None, tp=None, sl=None, sort_by="profit", use_custom_configs=False):
    global _baret_live_running, _baret_live_thread
    if _baret_live_running:
        return {"ok": True, "message": "Already running", "state": _baret_live_state}
    _baret_live_running = True
    _baret_live_thread = threading.Thread(
        target=_baret_live_loop, args=(mode, position_usd, min_wr, max_dd, min_ppd, leverage, max_bh, buffer, tp, sl, sort_by, use_custom_configs), daemon=True
    )
    _baret_live_thread.start()
    src = "custom configs" if use_custom_configs else "sweep filter"
    return {"ok": True, "message": f"Baret live started, mode={mode}, ${position_usd}×{leverage}x, source={src}"}


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


def close_position(symbol):
    """Close a specific position and cancel all orders for symbol."""
    symbol = symbol.upper()
    _cancel_all_orders(symbol)
    pos = _get_position(symbol)
    if not pos:
        return {"ok": True, "message": f"{symbol}: no position found"}
    amt = float(pos.get("positionAmt", 0))
    if amt == 0:
        return {"ok": True, "message": f"{symbol}: position already flat"}
    side = "SELL" if amt > 0 else "BUY"
    qty = abs(amt)
    result = _place_market_close(symbol, "BUY" if amt > 0 else "SELL", qty)
    # Clean from bot state
    if symbol in _baret_live_state.get("positions", {}):
        del _baret_live_state["positions"][symbol]
    if symbol in _baret_live_state.get("pending_orders", {}):
        del _baret_live_state["pending_orders"][symbol]
    _log(f"  🔒 {symbol}: closed {side} {qty} → {result.get('orderId', result.get('msg', result))}")
    return {"ok": True, "symbol": symbol, "side": side, "qty": qty, "result": result}


def close_all_positions():
    """Close all open positions."""
    try:
        positions = _api_get("/fapi/v2/positionRisk", signed=True)
    except:
        return {"ok": False, "error": "Failed to fetch positions"}
    closed = []
    for p in positions:
        amt = float(p.get("positionAmt", 0))
        if amt != 0:
            r = close_position(p["symbol"])
            closed.append(r)
    return {"ok": True, "closed": len(closed), "details": closed}
