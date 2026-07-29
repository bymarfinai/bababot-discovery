"""
BBC Live Trading — Wire BBC Switcher engine to live exchange.

v2.2: Per-pair configs + state-safe SKIP handling.
      - Per-pair config: EMA period, TP/SL, body ratios from saved sweep results
      - MTF_SKIP and SW SKIP: cancel position WITHOUT state transition (match backtest)
      - 15m candle fetch: 40 candles for accurate EMA20
      - ConnectionResetError: don't treat as position closed

v2.1: MTF 15m confirmation enabled — fetch 15m candles at entry,
      check for EMA reclaim/reject confirmation before placing order.
      Without MTF: WR 49% (losing). With MTF: WR 65% (profitable).

Architecture:
- 1 Switcher instance per pair (stateful state machine)
- Market orders at candle close (not limit like Baret)
- SL/TP via algoOrder at exchange
- MTF 15m: at entry signal, fetch 4x 15m candles, check confirmation
- Uses same ExchangeClient + logging as baret_live
- Per-pair config: each pair has its own Mode3BBCConfig (EMA, TP, SL, body ratio)

Flow per candle:
1. Fetch closed 1H candle
2. Compute EMA, VAH, VAL
3. Feed candle to Switcher
4. If Switcher opened position:
   a. Fetch 4x 15m candles for that hour
   b. Check MTF confirmation (EMA reclaim/reject on 15m)
   c. If confirmed → place market order at 15m entry price + SL/TP
   d. If NOT confirmed → cancel switcher position (NO state change)
5. If Switcher closed position → verify exchange state
6. Between candles: exchange monitors SL/TP via algoOrder
"""

import time
import threading
import traceback
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import deque

from baret_live import (
    ExchangeClient, _log, _send_telegram, _get_price,
    _fetch_candles, _calc_quantity, _place_sl_tp, _cancel_sl_tp,
    _fmt_price, _fmt_qty, _log_trade_to_d1,
    _get_default_client, _account_bots,
    PRECISION,
)
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher


# ══════════════════════════════════════════════
# INDICATORS (same as backtest engine)
# ══════════════════════════════════════════════

def _compute_ema(closes, period):
    """Compute EMA series from close prices."""
    if len(closes) < period:
        return [closes[-1]] * len(closes)
    ema = [0.0] * len(closes)
    ema[0] = closes[0]
    k = 2.0 / (period + 1)
    for i in range(1, len(closes)):
        ema[i] = closes[i] * k + ema[i - 1] * (1 - k)
    return ema


def _compute_va(highs, lows, closes, volumes, window, pct_high=85, pct_low=15):
    """Compute rolling Value Area (percentile-based). Returns (vah_list, val_list, poc_list)."""
    n = len(highs)
    vah_list = [None] * n
    val_list = [None] * n
    poc_list = [None] * n
    for i in range(window, n):
        h_slice = highs[i - window:i]
        l_slice = lows[i - window:i]
        c_slice = closes[i - window:i]
        vah_list[i] = float(np.percentile(h_slice, pct_high))
        val_list[i] = float(np.percentile(l_slice, pct_low))
        if volumes and len(volumes) >= i:
            v_slice = volumes[i - window:i]
            typical = [(h_slice[j] + l_slice[j] + c_slice[j]) / 3 for j in range(window)]
            total_v = sum(v_slice) or 1
            poc_list[i] = sum(typical[j] * v_slice[j] for j in range(window)) / total_v
        else:
            poc_list[i] = (vah_list[i] + val_list[i]) / 2
    return vah_list, val_list, poc_list


# ══════════════════════════════════════════════
# MTF 15m CONFIRMATION (v2.1 — critical for WR)
# ══════════════════════════════════════════════

def _check_mtf_bull_entry(candles_15m):
    """Check if any of the 4 15m candles confirms BULL EMA reclaim.
    Returns (entry_price, sl_price) or (None, None) if no confirmation.
    Same logic as backtest compute_mtf_bull_entry().
    """
    if not candles_15m or len(candles_15m) < 4:
        return None, None
    closes = [c["close"] for c in candles_15m]
    ema15 = _compute_ema(closes, 20)
    for i in range(len(candles_15m)):
        c = candles_15m[i]
        ema_val = ema15[i] if i < len(ema15) else ema15[-1]
        if c["low"] <= ema_val and c["close"] > ema_val and c["close"] > c["open"]:
            return c["close"], c["low"]
    return None, None


