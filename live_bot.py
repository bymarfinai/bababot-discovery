"""
BabaBot Live Trading — 3-Tier Hybrid System
  Iron Legion (Dumb Bot) — execute tanpa mikir
  Ultron (MiniMax M2.7) — 24/7 gatekeeper
  Jarvis (Claude MCP) — on-demand strategic commander
"""

import os, json, time, hmac, hashlib, threading, traceback, re
from datetime import datetime, timezone
from urllib.parse import urlencode
from collections import deque

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

ULTRON_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
ULTRON_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")
ULTRON_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/anthropic")
ULTRON_ENABLED = os.environ.get("ULTRON_ENABLED", "true").lower() == "true"

CANDLE_BUFFER = 300
LEVERAGE = 50
TF_MAP = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h"}
PAIR_QTY = {
    "BTCUSDT": 0.01, "ETHUSDT": 0.4, "XRPUSDT": 400, "YFIUSDT": 0.1,
    "SOLUSDT": 6, "BNBUSDT": 1.5, "DOGEUSDT": 4000, "LINKUSDT": 60,
    "AVAXUSDT": 30, "PEPEUSDT": 50000000, "1000PEPEUSDT": 50000,
}

_trade_count = 0

# ============================================================
# ACTIVITY LOG — Dashboard reads this
# ============================================================

_activity_log = deque(maxlen=500)

def _log(icon: str, category: str, message: str, detail: dict = None):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "icon": icon,
        "category": category,
        "message": message,
        "detail": detail or {},
    }
    _activity_log.appendleft(entry)
    # Also print to Railway logs
    print(f"[{category}] {icon} {message}")

def get_activity_log(limit: int = 100) -> list:
    return list(_activity_log)[:limit]

# ============================================================
# ULTRON — MiniMax Gatekeeper
# ============================================================

ULTRON_SYSTEM_PROMPT = """You are Ultron, BabaBot's trading co-pilot. Fast entry decisions only.

Rules:
- ONLY skip if genuine danger (BTC crash >3%, regime mismatch, overexposure 3+ positions)
- Do NOT skip for small dips (<2% is normal)
- Trust verified strategy edge (validated 5 years)
- High WR (>80%) + matching regime = ALWAYS proceed

Respond ONLY with JSON: {"decision": "PROCEED" or "SKIP", "reason": "one line", "confidence": 0.0-1.0}"""

def call_ultron(context: str) -> dict:
    if not ULTRON_API_KEY:
        return {"decision": "PROCEED", "reason": "Ultron offline (no API key)", "confidence": 0.5}
    try:
        resp = requests.post(f"{ULTRON_BASE_URL}/v1/messages",
            headers={"Content-Type": "application/json", "x-api-key": ULTRON_API_KEY, "anthropic-version": "2023-06-01"},
            json={"model": ULTRON_MODEL, "max_tokens": 200, "system": ULTRON_SYSTEM_PROMPT,
                  "messages": [{"role": "user", "content": context}]}, timeout=10)
        if resp.status_code != 200:
            _log("⚠️", "Ultron", f"API error {resp.status_code}")
            return {"decision": "PROCEED", "reason": f"API error {resp.status_code}", "confidence": 0.5}
        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text": text = block.get("text", ""); break
        text = re.sub(r'^```json\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)
        r = json.loads(text)
        return {"decision": r.get("decision", "PROCEED"), "reason": r.get("reason", ""), "confidence": float(r.get("confidence", 0.5))}
    except json.JSONDecodeError:
        return {"decision": "PROCEED", "reason": "parse error", "confidence": 0.5}
    except Exception as e:
        return {"decision": "PROCEED", "reason": str(e)[:50], "confidence": 0.5}

def get_btc_context() -> dict:
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/klines",
            params={"symbol": "BTCUSDT", "interval": "1h", "limit": 3}, timeout=5)
        if r.status_code == 200:
            kl = r.json()
            if len(kl) >= 3:
                return {"price": float(kl[-1][4]), "change_2h": round((float(kl[-1][4]) - float(kl[0][1])) / float(kl[0][1]) * 100, 2)}
    except: pass
    return {"price": 0, "change_2h": 0}

