"""
state_orchestrator.py — v1.5 with structural HH/LL detection modes
======================================================
v1.5 change: HH/LL detection modes for state transition
- vah_break (default): close > VAH + margin (existing)
- swing_high (B): close > previous swing high in lookback window
- combined (C): VAH break AND swing_high both required
Mirror for LL: val_break | swing_low | combined

All other logic (rolling VA, TP at VAH/VAL, SL buffer, timeout) preserved.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema as compute_ema
from .strategy_sideways import (
    SideEnum, SidewaysMode, SidewaysConfig,
    generate_sideways_signals,
)
from .regime import RegimeConfig, classify_regime_series
from .bull_tool import BullConfig, detect_bull_entry_signal, run_bull_trade
from .bear_tool import BearConfig, detect_bear_entry_signal, run_bear_trade


class State(Enum):
    SIDEWAYS = "sideways"
    BULL = "bull"
    BEAR = "bear"


@dataclass
class OrchestratorConfig:
    sideways_cfg: SidewaysConfig = field(default_factory=SidewaysConfig)
    sw_max_hold: int = 48
    sw_sl_pct_from_level: float = 0.005
    sw_tp1_ratio: float = 0.5
    sw_tp2_ratio: float = 0.3
    sw_tp3_ratio: float = 0.2
    sw_ema_period: int = 20
    sw_ema_exit_min_profit_pct: float = 0.003
    sw_ema_reject_cooldown: int = 48

    bull_cfg: BullConfig = field(default_factory=BullConfig)
    bear_cfg: BearConfig = field(default_factory=BearConfig)
    trending_max_hold: int = 200
    post_transition_wait: int = 24

    use_rolling_va: bool = True
    va_window: int = 50
    va_recompute_every: int = 20

    use_va_tp: bool = True
    tp1_partial_ratio: float = 0.5

    use_sl_buffer: bool = True
    sl_buffer_pct: float = 0.001

    # v1.5: HH/LL detection mode
    hh_detection_mode: str = "vah_break"   # vah_break | swing_high | combined
    ll_detection_mode: str = "val_break"   # val_break | swing_low | combined
    swing_lookback: int = 20               # candles for swing detection
    swing_buffer: int = 3                  # exclude last N candles

    vah_break_candles: int = 1
    val_break_candles: int = 1
    vah_break_margin: float = 0.0

    enable_state_timeout: bool = True
    state_timeout_candles: int = 100

    double_confirm_lookback: int = 20
    double_confirm_tolerance: float = 0.003
    double_size_multiplier: float = 1.5
    double_sl_pct: float = 0.003

    position_usd: float = 10.0
    leverage: float = 50.0
    fee_pct: float = 0.0004
    slippage_pct: float = 0.001


@dataclass
class TradeRecord:
    state: str
    side: str
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_high: float
    entry_low: float
    exit_reason: str
    pnl_net: float
    hold_candles: int
    is_double: bool = False
    size_multiplier: float = 1.0
    state_transition: str = ""
    tp1_target: Optional[float] = None


def compute_va_from_window(highs, lows, closes, volumes, i, window=50):
    if i < window:
        return None, None, None
    seg_h = highs[i - window:i]
    seg_l = lows[i - window:i]
    seg_c = closes[i - window:i]
    seg_v = volumes[i - window:i]
    if len(seg_h) < window:
        return None, None, None
    total_vol = float(np.sum(seg_v))
    if total_vol <= 0:
        return None, None, None
    typical = (seg_h + seg_l + seg_c) / 3.0
    poc = float(np.sum(typical * seg_v) / total_vol)
    vah = float(np.percentile(seg_h, 85))
    val = float(np.percentile(seg_l, 15))
    return vah, val, poc


def _detect_hh(highs, closes, i, current_vah, cfg):
    """
    Multi-mode HH detection.
    Returns (is_hh, description)
    """
    c = float(closes[i])
    prev_peak = None
    if i >= cfg.swing_lookback + cfg.swing_buffer:
        start = i - cfg.swing_lookback
        end = i - cfg.swing_buffer
        if end > start:
            prev_peak = float(np.max(highs[start:end]))
    swing_hh = (prev_peak is not None) and (c > prev_peak)

    vah_break = False
    if current_vah is not None:
        vah_break = c > current_vah * (1 + cfg.vah_break_margin)

    if cfg.hh_detection_mode == "swing_high":
        desc = f"swing_HH > {prev_peak:.0f}" if swing_hh else "no swing"
        return swing_hh, desc
    elif cfg.hh_detection_mode == "combined":
        return (vah_break and swing_hh), f"VAH+swing"
    else:
        desc = f"VAH_break > {current_vah:.0f}" if vah_break else "no VAH"
        return vah_break, desc


def _detect_ll(lows, closes, i, current_val, cfg):
    c = float(closes[i])
    prev_trough = None
    if i >= cfg.swing_lookback + cfg.swing_buffer:
        start = i - cfg.swing_lookback
        end = i - cfg.swing_buffer
        if end > start:
            prev_trough = float(np.min(lows[start:end]))
    swing_ll = (prev_trough is not None) and (c < prev_trough)

    val_break = False
    if current_val is not None:
        val_break = c < current_val * (1 - cfg.vah_break_margin)

    if cfg.ll_detection_mode == "swing_low":
        desc = f"swing_LL < {prev_trough:.0f}" if swing_ll else "no swing"
        return swing_ll, desc
    elif cfg.ll_detection_mode == "combined":
        return (val_break and swing_ll), f"VAL+swing"
    else:
        desc = f"VAL_break < {current_val:.0f}" if val_break else "no VAL"
        return val_break, desc


def run_state_machine_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    opens: np.ndarray,
    volumes: np.ndarray,
    cfg: OrchestratorConfig,
    mtf_classifications=None,
    warmup: int = 100,
) -> dict:
    n = len(closes)
    if n < warmup + 50:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    ema20 = compute_ema(closes, cfg.sw_ema_period)
    regime_cfg = RegimeConfig()
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)

    sw_signals = generate_sideways_signals(
        highs, lows, closes, volumes, regime_states, cfg.sideways_cfg,
        mtf_classifications=mtf_classifications, opens=opens,
    )
    sw_signal_by_idx = {sig.idx: sig for sig in sw_signals}

    trades: list[TradeRecord] = []
    state = State.SIDEWAYS
    state_transitions: list[dict] = []
    state_entered_at: int = warmup

    recent_short_reject_highs: list[tuple[int, float]] = []
    recent_long_bounce_lows: list[tuple[int, float]] = []

    ema_reject_long_cd_until = -1
    ema_reject_short_cd_until = -1

    current_vah: Optional[float] = None
    current_val: Optional[float] = None
    current_poc: Optional[float] = None
    va_last_computed_at: int = -999
    vah_break_streak: int = 0
    val_break_streak: int = 0

    i = warmup
    while i < n - 1:
        c = float(closes[i])
        cur_ema = float(ema20[i])

        # Rolling VA recompute
        if cfg.use_rolling_va and state == State.SIDEWAYS:
            if i - va_last_computed_at >= cfg.va_recompute_every:
                vah, val, poc = compute_va_from_window(
                    highs, lows, closes, volumes, i, cfg.va_window
                )
                if vah is not None and val is not None:
                    current_vah = vah
                    current_val = val
                    current_poc = poc
                    va_last_computed_at = i
                    vah_break_streak = 0
                    val_break_streak = 0

        # v1.5: HH/LL detection with mode
        if state == State.SIDEWAYS:
            is_hh, hh_desc = _detect_hh(highs, closes, i, current_vah, cfg)
            is_ll, ll_desc = _detect_ll(lows, closes, i, current_val, cfg)

            if is_hh:
                vah_break_streak += 1
                val_break_streak = 0
            elif is_ll:
                val_break_streak += 1
                vah_break_streak = 0
            else:
                vah_break_streak = 0
                val_break_streak = 0

            if vah_break_streak >= cfg.vah_break_candles:
                state_transitions.append({
                    "idx": i, "from": "sideways", "to": "bull",
                    "reason": f"HH[{cfg.hh_detection_mode}] {hh_desc}",
                })
                state = State.BULL
                state_entered_at = i
                vah_break_streak = 0
                val_break_streak = 0
                continue

            if val_break_streak >= cfg.val_break_candles:
                state_transitions.append({
                    "idx": i, "from": "sideways", "to": "bear",
                    "reason": f"LL[{cfg.ll_detection_mode}] {ll_desc}",
                })
                state = State.BEAR
                state_entered_at = i
                vah_break_streak = 0
                val_break_streak = 0
                continue

        # State timeout
        if cfg.enable_state_timeout and state != State.SIDEWAYS:
            if i - state_entered_at > cfg.state_timeout_candles:
                state_transitions.append({
                    "idx": i, "from": state.value, "to": "sideways",
                    "reason": f"Timeout {cfg.state_timeout_candles}c no entry",
                })
                state = State.SIDEWAYS
                state_entered_at = i

        # ═══ SIDEWAYS ═══
        if state == State.SIDEWAYS:
            sig = sw_signal_by_idx.get(i)
            if sig is None:
                i += 1
                continue

            current_vah = sig.vah
            current_val = sig.val
            current_poc = sig.poc
            va_last_computed_at = i
            vah_break_streak = 0
            val_break_streak = 0

            if sig.side == SideEnum.LONG and i < ema_reject_long_cd_until:
                i += 1
                continue
            if sig.side == SideEnum.SHORT and i < ema_reject_short_cd_until:
                i += 1
                continue

            side_str = "long" if sig.side == SideEnum.LONG else "short"

            is_double = False
            size_mult = 1.0
            sl_pct = cfg.sw_sl_pct_from_level

            if side_str == "short":
                for prev_idx, prev_high in recent_short_reject_highs:
                    if i - prev_idx > cfg.double_confirm_lookback:
                        continue
                    cur_high = float(highs[i])
                    if abs(cur_high - prev_high) / prev_high <= cfg.double_confirm_tolerance:
                        is_double = True
                        size_mult = cfg.double_size_multiplier
                        sl_pct = cfg.double_sl_pct
                        break
                recent_short_reject_highs.append((i, float(highs[i])))
                recent_short_reject_highs = [(idx, hi) for idx, hi in recent_short_reject_highs if i - idx <= cfg.double_confirm_lookback]
            else:
                for prev_idx, prev_low in recent_long_bounce_lows:
                    if i - prev_idx > cfg.double_confirm_lookback:
                        continue
                    cur_low = float(lows[i])
                    if abs(cur_low - prev_low) / prev_low <= cfg.double_confirm_tolerance:
                        is_double = True
                        size_mult = cfg.double_size_multiplier
                        sl_pct = cfg.double_sl_pct
                        break
                recent_long_bounce_lows.append((i, float(lows[i])))
                recent_long_bounce_lows = [(idx, lo) for idx, lo in recent_long_bounce_lows if i - idx <= cfg.double_confirm_lookback]

            entry_price = c * (1 + cfg.slippage_pct if side_str == "long" else 1 - cfg.slippage_pct)
            position_usd = cfg.position_usd * size_mult
            notional = position_usd * cfg.leverage

            if side_str == "long":
                sl_level = sig.val * (1 - sl_pct)
                tp1_p = sig.poc
                tp3_p = sig.vah
            else:
                sl_level = sig.vah * (1 + sl_pct)
                tp1_p = sig.poc
                tp3_p = sig.val

            if side_str == "long" and (tp1_p <= entry_price or sl_level >= entry_price):
                i += 1
                continue
            if side_str == "short" and (tp1_p >= entry_price or sl_level <= entry_price):
                i += 1
                continue

            entry_high_anchor = float(highs[i])
            entry_low_anchor = float(lows[i])
            entry_idx = i
            exit_price = entry_price
            exit_reason = "end"
            exit_idx = entry_idx
            realized_pnl = 0.0
            remaining = 1.0
            tp1_hit = False
            moved_to_be = False
            ema_broken = False
            if side_str == "long" and entry_price >= cur_ema:
                ema_broken = True
            elif side_str == "short" and entry_price <= cur_ema:
                ema_broken = True

            for j in range(entry_idx + 1, min(entry_idx + cfg.sw_max_hold + 1, n)):
                hh = float(highs[j])
                ll = float(lows[j])
                cc = float(closes[j])
                cur_ema_j = float(ema20[j])

                sl_hit = (side_str == "long" and cc <= sl_level) or (side_str == "short" and cc >= sl_level)
                if sl_hit:
                    exit_reason = "sl_breakeven" if moved_to_be else "sl"
                    exit_price = cc
                    exit_idx = j
                    break

                if not tp1_hit:
                    if (side_str == "long" and hh >= tp1_p) or (side_str == "short" and ll <= tp1_p):
                        tp1_hit = True
                        pn = notional * cfg.sw_tp1_ratio
                        gp = (tp1_p - entry_price) / entry_price if side_str == "long" else (entry_price - tp1_p) / entry_price
                        realized_pnl += gp * pn - cfg.fee_pct * pn - cfg.slippage_pct * pn
                        remaining -= cfg.sw_tp1_ratio
                        sl_level = entry_price
                        moved_to_be = True

                if tp1_hit and remaining > 0:
                    if (side_str == "long" and hh >= tp3_p) or (side_str == "short" and ll <= tp3_p):
                        exit_reason = "tp3"
                        exit_price = tp3_p
                        exit_idx = j
                        break

                if cur_ema_j > 0 and not ema_broken:
                    cur_profit = (cc - entry_price) / entry_price if side_str == "long" else (entry_price - cc) / entry_price
                    min_profit_ok = cur_profit >= cfg.sw_ema_exit_min_profit_pct
                    if side_str == "long":
                        if cc >= cur_ema_j:
                            ema_broken = True
                        elif hh >= cur_ema_j and cc < cur_ema_j and min_profit_ok:
                            exit_reason = "ema_reject"
                            exit_price = cc
                            exit_idx = j
                            break
                    else:
                        if cc <= cur_ema_j:
                            ema_broken = True
                        elif ll <= cur_ema_j and cc > cur_ema_j and min_profit_ok:
                            exit_reason = "ema_reject"
                            exit_price = cc
                            exit_idx = j
                            break

                if j - entry_idx >= cfg.sw_max_hold:
                    exit_reason = "max_hold"
                    exit_price = cc
                    exit_idx = j
                    break
            else:
                exit_idx = min(entry_idx + cfg.sw_max_hold, n - 1)
                exit_price = float(closes[exit_idx])

            if remaining > 0:
                gp = (exit_price - entry_price) / entry_price if side_str == "long" else (entry_price - exit_price) / entry_price
                pn = notional * remaining
                realized_pnl += gp * pn - cfg.fee_pct * pn - cfg.slippage_pct * pn
            entry_fee = cfg.fee_pct * notional + cfg.slippage_pct * notional
            realized_pnl -= entry_fee

            trades.append(TradeRecord(
                state="sideways" + ("+double" if is_double else ""),
                side=side_str, entry_idx=entry_idx, exit_idx=exit_idx,
                entry_price=entry_price, exit_price=exit_price,
                entry_high=entry_high_anchor, entry_low=entry_low_anchor,
                exit_reason=exit_reason, pnl_net=realized_pnl,
                hold_candles=exit_idx - entry_idx,
                is_double=is_double, size_multiplier=size_mult,
            ))

            if exit_reason == "ema_reject":
                if side_str == "long":
                    ema_reject_long_cd_until = exit_idx + cfg.sw_ema_reject_cooldown
                else:
                    ema_reject_short_cd_until = exit_idx + cfg.sw_ema_reject_cooldown
                trades[-1].state_transition = f"cooldown_{side_str}"

            i = exit_idx + 1
            continue

        # ═══ BULL ═══
        elif state == State.BULL:
            if i - state_entered_at < cfg.post_transition_wait:
                i += 1
                continue

            sig = detect_bull_entry_signal(highs, lows, closes, opens, ema20, i, cfg.bull_cfg)
            if sig is None:
                i += 1
                continue

            tp1_target = None
            if cfg.use_va_tp and current_vah is not None:
                if current_vah > sig.entry_price:
                    tp1_target = current_vah

            sl_buf = cfg.sl_buffer_pct if cfg.use_sl_buffer else 0.0

            trade = run_bull_trade(
                highs, lows, closes, ema20, sig, i,
                entry_low_anchor=float(lows[i]),
                max_hold=cfg.trending_max_hold,
                fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct,
                position_usd=cfg.position_usd, leverage=cfg.leverage,
                sl_buffer_pct=sl_buf,
                tp1_target=tp1_target,
                tp1_partial_ratio=cfg.tp1_partial_ratio,
            )

            trades.append(TradeRecord(
                state="bull", side="long",
                entry_idx=trade.entry_idx, exit_idx=trade.exit_idx,
                entry_price=trade.entry_price, exit_price=trade.exit_price,
                entry_high=float(highs[i]), entry_low=trade.entry_low,
                exit_reason=trade.exit_reason, pnl_net=trade.pnl_net,
                hold_candles=trade.hold_candles,
                state_transition=trade.state_signal,
                tp1_target=tp1_target,
            ))

            state_transitions.append({
                "idx": trade.exit_idx, "from": "bull", "to": "sideways",
                "reason": f"BULL exit ({trade.exit_reason})",
            })
            state = State.SIDEWAYS
            state_entered_at = trade.exit_idx
            va_last_computed_at = -999

            i = trade.exit_idx + 1
            continue

        # ═══ BEAR ═══
        elif state == State.BEAR:
            if i - state_entered_at < cfg.post_transition_wait:
                i += 1
                continue

            sig = detect_bear_entry_signal(highs, lows, closes, opens, ema20, i, cfg.bear_cfg)
            if sig is None:
                i += 1
                continue

            tp1_target = None
            if cfg.use_va_tp and current_val is not None:
                if current_val < sig.entry_price:
                    tp1_target = current_val

            sl_buf = cfg.sl_buffer_pct if cfg.use_sl_buffer else 0.0

            trade = run_bear_trade(
                highs, lows, closes, ema20, sig, i,
                entry_high_anchor=float(highs[i]),
                max_hold=cfg.trending_max_hold,
                fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct,
                position_usd=cfg.position_usd, leverage=cfg.leverage,
                sl_buffer_pct=sl_buf,
                tp1_target=tp1_target,
                tp1_partial_ratio=cfg.tp1_partial_ratio,
            )

            trades.append(TradeRecord(
                state="bear", side="short",
                entry_idx=trade.entry_idx, exit_idx=trade.exit_idx,
                entry_price=trade.entry_price, exit_price=trade.exit_price,
                entry_high=trade.entry_high, entry_low=float(lows[i]),
                exit_reason=trade.exit_reason, pnl_net=trade.pnl_net,
                hold_candles=trade.hold_candles,
                state_transition=trade.state_signal,
                tp1_target=tp1_target,
            ))

            state_transitions.append({
                "idx": trade.exit_idx, "from": "bear", "to": "sideways",
                "reason": f"BEAR exit ({trade.exit_reason})",
            })
            state = State.SIDEWAYS
            state_entered_at = trade.exit_idx
            va_last_computed_at = -999

            i = trade.exit_idx + 1
            continue

        else:
            i += 1

    total = len(trades)
    wins = sum(1 for t in trades if t.pnl_net > 0.01)
    losses = sum(1 for t in trades if t.pnl_net < -0.01)
    pnl_total = sum(t.pnl_net for t in trades)
    wr = wins / max(wins + losses, 1)

    by_state = {}
    for t in trades:
        s = t.state.split("+")[0]
        if s not in by_state:
            by_state[s] = {"trades": 0, "wins": 0, "pnl": 0.0}
        by_state[s]["trades"] += 1
        if t.pnl_net > 0.01:
            by_state[s]["wins"] += 1
        by_state[s]["pnl"] += t.pnl_net
    for s in by_state:
        by_state[s]["wr"] = round(by_state[s]["wins"] / max(by_state[s]["trades"], 1), 4)
        by_state[s]["pnl"] = round(by_state[s]["pnl"], 2)

    doubles = sum(1 for t in trades if t.is_double)

    return {
        "ok": True,
        "orchestrator": "v1.5",
        "hh_detection_mode": cfg.hh_detection_mode,
        "ll_detection_mode": cfg.ll_detection_mode,
        "stats": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 4),
            "total_pnl": round(pnl_total, 2),
            "by_state": by_state,
            "double_confirms": doubles,
            "state_transition_count": len(state_transitions),
        },
        "state_transitions": state_transitions[:50],
        "sample_trades": [
            {
                "state": t.state, "side": t.side,
                "entry_idx": t.entry_idx, "exit_idx": t.exit_idx,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "exit_reason": t.exit_reason,
                "pnl_net": round(t.pnl_net, 2),
                "tp1_target": round(t.tp1_target, 2) if t.tp1_target else None,
                "is_double": t.is_double,
                "hold": t.hold_candles,
            }
            for t in trades[:50]
        ],
    }


__all__ = [
    "State", "OrchestratorConfig", "TradeRecord",
    "run_state_machine_backtest", "compute_va_from_window",
]
