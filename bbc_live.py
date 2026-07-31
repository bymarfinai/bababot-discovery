"""
BBC Live Trading — v3.0: MTF 15m INSIDE switcher (same as backtest).

v3.0 FIX: MTF 15m enabled in switcher config (not manually checked outside).
     Entry price = 15m close (same as backtest), not 1H close.
     Warmup pre-computes MTF arrays. Live cycle extends per bar.

v2.2: Per-pair configs + state-safe SKIP handling.

v3.1: Detection layers — phantom position check after warmup + dead bot alert.
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
    if len(closes) < period:
        return [closes[-1]] * len(closes)
    ema = [0.0] * len(closes)
    ema[0] = closes[0]
    k = 2.0 / (period + 1)
    for i in range(1, len(closes)):
        ema[i] = closes[i] * k + ema[i - 1] * (1 - k)
    return ema


def _compute_va(highs, lows, closes, volumes, window, pct_high=85, pct_low=15):
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
# MTF 15m — SAME FUNCTIONS AS BACKTEST
# ══════════════════════════════════════════════

def _compute_mtf_bull_for_bar(candles_15m_for_hour):
    """Check 4 15m candles for BULL EMA reclaim. Same logic as backtest.
    Returns (entry_close, entry_low) or (None, None)."""
    if not candles_15m_for_hour or len(candles_15m_for_hour) < 4:
        return None, None
    closes = [c["close"] for c in candles_15m_for_hour]
    ema15 = _compute_ema(closes, 20)
    for i in range(len(candles_15m_for_hour)):
        c = candles_15m_for_hour[i]
        ev = ema15[i] if i < len(ema15) else ema15[-1]
        if c["low"] <= ev and c["close"] > ev and c["close"] > c["open"]:
            return c["close"], c["low"]
    return None, None


def _compute_mtf_bear_for_bar(candles_15m_for_hour):
    """Check 4 15m candles for BEAR EMA reject. Same logic as backtest.
    Returns (entry_close, entry_high) or (None, None)."""
    if not candles_15m_for_hour or len(candles_15m_for_hour) < 4:
        return None, None
    closes = [c["close"] for c in candles_15m_for_hour]
    ema15 = _compute_ema(closes, 20)
    for i in range(len(candles_15m_for_hour)):
        c = candles_15m_for_hour[i]
        ev = ema15[i] if i < len(ema15) else ema15[-1]
        if c["high"] >= ev and c["close"] < ev and c["close"] < c["open"]:
            return c["close"], c["high"]
    return None, None


def _compute_mtf_arrays(candles_1h, all_15m_candles):
    """Pre-compute MTF arrays for warmup — SAME as backtest.
    
    For each 1H candle, find matching 15m candles by timestamp,
    check bull/bear confirmation, build arrays indexed by bar_idx.
    """
    n = len(candles_1h)
    bull_ec = [None] * n
    bull_el = [None] * n
    bear_ec = [None] * n
    bear_eh = [None] * n
    
    # Index 15m candles by timestamp for fast lookup
    idx_15m = {}
    for c in all_15m_candles:
        idx_15m[c["time"]] = c
    
    for i, c1h in enumerate(candles_1h):
        t = c1h["time"]
        # Get 4 15m candles within this 1H period
        M = 15 * 60 * 1000
        candles_in_hour = []
        for k in range(4):
            c15 = idx_15m.get(t + k * M)
            if c15:
                candles_in_hour.append(c15)
        
        if len(candles_in_hour) >= 4:
            # Need full 15m history for accurate EMA20
            # Get all 15m candles up to and including this hour
            hour_end = t + 4 * M
            history_15m = [c for c in all_15m_candles if c["time"] <= hour_end]
            if len(history_15m) >= 20:
                closes_15m = [c["close"] for c in history_15m]
                ema15 = _compute_ema(closes_15m, 20)
                
                # Check last 4 candles (the ones in this hour)
                for k in range(4):
                    c15_time = t + k * M
                    c15 = idx_15m.get(c15_time)
                    if not c15:
                        continue
                    # Find index in history
                    try:
                        j = next(idx for idx, c in enumerate(history_15m) if c["time"] == c15_time)
                    except StopIteration:
                        continue
                    ev = ema15[j]
                    
                    # BULL check
                    if bull_ec[i] is None:
                        if c15["low"] <= ev and c15["close"] > ev and c15["close"] > c15["open"]:
                            bull_ec[i] = c15["close"]
                            bull_el[i] = c15["low"]
                    
                    # BEAR check
                    if bear_ec[i] is None:
                        if c15["high"] >= ev and c15["close"] < ev and c15["close"] < c15["open"]:
                            bear_ec[i] = c15["close"]
                            bear_eh[i] = c15["high"]
    
    return bull_ec, bull_el, bear_ec, bear_eh


def _fetch_15m_for_period(symbol, start_time_ms, count=40):
    """Fetch 15m candles for a period. Returns list of candle dicts."""
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
    def __init__(self, symbol, config):
        self.symbol = symbol
        self.config = config
        self.switcher = Switcher(config)
        self.candle_history = []
        self.exchange_position = None
        self.bar_idx = 0
        self.last_candle_time = 0
        self.warmup_ok = False


def _build_pair_config(symbol, position_usd, leverage, config_overrides=None):
    cfg = Mode3BBCConfig()
    cfg.entry_usd = position_usd
    cfg.leverage = leverage

    if config_overrides:
        for k, v in config_overrides.items():
            if not isinstance(v, dict) and hasattr(cfg, k):
                setattr(cfg, k, v)
        if symbol in config_overrides and isinstance(config_overrides[symbol], dict):
            for k, v in config_overrides[symbol].items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

    # v3.0: MTF 15m ENABLED in switcher — same as backtest
    cfg.bull_mtf_15m_enabled = True
    cfg.bear_mtf_15m_enabled = True
    cfg.sideways_mtf_15m_enabled = False  # sideways is skipped anyway

    return cfg


# ══════════════════════════════════════════════
# CONNECTION ERROR HELPER
# ══════════════════════════════════════════════

def _is_connection_error(e):
    err_str = str(e).lower()
    return isinstance(e, (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError)) \
        or "connection" in err_str or "reset" in err_str or "timeout" in err_str \
        or "broken pipe" in err_str or "eof" in err_str


# ══════════════════════════════════════════════
# BBC LIVE LOOP — v3.1
# ══════════════════════════════════════════════

_bbc_live_running = False
_bbc_live_thread = None
_bbc_live_state = {
    "mode": "bbc", "pairs": {}, "cycle_count": 0,
    "last_cycle": None, "started_at": None,
    "active_pairs": [], "positions": {}, "error": None,
}


def _next_candle_close(now, interval_min):
    EPOCH = datetime(2020, 1, 1, tzinfo=timezone.utc)
    elapsed = (now - EPOCH).total_seconds()
    interval_sec = interval_min * 60
    current_boundary = EPOCH + timedelta(seconds=(elapsed // interval_sec) * interval_sec)
    return current_boundary + timedelta(seconds=interval_sec)


def _bbc_live_loop(symbols, timeframe="1h", position_usd=10.0, leverage=50,
                   config_overrides=None, client=None, state=None,
                   running_check=None, acct_name=""):
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
        # ═══ PER-PAIR CONFIGS ═══
        pair_states = {}
        for symbol in symbols:
            cfg = _build_pair_config(symbol, position_usd, leverage, config_overrides)
            pair_states[symbol] = BBCPairState(symbol, cfg)
            try:
                client.set_leverage(symbol)
            except Exception as e:
                _log(f"{prefix}  ⚠️ set_leverage {symbol}: {e}")

        state["mode"] = "bbc"
        state["started_at"] = datetime.now(timezone.utc).isoformat()
        state["active_pairs"] = symbols
        state["error"] = None

        tf_minutes = {"15m": 15, "1h": 60, "4h": 240}
        interval_min = tf_minutes.get(timeframe, 60)

        for symbol in symbols:
            pc = pair_states[symbol].config
            _log(f"{prefix}  📋 {symbol}: EMA={pc.ema_period} TP={pc.tp_pct*100:.1f}% SL={pc.sl_pct*100:.1f}% BullBody={pc.bull_body_ratio_min} BearBody={pc.bear_body_ratio_min} MTF=INSIDE")

        _log(f"{prefix}═══ BBC LIVE v3.1 STARTED ═══ {len(symbols)} pairs, TF={timeframe}, MTF=INSIDE_SWITCHER (same as backtest)")
        _send_telegram(f"📊 BBC LIVE v3.1 STARTED\nPairs: {', '.join(symbols)}\nMTF: INSIDE SWITCHER ✅ (same as backtest)")

        # ═══ WARMUP ═══
        for symbol in symbols:
            ps = pair_states[symbol]
            warmup_count = ps.config.startup_warmup_candles + 10
            if symbol == symbols[0]:
                _log(f"{prefix}  🔥 Warming up Switchers ({warmup_count} candles + 15m MTF)...")
            try:
                candles = _fetch_candles(symbol, timeframe, warmup_count)
                if not candles or len(candles) < ps.config.startup_warmup_candles:
                    _log(f"{prefix}  ❌ {symbol}: insufficient 1H candles ({len(candles) if candles else 0})")
                    continue

                # v3.0: Also fetch 15m candles for MTF during warmup
                candles_15m = _fetch_candles(symbol, "15m", warmup_count * 4 + 20)
                
                opens = [c["open"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                closes = [c["close"] for c in candles]
                volumes = [c.get("volume", 1.0) for c in candles]

                ema_series = _compute_ema(closes, ps.config.ema_period)
                vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, ps.config.va_window)

                # v3.0: Pre-compute MTF arrays (same as backtest)
                if candles_15m and len(candles_15m) >= 20:
                    bull_ec, bull_el, bear_ec, bear_eh = _compute_mtf_arrays(candles, candles_15m)
                    ps.switcher.mtf_bull_entry_close = bull_ec
                    ps.switcher.mtf_bull_entry_low = bull_el
                    ps.switcher.mtf_bear_entry_close = bear_ec
                    ps.switcher.mtf_bear_entry_high = bear_eh
                    _log(f"{prefix}  ✅ {symbol}: 15m MTF arrays computed ({len(candles_15m)} 15m candles)")
                else:
                    _log(f"{prefix}  ⚠️ {symbol}: insufficient 15m candles for MTF warmup")

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
            state["error"] = "All pairs failed warmup"
            _bbc_live_running = False
            return
        _log(f"{prefix}  ✅ {len(warmed)}/{len(symbols)} pairs warmed up: {', '.join(warmed)}")

        state["pairs"] = {s: {"state": ps.switcher.state, "position": None} for s, ps in pair_states.items() if ps.warmup_ok}

        # ═══ LAYER 1: PHANTOM POSITION DETECTION (v3.1) ═══
        phantom_count = 0
        for symbol in symbols:
            ps = pair_states[symbol]
            if not ps.warmup_ok or ps.switcher.position is None:
                continue
            try:
                ex_pos = client.get_position(symbol)
                ex_amt = abs(float(ex_pos.get("positionAmt", 0))) if ex_pos else 0
                if ex_amt == 0:
                    phantom = ps.switcher.position
                    phantom_count += 1
                    _log(f"{prefix}  🚨 PHANTOM DETECTED: {symbol} — Switcher says {phantom.tool} {phantom.side} @ ${phantom.entry_price:.4f} but exchange is FLAT")
                    _log(f"{prefix}     → Resetting Switcher position to None (state={ps.switcher.state} preserved)")
                    _send_telegram(
                        f"🚨 *PHANTOM POSITION DETECTED*\n"
                        f"{symbol}: Switcher={phantom.tool} {phantom.side} @ ${phantom.entry_price:.4f}\n"
                        f"Exchange: FLAT (no position)\n"
                        f"Action: Position reset, state={ps.switcher.state}\n"
                        f"⚠️ State may be wrong — monitor next entries"
                    )
                    ps.switcher.position = None
                else:
                    sw_side = ps.switcher.position.side
                    ex_side = "LONG" if float(ex_pos.get("positionAmt", 0)) > 0 else "SHORT"
                    if sw_side != ex_side:
                        _log(f"{prefix}  🚨 SIDE MISMATCH: {symbol} — Switcher={sw_side} but exchange={ex_side}")
                        _send_telegram(
                            f"🚨 *SIDE MISMATCH*\n"
                            f"{symbol}: Switcher={sw_side}, Exchange={ex_side}\n"
                            f"Manual intervention needed!"
                        )
            except Exception as e:
                _log(f"{prefix}  ⚠️ Phantom check {symbol}: {e}")

        if phantom_count > 0:
            _log(f"{prefix}  🚨 {phantom_count} phantom position(s) detected and reset")
        else:
            _log(f"{prefix}  ✅ No phantom positions — all clear")

        # ═══ ORPHAN CHECK (log only, no auto-close) ═══
        for symbol in symbols:
            try:
                pos = client.get_position(symbol)
                if pos and float(pos.get("positionAmt", 0)) != 0:
                    amt = float(pos["positionAmt"])
                    side = "LONG" if amt > 0 else "SHORT"
                    entry = float(pos.get("entryPrice", 0))
                    _log(f"{prefix}  ⚠️ {symbol}: existing {side} position on exchange @ ${entry:.4f} — NOT auto-closing")
                    _send_telegram(f"⚠️ BBC {symbol}: existing {side} @ ${entry:.4f}\nManual close from dashboard if needed")
            except Exception as e:
                _log(f"{prefix}  ⚠️ Orphan check {symbol}: {e}")

        _log(f"{prefix}  ⏰ Cycle interval: {interval_min}min")

        poll_sec = 15
        cycle = 0
        last_processed_boundary = 0
        _cycles_without_trade = 0
        _DEAD_BOT_THRESHOLD = 6

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

                            if abs(pnl_pct) < 0.02:
                                time.sleep(2)
                                recheck = client.get_position(symbol)
                                if recheck is None:
                                    continue
                                if float(recheck.get("positionAmt", 0)) != 0:
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
                        _log(f"{prefix}  ⚠️ {symbol}: insufficient candles")
                        continue

                    latest_time = candles[-1]["time"]
                    if latest_time <= ps.last_candle_time:
                        _log(f"{prefix}  ⏩ {symbol}: no new candle yet")
                        continue
                    ps.last_candle_time = latest_time

                    opens = [c["open"] for c in candles]
                    highs = [c["high"] for c in candles]
                    lows = [c["low"] for c in candles]
                    closes = [c["close"] for c in candles]
                    volumes = [c.get("volume", 1.0) for c in candles]

                    ema_series = _compute_ema(closes, ps.config.ema_period)
                    vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, ps.config.va_window)

                    last = candles[-1]
                    last_ema = ema_series[-1]
                    last_vah = vah_list[-1]
                    last_val = val_list[-1]
                    last_poc = poc_list[-1]

                    # v3.0: Fetch 15m and compute MTF for THIS bar
                    candles_15m = _fetch_candles(symbol, "15m", 40)
                    if candles_15m and len(candles_15m) >= 20:
                        # Build MTF data for current bar
                        M = 15 * 60 * 1000
                        idx_15m = {c["time"]: c for c in candles_15m}
                        candles_in_hour = [idx_15m.get(latest_time + k * M) for k in range(4)]
                        candles_in_hour = [c for c in candles_in_hour if c]
                        
                        closes_15m = [c["close"] for c in candles_15m]
                        ema15 = _compute_ema(closes_15m, 20)
                        
                        b_ec, b_el, br_ec, br_eh = None, None, None, None
                        
                        for k in range(4):
                            c15_time = latest_time + k * M
                            c15 = idx_15m.get(c15_time)
                            if not c15:
                                continue
                            try:
                                j = next(idx for idx, c in enumerate(candles_15m) if c["time"] == c15_time)
                            except StopIteration:
                                continue
                            ev = ema15[j]
                            
                            if b_ec is None and c15["low"] <= ev and c15["close"] > ev and c15["close"] > c15["open"]:
                                b_ec = c15["close"]
                                b_el = c15["low"]
                            if br_ec is None and c15["high"] >= ev and c15["close"] < ev and c15["close"] < c15["open"]:
                                br_ec = c15["close"]
                                br_eh = c15["high"]
                        
                        # Extend MTF arrays for NEXT bar_idx (process_candle uses bar_idx+1)
                        next_bar = ps.bar_idx + 1
                        while len(ps.switcher.mtf_bull_entry_close or []) <= next_bar:
                            if ps.switcher.mtf_bull_entry_close is None:
                                ps.switcher.mtf_bull_entry_close = []
                            ps.switcher.mtf_bull_entry_close.append(None)
                        if ps.switcher.mtf_bull_entry_low is None:
                            ps.switcher.mtf_bull_entry_low = []
                        while len(ps.switcher.mtf_bull_entry_low) <= next_bar:
                            ps.switcher.mtf_bull_entry_low.append(None)
                        if ps.switcher.mtf_bear_entry_close is None:
                            ps.switcher.mtf_bear_entry_close = []
                        while len(ps.switcher.mtf_bear_entry_close) <= next_bar:
                            ps.switcher.mtf_bear_entry_close.append(None)
                        if ps.switcher.mtf_bear_entry_high is None:
                            ps.switcher.mtf_bear_entry_high = []
                        while len(ps.switcher.mtf_bear_entry_high) <= next_bar:
                            ps.switcher.mtf_bear_entry_high.append(None)
                        
                        ps.switcher.mtf_bull_entry_close[next_bar] = b_ec
                        ps.switcher.mtf_bull_entry_low[next_bar] = b_el
                        ps.switcher.mtf_bear_entry_close[next_bar] = br_ec
                        ps.switcher.mtf_bear_entry_high[next_bar] = br_eh
                        
                        if b_ec: _log(f"{prefix}  🔍 {symbol}: 15m BULL confirm @ ${b_ec:.4f}")
                        if br_ec: _log(f"{prefix}  🔍 {symbol}: 15m BEAR confirm @ ${br_ec:.4f}")

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

                    # ═══ NEW POSITION OPENED (by switcher with MTF inside) ═══
                    if not had_position and has_position:
                        sp = ps.switcher.position
                        side = sp.side
                        entry_price = sp.entry_price  # v3.0: THIS IS NOW 15m CLOSE (same as backtest!)
                        sl_price = sp.sl_level
                        tp_price = sp.tp_level
                        tool = sp.tool

                        # Skip SIDEWAYS
                        if tool == "SIDEWAYS":
                            _log(f"{prefix}  ⏩ {symbol}: SKIP SIDEWAYS entry ({side})")
                            ps.switcher.position = None
                            continue

                        order_side = "BUY" if side == "LONG" else "SELL"
                        qty = _calc_quantity(symbol, entry_price, position_usd, leverage)

                        _log(f"{prefix}  📊 {symbol} BBC ENTRY: {tool} {side} @ ${entry_price:.4f} (15m sniper) | TP=${tp_price:.4f} SL=${sl_price:.4f}")

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

                                # v3.0: Use SWITCHER's TP/SL (calculated from 15m entry, same as backtest)
                                # Only adjust if actual fill is significantly different
                                if abs(actual_entry - entry_price) / entry_price > 0.001:
                                    # Fill price >0.1% different — recalculate from fill
                                    if side == "LONG":
                                        tp_price = actual_entry * (1 + ps.config.tp_pct)
                                        sl_price = actual_entry * (1 - ps.config.sl_pct)
                                    else:
                                        tp_price = actual_entry * (1 - ps.config.get_bear_tp_pct())
                                        sl_price = actual_entry * (1 + ps.config.get_bear_sl_pct())
                                    _log(f"{prefix}  ⚠️ {symbol}: fill ${actual_entry:.4f} differs from 15m ${entry_price:.4f}, adjusted TP/SL")

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
                                    f"15m sniper: ${entry_price:.4f}\n"
                                    f"State: {new_state}"
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
                                _log(f"{prefix}  {emoji} {symbol} {side} {exit_type} @ ${cp:.4f} | PnL: {pnl_pct:+.2f}%")
                                _send_telegram(f"{emoji} *BBC {symbol} {side} {exit_type}*\nEntry: ${entry:.4f}\nExit: ${cp:.4f}\nPnL: {pnl_pct:+.2f}%")
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
                        entry_price = sp.entry_price  # 15m sniper price
                        sl_price = sp.sl_level
                        tp_price = sp.tp_level
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
                                if abs(actual_entry - entry_price) / entry_price > 0.001:
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

            # ═══ LAYER 2: DEAD BOT DETECTION (v3.1) ═══
            cycle_has_positions = any(
                ps.exchange_position is not None
                for ps in pair_states.values() if ps.warmup_ok
            )
            if cycle_has_positions:
                _cycles_without_trade = 0
            else:
                _cycles_without_trade += 1

            if _cycles_without_trade >= _DEAD_BOT_THRESHOLD:
                states_summary = ", ".join(
                    f"{s}={ps.switcher.state}" for s, ps in pair_states.items() if ps.warmup_ok
                )
                _log(f"{prefix}  ⚠️ DEAD BOT ALERT: {_cycles_without_trade} cycles without any trade!")
                _send_telegram(
                    f"⚠️ *DEAD BOT ALERT*\n"
                    f"{_cycles_without_trade} cycles (≈{_cycles_without_trade}h) without any trade\n"
                    f"States: {states_summary}\n"
                    f"Check if bot is stuck or market is just quiet"
                )
                _cycles_without_trade = 0

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
