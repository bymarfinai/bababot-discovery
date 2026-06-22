"""
BabaBot — Baret Live Trading (v3 Production)
Predicted range entry: limit orders at predicted extremes + buffer.
Supports: baret (single), baret_dca (L1+L2), baret_marfin (close filter).

Uses Binance Real/Demo API for order placement.
Data from OKX (cloud-accessible).

v3 Changes (from v2):
- Verified endpoints from official Binance docs (June 2026):
  * POST /fapi/v1/algoOrder (place SL/TP)
  * DELETE /fapi/v1/algoOrder (cancel single, requires algoId)
  * DELETE /fapi/v1/algoOpenOrders (cancel all algo per symbol)
  * GET /fapi/v1/openAlgoOrders (list open algo)
  * DELETE /fapi/v1/allOpenOrders does NOT cancel algo orders
- Since 2025-12-09: STOP_MARKET/TAKE_PROFIT_MARKET REQUIRE algoOrder (error -4120 on /fapi/v1/order)
- Store algoId for targeted cancellation
- Cycle-end position close now logs PnL to D1
- Deduplicated exchange-close detection into helper
- Removed unused numpy import
- close_position supports multi-account client
- Consistent DCA L2 formula: always entry × (1 ± buf2%)
"""

import os
import time
import hmac
import hashlib
import threading
import traceback
import requests as req
from datetime import datetime, timezone, timedelta
from collections import deque
from urllib.parse import urlencode

# ── Config ──
WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_ID", "888366328")

# Legacy single-account (backward compat)
TESTNET_URL = os.environ.get("BINANCE_TESTNET_URL", "https://demo-fapi.binance.com")
TESTNET_KEY = os.environ.get("BINANCE_TESTNET_KEY", "")
TESTNET_SECRET = os.environ.get("BINANCE_TESTNET_SECRET", "")
LEVERAGE = int(os.environ.get("LEVERAGE", "50"))


# ══════════════════════════════════════════════
# EXCHANGE CLIENT (per-account)
# ══════════════════════════════════════════════

