"""
BabaBot Live Trading — Dumb Bot Core (Tier 1)
Runs as background thread on Railway.
Reads bot_config from D1 via Workers API, detects signals, executes on Binance Testnet.
"""

import os
import time
import hmac
import hashlib
import threading
import traceback
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import numpy as np
import requests

from backtesting_core import (
    StrategyConfig, ENTRY_LOGICS,
    precompute_indicators, get_signals, apply_filters,
    classify_regime, extract_signal_features, parse_rule,
)

# ============================================================
# CONFIG
# ============================================================

WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")
TESTNET_URL = os.environ.get("BINANCE_TESTNET_URL", "https://demo-fapi.binance.com")
TESTNET_KEY = os.environ.get("BINANCE_TESTNET_KEY", "")
TESTNET_SECRET = os.environ.get("BINANCE_TESTNET_SECRET", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_ID", "888366328")
BOT_INTERVAL = int(os.environ.get("BOT_INTERVAL", "60"))
BOT_ENABLED = os.environ.get("BOT_ENABLED", "false").lower() == "true"

# Candles needed for indicator warmup (EMA200 + buffer)
CANDLE_BUFFER = 300

# Position size from config ($10K capital, 10.5% per trade, 50x leverage)
CAPITAL = 10000.0
LEVERAGE = 50

# Map timeframe to Binance interval string
TF_MAP = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h"}

# Pair quantity map (notional ~$1050 per trade)
PAIR_QTY = {
    "BTCUSDT": 0.01, "ETHUSDT": 0.4, "XRPUSDT": 400, "YFIUSDT": 0.1,
    "SOLUSDT": 6, "BNBUSDT": 1.5, "DOGEUSDT": 4000, "LINKUSDT": 60,
    "AVAXUSDT": 30, "PEPEUSDT": 50000000, "1000PEPEUSDT": 50000,
}

# ============================================================
# BINANCE TESTNET API
# ============================================================

def _sign(params: dict) -> dict:
    """Add timestamp + HMAC signature to params."""
    params["timestamp"] = int(time.time() * 1000)
    query = urlencode(params)
    sig = hmac.new(TESTNET_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = sig
    return params


def _headers():
    return {"X-MBX-APIKEY": TESTNET_KEY}


def binance_get(path: str, params: dict = None, signed: bool = False) -> dict:
    """GET request to Binance Testnet."""
    params = params or {}
    if signed:
        params = _sign(params)
    url = f"{TESTNET_URL}{path}"
    r = requests.get(url, params=params, headers=_headers(), timeout=10)
    return r.json()


def binance_post(path: str, params: dict) -> dict:
    """POST request to Binance Testnet (signed)."""
    params = _sign(params)
    url = f"{TESTNET_URL}{path}"
    r = requests.post(url, params=params, headers=_headers(), timeout=10)
    return r.json()


def fetch_klines(symbol: str, interval: str, limit: int = 300) -> list:
    """Fetch klines from Binance Futures (mainnet for real prices)."""
    # Use mainnet for price data (testnet has fake/stale prices)
    url = f"https://fapi.binance.com/fapi/v1/klines"
    try:
        r = requests.get(url, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[Bot] Mainnet klines failed for {symbol} {interval}: {e}")

    # Fallback: proxy via Workers
    try:
        r = requests.get(f"{WORKER_URL}/bot/klines", params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("klines", [])
    except Exception as e:
        print(f"[Bot] Workers klines fallback also failed: {e}")

    return []


def klines_to_data(klines: list) -> dict:
    """Convert Binance klines to numpy dict format (same as backtesting_core)."""
    if not klines or len(klines) < 50:
        return None
    arr = np.array([
        [float(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]), float(k[9])]
        for k in klines
    ])
    return {
        "open_time": arr[:, 0],
        "open": arr[:, 1],
        "high": arr[:, 2],
        "low": arr[:, 3],
        "close": arr[:, 4],
        "volume": arr[:, 5],
        "taker_buy_volume": arr[:, 6],
    }


def get_current_price(symbol: str) -> float:
    """Get current mark price."""
    try:
        r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price", params={"symbol": symbol}, timeout=5)
        if r.status_code == 200:
            return float(r.json()["price"])
    except:
        pass
    return 0.0


def place_order(symbol: str, side: str, qty: float, sl_price: float, tp_price: float) -> dict:
    """Place market order + SL + TP on Binance Testnet."""
    results = {"market": None, "sl": None, "tp": None, "error": None}

    try:
        # Set leverage
        try:
            binance_post("/fapi/v1/leverage", {"symbol": symbol, "leverage": LEVERAGE})
        except:
            pass

        # Market order
        market = binance_post("/fapi/v1/order", {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": qty,
        })
        results["market"] = market

        if "orderId" not in market:
            results["error"] = f"Market order failed: {market}"
            return results

        # Stop Loss
        sl_side = "SELL" if side == "BUY" else "BUY"
        sl = binance_post("/fapi/v1/order", {
            "symbol": symbol,
            "side": sl_side,
            "type": "STOP_MARKET",
            "stopPrice": f"{sl_price:.6f}",
            "closePosition": "true",
        })
        results["sl"] = sl

        # Take Profit
        tp = binance_post("/fapi/v1/order", {
            "symbol": symbol,
            "side": sl_side,
            "type": "TAKE_PROFIT_MARKET",
            "stopPrice": f"{tp_price:.6f}",
            "closePosition": "true",
        })
        results["tp"] = tp

    except Exception as e:
        results["error"] = str(e)

    return results


def get_open_positions() -> list:
    """Get all open positions from testnet."""
    try:
        positions = binance_get("/fapi/v2/positionRisk", signed=True)
        return [p for p in positions if float(p.get("positionAmt", 0)) != 0]
    except Exception as e:
        print(f"[Bot] Failed to get positions: {e}")
        return []


# ============================================================
# WORKERS D1 INTERFACE
# ============================================================

def fetch_bot_configs() -> list:
    """Get active configs from D1 via Workers."""
    try:
        r = requests.get(f"{WORKER_URL}/bot/config", timeout=10)
        data = r.json()
        if data.get("ok"):
            return [c for c in data["configs"] if c.get("active")]
    except Exception as e:
        print(f"[Bot] Failed to fetch configs: {e}")
    return []


def log_trade(trade_data: dict):
    """Write trade to D1 via Workers."""
    try:
        r = requests.post(f"{WORKER_URL}/bot/trade-log", json=trade_data, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[Bot] Failed to log trade: {e}")
        return {"ok": False}


def send_telegram(msg: str):
    """Send Telegram notification."""
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=5,
        )
    except:
        pass


# ============================================================
# SIGNAL DETECTION (reuses backtesting_core)
# ============================================================

def check_signal(config: dict, data: dict) -> dict:
    """
    Check if latest candle has a signal for this strategy.
    Returns: {signal: 1/-1/0, features: {...}, regime: str} or None.
    """
    entry_logic = config["entry_logic"]
    entry_logic_2 = config.get("entry_logic_2")

    if entry_logic not in ENTRY_LOGICS:
        return None

    # Build StrategyConfig
    sc = StrategyConfig(
        symbol=config["symbol"],
        timeframe=config["timeframe"],
        entry_logic=entry_logic,
        entry_logic_2=entry_logic_2 if entry_logic_2 in ENTRY_LOGICS else None,
        sl_pct=config.get("sl_pct", 0.6),
        tp_pct=config.get("tp_pct", 1.5),
    )

    # Compute indicators
    ind = precompute_indicators(data, sc)

    # Generate signals
    signals = get_signals(data, ind, sc)

    # Multi-entry AND
    if sc.entry_logic_2 and sc.entry_logic_2 in ENTRY_LOGICS:
        from dataclasses import replace as dc_replace
        config2 = dc_replace(sc, entry_logic=sc.entry_logic_2)
        signals2 = get_signals(data, ind, config2)
        window = 3
        combined = np.zeros(len(signals), dtype=int)
        for i in range(window, len(signals)):
            if signals[i] != 0:
                for j in range(max(0, i - window), i + 1):
                    if signals2[j] == signals[i]:
                        combined[i] = signals[i]
                        break
            elif signals2[i] != 0:
                for j in range(max(0, i - window), i + 1):
                    if signals[j] == signals2[i]:
                        combined[i] = signals2[i]
                        break
        signals = combined

    # Apply filters
    signals = apply_filters(data, ind, signals, sc)

    # Check LAST CLOSED candle (index -2, because -1 is still forming)
    check_idx = len(signals) - 2
    if check_idx < 0:
        return None

    sig = int(signals[check_idx])
    if sig == 0:
        return None

    # Regime
    regimes = classify_regime(data, ind)
    regime = {0: "sideways", 1: "bull", -1: "bear", 2: "shock"}.get(int(regimes[check_idx]), "unknown")

    # Features (for rule filter)
    combo_label = entry_logic + (" AND " + entry_logic_2 if entry_logic_2 else "")
    features = extract_signal_features(combo_label, data, ind, check_idx, signals, regimes)

    return {
        "signal": sig,
        "side": "LONG" if sig == 1 else "SHORT",
        "features": features,
        "regime": regime,
        "price": float(data["close"][check_idx]),
        "check_idx": check_idx,
    }


def check_rule_filter(rule_str: str, features: dict) -> bool:
    """Apply P2 rule filter to signal features. Returns True if passes."""
    if not rule_str or rule_str.strip() == "":
        return True  # No rule = always pass

    conditions = parse_rule(rule_str)
    if not conditions:
        return True

    for feature, operator, value in conditions:
        feat_val = features.get(feature)
        if feat_val is None or not isinstance(feat_val, (int, float)):
            return False  # Missing feature = fail

        if operator == ">=" and not (feat_val >= value): return False
        elif operator == "<=" and not (feat_val <= value): return False
        elif operator == ">" and not (feat_val > value): return False
        elif operator == "<" and not (feat_val < value): return False
        elif operator == "==" and not (feat_val == value): return False
        elif operator == "!=" and not (feat_val != value): return False

    return True


# ============================================================
# POSITION MONITOR
# ============================================================

# Track open trades by symbol (to avoid duplicate entries)
_open_trades: dict = {}  # symbol -> trade_log_id


def monitor_positions():
    """Check open positions and close trades that hit SL/TP."""
    # TODO Step 4: MiniMax position manager replaces this
    # For now just log positions status
    try:
        positions = get_open_positions()
        for p in positions:
            symbol = p.get("symbol", "")
            amt = float(p.get("positionAmt", 0))
            pnl = float(p.get("unRealizedProfit", 0))
            if amt != 0:
                print(f"[Bot] Position: {symbol} amt={amt} uPnL=${pnl:.2f}")
    except Exception as e:
        print(f"[Bot] Monitor error: {e}")


# ============================================================
# MAIN BOT LOOP
# ============================================================

_bot_running = False
_bot_lock = threading.Lock()
_last_signals: dict = {}  # "symbol_tf_logic" -> timestamp of last signal (cooldown)
SIGNAL_COOLDOWN = 300  # 5 min cooldown per strategy


def _bot_loop():
    global _bot_running
    print(f"[Bot] 🤖 Dumb bot started! Interval={BOT_INTERVAL}s, testnet={TESTNET_URL}")
    send_telegram("🤖 *BabaBot Dumb Bot Started*\nPaper trading mode (testnet)")

    while _bot_running:
        cycle_start = time.time()
        try:
            # ── 1. Fetch active configs ──
            configs = fetch_bot_configs()
            if not configs:
                time.sleep(BOT_INTERVAL)
                continue

            # ── 2. Group by symbol+timeframe (avoid redundant kline fetches) ──
            groups: dict = {}  # "ETHUSDT_1h" -> [config1, config2, ...]
            for cfg in configs:
                key = f"{cfg['symbol']}_{cfg['timeframe']}"
                if key not in groups:
                    groups[key] = []
                groups[key].append(cfg)

            # ── 3. Per group: fetch klines, check signals ──
            for group_key, group_configs in groups.items():
                symbol, tf = group_key.split("_", 1)
                interval = TF_MAP.get(tf)
                if not interval:
                    continue

                # Fetch candles
                klines = fetch_klines(symbol, interval, CANDLE_BUFFER)
                data = klines_to_data(klines)
                if data is None:
                    print(f"[Bot] ⚠️ No data for {symbol} {tf}")
                    continue

                # Check each strategy in this group
                for cfg in group_configs:
                    strategy_id = cfg["strategy_id"]
                    cooldown_key = f"{symbol}_{tf}_{cfg['entry_logic']}_{cfg.get('entry_logic_2','')}"

                    # Cooldown check
                    last_sig_time = _last_signals.get(cooldown_key, 0)
                    if time.time() - last_sig_time < SIGNAL_COOLDOWN:
                        continue

                    # Regime gate check
                    regime_gate = cfg.get("regime_gate", "all")

                    # Check signal
                    result = check_signal(cfg, data)
                    if result is None:
                        continue

                    sig = result["signal"]
                    side = result["side"]
                    features = result["features"]
                    regime = result["regime"]
                    price = result["price"]

                    # Regime gate filter
                    if regime_gate != "all":
                        allowed_regimes = [r.strip() for r in regime_gate.split(",")]
                        if regime not in allowed_regimes:
                            print(f"[Bot] ⏭️ {symbol} {side} skipped — regime '{regime}' not in gate [{regime_gate}]")
                            continue

                    # Rule filter
                    rule_str = cfg.get("rule", "")
                    if not check_rule_filter(rule_str, features):
                        print(f"[Bot] ⏭️ {symbol} {side} skipped — rule filter failed")
                        continue

                    # ── SIGNAL PASSED ALL FILTERS! ──
                    combo = cfg["entry_logic"] + (f"+{cfg['entry_logic_2']}" if cfg.get("entry_logic_2") else "")
                    sl_pct = cfg.get("sl_pct", 0.6)
                    tp_pct = cfg.get("tp_pct", 1.5)

                    # Check if we already have an open position for this symbol
                    if symbol in _open_trades:
                        print(f"[Bot] ⏭️ {symbol} {side} skipped — already have open position")
                        continue

                    # Calculate SL/TP prices
                    current_price = get_current_price(symbol) or price
                    if side == "LONG":
                        sl_price = current_price * (1 - sl_pct / 100)
                        tp_price = current_price * (1 + tp_pct / 100)
                        order_side = "BUY"
                    else:
                        sl_price = current_price * (1 + sl_pct / 100)
                        tp_price = current_price * (1 - tp_pct / 100)
                        order_side = "SELL"

                    qty = PAIR_QTY.get(symbol, 0)
                    if qty == 0:
                        print(f"[Bot] ⚠️ No qty configured for {symbol}")
                        continue

                    # ── PLACEHOLDER: MiniMax gatekeeper (Step 3) ──
                    minimax_verdict = "PROCEED (no gatekeeper yet)"

                    # ── EXECUTE ──
                    print(f"[Bot] 🎯 SIGNAL: {symbol} {side} @ ${current_price:.2f} | {combo} | regime={regime}")
                    print(f"[Bot]   SL=${sl_price:.2f} ({sl_pct}%) | TP=${tp_price:.2f} ({tp_pct}%)")

                    order_result = place_order(symbol, order_side, qty, sl_price, tp_price)

                    if order_result.get("error"):
                        print(f"[Bot] ❌ Order failed: {order_result['error']}")
                        send_telegram(f"❌ Order failed: {symbol} {side}\n{order_result['error']}")
                        continue

                    # ── LOG TRADE ──
                    entry_time = datetime.now(timezone.utc).isoformat()
                    trade_data = {
                        "strategy_id": strategy_id,
                        "symbol": symbol,
                        "timeframe": tf,
                        "side": side,
                        "entry_price": current_price,
                        "entry_time": entry_time,
                        "sl_pct": sl_pct,
                        "tp_pct": tp_pct,
                        "regime_at_entry": regime,
                        "minimax_entry_verdict": minimax_verdict,
                        "backtest_wr": cfg.get("rule_wr", 0),
                        "notes": f"Auto entry: {combo} | Features: V={features.get('V','?')} B={features.get('B','?')} H={features.get('H','?')}",
                    }
                    log_result = log_trade(trade_data)

                    # Track open trade
                    _open_trades[symbol] = strategy_id

                    # Set cooldown
                    _last_signals[cooldown_key] = time.time()

                    # Telegram notification
                    send_telegram(
                        f"🎯 *TRADE OPENED*\n\n"
                        f"{'🟢' if side == 'LONG' else '🔴'} {side} {symbol} @ ${current_price:.2f}\n"
                        f"Strategy: {combo} ({tf})\n"
                        f"SL: ${sl_price:.2f} ({sl_pct}%)\n"
                        f"TP: ${tp_price:.2f} ({tp_pct}%)\n"
                        f"Regime: {regime}\n"
                        f"MiniMax: {minimax_verdict}\n"
                        f"_Paper trading (testnet)_"
                    )

            # ── 4. Monitor open positions ──
            monitor_positions()

        except Exception as e:
            print(f"[Bot] ❌ Cycle error: {e}")
            traceback.print_exc()

        # Sleep remaining time
        elapsed = time.time() - cycle_start
        sleep_time = max(1, BOT_INTERVAL - elapsed)
        time.sleep(sleep_time)

    print("[Bot] 🛑 Dumb bot stopped")
    send_telegram("🛑 *BabaBot Dumb Bot Stopped*")


# ============================================================
# START / STOP / STATUS
# ============================================================

def start_bot():
    global _bot_running
    if _bot_running:
        return {"ok": True, "message": "Already running"}
    if not TESTNET_KEY or not TESTNET_SECRET:
        return {"ok": False, "error": "BINANCE_TESTNET_KEY/SECRET not set"}

    _bot_running = True
    t = threading.Thread(target=_bot_loop, daemon=True)
    t.start()
    return {"ok": True, "message": f"Bot started, interval={BOT_INTERVAL}s"}


def stop_bot():
    global _bot_running
    _bot_running = False
    return {"ok": True, "message": "Bot stopping..."}


def bot_status():
    return {
        "running": _bot_running,
        "interval": BOT_INTERVAL,
        "testnet_url": TESTNET_URL,
        "has_keys": bool(TESTNET_KEY and TESTNET_SECRET),
        "open_trades": dict(_open_trades),
        "cooldowns": {k: int(time.time() - v) for k, v in _last_signals.items()},
    }