def ultron_gatekeeper(cfg, signal_result, btc_ctx, open_count) -> dict:
    if not ULTRON_ENABLED:
        return {"decision": "PROCEED", "reason": "Ultron disabled", "confidence": 1.0}
    combo = cfg["entry_logic"] + (f"+{cfg.get('entry_logic_2','')}" if cfg.get("entry_logic_2") else "")
    ctx = f"""ENTRY DECISION:
- Signal: {combo} {cfg['symbol']} {cfg['timeframe']} {signal_result['side']}
- BTC: ${btc_ctx['price']:.0f} ({btc_ctx['change_2h']:+.1f}% 2h)
- Regime: {signal_result['regime']}
- Open positions: {open_count}
- Strategy WR: {cfg.get('rule_wr', '?')}%
- V={signal_result['features'].get('V','?')} B={signal_result['features'].get('B','?')} RSI={signal_result['features'].get('rsi_val','?')}"""
    return call_ultron(ctx)

# ============================================================
# BINANCE TESTNET API
# ============================================================

def _sign(p):
    p["timestamp"] = int(time.time() * 1000)
    p["signature"] = hmac.new(TESTNET_SECRET.encode(), urlencode(p).encode(), hashlib.sha256).hexdigest()
    return p

def _h(): return {"X-MBX-APIKEY": TESTNET_KEY}

def binance_get(path, params=None, signed=False):
    params = params or {}
    if signed: params = _sign(params)
    return requests.get(f"{TESTNET_URL}{path}", params=params, headers=_h(), timeout=10).json()

def binance_post(path, params):
    return requests.post(f"{TESTNET_URL}{path}", params=_sign(params), headers=_h(), timeout=10).json()

def fetch_klines(symbol, interval, limit=300):
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        if r.status_code == 200: return r.json()
    except: pass
    try:
        r = requests.get(f"{WORKER_URL}/bot/klines", params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=15)
        if r.status_code == 200: return r.json().get("klines", [])
    except: pass
    return []

def klines_to_data(klines):
    if not klines or len(klines) < 50: return None
    arr = np.array([[float(k[0]),float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5]),float(k[9])] for k in klines])
    return {"open_time":arr[:,0],"open":arr[:,1],"high":arr[:,2],"low":arr[:,3],"close":arr[:,4],"volume":arr[:,5],"taker_buy_volume":arr[:,6]}

def get_current_price(symbol):
    try:
        r = requests.get("https://fapi.binance.com/fapi/v1/ticker/price", params={"symbol": symbol}, timeout=5)
        if r.status_code == 200: return float(r.json()["price"])
    except: pass
    return 0.0

def place_order(symbol, side, qty, sl_price, tp_price):
    results = {"market": None, "sl": None, "tp": None, "error": None}
    try:
        try: binance_post("/fapi/v1/leverage", {"symbol": symbol, "leverage": LEVERAGE})
        except: pass
        market = binance_post("/fapi/v1/order", {"symbol": symbol, "side": side, "type": "MARKET", "quantity": qty})
        results["market"] = market
        if "orderId" not in market:
            results["error"] = f"Market order failed: {market}"
            return results
        sl_side = "SELL" if side == "BUY" else "BUY"
        results["sl"] = binance_post("/fapi/v1/order", {"symbol": symbol, "side": sl_side, "type": "STOP_MARKET", "stopPrice": f"{sl_price:.6f}", "closePosition": "true"})
        results["tp"] = binance_post("/fapi/v1/order", {"symbol": symbol, "side": sl_side, "type": "TAKE_PROFIT_MARKET", "stopPrice": f"{tp_price:.6f}", "closePosition": "true"})
    except Exception as e:
        results["error"] = str(e)
    return results

def get_open_positions():
    try:
        pos = binance_get("/fapi/v2/positionRisk", signed=True)
        return [p for p in pos if float(p.get("positionAmt", 0)) != 0]
    except: return []

# ============================================================
# D1 INTERFACE
# ============================================================

