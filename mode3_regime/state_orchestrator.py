"""
state_orchestrator.py — v1.0 3-State Trading Bot
======================================================
State machine routing: SIDEWAYS ↔ BULL ↔ BEAR

Full transition matrix (10 rows):
  SIDEWAYS → SIDEWAYS: normal trade, no breach
  SIDEWAYS → SIDEWAYS+Double: 2× same signal in 20 candles at 0.3% tolerance
  SIDEWAYS → BULL: SHORT exit via EMA reject + break entry high
  SIDEWAYS → BEAR: LONG exit via EMA reject + break entry low
  BULL → SIDEWAYS: trailing stop, no LL breach
  BULL → BEAR: LL breach (candle close < latest LONG entry low) force exit
  BULL → BULL: still in position, no LL
  BEAR → SIDEWAYS: trailing stop, no HH breach
  BEAR → BULL: HH breach force exit
  BEAR → BEAR: still in position, no HH
  SIDEWAYS+Double → BULL/BEAR: candle #3 break entry high/low

Double confirm rules:
- 2× same-side signal in 20 candles at 0.3% level tolerance
- Trade #2: size 1.5×, SL 0.3% (tighter vs 0.5%)
- Reset counter on breakout or 20-candle timeout
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
    # SIDEWAYS-specific (from v0.9)
    sideways_cfg: SidewaysConfig = field(default_factory=SidewaysConfig)
    sw_max_hold: int = 48
    sw_sl_pct_from_level: float = 0.005
    sw_tp1_ratio: float = 0.5
    sw_tp2_ratio: float = 0.3
    sw_tp3_ratio: float = 0.2
    sw_ema_period: int = 20
    sw_ema_exit_min_profit_pct: float = 0.003
    sw_ema_reject_cooldown: int = 48

    # BULL/BEAR shared
    bull_cfg: BullConfig = field(default_factory=BullConfig)
    bear_cfg: BearConfig = field(default_factory=BearConfig)
    trending_max_hold: int = 200

    # Double confirm rules
    double_confirm_lookback: int = 20      # window candles
    double_confirm_tolerance: float = 0.003  # 0.3% level tolerance
    double_size_multiplier: float = 1.5
    double_sl_pct: float = 0.003            # tighter SL

    # Common
    position_usd: float = 10.0
    leverage: float = 50.0
    fee_pct: float = 0.0004
    slippage_pct: float = 0.001


@dataclass
class TradeRecord:
    state: str                              # SIDEWAYS / BULL / BEAR
    side: str                               # long / short
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_high: float                       # for HH breach tracking
    entry_low: float                        # for LL breach tracking
    exit_reason: str
    pnl_net: float
    hold_candles: int
    is_double: bool = False                 # was this trade a double-confirm boosted?
    size_multiplier: float = 1.0
    state_transition: str = ""              # what state we went to after


def _pnl_from(entry_price, exit_price, side, notional, fee_pct, slippage_pct):
    if side == "long":
        gross_pct = (exit_price - entry_price) / entry_price
    else:
        gross_pct = (entry_price - exit_price) / entry_price
    gross = gross_pct * notional
    fee = fee_pct * notional * 2
    slip = slippage_pct * notional
    return gross - fee - slip


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
    """
    Run 3-state orchestrator backtest.
    State starts at SIDEWAYS. Transitions per rules.
    """
    n = len(closes)
    if n < warmup + 50:
        return {"ok": False, "error": f"insufficient candles: {n}"}

    # Precompute
    ema20 = compute_ema(closes, cfg.sw_ema_period)
    regime_cfg = RegimeConfig()
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)

    # Precompute SIDEWAYS signals list (used in SIDEWAYS state)
    sw_signals = generate_sideways_signals(
        highs, lows, closes, volumes, regime_states, cfg.sideways_cfg,
        mtf_classifications=mtf_classifications, opens=opens,
    )
    sw_signal_by_idx = {sig.idx: sig for sig in sw_signals}

    trades: list[TradeRecord] = []
    state = State.SIDEWAYS
    state_transitions: list[dict] = []  # audit trail

    # Anchor points for HH/LL tracking
    last_short_entry_high: Optional[float] = None
    last_long_entry_low: Optional[float] = None
    last_short_entry_idx: Optional[int] = None
    last_long_entry_idx: Optional[int] = None

    # Double confirm state
    recent_short_reject_highs: list[tuple[int, float]] = []  # (idx, high) recent SHORT reject signals
    recent_long_bounce_lows: list[tuple[int, float]] = []    # (idx, low) recent LONG bounce signals

    # Post-safeguard-exit watch: after EMA reject exit in SIDEWAYS, watch N candles for breach
    watch_for_breach: Optional[dict] = None  # {side: 'long'|'short', anchor: price, expires_at: idx}

    # EMA reject cooldown (from v0.9)
    ema_reject_long_cd_until = -1
    ema_reject_short_cd_until = -1

    i = warmup
    while i < n - 1:
        c = float(closes[i])
        cur_ema = float(ema20[i])

        # ═══════════════ Priority check: watch_for_breach ═══════════════
        # After SIDEWAYS safeguard exit, check next N candles for HH/LL breach
        if watch_for_breach is not None and i <= watch_for_breach["expires_at"]:
            if watch_for_breach["side"] == "short" and c > watch_for_breach["anchor"]:
                # SHORT was rejected + candle break entry high → SWITCH BULL
                state_transitions.append({
                    "idx": i, "from": state.value, "to": "bull",
                    "reason": f"HH breach: close {c:.2f} > short anchor {watch_for_breach['anchor']:.2f}",
                })
                state = State.BULL
                watch_for_breach = None
            elif watch_for_breach["side"] == "long" and c < watch_for_breach["anchor"]:
                # LONG was rejected + candle break entry low → SWITCH BEAR
                state_transitions.append({
                    "idx": i, "from": state.value, "to": "bear",
                    "reason": f"LL breach: close {c:.2f} < long anchor {watch_for_breach['anchor']:.2f}",
                })
                state = State.BEAR
                watch_for_breach = None
            elif i >= watch_for_breach["expires_at"]:
                watch_for_breach = None  # timeout, no breach → stay SIDEWAYS

        # ═══════════════ STATE: SIDEWAYS ═══════════════
        if state == State.SIDEWAYS:
            sig = sw_signal_by_idx.get(i)
            if sig is None:
                i += 1
                continue

            # Check EMA reject cooldown (v0.9)
            if sig.side == SideEnum.LONG and i < ema_reject_long_cd_until:
                i += 1
                continue
            if sig.side == SideEnum.SHORT and i < ema_reject_short_cd_until:
                i += 1
                continue

            side_str = "long" if sig.side == SideEnum.LONG else "short"

            # ─── Check double confirm ───
            is_double = False
            size_mult = 1.0
            sl_pct = cfg.sw_sl_pct_from_level

            if side_str == "short":
                # Check if there's a recent SHORT reject signal within tolerance
                for prev_idx, prev_high in recent_short_reject_highs:
                    if i - prev_idx > cfg.double_confirm_lookback:
                        continue
                    cur_high = float(highs[i])
                    if abs(cur_high - prev_high) / prev_high <= cfg.double_confirm_tolerance:
                        is_double = True
                        size_mult = cfg.double_size_multiplier
                        sl_pct = cfg.double_sl_pct
                        break
                # Update recent list
                recent_short_reject_highs.append((i, float(highs[i])))
                # Trim old
                recent_short_reject_highs = [
                    (idx, hi) for idx, hi in recent_short_reject_highs
                    if i - idx <= cfg.double_confirm_lookback
                ]
            else:  # long
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

            # ─── Execute SIDEWAYS trade (simplified from v0.9) ───
            entry_price = c * (1 + cfg.slippage_pct if side_str == "long" else 1 - cfg.slippage_pct)
            position_usd = cfg.position_usd * size_mult
            notional = position_usd * cfg.leverage

            # SL/TP from VAL/VAH/POC
            if side_str == "long":
                sl_level = sig.val * (1 - sl_pct)
                tp1_p = sig.poc
                tp3_p = sig.vah
            else:
                sl_level = sig.vah * (1 + sl_pct)
                tp1_p = sig.poc
                tp3_p = sig.val

            # Validation
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

            # Manage position
            for j in range(entry_idx + 1, min(entry_idx + cfg.sw_max_hold + 1, n)):
                hh = float(highs[j])
                ll = float(lows[j])
                cc = float(closes[j])
                cur_ema_j = float(ema20[j])

                # SL check (close-confirm from v0.7.1)
                sl_hit = (side_str == "long" and cc <= sl_level) or \
                         (side_str == "short" and cc >= sl_level)
                if sl_hit:
                    exit_reason = "sl_breakeven" if moved_to_be else "sl"
                    exit_price = cc
                    exit_idx = j
                    break

                # TP1
                if not tp1_hit:
                    if (side_str == "long" and hh >= tp1_p) or (side_str == "short" and ll <= tp1_p):
                        tp1_hit = True
                        pn = notional * cfg.sw_tp1_ratio
                        gp = (tp1_p - entry_price) / entry_price if side_str == "long" else (entry_price - tp1_p) / entry_price
                        realized_pnl += gp * pn - cfg.fee_pct * pn - cfg.slippage_pct * pn
                        remaining -= cfg.sw_tp1_ratio
                        sl_level = entry_price
                        moved_to_be = True

                # TP2, TP3 (simplified—skip intermediate levels)
                if tp1_hit and remaining > 0:
                    if (side_str == "long" and hh >= tp3_p) or (side_str == "short" and ll <= tp3_p):
                        exit_reason = "tp3"
                        exit_price = tp3_p
                        exit_idx = j
                        break

                # EMA reject exit (v0.7.1: current-profit gate)
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

                # Max hold
                if j - entry_idx >= cfg.sw_max_hold:
                    exit_reason = "max_hold"
                    exit_price = cc
                    exit_idx = j
                    break
            else:
                exit_idx = min(entry_idx + cfg.sw_max_hold, n - 1)
                exit_price = float(closes[exit_idx])

            # Compute final PnL including remaining
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

            # Track anchors
            if side_str == "short":
                last_short_entry_high = entry_high_anchor
                last_short_entry_idx = entry_idx
            else:
                last_long_entry_low = entry_low_anchor
                last_long_entry_idx = entry_idx

            # Set EMA reject cooldown for same direction
            if exit_reason == "ema_reject":
                if side_str == "long":
                    ema_reject_long_cd_until = exit_idx + cfg.sw_ema_reject_cooldown
                else:
                    ema_reject_short_cd_until = exit_idx + cfg.sw_ema_reject_cooldown

                # Set watch for breach (SIDEWAYS transition trigger)
                # Watch for 10 candles after EMA reject exit for HH/LL breach
                watch_for_breach = {
                    "side": side_str,
                    "anchor": entry_high_anchor if side_str == "short" else entry_low_anchor,
                    "expires_at": exit_idx + 10,
                }
                trades[-1].state_transition = f"watch_{side_str}_breach"

            i = exit_idx + 1
            continue

        # ═══════════════ STATE: BULL ═══════════════
        elif state == State.BULL:
            sig = detect_bull_entry_signal(highs, lows, closes, opens, ema20, i, cfg.bull_cfg)
            if sig is None:
                # Also check if we should switch state without entry (LL breach absent → stay BULL)
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

            # State transition based on trade outcome
            if trade.state_signal == "switch_bear":
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bull", "to": "bear",
                    "reason": "LL breach during BULL trade",
                })
                state = State.BEAR
            else:  # stay_bull → but we changed rule: trailing exit → SIDEWAYS
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bull", "to": "sideways",
                    "reason": "Trailing stop, no LL breach",
                })
                state = State.SIDEWAYS

            i = trade.exit_idx + 1
            continue

        # ═══════════════ STATE: BEAR ═══════════════
        elif state == State.BEAR:
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

            if trade.state_signal == "switch_bull":
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bear", "to": "bull",
                    "reason": "HH breach during BEAR trade",
                })
                state = State.BULL
            else:  # stay_bear → trailing exit → SIDEWAYS
                state_transitions.append({
                    "idx": trade.exit_idx, "from": "bear", "to": "sideways",
                    "reason": "Trailing stop, no HH breach",
                })
                state = State.SIDEWAYS

            i = trade.exit_idx + 1
            continue

        else:
            i += 1

    # Aggregate stats
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
        "orchestrator": "v1.0",
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
