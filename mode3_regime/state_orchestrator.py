"""
state_orchestrator.py — v1.2 3-State Trading Bot
======================================================
v1.2 changes:
1. Fix A: state_timeout — force back to SIDEWAYS if BULL/BEAR stuck >N candles (default 100, toggleable)
2. Fix B: broader_transition_triggers — HH/LL breach + slope confirmation, not just EMA reject exit (toggleable)
3. Fix C: trend_slope_gate — require EMA20 slope confirmation before BULL/BEAR entry (toggleable)
4. NO DIRECT BULL↔BEAR switch — always route through SIDEWAYS wait state (user design intent)
   - BULL LL breach → close position → SIDEWAYS (watch for next transition trigger)
   - BEAR HH breach → close position → SIDEWAYS (watch for next transition trigger)

All 3 fixes toggleable via config for isolation testing.
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
from .bull_tool import (
    BullConfig, detect_bull_entry_signal, run_bull_trade,
)
from .bear_tool import (
    BearConfig, detect_bear_entry_signal, run_bear_trade,
)


class State(Enum):
    SIDEWAYS = "sideways"
    BULL = "bull"
    BEAR = "bear"


@dataclass
class OrchestratorConfig:
    # SIDEWAYS
    sideways_cfg: SidewaysConfig = field(default_factory=SidewaysConfig)
    sw_max_hold: int = 48
    sw_sl_pct_from_level: float = 0.005
    sw_tp1_ratio: float = 0.5
    sw_tp2_ratio: float = 0.3
    sw_tp3_ratio: float = 0.2
    sw_ema_period: int = 20
    sw_ema_exit_min_profit_pct: float = 0.003
    sw_ema_reject_cooldown: int = 48

    # BULL/BEAR
    bull_cfg: BullConfig = field(default_factory=BullConfig)
    bear_cfg: BearConfig = field(default_factory=BearConfig)
    trending_max_hold: int = 200
    post_transition_wait: int = 8

    # v1.2 Fix A: state timeout
    enable_state_timeout: bool = True
    state_timeout_candles: int = 100    # after N candles no entry → back to SIDEWAYS

    # v1.2 Fix B: broader transition triggers
    enable_broader_triggers: bool = True
    trigger_lookback: int = 20          # window for HH/LL structure detection
    trigger_slope_candles: int = 3      # candles for slope confirmation

    # v1.2 Fix C: trend slope gate
    enable_slope_gate: bool = True
    slope_min_pct: float = 0.001        # min 0.1% slope per candle for trend confirmation
    slope_lookback: int = 10

    # Watch window after safeguard exit
    watch_window_candles: int = 20

    # Double confirm
    double_confirm_lookback: int = 20
    double_confirm_tolerance: float = 0.003
    double_size_multiplier: float = 1.5
    double_sl_pct: float = 0.003

    # Common
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


def _ema_slope_pct(ema_arr, i, lookback):
    """Compute EMA slope over N candles as % change per candle."""
    if i < lookback or i >= len(ema_arr):
        return 0.0
    e0 = float(ema_arr[i - lookback])
    e1 = float(ema_arr[i])
    if e0 <= 0:
        return 0.0
    return (e1 - e0) / e0 / lookback


def _detect_hh_structure(highs, i, lookback):
    """Detect if recent lookback window has higher-highs structure."""
    if i < lookback:
        return False
    recent = highs[i - lookback:i + 1]
    # Check if last third avg > first third avg by at least 1%
    third = len(recent) // 3
    if third < 2:
        return False
    first_avg = float(np.mean(recent[:third]))
    last_avg = float(np.mean(recent[-third:]))
    if first_avg <= 0:
        return False
    return (last_avg - first_avg) / first_avg > 0.01


def _detect_ll_structure(lows, i, lookback):
    """Detect if recent lookback window has lower-lows structure."""
    if i < lookback:
        return False
    recent = lows[i - lookback:i + 1]
    third = len(recent) // 3
    if third < 2:
        return False
    first_avg = float(np.mean(recent[:third]))
    last_avg = float(np.mean(recent[-third:]))
    if first_avg <= 0:
        return False
    return (first_avg - last_avg) / first_avg > 0.01


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
    watch_for_breach: Optional[dict] = None

    ema_reject_long_cd_until = -1
    ema_reject_short_cd_until = -1

    # Track latest HH/LL anchors for BULL/BEAR re-entry after safeguard exit
    latest_bull_hh_anchor: Optional[float] = None
    latest_bear_ll_anchor: Optional[float] = None

    i = warmup
    while i < n - 1:
        c = float(closes[i])
        cur_ema = float(ema20[i])

        # ─── Watch for breach EVERY candle ───
        if watch_for_breach is not None:
            if i > watch_for_breach["expires_at"]:
                watch_for_breach = None
            else:
                if watch_for_breach["side"] == "short" and c > watch_for_breach["anchor"]:
                    # SHORT was rejected + break entry high → BULL
                    # v1.2 Fix C: check slope gate
                    slope_ok = True
                    if cfg.enable_slope_gate:
                        slope = _ema_slope_pct(ema20, i, cfg.slope_lookback)
                        slope_ok = slope >= cfg.slope_min_pct
                    if slope_ok:
                        state_transitions.append({
                            "idx": i, "from": state.value, "to": "bull",
                            "reason": f"HH breach + slope_ok: close {c:.2f} > {watch_for_breach['anchor']:.2f}",
                        })
                        state = State.BULL
                        state_entered_at = i
                        latest_bull_hh_anchor = watch_for_breach["anchor"]
                        watch_for_breach = None
                elif watch_for_breach["side"] == "long" and c < watch_for_breach["anchor"]:
                    slope_ok = True
                    if cfg.enable_slope_gate:
                        slope = _ema_slope_pct(ema20, i, cfg.slope_lookback)
                        slope_ok = slope <= -cfg.slope_min_pct
                    if slope_ok:
                        state_transitions.append({
                            "idx": i, "from": state.value, "to": "bear",
                            "reason": f"LL breach + slope_ok: close {c:.2f} < {watch_for_breach['anchor']:.2f}",
                        })
                        state = State.BEAR
                        state_entered_at = i
                        latest_bear_ll_anchor = watch_for_breach["anchor"]
                        watch_for_breach = None

        # ─── v1.2 Fix B: Broader trigger check (from SIDEWAYS) ───
        # If in SIDEWAYS and not currently trading, check for HH/LL structure trigger
        if state == State.SIDEWAYS and cfg.enable_broader_triggers and watch_for_breach is None:
            # HH structure → possible BULL
            if _detect_hh_structure(highs, i, cfg.trigger_lookback):
                slope_ok = True
                if cfg.enable_slope_gate:
                    slope = _ema_slope_pct(ema20, i, cfg.slope_lookback)
                    slope_ok = slope >= cfg.slope_min_pct
                if slope_ok:
                    state_transitions.append({
                        "idx": i, "from": "sideways", "to": "bull",
                        "reason": f"HH structure detected + slope confirmed",
                    })
                    state = State.BULL
                    state_entered_at = i
                    latest_bull_hh_anchor = float(np.max(highs[i - cfg.trigger_lookback:i + 1]))
            # LL structure → possible BEAR
            elif _detect_ll_structure(lows, i, cfg.trigger_lookback):
                slope_ok = True
                if cfg.enable_slope_gate:
                    slope = _ema_slope_pct(ema20, i, cfg.slope_lookback)
                    slope_ok = slope <= -cfg.slope_min_pct
                if slope_ok:
                    state_transitions.append({
                        "idx": i, "from": "sideways", "to": "bear",
                        "reason": f"LL structure detected + slope confirmed",
                    })
                    state = State.BEAR
                    state_entered_at = i
                    latest_bear_ll_anchor = float(np.min(lows[i - cfg.trigger_lookback:i + 1]))

        # ─── v1.2 Fix A: State timeout ───
        if cfg.enable_state_timeout and state != State.SIDEWAYS:
            if i - state_entered_at > cfg.state_timeout_candles:
                state_transitions.append({
                    "idx": i, "from": state.value, "to": "sideways",
                    "reason": f"Timeout {cfg.state_timeout_candles} candles no entry",
                })
                state = State.SIDEWAYS
                state_entered_at = i

        # ═══════════════ STATE: SIDEWAYS ═══════════════
        if state == State.SIDEWAYS:
            sig = sw_signal_by_idx.get(i)
            if sig is None:
                i += 1
                continue

            if sig.side == SideEnum.LONG and i < ema_reject_long_cd_until:
                i += 1
                continue
            if sig.side == SideEnum.SHORT and i < ema_reject_short_cd_until:
                i += 1
                continue

            side_str = "long" if sig.side == SideEnum.LONG else "short"

            # Double confirm
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
                recent_short_reject_highs = [
                    (idx, hi) for idx, hi in recent_short_reject_highs
                    if i - idx <= cfg.double_confirm_lookback
                ]
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
                recent_long_bounce_lows = [
                    (idx, lo) for idx, lo in recent_long_bounce_lows
                    if i - idx <= cfg.double_confirm_lookback
                ]

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

                sl_hit = (side_str == "long" and cc <= sl_level) or \
                         (side_str == "short" and cc >= sl_level)
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

                watch_for_breach = {
                    "side": side_str,
                    "anchor": entry_high_anchor if side_str == "short" else entry_low_anchor,
                    "expires_at": exit_idx + cfg.watch_window_candles,
                }
                trades[-1].state_transition = f"watch_{side_str}_breach"

            i = exit_idx + 1
            continue

        # ═══════════════ STATE: BULL ═══════════════
        elif state == State.BULL:
            if i - state_entered_at < cfg.post_transition_wait:
                i += 1
                continue

            sig = detect_bull_entry_signal(highs, lows, closes, opens, ema20, i, cfg.bull_cfg)
            if sig is None:
                i += 1
                continue

            trade = run_bull_trade(
                highs, lows, closes, ema20, sig, i,
                entry_low_anchor=float(lows[i]),
                max_hold=cfg.trending_max_hold,
                fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct,
                position_usd=cfg.position_usd, leverage=cfg.leverage,
            )

            trades.append(TradeRecord(
                state="bull", side="long",
                entry_idx=trade.entry_idx, exit_idx=trade.exit_idx,
                entry_price=trade.entry_price, exit_price=trade.exit_price,
                entry_high=float(highs[i]), entry_low=trade.entry_low,
                exit_reason=trade.exit_reason, pnl_net=trade.pnl_net,
                hold_candles=trade.hold_candles,
                state_transition=trade.state_signal,
            ))

            # v1.2 KEY CHANGE: ALWAYS route through SIDEWAYS (no direct BULL→BEAR)
            if trade.state_signal == "switch_bear":
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bull", "to": "sideways",
                    "reason": "LL breach during BULL trade → SIDEWAYS wait (v1.2)",
                })
                # Set up watch for further LL confirmation → BEAR
                watch_for_breach = {
                    "side": "long",  # anchor is BULL entry low, watch for LL break
                    "anchor": trade.entry_low,
                    "expires_at": trade.exit_idx + cfg.watch_window_candles,
                }
            else:
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bull", "to": "sideways",
                    "reason": "Trailing stop, no LL breach",
                })
            state = State.SIDEWAYS
            state_entered_at = trade.exit_idx

            i = trade.exit_idx + 1
            continue

        # ═══════════════ STATE: BEAR ═══════════════
        elif state == State.BEAR:
            if i - state_entered_at < cfg.post_transition_wait:
                i += 1
                continue

            sig = detect_bear_entry_signal(highs, lows, closes, opens, ema20, i, cfg.bear_cfg)
            if sig is None:
                i += 1
                continue

            trade = run_bear_trade(
                highs, lows, closes, ema20, sig, i,
                entry_high_anchor=float(highs[i]),
                max_hold=cfg.trending_max_hold,
                fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct,
                position_usd=cfg.position_usd, leverage=cfg.leverage,
            )

            trades.append(TradeRecord(
                state="bear", side="short",
                entry_idx=trade.entry_idx, exit_idx=trade.exit_idx,
                entry_price=trade.entry_price, exit_price=trade.exit_price,
                entry_high=trade.entry_high, entry_low=float(lows[i]),
                exit_reason=trade.exit_reason, pnl_net=trade.pnl_net,
                hold_candles=trade.hold_candles,
                state_transition=trade.state_signal,
            ))

            # v1.2 KEY CHANGE: ALWAYS route through SIDEWAYS (no direct BEAR→BULL)
            if trade.state_signal == "switch_bull":
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bear", "to": "sideways",
                    "reason": "HH breach during BEAR trade → SIDEWAYS wait (v1.2)",
                })
                watch_for_breach = {
                    "side": "short",
                    "anchor": trade.entry_high,
                    "expires_at": trade.exit_idx + cfg.watch_window_candles,
                }
            else:
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bear", "to": "sideways",
                    "reason": "Trailing stop, no HH breach",
                })
            state = State.SIDEWAYS
            state_entered_at = trade.exit_idx

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
        "orchestrator": "v1.2",
        "features_active": {
            "state_timeout": cfg.enable_state_timeout,
            "broader_triggers": cfg.enable_broader_triggers,
            "slope_gate": cfg.enable_slope_gate,
        },
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
                "is_double": t.is_double, "size_mult": t.size_multiplier,
                "hold": t.hold_candles,
                "state_next": t.state_transition,
            }
            for t in trades[:50]
        ],
    }


__all__ = [
    "State", "OrchestratorConfig", "TradeRecord",
    "run_state_machine_backtest",
]