def fetch_bot_configs():
    try:
        r = requests.get(f"{WORKER_URL}/bot/config", timeout=10)
        d = r.json()
        if d.get("ok"): return [c for c in d["configs"] if c.get("active")]
    except: pass
    return []

def log_trade(data):
    try: return requests.post(f"{WORKER_URL}/bot/trade-log", json=data, timeout=10).json()
    except: return {"ok": False}

def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN: return
    try: requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

# ============================================================
# SIGNAL DETECTION
# ============================================================

def check_signal(config, data):
    entry_logic = config["entry_logic"]
    entry_logic_2 = config.get("entry_logic_2")
    if entry_logic not in ENTRY_LOGICS: return None
    sc = StrategyConfig(symbol=config["symbol"], timeframe=config["timeframe"], entry_logic=entry_logic,
        entry_logic_2=entry_logic_2 if entry_logic_2 in ENTRY_LOGICS else None,
        sl_pct=config.get("sl_pct", 0.6), tp_pct=config.get("tp_pct", 1.5))
    ind = precompute_indicators(data, sc)
    signals = get_signals(data, ind, sc)
    if sc.entry_logic_2 and sc.entry_logic_2 in ENTRY_LOGICS:
        from dataclasses import replace as dc_replace
        c2 = dc_replace(sc, entry_logic=sc.entry_logic_2)
        s2 = get_signals(data, ind, c2)
        combined = np.zeros(len(signals), dtype=int)
        for i in range(3, len(signals)):
            if signals[i] != 0:
                for j in range(max(0,i-3), i+1):
                    if s2[j] == signals[i]: combined[i] = signals[i]; break
            elif s2[i] != 0:
                for j in range(max(0,i-3), i+1):
                    if signals[j] == s2[i]: combined[i] = s2[i]; break
        signals = combined
    signals = apply_filters(data, ind, signals, sc)
    idx = len(signals) - 2
    if idx < 0 or int(signals[idx]) == 0: return None
    sig = int(signals[idx])
    regimes = classify_regime(data, ind)
    regime = {0:"sideways",1:"bull",-1:"bear",2:"shock"}.get(int(regimes[idx]),"unknown")
    combo_label = entry_logic + (" AND " + entry_logic_2 if entry_logic_2 else "")
    features = extract_signal_features(combo_label, data, ind, idx, signals, regimes)
    return {"signal":sig,"side":"LONG" if sig==1 else "SHORT","features":features,"regime":regime,"price":float(data["close"][idx])}

def check_rule_filter(rule_str, features):
    if not rule_str or not rule_str.strip(): return True
    conditions = parse_rule(rule_str)
    if not conditions: return True
    for feat, op, val in conditions:
        fv = features.get(feat)
        if fv is None or not isinstance(fv,(int,float)): return False
        if op==">=" and not fv>=val: return False
        if op=="<=" and not fv<=val: return False
        if op==">" and not fv>val: return False
        if op=="<" and not fv<val: return False
    return True

# ============================================================
# POSITION MONITOR (Step 4: Ultron position manager)
# ============================================================

_open_trades = {}

def monitor_positions():
    try:
        for p in get_open_positions():
            sym = p.get("symbol","")
            amt = float(p.get("positionAmt",0))
            pnl = float(p.get("unRealizedProfit",0))
            if amt != 0:
                _log("📍", "Iron Legion", f"{sym} uPnL=${pnl:.2f}", {"symbol":sym,"amt":amt,"pnl":pnl})
    except: pass

# ============================================================
# MAIN LOOP
# ============================================================

_bot_running = False
_bot_thread = None
_last_signals = {}
_cycle_count = 0
SIGNAL_COOLDOWN = 300