class ExchangeClient:
    def __init__(self, base_url, api_key, api_secret, leverage=50):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.leverage = leverage

    def _sign(self, params):
        p = dict(params)  # don't mutate caller's dict
        p["timestamp"] = int(time.time() * 1000)
        p["recvWindow"] = 10000
        qs = urlencode(p)
        sig = hmac.new(self.api_secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
        return qs + f"&signature={sig}"

    def api_post(self, path, params):
        headers = {"X-MBX-APIKEY": self.api_key}
        body = self._sign(params)
        r = req.post(f"{self.base_url}{path}", data=body, headers=headers, timeout=10)
        return r.json()

    def api_get(self, path, params=None, signed=False):
        headers = {"X-MBX-APIKEY": self.api_key}
        if signed:
            qs = self._sign(params or {})
            r = req.get(f"{self.base_url}{path}?{qs}", headers=headers, timeout=10)
        else:
            r = req.get(f"{self.base_url}{path}", params=params, headers=headers, timeout=10)
        return r.json()

    def api_delete(self, path, params):
        headers = {"X-MBX-APIKEY": self.api_key}
        body = self._sign(params)
        r = req.delete(f"{self.base_url}{path}?{body}", headers=headers, timeout=10)
        return r.json()

    # ── Standard Orders (LIMIT, MARKET only) ──

    def place_limit(self, symbol, side, price, qty):
        result = self.api_post("/fapi/v1/order", {
            "symbol": symbol, "side": side, "type": "LIMIT",
            "timeInForce": "GTC", "quantity": _fmt_qty(symbol, qty),
            "price": _fmt_price(symbol, price),
        })
        if result.get("orderId"):
            _log(f"  📋 Limit {side} {symbol} @ ${_fmt_price(symbol, price)} qty={_fmt_qty(symbol, qty)} → orderId={result['orderId']}")
        elif result.get("code") or result.get("msg"):
            _log(f"  ❌ Order FAILED {side} {symbol}: {result.get('msg', result)}")
        return result

    def place_market_close(self, symbol, side, qty):
        result = self.api_post("/fapi/v1/order", {
            "symbol": symbol, "side": side, "type": "MARKET",
            "quantity": _fmt_qty(symbol, qty),
            "reduceOnly": "true",
        })
        if result.get("code"):
            _log(f"  ⚠️ Close order error: {result.get('msg', result)}")
        return result

    def cancel_all_orders(self, symbol):
        """Cancel all regular open orders (LIMIT, MARKET). Does NOT cancel algo orders."""
        try:
            return self.api_delete("/fapi/v1/allOpenOrders", {"symbol": symbol})
        except Exception as e:
            _log(f"  ⚠️ cancel_all_orders {symbol}: {e}")
            return {}

    def cancel_order(self, symbol, order_id):
        """Cancel a single regular order by orderId."""
        try:
            return self.api_delete("/fapi/v1/order", {"symbol": symbol, "orderId": order_id})
        except Exception as e:
            _log(f"  ⚠️ cancel_order {symbol} #{order_id}: {e}")
            return {}

    def get_position(self, symbol):
        try:
            positions = self.api_get("/fapi/v2/positionRisk", signed=True)
            if isinstance(positions, list):
                for p in positions:
                    if p["symbol"] == symbol and float(p.get("positionAmt", 0)) != 0:
                        return p
        except Exception as e:
            _log(f"  ⚠️ get_position {symbol}: {e}")
        return None

    def set_leverage(self, symbol):
        try:
            self.api_post("/fapi/v1/leverage", {"symbol": symbol, "leverage": self.leverage})
        except:
            pass

    def get_all_positions(self):
        try:
            positions = self.api_get("/fapi/v2/positionRisk", signed=True)
            if isinstance(positions, list):
                return [p for p in positions if float(p.get("positionAmt", 0)) != 0]
        except:
            pass
        return []

    # ══════════════════════════════════════════
    # algoOrder — SL/TP (Binance Real, mandatory since 2025-12-09)
    #
    # Verified endpoints from official Binance docs:
    #   POST   /fapi/v1/algoOrder       — place conditional order
    #   DELETE /fapi/v1/algoOrder        — cancel single (requires algoId)
    #   DELETE /fapi/v1/algoOpenOrders   — cancel ALL open algo per symbol
    #   GET    /fapi/v1/openAlgoOrders   — list open algo orders
    #
    # Since 2025-12-09, /fapi/v1/order REJECTS STOP_MARKET/TAKE_PROFIT_MARKET
    # with error -4120. Must use algoOrder.
    # ══════════════════════════════════════════

    def place_algo_order(self, symbol, side, algo_type, trigger_price):
        """Place SL or TP via algoOrder (CONDITIONAL).

        Args:
            symbol: e.g. "SOLUSDT"
            side: "BUY" or "SELL" (close side, opposite of position)
            algo_type: "STOP_MARKET" or "TAKE_PROFIT_MARKET"
            trigger_price: price at which to trigger

        Returns: API response dict with algoId
        """
        params = {
            "symbol": symbol,
            "side": side,
            "algoType": "CONDITIONAL",
            "type": algo_type,
            "triggerPrice": _fmt_price(symbol, trigger_price),
            "closePosition": "true",
            # NOTE: timeInForce only for STOP/TAKE_PROFIT (limit types).
            # STOP_MARKET/TAKE_PROFIT_MARKET don't use it.
            # NOTE: quantity cannot be sent with closePosition=true.
        }
        result = self.api_post("/fapi/v1/algoOrder", params)
        label = "SL" if algo_type == "STOP_MARKET" else "TP"

        if result.get("algoId"):
            _log(f"    ✅ {label} algoOrder {side} {symbol} trigger=${_fmt_price(symbol, trigger_price)} → algoId={result['algoId']}")
        else:
            _log(f"    ❌ {label} algoOrder FAILED {symbol}: code={result.get('code')} msg={result.get('msg', result)}")
        return result

    def cancel_algo_order(self, symbol, algo_id):
        """Cancel a single algo order by algoId.
        Endpoint: DELETE /fapi/v1/algoOrder
        """
        try:
            result = self.api_delete("/fapi/v1/algoOrder", {"symbol": symbol, "algoId": algo_id})
            _log(f"    🗑 Cancelled algo #{algo_id} for {symbol}")
            return result
        except Exception as e:
            _log(f"    ⚠️ cancel_algo_order {symbol} #{algo_id}: {e}")
            return {}

    def cancel_all_algo_orders(self, symbol):
        """Cancel ALL open algo orders for a symbol.
        Endpoint: DELETE /fapi/v1/algoOpenOrders
        """
        try:
            result = self.api_delete("/fapi/v1/algoOpenOrders", {"symbol": symbol})
            _log(f"    🗑 Cancelled all algo orders for {symbol}")
            return result
        except Exception as e:
            _log(f"    ⚠️ cancel_all_algo_orders {symbol}: {e}")
            return {}

    def get_open_algo_orders(self, symbol=None):
        """Get all open algo orders (optionally filtered by symbol).
        Endpoint: GET /fapi/v1/openAlgoOrders
        """
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol
            return self.api_get("/fapi/v1/openAlgoOrders", params, signed=True)
        except Exception as e:
            _log(f"  ⚠️ get_open_algo_orders: {e}")
            return []


# ── Default Client (legacy) ──
_default_client = None

def _get_default_client():
    global _default_client
    if not _default_client:
        _default_client = ExchangeClient(TESTNET_URL, TESTNET_KEY, TESTNET_SECRET, LEVERAGE)
    return _default_client


# ══════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════

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

# Multi-account state
_account_bots = {}


# ══════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════

def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _baret_live_log.append(entry)
    print(f"[BaretLive] {entry}")


# ── Symbol Precision (Binance Futures) ──
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


# ── Legacy wrappers (backward compat) ──
def _api_post(path, params):
    return _get_default_client().api_post(path, params)

def _api_get(path, params=None, signed=False):
    return _get_default_client().api_get(path, params, signed)

def _api_delete(path, params):
    return _get_default_client().api_delete(path, params)


# ── Quantity Calculation ──
def _calc_quantity(symbol, price, position_usd=10.0, leverage=50):
    """Calculate order qty from position size, price, and leverage."""
    notional = position_usd * leverage
    qty = notional / price
    d = PRECISION.get(symbol, {"qty": 1})["qty"]
    return round(qty, d)


# ── Telegram ──
def _send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        resp = req.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                 json={"chat_id": ADMIN_CHAT_ID, "text": msg}, timeout=5)
        if resp.status_code != 200:
            _log(f"⚠️ Telegram send failed: {resp.status_code}")
    except Exception as e:
        _log(f"⚠️ Telegram error: {e}")


# ══════════════════════════════════════════════
# SL/TP PLACEMENT & CANCELLATION (algoOrder)
# ══════════════════════════════════════════════

def _place_sl_tp(client, symbol, position_side, sl_price, tp_price):
    """Place SL and TP via algoOrder. Exchange auto-closes position.

    Returns: dict with "sl" and "tp" results (each containing algoId on success)
    """
    close_side = "SELL" if position_side == "LONG" else "BUY"
    results = {}

    try:
        results["sl"] = client.place_algo_order(symbol, close_side, "STOP_MARKET", sl_price)
    except Exception as e:
        results["sl"] = {"error": str(e)}
        _log(f"    ❌ SL algoOrder error {symbol}: {e}")

    try:
        results["tp"] = client.place_algo_order(symbol, close_side, "TAKE_PROFIT_MARKET", tp_price)
    except Exception as e:
        results["tp"] = {"error": str(e)}
        _log(f"    ❌ TP algoOrder error {symbol}: {e}")

    return results