def _check_mtf_bear_entry(candles_15m):
    """Check if any of the 4 15m candles confirms BEAR EMA reject.
    Returns (entry_price, sl_price) or (None, None) if no confirmation.
    Same logic as backtest compute_mtf_bear_entry().
    """
    if not candles_15m or len(candles_15m) < 4:
        return None, None
    closes = [c["close"] for c in candles_15m]
    ema15 = _compute_ema(closes, 20)
    for i in range(len(candles_15m)):
        c = candles_15m[i]
        ema_val = ema15[i] if i < len(ema15) else ema15[-1]
        if c["high"] >= ema_val and c["close"] < ema_val and c["close"] < c["open"]:
            return c["close"], c["high"]
    return None, None


def _fetch_15m_for_mtf(symbol, count=40):
    """Fetch recent 15m candles for MTF confirmation. 
    40 candles = 10 hours, enough for EMA20 computation + 4-candle window.
    (v2.2: increased from 24 → 40 for accurate EMA20 — first 19 values are meaningless)
    """
    try:
        candles = _fetch_candles(symbol, "15m", count)
        return candles if candles else []
    except Exception as e:
        _log(f"  ⚠️ MTF 15m fetch {symbol}: {e}")
        return []


# ══════════════════════════════════════════════
# BBC LIVE STATE
# ══════════════════════════════════════════════

class BBCPairState:
    """Tracks BBC state for one pair."""
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.config = config
        self.switcher = Switcher(config)
        self.candle_history = []
        self.exchange_position = None
        self.bar_idx = 0
        self.last_candle_time = 0
        self.warmup_ok = False


# ══════════════════════════════════════════════
# PER-PAIR CONFIG BUILDER (v2.2)
# ══════════════════════════════════════════════

def _build_pair_config(symbol, position_usd, leverage, config_overrides=None):
    """Build Mode3BBCConfig for a specific pair.
    
    config_overrides can be:
      - flat dict: applies to ALL pairs (backwards compatible)
      - nested dict with symbol keys: {"SOLUSDT": {"ema_period": 7, ...}}
      - mixed: flat keys + symbol keys
    """
    cfg = Mode3BBCConfig()
    cfg.entry_usd = position_usd
    cfg.leverage = leverage

    if config_overrides:
        # Apply flat (non-dict) overrides first (global defaults)
        for k, v in config_overrides.items():
            if not isinstance(v, dict) and hasattr(cfg, k):
                setattr(cfg, k, v)
        # Apply per-pair overrides (takes priority)
        if symbol in config_overrides and isinstance(config_overrides[symbol], dict):
            for k, v in config_overrides[symbol].items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

    # v2.1: MTF 15m handled MANUALLY in live loop (not by switcher)
    cfg.bull_mtf_15m_enabled = False
    cfg.bear_mtf_15m_enabled = False
    cfg.sideways_mtf_15m_enabled = False

    return cfg


# ══════════════════════════════════════════════
# BBC LIVE LOOP
# ══════════════════════════════════════════════

_bbc_live_running = False
_bbc_live_thread = None
_bbc_live_state = {
    "mode": "bbc",
    "pairs": {},
    "cycle_count": 0,
    "last_cycle": None,
    "started_at": None,
    "active_pairs": [],
    "positions": {},
    "error": None,
}