def _bot_loop():
    global _bot_running, _trade_count, _cycle_count
    try:
        ultron_status = "ONLINE" if ULTRON_ENABLED and ULTRON_API_KEY else "OFFLINE"
        _log("🦾", "Iron Legion", f"Deployed! Ultron: {ultron_status}")

        while _bot_running:
            t0 = time.time()
            _cycle_count += 1
            try:
                configs = fetch_bot_configs()
                if not configs:
                    if _cycle_count % 30 == 1:  # log every ~30 min so terminal shows sign of life
                        _log("💤", "Iron Legion", f"Cycle #{_cycle_count}: 0 active configs in D1 — waiting")
                    time.sleep(BOT_INTERVAL); continue

                btc_ctx = get_btc_context()
                groups = {}
                for cfg in configs:
                    groups.setdefault(f"{cfg['symbol']}_{cfg['timeframe']}", []).append(cfg)

                kline_ok, kline_fail, signals_checked = 0, 0, 0
                for gk, gconfigs in groups.items():
                    symbol, tf = gk.split("_", 1)
                    interval = TF_MAP.get(tf)
                    if not interval: continue
                    klines = fetch_klines(symbol, interval, CANDLE_BUFFER)
                    data = klines_to_data(klines)
                    if data is None:
                        kline_fail += 1
                        continue
                    kline_ok += 1

                    for cfg in gconfigs:
                        sid = cfg["strategy_id"]
                        ck = f"{symbol}_{tf}_{cfg['entry_logic']}_{cfg.get('entry_logic_2','')}"
                        if time.time() - _last_signals.get(ck, 0) < SIGNAL_COOLDOWN: continue

                        signals_checked += 1
                        result = check_signal(cfg, data)
                        if result is None: continue

                        side = result["side"]
                        features = result["features"]
                        regime = result["regime"]
                        price = result["price"]
                        combo = cfg["entry_logic"] + (f"+{cfg.get('entry_logic_2','')}" if cfg.get("entry_logic_2") else "")

                        _log("🎯", "Signal", f"{symbol} {tf} {combo} {side} @ ${price:.2f} | regime={regime}",
                             {"symbol":symbol,"tf":tf,"combo":combo,"side":side,"price":price,"regime":regime,"features":features})

                        # Regime gate
                        rg = cfg.get("regime_gate", "all")
                        if rg != "all" and regime not in [x.strip() for x in rg.split(",")]:
                            _log("⏭️", "Filter", f"Regime gate blocked: {regime} not in [{rg}]")
                            continue

                        # Rule filter
                        rule_str = cfg.get("rule", "")
                        if not check_rule_filter(rule_str, features):
                            _log("⏭️", "Filter", f"Rule filter failed: {rule_str[:60]}")
                            continue

                        _log("✅", "Filter", "All filters passed")

                        # Duplicate
                        if symbol in _open_trades:
                            _log("⏭️", "Iron Legion", f"Already have {symbol} position")
                            continue

                        # ── ULTRON ──
                        ultron = ultron_gatekeeper(cfg, result, btc_ctx, len(_open_trades))
                        decision = ultron["decision"]

                        if decision == "SKIP":
                            _log("❌", "Ultron", f"SKIP — {ultron['reason']} ({ultron['confidence']:.0%})",
                                 {"decision":"SKIP","reason":ultron["reason"],"confidence":ultron["confidence"]})
                            _last_signals[ck] = time.time()
                            continue

                        _log("✅", "Ultron", f"PROCEED — {ultron['reason']} ({ultron['confidence']:.0%})",
                             {"decision":"PROCEED","reason":ultron["reason"],"confidence":ultron["confidence"]})

                        # ── EXECUTE ──
                        sl_pct = cfg.get("sl_pct", 0.6)
                        tp_pct = cfg.get("tp_pct", 1.5)
                        cp = get_current_price(symbol) or price
                        if side == "LONG":
                            sl_p, tp_p, os_ = cp*(1-sl_pct/100), cp*(1+tp_pct/100), "BUY"
                        else:
                            sl_p, tp_p, os_ = cp*(1+sl_pct/100), cp*(1-tp_pct/100), "SELL"

                        qty = PAIR_QTY.get(symbol, 0)
                        if not qty:
                            _log("❌", "Iron Legion", f"No qty for {symbol}"); continue

                        order = place_order(symbol, os_, qty, sl_p, tp_p)
                        if order.get("error"):
                            _log("❌", "Iron Legion", f"Order failed: {order['error'][:150]}")
                            continue

                        # ── LOG ──
                        _trade_count += 1
                        log_trade({
                            "strategy_id":sid,"symbol":symbol,"timeframe":tf,"side":side,
                            "entry_price":cp,"entry_time":datetime.now(timezone.utc).isoformat(),
                            "sl_pct":sl_pct,"tp_pct":tp_pct,"regime_at_entry":regime,
                            "minimax_entry_verdict":f"{decision} ({ultron['reason']})",
                            "backtest_wr":cfg.get("rule_wr",0),
                            "notes":f"Ultron:{ultron['confidence']:.0%} V={features.get('V','?')} B={features.get('B','?')} H={features.get('H','?')}",
                        })
                        _open_trades[symbol] = {"strategy_id":sid,"entry_price":cp}
                        _last_signals[ck] = time.time()

                        _log("🦾", "Iron Legion", f"TRADE #{_trade_count}: {side} {symbol} @ ${cp:.2f} | SL ${sl_p:.2f} TP ${tp_p:.2f}",
                             {"trade_num":_trade_count,"symbol":symbol,"side":side,"entry":cp,"sl":sl_p,"tp":tp_p,
                              "sl_pct":sl_pct,"tp_pct":tp_pct,"regime":regime,"ultron":ultron,"combo":combo,"wr":cfg.get("rule_wr","?")})

                        _log("📚", "Database", f"Trade #{_trade_count} saved — learning data accumulating ({_trade_count} total)")

                # Cycle summary — log every cycle so terminal shows bot is alive
                if _cycle_count % 5 == 0:  # every ~5 min
                    _log("🔄", "Iron Legion", f"Cycle #{_cycle_count}: {len(configs)} configs, klines {kline_ok}✅/{kline_fail}❌, {signals_checked} checked, {_trade_count} trades total")

                monitor_positions()

            except Exception as e:
                _log("❌", "System", f"Cycle #{_cycle_count} error: {e}")
                traceback.print_exc()

            time.sleep(max(1, BOT_INTERVAL - (time.time() - t0)))

    except Exception as e:
        # Outer catch — thread is dying, log it so dashboard shows what happened
        _log("💀", "Iron Legion", f"Thread crashed: {e}")
        traceback.print_exc()
    finally:
        _bot_running = False
        _log("🛑", "Iron Legion", f"Stood down after {_cycle_count} cycles")

