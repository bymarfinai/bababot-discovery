"""
BBC Live Trading — Wire BBC Switcher engine to live exchange.

Architecture:
- 1 Switcher instance per pair (stateful state machine)
- Market orders at candle close (not limit like Baret)
- SL/TP via algoOrder at exchange
- Uses same ExchangeClient + logging as baret_live

Flow per candle:
1. Fetch closed candle from OKX
2. Compute EMA20, VAH, VAL
3. Feed candle to Switcher
4. If Switcher opened position → place market order + SL/TP
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
        cfg = Mode3BBCConfig()
        cfg.entry_usd = position_usd
        cfg.leverage = leverage
        if config_overrides:
            for k, v in config_overrides.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)

        cfg.bull_mtf_15m_enabled = False
        cfg.bear_mtf_15m_enabled = False
        cfg.sideways_mtf_15m_enabled = False

        pair_states = {}
        for symbol in symbols:
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

        _log(f"{prefix}═══ BBC LIVE STARTED ═══ {len(symbols)} pairs, TF={timeframe}, ${position_usd}/trade, {leverage}x")
        _send_telegram(f"📊 BBC LIVE STARTED\nPairs: {', '.join(symbols)}\nTF: {timeframe}\nPosition: ${position_usd}\nTP: {cfg.tp_pct*100:.1f}% SL: {cfg.sl_pct*100:.1f}%")

        warmup_count = cfg.startup_warmup_candles + 10
        _log(f"{prefix}  🔥 Warming up Switchers ({warmup_count} candles)...")
        for symbol in symbols:
            ps = pair_states[symbol]
            try:
                candles = _fetch_candles(symbol, timeframe, warmup_count)
                if not candles:
                    _log(f"{prefix}  ❌ {symbol}: _fetch_candles returned empty/None")
                    continue
                if len(candles) < cfg.startup_warmup_candles:
                    _log(f"{prefix}  ⚠️ {symbol}: only {len(candles)} candles (need {cfg.startup_warmup_candles}), skipping")
                    continue

                opens = [c["open"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                closes = [c["close"] for c in candles]
                volumes = [c.get("volume", 1.0) for c in candles]

                ema20 = _compute_ema(closes, cfg.ema_period)
                vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, cfg.va_window)

                for i in range(len(candles)):
                    ps.switcher.process_candle(
                        i, opens[i], highs[i], lows[i], closes[i],
                        ema20[i], vah_list[i], val_list[i], poc_list[i]
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

            while wait_secs > 0 and running_check():
                time.sleep(min(poll_sec, max(1, wait_secs)))
                wait_secs -= poll_sec

                for symbol, ps in pair_states.items():
                    if not ps.warmup_ok or not ps.exchange_position:
                        continue
                    try:
                        try:
                            ex_pos = client.get_position(symbol)
                        except (ConnectionError, Exception) as api_err:
                            _log(f"{prefix}  ⚠️ {symbol}: get_position API error, skipping poll: {api_err}")
                            continue  # Don't treat API error as position closed
                        if not ex_pos or float(ex_pos.get("positionAmt", 0)) == 0:
                            ep = ps.exchange_position
                            cp = _get_price(symbol)
                            side = ep["side"]
                            entry = ep["entry"]
                            qty = ep["qty"]
                            pnl_pct = ((cp - entry) / entry * 100) if side == "LONG" else ((entry - cp) / entry * 100)
                            pnl_dollar = pnl_pct / 100 * entry * qty
                            hit = "TP" if pnl_pct > 0 else "SL"
                            emoji = "🎯" if hit == "TP" else "🛑"

                            _log(f"{prefix}  {emoji} {symbol} {side} {hit} (exchange) @ ~${cp:.4f} | PnL: {pnl_pct:+.2f}%")
                            _send_telegram(f"{emoji} *BBC {symbol} {side} {hit}*\nEntry: ${entry:.4f}\nExit: ~${cp:.4f}\nPnL: {pnl_pct:+.2f}%")
                            _log_trade_to_d1(symbol, timeframe, side, entry, cp,
                                ep.get("filled_at", ""), datetime.now(timezone.utc).isoformat(),
                                cfg.sl_pct * 100, cfg.tp_pct * 100,
                                pnl_dollar, pnl_pct, hit, acct_name)

                            ps.exchange_position = None
                            state["positions"].pop(symbol, None)

                            if ps.switcher.position:
                                ps.switcher._close_position(ps.bar_idx, cp, hit)

                    except Exception as e:
                        _log(f"{prefix}  ⚠️ Monitor {symbol}: {e}")

            if not running_check():
                break

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

                    ema20 = _compute_ema(closes, cfg.ema_period)
                    vah_list, val_list, poc_list = _compute_va(highs, lows, closes, volumes, cfg.va_window)

                    last = candles[-1]
                    last_ema = ema20[-1]
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

                    _log(f"{prefix}  📊 {symbol}: state={new_state} | EMA={last_ema:.2f} VAH={last_vah:.2f} VAL={last_val:.2f} | close=${last['close']:.4f}")

                    if not had_position and has_position:
                        sp = ps.switcher.position
                        side = sp.side
                        entry_price = sp.entry_price
                        sl_price = sp.sl_level
                        tp_price = sp.tp_level
                        tool = sp.tool

                        # Skip SIDEWAYS entries — proven unprofitable (WR 35%, $76 from 342 trades)
                        if tool == "SIDEWAYS":
                            _log(f"{prefix}  ⏩ {symbol}: SKIP SIDEWAYS entry ({side})")
                            ps.switcher._close_position(ps.bar_idx, entry_price, "SKIP")
                            continue

                        order_side = "BUY" if side == "LONG" else "SELL"
                        qty = _calc_quantity(symbol, entry_price, position_usd, leverage)

                        _log(f"{prefix}  📊 {symbol} BBC ENTRY: {tool} {side} @ ${entry_price:.4f} | TP=${tp_price:.4f} SL=${sl_price:.4f}")

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
                                    tp_price = actual_entry * (1 + cfg.tp_pct)
                                    sl_price = actual_entry * (1 - cfg.sl_pct)
                                else:
                                    tp_price = actual_entry * (1 - cfg.get_bear_tp_pct())
                                    sl_price = actual_entry * (1 + cfg.get_bear_sl_pct())

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
                                    f"TP: ${tp_price:.4f} ({cfg.tp_pct*100:.1f}%)\n"
                                    f"SL: ${sl_price:.4f} ({cfg.sl_pct*100:.1f}%)\n"
                                    f"State: {new_state}"
                                )
                                _log(f"{prefix}  ✅ {symbol} {side} FILLED @ ${actual_entry:.4f}")
                            else:
                                _log(f"{prefix}  ⚠️ {symbol}: order placed but position not found")
                        else:
                            _log(f"{prefix}  ❌ {symbol} order FAILED: {result.get('msg', result)}")

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
                                    cfg.sl_pct * 100, cfg.tp_pct * 100,
                                    pnl_dollar, pnl_pct, exit_type, acct_name)

                            except Exception as e:
                                _log(f"{prefix}  ❌ {symbol} close error: {e}")

                            ps.exchange_position = None
                            state["positions"].pop(symbol, None)

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
                                    tp_price = actual_entry * (1 + cfg.tp_pct)
                                    sl_price = actual_entry * (1 - cfg.sl_pct)
                                else:
                                    tp_price = actual_entry * (1 - cfg.get_bear_tp_pct())
                                    sl_price = actual_entry * (1 + cfg.get_bear_sl_pct())
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