def _cancel_sl_tp(client, symbol):
    """Cancel all SL/TP algo orders for a symbol.
    Uses DELETE /fapi/v1/algoOpenOrders (bulk cancel).
    """
    try:
        client.cancel_all_algo_orders(symbol)
    except Exception as e:
        _log(f"    ⚠️ cancel SL/TP {symbol}: {e}")


# ══════════════════════════════════════════════
# OKX DATA
# ══════════════════════════════════════════════

OKX_TF_MAP = {"4h": "4H", "1h": "1H", "15m": "15m"}

def _fetch_candles(symbol, tf="4h", limit=15):
    """Fetch closed candles from OKX. Last (open) candle is dropped."""
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
        # Drop last candle (still open/incomplete)
        if candles:
            candles = candles[:-1]
        return candles
    except Exception as e:
        _log(f"  ❌ OKX fetch error {symbol}: {e}")
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


# ══════════════════════════════════════════════════════════════
# PREDICTED RANGE CALCULATION (Deret Statistik)
#
# Formula:
#   ratio[i] = value[i] / value[i-1]   (for i in 1..n)
#   avg_ratio = mean(ratio[-window:])   (last `window` ratios)
#   prediction = last_value × avg_ratio
#
# Applied to high, low, close separately.
# ══════════════════════════════════════════════════════════════

def _calculate_predicted_range(candles, window=10):
    """Calculate predicted high/low/close for next candle."""
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


# ══════════════════════════════════════════════
# CONFIG FETCHERS (from D1)
# ══════════════════════════════════════════════

SKIP_PAIRS = {"1000PEPEUSDT"}

def _fetch_custom_configs(mode="baret"):
    """Fetch custom configs from D1 where live_enabled=true."""
    try:
        r = req.get(f"{WORKER_URL}/custom-configs/list?live_only=true", timeout=15)
        all_configs = r.json().get("configs", [])
    except:
        _log("⚠️ Failed to fetch custom configs from D1")
        return []

    filtered = [c for c in all_configs if c.get("mode", "baret") == mode]
    if not filtered:
        return []

    configs = []
    for c in filtered:
        if c["symbol"] in SKIP_PAIRS:
            continue
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
        _log(f"  📋 [CUSTOM] {c['symbol']} {c.get('timeframe','4h')}: buf={c.get('buffer1_pct')}% TP={c.get('tp_pct')}% SL={c.get('sl_pct')}%")

    _log(f"  📊 {len(configs)} custom configs loaded (mode={mode})")
    return configs


def _fetch_baret_configs(mode="baret", min_wr=75.0, max_dd=20.0, min_ppd=0.0, max_bh=100.0,
                         buffer=None, tp=None, sl=None, sort_by="profit", position_usd=100.0):
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
        ]

    # Scale profit same as Dashboard: ppd_scaled = ppd_raw × position_usd / 100
    scale = position_usd / 100.0
    filtered = [r for r in results if
        r["win_rate"] >= min_wr and
        r["max_drawdown"] <= max_dd and
        (r["profit_per_day"] * scale) >= min_ppd and
        (r.get("both_hit_pct") is None or r.get("both_hit_pct", 0) <= max_bh) and
        (buffer is None or r.get("buffer1_pct") == buffer) and
        (tp is None or r.get("tp_pct") == tp) and
        (sl is None or r.get("sl_pct") == sl)
    ]

    best = {}
    for r in filtered:
        pair = r["symbol"]
        if pair in SKIP_PAIRS:
            continue
        if pair not in best:
            best[pair] = r
        elif sort_by == "wr" and r["win_rate"] > best[pair]["win_rate"]:
            best[pair] = r
        elif sort_by == "safe" and r["max_drawdown"] < best[pair]["max_drawdown"]:
            best[pair] = r
        elif sort_by == "profit" and r["profit_per_day"] > best[pair]["profit_per_day"]:
            best[pair] = r

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
        _log(f"  📋 {pair}: buf={r.get('buffer1_pct')}% TP={r.get('tp_pct')}% SL={r.get('sl_pct')}% WR={r.get('win_rate'):.1f}% ${ppd_scaled:.2f}/day")

    _log(f"  📊 {len(configs)} pairs loaded (WR≥{min_wr}% DD≤{max_dd}% sort={sort_by})")
    return configs


# ══════════════════════════════════════════════
# TRADE LOGGING (to D1)
# ══════════════════════════════════════════════

def _log_trade_to_d1(symbol, timeframe, side, entry_price, exit_price, entry_time, exit_time,
                     sl_pct, tp_pct, pnl_dollar, pnl_pct, exit_reason, acct_name=""):
    """Log a trade entry or exit to D1. Non-blocking, never raises."""
    try:
        req.post(f"{WORKER_URL}/bot/trade-log", json={
            "strategy_id": 0, "symbol": symbol, "timeframe": timeframe, "side": side,
            "entry_price": entry_price, "exit_price": exit_price,
            "entry_time": entry_time, "exit_time": exit_time,
            "sl_pct": sl_pct, "tp_pct": tp_pct,
            "pnl_dollar": pnl_dollar, "pnl_pct": pnl_pct, "exit_reason": exit_reason,
            "regime_at_entry": None, "minimax_entry_verdict": None,
            "minimax_exit_verdict": None, "minimax_adjustments": None,
            "bars_held": None, "max_favorable": None, "max_adverse": None,
            "backtest_wr": None,
            "notes": f"baret_live_{acct_name}" if acct_name else "baret_live",
        }, timeout=10)
    except:
        pass


# ══════════════════════════════════════════════
# CANDLE TIMING HELPERS
# ══════════════════════════════════════════════

_EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)