# ============================================================
# START / STOP / STATUS
# ============================================================

def start_bot():
    global _bot_running, _bot_thread, _cycle_count
    # If flag says running but thread is dead — reset and restart
    if _bot_running and _bot_thread and not _bot_thread.is_alive():
        _log("🔁", "Iron Legion", "Thread was dead — restarting")
        _bot_running = False
        _bot_thread = None
    if _bot_running: return {"ok": True, "message": "Already running"}
    if not TESTNET_KEY or not TESTNET_SECRET: return {"ok": False, "error": "BINANCE_TESTNET_KEY/SECRET not set"}
    _bot_running = True
    _cycle_count = 0
    _bot_thread = threading.Thread(target=_bot_loop, daemon=True)
    _bot_thread.start()
    u = "ONLINE" if ULTRON_ENABLED and ULTRON_API_KEY else "OFFLINE"
    return {"ok": True, "message": f"Iron Legion deployed, Ultron {u}, interval={BOT_INTERVAL}s"}

def stop_bot():
    global _bot_running
    _bot_running = False
    return {"ok": True, "message": "Iron Legion standing down..."}

def bot_status():
    thread_alive = _bot_thread.is_alive() if _bot_thread else False
    return {
        "running": _bot_running, "thread_alive": thread_alive,
        "cycle_count": _cycle_count,
        "interval": BOT_INTERVAL, "testnet_url": TESTNET_URL,
        "has_keys": bool(TESTNET_KEY and TESTNET_SECRET),
        "ultron": {"enabled": ULTRON_ENABLED, "has_key": bool(ULTRON_API_KEY), "model": ULTRON_MODEL},
        "trade_count": _trade_count, "open_trades": dict(_open_trades),
        "cooldowns": {k: int(time.time()-v) for k,v in _last_signals.items()},
    }