def _next_candle_close(now, interval_min):
    """Calculate next candle close time. Uses epoch-aligned boundaries."""
    EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)
    elapsed = (now - EPOCH).total_seconds()
    interval_sec = interval_min * 60
    current_boundary = EPOCH + timedelta(seconds=(elapsed // interval_sec) * interval_sec)
    return current_boundary + timedelta(seconds=interval_sec)


def _is_connection_error(e):
    """Check if exception is a connection/network error (should retry, not treat as position closed)."""
    err_str = str(e).lower()
    return isinstance(e, (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError)) \
        or "connection" in err_str or "reset" in err_str or "timeout" in err_str \
        or "broken pipe" in err_str or "eof" in err_str


def _bbc_live_loop(symbols, timeframe="1h", position_usd=10.0, leverage=50,
                   config_overrides=None, client=None, state=None,
                   running_check=None, acct_name=""):
    """Main BBC live trading loop."""
    global _bbc_live_running

    if client is None:
        client = _get_default_client()
        client.leverage = leverage
    if state is None:
        state = _bbc_live_state
    if running_check is None:
        running_check = lambda: _bbc_live_running

    prefix = f"[BBC {acct_name}] " if acct_name else "[BBC] "

    try:
        # ═══ v2.2: PER-PAIR CONFIGS ═══
        # Each pair gets its own Mode3BBCConfig (EMA, TP/SL, body ratios)
        pair_states = {}
        for symbol in symbols:
            cfg = _build_pair_config(symbol, position_usd, leverage, config_overrides)
            pair_states[symbol] = BBCPairState(symbol, cfg)
            try:
                client.set_leverage(symbol)
            except Exception as e:
                _log(f"{prefix}  ⚠️ set_leverage {symbol}: {e}")

        # MTF is checked manually — this flag controls it
        mtf_15m_enabled = True  # <-- THE FIX: always check 15m confirmation

        state["mode"] = "bbc"
        state["started_at"] = datetime.now(timezone.utc).isoformat()
        state["active_pairs"] = symbols
        state["error"] = None

        tf_minutes = {"15m": 15, "1h": 60, "4h": 240}
        interval_min = tf_minutes.get(timeframe, 60)

        # Log per-pair configs
        for symbol in symbols:
            pc = pair_states[symbol].config
            _log(f"{prefix}  📋 {symbol}: EMA={pc.ema_period} TP={pc.tp_pct*100:.1f}% SL={pc.sl_pct*100:.1f}% BullBody={pc.bull_body_ratio_min} BearBody={pc.bear_body_ratio_min}")

        _log(f"{prefix}═══ BBC LIVE STARTED ═══ {len(symbols)} pairs, TF={timeframe}, ${position_usd}/trade, {leverage}x, MTF15m={'ON' if mtf_15m_enabled else 'OFF'}")
        _send_telegram(f"📊 BBC LIVE STARTED\nPairs: {', '.join(symbols)}\nTF: {timeframe}\nPosition: ${position_usd}\nMTF 15m: {'ON ✅' if mtf_15m_enabled else 'OFF ❌'}\nPer-pair configs: ON")

        # ═══ WARMUP ═══
        for symbol in symbols:
            ps = pair_states[symbol]
            warmup_count = ps.config.startup_warmup_candles + 10
            if symbol == symbols[0]:
                _log(f"{prefix}  🔥 Warming up Switchers ({warmup_count} candles)...")
            try:
                candles = _fetch_candles(symbol, timeframe, warmup_count)
                if not candles:
                    _log(f"{prefix}  ❌ {symbol}: _fetch_candles returned empty/None")
                    continue
                if len(candles) < ps.config.startup_warmup_candles:
                    _log(f"{prefix}  ⚠️ {symbol}: only {len(candles)} candles (need {ps.config.startup_warmup_candles}), skipping")
                    continue

                opens = [c["open"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                closes = [c["close"] for c in candles]
                volumes = [c.get("volume", 1.0) for c in candles]

                ema_series = _compute_ema(closes, ps.config.ema_period)
                vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, ps.config.va_window)

                for i in range(len(candles)):
                    ps.switcher.process_candle(
                        i, opens[i], highs[i], lows[i], closes[i],
                        ema_series[i], vah_list[i], val_list[i], poc_list[i]
                    )

                ps.bar_idx = len(candles)
                ps.candle_history = candles
                ps.last_candle_time = candles[-1]["time"] if candles else 0
                ps.warmup_ok = True

                sw_state = ps.switcher.state
                sw_pos = "LONG" if ps.switcher.position and ps.switcher.position.side == "LONG" else (
                    "SHORT" if ps.switcher.position else "flat"
                )
                _log(f"{prefix}  ✅ {symbol}: warmup done, state={sw_state}, position={sw_pos}, {len(ps.switcher.trades)} warmup trades")

            except Exception as e:
                _log(f"{prefix}  ❌ {symbol} warmup CRASHED: {e}")
                _log(f"{prefix}     {traceback.format_exc()}")

        warmed = [s for s, ps in pair_states.items() if ps.warmup_ok]
        if not warmed:
            _log(f"{prefix}  ❌ ALL pairs failed warmup. BBC cannot start.")
            _send_telegram(f"❌ BBC FAILED: All pairs failed warmup")
            state["error"] = "All pairs failed warmup"
            _bbc_live_running = False
            return
        _log(f"{prefix}  ✅ {len(warmed)}/{len(symbols)} pairs warmed up: {', '.join(warmed)}")

        state["pairs"] = {s: {"state": ps.switcher.state, "position": None} for s, ps in pair_states.items() if ps.warmup_ok}

        # ═══ CLEANUP ORPHAN POSITIONS ═══
        for symbol in symbols:
            try:
                pos = client.get_position(symbol)
                if pos and float(pos.get("positionAmt", 0)) != 0:
                    amt = float(pos["positionAmt"])
                    side_close = "SELL" if amt > 0 else "BUY"
                    client.cancel_all_orders(symbol)
                    _cancel_sl_tp(client, symbol)
                    client.place_market_close(symbol, side_close, abs(amt))
                    _log(f"{prefix}  🧹 {symbol}: closed orphan position")
            except Exception as e:
                _log(f"{prefix}  ⚠️ Orphan cleanup {symbol}: {e}")

        _log(f"{prefix}  ⏰ Cycle interval: {interval_min}min")

        poll_sec = 15
        cycle = 0
        last_processed_boundary = 0

        while running_check():
            now = datetime.now(timezone.utc)
            nxt = _next_candle_close(now, interval_min)
            wait_secs = (nxt - now).total_seconds() + 5

            boundary_epoch = int(nxt.timestamp())
            if boundary_epoch == last_processed_boundary:
                nxt2 = nxt + timedelta(minutes=interval_min)
                wait_secs = (nxt2 - now).total_seconds() + 5
                nxt = nxt2
                boundary_epoch = int(nxt.timestamp())

            if wait_secs > 30:
                _log(f"{prefix}  ⏰ Next {timeframe} close: {nxt.strftime('%H:%M')} UTC ({int(wait_secs//60)}m {int(wait_secs%60)}s)")

            # ═══ INTER-CANDLE POLLING (SL/TP monitoring) ═══
            while wait_secs > 0 and running_check():
                time.sleep(min(poll_sec, max(1, wait_secs)))
                wait_secs -= poll_sec

                for symbol, ps in pair_states.items():
                    if not ps.warmup_ok or not ps.exchange_position:
                        continue
                    try:
                        ex_pos = client.get_position(symbol)
                        if ex_pos is None:
                            # v2.1: connection error — DON'T treat as position closed
                            continue
                        if float(ex_pos.get("positionAmt", 0)) == 0:
                            ep = ps.exchange_position
                            cp = _get_price(symbol)
                            if cp is None or cp <= 0:
                                continue
                            side = ep["side"]
                            entry = ep["entry"]
                            qty = ep["qty"]
                            pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                            pnl_dollar = pnl_pct / 100 * entry * qty

                            # v2.2: Sanity check — if PnL is near zero, likely connection glitch not real SL
                            if abs(pnl_pct) < 0.02:
                                # Re-check position after short delay
                                time.sleep(2)
                                recheck = client.get_position(symbol)
                                if recheck is None:
                                    _log(f"{prefix}  ⚠️ {symbol}: near-zero PnL ({pnl_pct:+.3f}%) + recheck=None → connection issue, skipping")
                                    continue
                                if float(recheck.get("positionAmt", 0)) != 0:
                                    _log(f"{prefix}  ⚠️ {symbol}: near-zero PnL but position still open on recheck — false alarm")
                                    continue

                            hit = "TP" if pnl_pct > 0 else "SL"
                            emoji = "🎯" if hit == "TP" else "🛑"

                            _log(f"{prefix}  {emoji} {symbol} {side} {hit} (exchange) @ ~${cp:.4f} | PnL: {pnl_pct:+.2f}%")
                            _send_telegram(f"{emoji} *BBC {symbol} {side} {hit}*\nEntry: ${entry:.4f}\nExit: ~${cp:.4f}\nPnL: {pnl_pct:+.2f}%")
                            _log_trade_to_d1(symbol, timeframe, side, entry, cp,
                                ep.get("filled_at", ""), datetime.now(timezone.utc).isoformat(),
                                ps.config.sl_pct * 100, ps.config.tp_pct * 100,
                                pnl_dollar, pnl_pct, hit, acct_name)

                            ps.exchange_position = None
                            state["positions"].pop(symbol, None)

                            if ps.switcher.position:
                                ps.switcher._close_position(ps.bar_idx, cp, hit)

                    except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
                        _log(f"{prefix}  ⚠️ Connection error monitoring {symbol} — will retry")
                    except Exception as e:
                        if _is_connection_error(e):
                            _log(f"{prefix}  ⚠️ Connection error monitoring {symbol} — will retry")
                        else:
                            _log(f"{prefix}  ⚠️ Monitor {symbol}: {e}")

            if not running_check():
                break

            # ═══ CANDLE CYCLE ═══
            cycle += 1
            last_processed_boundary = boundary_epoch
            state["cycle_count"] = cycle
            state["last_cycle"] = datetime.now(timezone.utc).isoformat()
            _log(f"{prefix}═══ CYCLE {cycle} ═══")

            for symbol in symbols:
                if not running_check():
                    break

                ps = pair_states[symbol]
                if not ps.warmup_ok:
                    continue

                try:
                    candles = _fetch_candles(symbol, timeframe, ps.config.va_window + 10)
                    if not candles or len(candles) < ps.config.va_window:
                        _log(f"{prefix}  ⚠️ {symbol}: insufficient candles ({len(candles) if candles else 0})")
                        continue

                    latest_time = candles[-1]["time"]
                    if latest_time <= ps.last_candle_time:
                        _log(f"{prefix}  ⏩ {symbol}: no new candle yet (latest={latest_time}, last={ps.last_candle_time})")
                        continue
                    ps.last_candle_time = latest_time

                    opens = [c["open"] for c in candles]
                    highs = [c["high"] for c in candles]
                    lows = [c["low"] for c in candles]
                    closes = [c["close"] for c in candles]
                    volumes = [c.get("volume", 1.0) for c in candles]

                    # v2.2: use per-pair config EMA period
                    ema_series = _compute_ema(closes, ps.config.ema_period)
                    vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, ps.config.va_window)

                    last = candles[-1]
                    last_ema = ema_series[-1]
                    last_vah = vah_list[-1]
                    last_val = val_list[-1]
                    last_poc = poc_list[-1]

                    had_position = ps.switcher.position is not None
                    old_side = ps.switcher.position.side if had_position else None

                    ps.bar_idx += 1
                    ps.switcher.process_candle(
                        ps.bar_idx,
                        last["open"], last["high"], last["low"], last["close"],
                        last_ema, last_vah, last_val, last_poc
                    )

                    has_position = ps.switcher.position is not None
                    new_state = ps.switcher.state

                    _log(f"{prefix}  📊 {symbol}: state={new_state} | EMA{ps.config.ema_period}={last_ema:.2f} VAH={last_vah:.2f} VAL={last_val:.2f} | close=${last['close']:.4f}")

                    # ═══ NEW POSITION OPENED ═══
                    if not had_position and has_position:
                        sp = ps.switcher.position
                        side = sp.side
                        entry_price = sp.entry_price
                        sl_price = sp.sl_level
                        tp_price = sp.tp_level
                        tool = sp.tool

                        # v2.2: Skip SIDEWAYS entries — proven unprofitable (WR 35%)
                        # Cancel position WITHOUT state transition (match backtest behavior)
                        if tool == "SIDEWAYS":
                            _log(f"{prefix}  ⏩ {symbol}: SKIP SIDEWAYS entry ({side}) — position cancelled, state unchanged")
                            ps.switcher.position = None  # v2.2 FIX: no _close_position, no state change
                            continue

                        # ═══ v2.1: MTF 15m CONFIRMATION ═══
                        if mtf_15m_enabled and tool in ("BULL", "BEAR"):
                            candles_15m = _fetch_15m_for_mtf(symbol, 40)  # v2.2: 40 candles for accurate EMA20
                            if candles_15m and len(candles_15m) >= 4:
                                # Check last 4 15m candles (= the 1H candle period)
                                # But compute EMA on full history for accuracy
                                closes_15m = [c["close"] for c in candles_15m]
                                ema15_series = _compute_ema(closes_15m, 20)

                                mtf_entry = None
                                mtf_sl = None

                                if tool == "BULL":
                                    for j in range(len(candles_15m) - 4, len(candles_15m)):
                                        c15 = candles_15m[j]
                                        ema15 = ema15_series[j]
                                        if c15["low"] <= ema15 and c15["close"] > ema15 and c15["close"] > c15["open"]:
                                            mtf_entry = c15["close"]
                                            mtf_sl = c15["low"]
                                            break
                                else:  # BEAR
                                    for j in range(len(candles_15m) - 4, len(candles_15m)):
                                        c15 = candles_15m[j]
                                        ema15 = ema15_series[j]
                                        if c15["high"] >= ema15 and c15["close"] < ema15 and c15["close"] < c15["open"]:
                                            mtf_entry = c15["close"]
                                            mtf_sl = c15["high"]
                                            break

                                if mtf_entry is None:
                                    # v2.2 FIX: No 15m confirmation → cancel position WITHOUT state transition
                                    _log(f"{prefix}  ⏩ {symbol}: {tool} signal but NO 15m confirmation — position cancelled, state unchanged")
                                    ps.switcher.position = None  # v2.2 FIX: no _close_position, no state change
                                    continue
                                else:
                                    # Use 15m entry price (more precise than 1H close)
                                    entry_price = mtf_entry
                                    # SL/TP: use per-pair config
                                    if side == "LONG":
                                        sl_price = entry_price * (1 - ps.config.sl_pct)
                                        tp_price = entry_price * (1 + ps.config.tp_pct)
                                    else:
                                        sl_price = entry_price * (1 + ps.config.get_bear_sl_pct())
                                        tp_price = entry_price * (1 - ps.config.get_bear_tp_pct())
                                    _log(f"{prefix}  ✅ {symbol}: 15m confirmed {tool} entry @ ${mtf_entry:.4f}")
                            else:
                                _log(f"{prefix}  ⚠️ {symbol}: 15m candles unavailable, using 1H entry")
                        # ═══ END MTF 15m ═══

                        order_side = "BUY" if side == "LONG" else "SELL"
                        qty = _calc_quantity(symbol, entry_price, position_usd, leverage)

                        _log(f"{prefix}  📊 {symbol} BBC ENTRY: {tool} {side} @ ${entry_price:.4f} | TP=${tp_price:.4f} ({ps.config.tp_pct*100:.1f}%) SL=${sl_price:.4f} ({ps.config.sl_pct*100:.1f}%)")

                        result = client.api_post("/fapi/v1/order", {
                            "symbol": symbol, "side": order_side, "type": "MARKET",
                            "quantity": _fmt_qty(symbol, qty),
                        })

                        if result.get("orderId"):
                            time.sleep(1)
                            ex_pos = client.get_position(symbol)
                            if ex_pos:
                                actual_entry = float(ex_pos.get("entryPrice", entry_price))
                                actual_qty = abs(float(ex_pos.get("positionAmt", qty)))

                                if side == "LONG":
                                    tp_price = actual_entry * (1 + ps.config.tp_pct)
                                    sl_price = actual_entry * (1 - ps.config.sl_pct)
                                else:
                                    tp_price = actual_entry * (1 - ps.config.get_bear_tp_pct())
                                    sl_price = actual_entry * (1 + ps.config.get_bear_sl_pct())

                                sl_tp = _place_sl_tp(client, symbol, side, sl_price, tp_price)

                                ps.exchange_position = {
                                    "side": side, "entry": actual_entry, "qty": actual_qty,
                                    "tp": tp_price, "sl": sl_price, "tool": tool,
                                    "sl_algo_id": sl_tp.get("sl", {}).get("algoId"),
                                    "tp_algo_id": sl_tp.get("tp", {}).get("algoId"),
                                    "filled_at": datetime.now(timezone.utc).isoformat(),
                                }
                                state["positions"][symbol] = {
                                    "side": side, "entry": actual_entry, "qty": actual_qty,
                                    "tp": tp_price, "sl": sl_price, "tool": tool,
                                }

                                _send_telegram(
                                    f"📊 *BBC ENTRY: {tool} {side}*\n"
                                    f"{symbol} @ ${actual_entry:.4f}\n"
                                    f"TP: ${tp_price:.4f} ({ps.config.tp_pct*100:.1f}%)\n"
                                    f"SL: ${sl_price:.4f} ({ps.config.sl_pct*100:.1f}%)\n"
                                    f"EMA: {ps.config.ema_period}\n"
                                    f"State: {new_state}\n"
                                    f"MTF: {'15m confirmed ✅' if mtf_15m_enabled else 'OFF'}"
                                )
                                _log(f"{prefix}  ✅ {symbol} {side} FILLED @ ${actual_entry:.4f}")
                            else:
                                _log(f"{prefix}  ⚠️ {symbol}: order placed but position not found")
                        else:
                            _log(f"{prefix}  ❌ {symbol} order FAILED: {result.get('msg', result)}")

                    # ═══ POSITION CLOSED BY SWITCHER ═══
                    elif had_position and not has_position:
                        if ps.exchange_position:
                            ep = ps.exchange_position
                            _log(f"{prefix}  📊 {symbol}: Switcher closed position, closing on exchange...")

                            try:
                                client.cancel_all_orders(symbol)
                                _cancel_sl_tp(client, symbol)
                                ex_pos = client.get_position(symbol)
                                if ex_pos:
                                    amt = abs(float(ex_pos.get("positionAmt", 0)))
                                    if amt > 0:
                                        close_side = "SELL" if ep["side"] == "LONG" else "BUY"
                                        client.place_market_close(symbol, close_side, amt)
                                        time.sleep(1)

                                cp = _get_price(symbol)
                                side = ep["side"]
                                entry = ep["entry"]
                                pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                                pnl_dollar = pnl_pct / 100 * entry * ep["qty"]

                                exit_type = ps.switcher.trades[-1].exit_type if ps.switcher.trades else "CLOSE"
                                emoji = "🎯" if exit_type == "TP" else ("🛑" if exit_type == "SL" else "📊")

                                _log(f"{prefix}  {emoji} {symbol} {side} {exit_type} @ ${cp:.4f} | PnL: {pnl_pct:+.2f}% (${pnl_dollar:+.2f})")
                                _send_telegram(f"{emoji} *BBC {symbol} {side} {exit_type}*\nEntry: ${entry:.4f}\nExit: ${cp:.4f}\nPnL: {pnl_pct:+.2f}%\nState: {new_state}")
                                _log_trade_to_d1(symbol, timeframe, side, entry, cp,
                                    ep.get("filled_at", ""), datetime.now(timezone.utc).isoformat(),
                                    ps.config.sl_pct * 100, ps.config.tp_pct * 100,
                                    pnl_dollar, pnl_pct, exit_type, acct_name)

                            except Exception as e:
                                _log(f"{prefix}  ❌ {symbol} close error: {e}")

                            ps.exchange_position = None
                            state["positions"].pop(symbol, None)

                    # ═══ POSITION FLIPPED ═══
                    elif had_position and has_position and old_side != ps.switcher.position.side:
                        _log(f"{prefix}  🔄 {symbol}: position FLIPPED {old_side} → {ps.switcher.position.side}")
                        if ps.exchange_position:
                            ep = ps.exchange_position
                            try:
                                client.cancel_all_orders(symbol)
                                _cancel_sl_tp(client, symbol)
                                ex_pos = client.get_position(symbol)
                                if ex_pos:
                                    amt = abs(float(ex_pos.get("positionAmt", 0)))
                                    if amt > 0:
                                        close_side = "SELL" if ep["side"] == "LONG" else "BUY"
                                        client.place_market_close(symbol, close_side, amt)
                                        time.sleep(1)
                            except Exception as e:
                                _log(f"{prefix}  ⚠️ {symbol} flip close error: {e}")
                            ps.exchange_position = None

                        sp = ps.switcher.position
                        side = sp.side
                        entry_price = sp.entry_price
                        order_side = "BUY" if side == "LONG" else "SELL"
                        qty = _calc_quantity(symbol, entry_price, position_usd, leverage)
                        result = client.api_post("/fapi/v1/order", {
                            "symbol": symbol, "side": order_side, "type": "MARKET",
                            "quantity": _fmt_qty(symbol, qty),
                        })
                        if result.get("orderId"):
                            time.sleep(1)
                            ex_pos = client.get_position(symbol)
                            if ex_pos:
                                actual_entry = float(ex_pos.get("entryPrice", entry_price))
                                actual_qty = abs(float(ex_pos.get("positionAmt", qty)))
                                if side == "LONG":
                                    tp_price = actual_entry * (1 + ps.config.tp_pct)
                                    sl_price = actual_entry * (1 - ps.config.sl_pct)
                                else:
                                    tp_price = actual_entry * (1 - ps.config.get_bear_tp_pct())
                                    sl_price = actual_entry * (1 + ps.config.get_bear_sl_pct())
                                sl_tp = _place_sl_tp(client, symbol, side, sl_price, tp_price)
                                ps.exchange_position = {
                                    "side": side, "entry": actual_entry, "qty": actual_qty,
                                    "tp": tp_price, "sl": sl_price, "tool": sp.tool,
                                    "sl_algo_id": sl_tp.get("sl", {}).get("algoId"),
                                    "tp_algo_id": sl_tp.get("tp", {}).get("algoId"),
                                    "filled_at": datetime.now(timezone.utc).isoformat(),
                                }
                                state["positions"][symbol] = {
                                    "side": side, "entry": actual_entry, "qty": actual_qty,
                                    "tp": tp_price, "sl": sl_price, "tool": sp.tool,
                                }
                                _send_telegram(f"🔄 *BBC FLIP: {sp.tool} {side}*\n{symbol} @ ${actual_entry:.4f}\nTP: ${tp_price:.4f} SL: ${sl_price:.4f}")

                    state["pairs"][symbol] = {
                        "state": new_state,
                        "position": ps.exchange_position,
                        "warmup": ps.switcher.state == "STARTUP",
                    }

                except Exception as e:
                    _log(f"{prefix}  ❌ {symbol} error: {e}")
                    _log(f"{prefix}     {traceback.format_exc()}")

            _log(f"{prefix}═══ CYCLE {cycle} DONE ═══")

    except Exception as e:
        err_msg = f"FATAL CRASH: {e}"
        _log(f"{prefix}  💀 {err_msg}")
        _log(f"{prefix}     {traceback.format_exc()}")
        state["error"] = err_msg
        try:
            _send_telegram(f"💀 *BBC CRASHED*\n{err_msg}")
        except:
            pass

    _log(f"{prefix}═══ BBC LIVE STOPPED ═══")
    _bbc_live_running = False


# ══════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════

def start_bbc_live(symbols=None, timeframe="1h", position_usd=10.0, leverage=50,
                   config_overrides=None):
    global _bbc_live_running, _bbc_live_thread

    if _bbc_live_running:
        return {"ok": True, "message": "BBC already running", "state": _bbc_live_state}

    if symbols is None:
        symbols = ["BTCUSDT"]

    _bbc_live_running = True
    _bbc_live_state["cycle_count"] = 0
    _bbc_live_state["error"] = None
    _bbc_live_thread = threading.Thread(
        target=_bbc_live_loop,
        args=(symbols, timeframe, position_usd, leverage, config_overrides),
        daemon=True,
    )
    _bbc_live_thread.start()
    return {"ok": True, "message": f"BBC live started: {', '.join(symbols)}, TF={timeframe}"}


def stop_bbc_live():
    global _bbc_live_running
    _bbc_live_running = False
    return {"ok": True, "message": "BBC live stopped"}


def bbc_live_status():
    return {
        "ok": True,
        "running": _bbc_live_running,
        "thread_alive": _bbc_live_thread.is_alive() if _bbc_live_thread else False,
        **_bbc_live_state,
    }