def _next_boundary(now, interval_min):
    """Next candle close time for given interval in minutes."""
    elapsed = (now - _EPOCH).total_seconds()
    interval_sec = interval_min * 60
    current = _EPOCH + timedelta(seconds=(elapsed // interval_sec) * interval_sec)
    return current + timedelta(seconds=interval_sec)

def _at_boundary(now, interval_min):
    """Check if we're within 2 minutes after a candle boundary."""
    elapsed = (now - _EPOCH).total_seconds()
    interval_sec = interval_min * 60
    since_boundary = elapsed % interval_sec
    return since_boundary < 120


# ══════════════════════════════════════════════════════════════
# EXCHANGE-CLOSE DETECTION (deduplicated helper)
# ══════════════════════════════════════════════════════════════

def _detect_exchange_close(client, symbol, pos_info, configs, state, prefix, acct_name):
    """Check if exchange closed position (algoOrder triggered).
    If closed: log PnL, send Telegram, clean up state.
    Returns True if position was closed, False if still open.
    """
    try:
        ex_pos = client.get_position(symbol)
        if ex_pos and float(ex_pos.get("positionAmt", 0)) != 0:
            return False  # still open

        _log(f"{prefix}  📊 {symbol}: position closed by exchange (algoOrder)")
        cp = _get_price(symbol)
        side = pos_info["side"]
        entry = pos_info["entry"]
        qty = pos_info.get("qty", 0)

        if cp > 0 and entry > 0:
            pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
            pnl_dollar = pnl_pct / 100 * entry * qty
            hit = "TP" if pnl_pct > 0 else "SL"
            emoji = "🎯" if hit == "TP" else "🛑"
            _log(f"{prefix}  {emoji} {symbol} {side} {hit} (exchange) @ ~${cp:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_dollar:+.2f})")
            _send_telegram(f"{emoji} *{symbol} {side} {hit}* (exchange)\nEntry: ${entry:.4f}\nExit: ~${cp:.4f}\nPnL: {pnl_pct:+.2f}%")
            cfg_tf = next((c.get("timeframe", "4h") for c in configs if c["symbol"] == symbol), "4h")
            _log_trade_to_d1(symbol, cfg_tf, side, entry, cp,
                pos_info.get("filled_at"), datetime.now(timezone.utc).isoformat(),
                pos_info.get("cfg_sl_pct"), pos_info.get("cfg_tp_pct"),
                pnl_dollar, pnl_pct, hit, acct_name)
        else:
            _log(f"{prefix}  📊 {symbol}: closed (price unavailable, PnL unknown)")

        state["positions"].pop(symbol, None)
        state.get("pending_orders", {}).pop(symbol, None)
        return True

    except Exception as e:
        _log(f"{prefix}  ⚠️ exchange-close check error {symbol}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# BOT-SIDE POSITION CLOSE (backup for algoOrder)
# ══════════════════════════════════════════════════════════════

def _handle_position_close(client, symbol, pos_info, current_price, configs, state, prefix, acct_name):
    """Check if price hit TP/SL, market-close, log trade, cleanup.
    Bot-side backup — primary close is algoOrder at exchange.
    """
    side = pos_info["side"]
    entry = pos_info["entry"]
    qty = pos_info.get("qty", 0)
    tp_val = pos_info["tp"]
    sl_val = pos_info["sl"]

    hit = None
    if side == "LONG":
        if current_price >= tp_val: hit = "TP"
        elif current_price <= sl_val: hit = "SL"
    else:
        if current_price <= tp_val: hit = "TP"
        elif current_price >= sl_val: hit = "SL"

    if not hit:
        return False

    # Cancel all (regular + algo)
    try: client.cancel_all_orders(symbol)
    except: pass
    try: _cancel_sl_tp(client, symbol)
    except: pass

    # Market close
    try:
        ex_pos = client.get_position(symbol)
        if ex_pos:
            actual_qty = abs(float(ex_pos.get("positionAmt", 0)))
            if actual_qty > 0:
                close_side = "SELL" if side == "LONG" else "BUY"
                client.place_market_close(symbol, close_side, actual_qty)
                time.sleep(1)
                verify = client.get_position(symbol)
                if verify and abs(float(verify.get("positionAmt", 0))) > 0:
                    _log(f"{prefix}  ⚠️ {symbol}: market close failed, still open!")
                    return False
                qty = actual_qty
    except Exception as e:
        _log(f"{prefix}  ❌ {symbol} close error: {e}")
        return False

    pnl_pct = ((current_price - entry) / entry * 100) if side == "LONG" else ((entry - current_price) / entry * 100)
    pnl_dollar = pnl_pct / 100 * entry * qty

    emoji = "🎯" if hit == "TP" else "🛑"
    _log(f"{prefix}  {emoji} {symbol} {side} {hit} @ ${current_price:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_dollar:+.2f})")
    _send_telegram(f"{emoji} *{symbol} {side} {hit}*\nEntry: ${entry:.4f}\nExit: ${current_price:.4f}\nPnL: {pnl_pct:+.2f}%")

    cfg_tf = next((c.get("timeframe", "4h") for c in configs if c["symbol"] == symbol), "4h")
    _log_trade_to_d1(symbol, cfg_tf, side, entry, current_price,
        pos_info.get("filled_at", datetime.now(timezone.utc).isoformat()),
        datetime.now(timezone.utc).isoformat(),
        pos_info.get("cfg_sl_pct"), pos_info.get("cfg_tp_pct"),
        pnl_dollar, pnl_pct, hit, acct_name)

    state["positions"].pop(symbol, None)
    state.get("pending_orders", {}).pop(symbol, None)
    return True


# ══════════════════════════════════════════════════════════════
# MONITOR POSITIONS (shared helper for Phase 1 & Phase 3)
# ══════════════════════════════════════════════════════════════

def _monitor_positions(client, configs, state, prefix, acct_name, last_debug_ref):
    """Monitor all open positions: exchange-close detection + bot-side TP/SL backup.
    Args: last_debug_ref: mutable [datetime] for 5-min debug log timing.
    """
    for sym in list(state["positions"].keys()):
        try:
            pos_info = state["positions"].get(sym)
            if not pos_info:
                continue

            # 1. Exchange already closed? (algoOrder fired)
            if _detect_exchange_close(client, sym, pos_info, configs, state, prefix, acct_name):
                continue

            # 2. Bot-side backup
            cp = _get_price(sym)
            if cp <= 0:
                continue

            # Debug log every 5 min
            now_dbg = datetime.now(timezone.utc)
            if (now_dbg - last_debug_ref[0]).total_seconds() > 300:
                _log(f"{prefix}  🔎 {sym} {pos_info['side']}: price=${cp:.4f} tp=${pos_info['tp']:.4f} sl=${pos_info['sl']:.4f}")
                last_debug_ref[0] = now_dbg

            _handle_position_close(client, sym, pos_info, cp, configs, state, prefix, acct_name)

        except Exception as e:
            _log(f"{prefix}  ⚠️ Monitor error {sym}: {e}")


# ══════════════════════════════════════════════════════════════
# ENTRY LEVEL FORMULAS (documented for consistency)
#
# BARET (all modes):
#   long_entry  = pred_low  × (1 - buffer_pct / 100)
#   short_entry = pred_high × (1 + buffer_pct / 100)
#
# TP/SL from entry (all modes, applied to actual fill price):
#   LONG TP  = entry × (1 + tp_pct / 100)
#   LONG SL  = entry × (1 - sl_pct / 100)
#   SHORT TP = entry × (1 - tp_pct / 100)
#   SHORT SL = entry × (1 + sl_pct / 100)
#
# DCA L2 (baret_dca only):
#   Initial:     long_l2  = long_entry  × (1 - buffer2_pct / 100)
#                short_l2 = short_entry × (1 + buffer2_pct / 100)
#   Re-placement: long_l2  = actual_entry × (1 - buffer2_pct / 100)
#                 short_l2 = actual_entry × (1 + buffer2_pct / 100)
#
# DCA L2 fill → TP/SL recalculated from Binance avg entry:
#   Same TP/SL formulas applied to new avg entry price
#
# CLOSE FILTER (baret_marfin only):
#   gap_long  = (pred_close - pred_low) / pred_low × 100
#   gap_short = (pred_high - pred_close) / pred_high × 100
#   Skip pair if BOTH gaps < close_filter_pct
# ══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════
# MAIN TRADING LOOP
# ══════════════════════════════════════════════

def _baret_live_loop(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0,
                     min_ppd=0.0, leverage=50, max_bh=100.0, buffer=None, tp=None,
                     sl=None, sort_by="profit", use_custom_configs=False,
                     client=None, state=None, running_check=None, acct_name=""):
    """Main Baret live trading loop."""
    global _baret_live_running, _baret_live_state, LEVERAGE

    # Defaults for legacy mode
    if client is None:
        LEVERAGE = leverage
        if not TESTNET_KEY or not TESTNET_SECRET:
            _log("❌ BINANCE_TESTNET_KEY/SECRET not set. Cannot trade.")
            _baret_live_running = False
            return
        client = _get_default_client()
        client.leverage = leverage

    if state is None:
        state = _baret_live_state
    if running_check is None:
        running_check = lambda: _baret_live_running

    prefix = f"[{acct_name}] " if acct_name else ""

    # ── Load configs ──
    state["mode"] = mode
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["filters"] = {"min_wr": min_wr, "max_dd": max_dd, "min_ppd": min_ppd,
                        "max_bh": max_bh, "buffer": buffer, "tp": tp, "sl": sl, "sort_by": sort_by}

    configs = []
    if use_custom_configs:
        configs = _fetch_custom_configs(mode=mode)
    if not configs:
        configs = _fetch_baret_configs(
            mode=mode, min_wr=min_wr, max_dd=max_dd, min_ppd=min_ppd,
            max_bh=max_bh, buffer=buffer, tp=tp, sl=sl,
            sort_by=sort_by, position_usd=position_usd,
        )
    state["active_pairs"] = [c["symbol"] for c in configs]

    # Cycle interval from shortest TF
    tf_minutes = {"15m": 15, "1h": 60, "4h": 240}
    all_tfs = set(c.get("timeframe", "4h") for c in configs)
    shortest_tf = min(all_tfs, key=lambda t: tf_minutes.get(t, 240))
    interval_min = tf_minutes.get(shortest_tf, 240)

    _log(f"{prefix}═══ BARET LIVE STARTED ═══ mode={mode}, {len(configs)} pairs, ${position_usd}/trade, cycle={interval_min}min")
    _send_telegram(f"📐 BARET LIVE STARTED\nMode: {mode}\nPairs: {', '.join(c['symbol'] for c in configs)}\nPosition: ${position_usd}\nCycle: {interval_min}min")

    for cfg in configs:
        client.set_leverage(cfg["symbol"])

    # ── Auto-cleanup orphan positions ──
    _log(f"{prefix}  🔍 Checking for orphan positions...")
    orphan_count = 0
    for cfg in configs:
        symbol = cfg["symbol"]
        try:
            pos = client.get_position(symbol)
            if pos:
                amt = float(pos.get("positionAmt", 0))
                if amt != 0:
                    side_close = "SELL" if amt > 0 else "BUY"
                    client.cancel_all_orders(symbol)
                    _cancel_sl_tp(client, symbol)
                    client.place_market_close(symbol, side_close, abs(amt))
                    _log(f"{prefix}  🧹 {symbol}: closed orphan {'LONG' if amt > 0 else 'SHORT'} {abs(amt)}")
                    orphan_count += 1
        except Exception as e:
            _log(f"{prefix}  ⚠️ Orphan cleanup {symbol}: {e}")
    _log(f"{prefix}  ✅ {orphan_count} orphan positions cleaned" if orphan_count else f"{prefix}  ✅ No orphan positions")

    poll_sec = 10 if interval_min <= 15 else 20 if interval_min <= 60 else 30
    last_debug_ref = [datetime.min.replace(tzinfo=timezone.utc)]

    cycle = 0
    while running_check():

        # ════════════════════════════════════════
        # PHASE 1: Wait for candle close
        # ════════════════════════════════════════
        now = datetime.now(timezone.utc)
        if not _at_boundary(now, interval_min):
            next_close = _next_boundary(now, interval_min)
            wait_secs = max(0, (next_close - now).total_seconds()) + 5
            _log(f"{prefix}  ⏰ Waiting for {shortest_tf} close at {next_close.strftime('%H:%M')} UTC ({int(wait_secs//60)}min)")

            while wait_secs > 0 and running_check():
                time.sleep(min(poll_sec, wait_secs))
                wait_secs -= poll_sec
                _monitor_positions(client, configs, state, prefix, acct_name, last_debug_ref)

        if not running_check():
            break

        # ════════════════════════════════════════
        # PHASE 2: New cycle — place orders
        # ════════════════════════════════════════
        cycle += 1
        state["cycle_count"] = cycle
        state["last_cycle"] = datetime.now(timezone.utc).isoformat()
        _log(f"{prefix}═══ CYCLE {cycle} ═══")

        for cfg in configs:
            if not running_check():
                break

            symbol = cfg["symbol"]
            buffer_pct = cfg["buffer_pct"]
            tp_pct = cfg["tp_pct"]
            sl_pct = cfg["sl_pct"]
            window = cfg.get("window", 10)
            cfg_tf = cfg.get("timeframe", "4h")

            try:
                pos = client.get_position(symbol)
                has_position = pos and float(pos.get("positionAmt", 0)) != 0

                if has_position:
                    tracked = state["positions"].get(symbol)

                    if tracked and mode == "baret_dca" and not tracked.get("dca_filled"):
                        # Re-place DCA L2.
                        # cancel_all_orders only cancels LIMIT orders.
                        # SL/TP algo orders stay active at exchange.
                        client.cancel_all_orders(symbol)

                        buf2 = cfg.get("buffer2_pct", 1.0)
                        side = tracked["side"]
                        entry = tracked["entry"]
                        amt = abs(float(pos.get("positionAmt", 0)))

                        # L2 = entry × (1 ± buf2%)
                        if side == "LONG":
                            l2_price = entry * (1 - buf2 / 100)
                            client.place_limit(symbol, "BUY", l2_price, amt)
                        else:
                            l2_price = entry * (1 + buf2 / 100)
                            client.place_limit(symbol, "SELL", l2_price, amt)
                        _log(f"{prefix}  🔄 {symbol}: re-placed DCA L2 {side} @ ${l2_price:.4f}")
                    else:
                        _log(f"{prefix}  ⏩ {symbol}: in position, skipping")
                    continue

                # ── No position — place new orders ──
                client.cancel_all_orders(symbol)
                _cancel_sl_tp(client, symbol)

                candles = _fetch_candles(symbol, cfg_tf, window + 5)
                if not candles:
                    _log(f"{prefix}  ⚠️ {symbol}: no candle data")
                    continue

                pred = _calculate_predicted_range(candles, window)
                if not pred:
                    _log(f"{prefix}  ⚠️ {symbol}: insufficient data")
                    continue

                pred_high = pred["pred_high"]
                pred_low = pred["pred_low"]
                pred_close = pred["pred_close"]
                current = pred["current_price"]

                # Close filter (baret_marfin only)
                if mode == "baret_marfin":
                    close_filter = cfg.get("close_filter_pct", 0.3)
                    gap_long = (pred_close - pred_low) / pred_low * 100 if pred_low > 0 else 0
                    gap_short = (pred_high - pred_close) / pred_high * 100 if pred_high > 0 else 0
                    if gap_long < close_filter and gap_short < close_filter:
                        _log(f"{prefix}  ⏩ {symbol}: close filter skip (L={gap_long:.2f}% S={gap_short:.2f}%)")
                        continue

                # Entry levels
                long_entry = pred_low * (1 - buffer_pct / 100)
                short_entry = pred_high * (1 + buffer_pct / 100)
                qty = _calc_quantity(symbol, current, position_usd, client.leverage)

                _log(f"{prefix}  📐 {symbol}: range ${pred_low:.4f}-${pred_high:.4f}, cur=${current:.4f}")
                _log(f"{prefix}     LONG@${long_entry:.4f} SHORT@${short_entry:.4f} qty={qty}")

                long_order = client.place_limit(symbol, "BUY", long_entry, qty)
                short_order = client.place_limit(symbol, "SELL", short_entry, qty)

                pending = {
                    "long_id": long_order.get("orderId"),
                    "short_id": short_order.get("orderId"),
                    "long_entry": long_entry,
                    "short_entry": short_entry,
                    "tp_pct": tp_pct,
                    "sl_pct": sl_pct,
                    "qty": qty,
                    "placed_at": datetime.now(timezone.utc).isoformat(),
                }

                # DCA L2: L1_entry × (1 ± buf2%)
                if mode == "baret_dca":
                    buf2 = cfg.get("buffer2_pct", 1.0)
                    long_l2 = long_entry * (1 - buf2 / 100)
                    short_l2 = short_entry * (1 + buf2 / 100)
                    l2_long = client.place_limit(symbol, "BUY", long_l2, qty)
                    l2_short = client.place_limit(symbol, "SELL", short_l2, qty)
                    pending["long_l2_id"] = l2_long.get("orderId")
                    pending["short_l2_id"] = l2_short.get("orderId")
                    pending["long_l2_entry"] = long_l2
                    pending["short_l2_entry"] = short_l2
                    _log(f"{prefix}     DCA L2: LONG=${long_l2:.4f} SHORT=${short_l2:.4f}")

                state["pending_orders"][symbol] = pending

            except Exception as e:
                _log(f"{prefix}  ❌ {symbol} order error: {e}")
                _log(f"{prefix}     {traceback.format_exc()}")

        # ════════════════════════════════════════
        # PHASE 3: Monitor fills until next candle
        # ════════════════════════════════════════
        now_m = datetime.now(timezone.utc)
        monitor_until = _next_boundary(now_m, interval_min)
        _log(f"{prefix}  ⏳ Monitoring until {monitor_until.strftime('%H:%M')} UTC ({int((monitor_until - now_m).total_seconds() // 60)}min)")

        while running_check() and datetime.now(timezone.utc) < monitor_until:
            time.sleep(poll_sec)

            # ── Check for new fills ──
            for cfg in configs:
                if not running_check():
                    break
                symbol = cfg["symbol"]
                pending = state["pending_orders"].get(symbol)
                if not pending:
                    continue

                try:
                    pos = client.get_position(symbol)
                    if not pos or float(pos.get("positionAmt", 0)) == 0:
                        continue

                    amt = float(pos["positionAmt"])
                    entry_price = float(pos.get("entryPrice", 0))
                    side = "LONG" if amt > 0 else "SHORT"
                    existing = state["positions"].get(symbol)

                    # ── DCA L2 fill (qty increased) ──
                    if existing and mode == "baret_dca" and not existing.get("dca_filled"):
                        old_qty = existing.get("qty", 0)
                        if abs(amt) > old_qty * 1.3:
                            # Cancel old orders + SL/TP, set new from avg entry
                            client.cancel_all_orders(symbol)
                            _cancel_sl_tp(client, symbol)

                            if side == "LONG":
                                tp_price = entry_price * (1 + pending["tp_pct"] / 100)
                                sl_price = entry_price * (1 - pending["sl_pct"] / 100)
                            else:
                                tp_price = entry_price * (1 - pending["tp_pct"] / 100)
                                sl_price = entry_price * (1 + pending["sl_pct"] / 100)

                            sl_tp = _place_sl_tp(client, symbol, side, sl_price, tp_price)

                            _log(f"{prefix}  🔄 {symbol} DCA L2 FILLED → avg ${entry_price:.4f} → TP=${tp_price:.4f} SL=${sl_price:.4f}")
                            _send_telegram(f"🔄 DCA L2 FILLED\n{symbol} {side} avg ${entry_price:.4f}\nTP: ${tp_price:.4f} SL: ${sl_price:.4f}")

                            existing["entry"] = entry_price
                            existing["tp"] = tp_price
                            existing["sl"] = sl_price
                            existing["qty"] = abs(amt)
                            existing["dca_filled"] = True
                            existing["sl_algo_id"] = sl_tp.get("sl", {}).get("algoId")
                            existing["tp_algo_id"] = sl_tp.get("tp", {}).get("algoId")
                            state["pending_orders"].pop(symbol, None)
                        continue

                    # ── New fill (L1) ──
                    if not existing:
                        if mode == "baret_dca":
                            # Cancel opposite side only
                            if side == "LONG":
                                for k in ["short_id", "short_l2_id"]:
                                    oid = pending.get(k)
                                    if oid:
                                        try: client.cancel_order(symbol, oid)
                                        except: pass
                                _log(f"{prefix}     DCA: cancelled SHORT orders, LONG L2 active")
                            else:
                                for k in ["long_id", "long_l2_id"]:
                                    oid = pending.get(k)
                                    if oid:
                                        try: client.cancel_order(symbol, oid)
                                        except: pass
                                _log(f"{prefix}     DCA: cancelled LONG orders, SHORT L2 active")
                        else:
                            client.cancel_all_orders(symbol)

                        # TP/SL from actual fill price
                        if side == "LONG":
                            tp_price = entry_price * (1 + pending["tp_pct"] / 100)
                            sl_price = entry_price * (1 - pending["sl_pct"] / 100)
                        else:
                            tp_price = entry_price * (1 - pending["tp_pct"] / 100)
                            sl_price = entry_price * (1 + pending["sl_pct"] / 100)

                        sl_tp = _place_sl_tp(client, symbol, side, sl_price, tp_price)

                        dca_label = " (L1, L2 pending)" if mode == "baret_dca" else ""
                        _log(f"{prefix}  ✅ {symbol} {side} FILLED @ ${entry_price:.4f} → TP=${tp_price:.4f} SL=${sl_price:.4f}{dca_label}")
                        _send_telegram(f"📐 BARET ENTRY{dca_label}\n{symbol} {side} @ ${entry_price:.4f}\nTP: ${tp_price:.4f} SL: ${sl_price:.4f}")

                        _log_trade_to_d1(symbol, cfg.get("timeframe", "4h"), side,
                            entry_price, None, datetime.now(timezone.utc).isoformat(), None,
                            cfg.get("sl_pct"), cfg.get("tp_pct"), None, None, None, acct_name)

                        state["positions"][symbol] = {
                            "side": side, "entry": entry_price,
                            "tp": tp_price, "sl": sl_price,
                            "qty": abs(amt), "dca_filled": False,
                            "filled_at": datetime.now(timezone.utc).isoformat(),
                            "cfg_sl_pct": cfg.get("sl_pct"),
                            "cfg_tp_pct": cfg.get("tp_pct"),
                            "sl_algo_id": sl_tp.get("sl", {}).get("algoId"),
                            "tp_algo_id": sl_tp.get("tp", {}).get("algoId"),
                        }

                        if mode != "baret_dca":
                            state["pending_orders"].pop(symbol, None)

                except Exception as e:
                    _log(f"{prefix}  ⚠️ Fill check error {symbol}: {e}")

            # ── Monitor existing positions ──
            _monitor_positions(client, configs, state, prefix, acct_name, last_debug_ref)

        # ════════════════════════════════════════
        # PHASE 4: Candle close — cleanup
        # ════════════════════════════════════════
        for cfg in configs:
            symbol = cfg["symbol"]
            if symbol in state["pending_orders"]:
                try: client.cancel_all_orders(symbol)
                except: pass
                _log(f"{prefix}  🗑 {symbol}: unfilled orders cancelled")
                del state["pending_orders"][symbol]

        # Detect positions closed between monitoring and cycle end (with PnL)
        for symbol in list(state["positions"].keys()):
            pos_info = state["positions"].get(symbol)
            if pos_info:
                _detect_exchange_close(client, symbol, pos_info, configs, state, prefix, acct_name)

        _log(f"{prefix}═══ CYCLE {cycle} DONE ═══")
        time.sleep(5)

    _log(f"{prefix}═══ BARET LIVE STOPPED ═══")
    if not acct_name:
        _baret_live_running = False


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════

def start_baret_live(mode="baret", position_usd=10.0, min_wr=75.0, max_dd=20.0,
                     min_ppd=0.0, leverage=50, max_bh=100.0, buffer=None, tp=None,
                     sl=None, sort_by="profit", use_custom_configs=False):
    global _baret_live_running, _baret_live_thread
    if _baret_live_running:
        return {"ok": True, "message": "Already running", "state": _baret_live_state}
    _baret_live_running = True
    _baret_live_thread = threading.Thread(
        target=_baret_live_loop,
        args=(mode, position_usd, min_wr, max_dd, min_ppd, leverage, max_bh,
              buffer, tp, sl, sort_by, use_custom_configs),
        daemon=True,
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


def close_position(symbol, client=None):
    """Close a specific position. Supports multi-account via optional client."""
    symbol = symbol.upper()
    if client is None:
        client = _get_default_client()
    client.cancel_all_orders(symbol)
    _cancel_sl_tp(client, symbol)
    pos = client.get_position(symbol)
    if not pos:
        return {"ok": True, "message": f"{symbol}: no position found"}
    amt = float(pos.get("positionAmt", 0))
    if amt == 0:
        return {"ok": True, "message": f"{symbol}: position already flat"}
    side = "SELL" if amt > 0 else "BUY"
    qty = abs(amt)
    result = client.place_market_close(symbol, side, qty)
    _baret_live_state.get("positions", {}).pop(symbol, None)
    _baret_live_state.get("pending_orders", {}).pop(symbol, None)
    _log(f"  🔒 {symbol}: closed {side} {qty}")
    return {"ok": True, "symbol": symbol, "side": side, "qty": qty, "result": result}


def close_all_positions(client=None):
    """Close all open positions. Supports multi-account via optional client."""
    if client is None:
        client = _get_default_client()
    try:
        positions = client.api_get("/fapi/v2/positionRisk", signed=True)
        if not isinstance(positions, list):
            return {"ok": False, "error": f"Unexpected response: {positions}"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to fetch positions: {e}"}
    closed = []
    for p in positions:
        amt = float(p.get("positionAmt", 0))
        if amt != 0:
            r = close_position(p["symbol"], client=client)
            closed.append(r)
    return {"ok": True, "closed": len(closed), "details": closed}


# ══════════════════════════════════════════════
# MULTI-ACCOUNT SYSTEM
# ══════════════════════════════════════════════

def _account_loop(account_id, client, account_info, mode="baret_dca"):
    bot = _account_bots.get(account_id)
    if not bot:
        return
    acct_name = account_info.get("name", f"Account-{account_id}")
    position_usd = account_info.get("position_usd", 10)
    leverage = account_info.get("leverage", 50)
    client.leverage = leverage
    try:
        _baret_live_loop(
            mode=mode, position_usd=position_usd, leverage=leverage,
            use_custom_configs=True, client=client, state=bot["state"],
            running_check=lambda: bot["running"], acct_name=acct_name,
        )
    except Exception as e:
        _log(f"[{acct_name}] ❌ CRASH: {e}")
        _log(f"[{acct_name}] {traceback.format_exc()}")
    bot["running"] = False
    try:
        req.post(f"{WORKER_URL}/trading-accounts/update-status",
                 json={"id": account_id, "status": "stopped"}, timeout=10)
    except:
        pass


def start_account_bot(account_id, mode="baret_dca"):
    global _account_bots
    account_id = int(account_id)
    if account_id in _account_bots and _account_bots[account_id].get("running"):
        return {"ok": True, "message": f"Account {account_id} already running"}
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
    bot_state = {
        "active_pairs": [], "positions": {}, "pending_orders": {},
        "cycle_count": 0, "last_cycle": None, "mode": mode, "started_at": None,
    }
    _account_bots[account_id] = {
        "running": True, "state": bot_state,
        "client": client, "account": account, "thread": None,
    }
    t = threading.Thread(target=_account_loop, args=(account_id, client, account, mode), daemon=True)
    _account_bots[account_id]["thread"] = t
    t.start()
    try:
        req.post(f"{WORKER_URL}/trading-accounts/update-status",
                 json={"id": account_id, "status": "running"}, timeout=10)
    except:
        pass
    return {"ok": True, "message": f"Account '{account['name']}' started, mode={mode}, ${account['position_usd']}×{account['leverage']}x"}


def stop_account_bot(account_id):
    account_id = int(account_id)
    bot = _account_bots.get(account_id)
    if not bot or not bot.get("running"):
        return {"ok": True, "message": f"Account {account_id} not running"}
    bot["running"] = False
    _log(f"[Account-{account_id}] Stop signal sent")
    try:
        req.post(f"{WORKER_URL}/trading-accounts/update-status",
                 json={"id": account_id, "status": "stopped"}, timeout=10)
    except:
        pass
    return {"ok": True, "message": f"Account {account_id} stopping..."}


def account_bot_status(account_id=None):
    if account_id:
        account_id = int(account_id)
        bot = _account_bots.get(account_id)
        if not bot:
            return {"ok": True, "running": False, "account_id": account_id}
        return {
            "ok": True, "account_id": account_id,
            "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "state": bot["state"],
            "account_name": bot["account"].get("name", ""),
        }
    result = {}
    for aid, bot in _account_bots.items():
        result[aid] = {
            "running": bot["running"],
            "thread_alive": bot["thread"].is_alive() if bot.get("thread") else False,
            "account_name": bot["account"].get("name", ""),
            "pairs": bot["state"].get("active_pairs", []),
            "cycle": bot["state"].get("cycle_count", 0),
            "positions": len(bot["state"].get("positions", {})),
        }
    return {"ok": True, "accounts": result}
