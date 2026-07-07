"""
backtest_sideways.py — v0.8: pass-through bias_arr_1h to strategy
==================================================================
v0.8 change: add bias_arr_1h param, forward to generate_sideways_signals
Everything else preserved from v0.7.1.
"""

from __future__ import annotations
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .regime import RegimeConfig, RegimeState, classify_regime_series
from .strategy_sideways import (
    SideEnum, SidewaysMode, SidewaysConfig, SidewaysSignal,
    generate_sideways_signals,
)
from .indicators import atr as compute_atr, ema as compute_ema


class ExitReasonSW(Enum):
    TP1 = "tp1"
    TP2 = "tp2"
    TP3 = "tp3"
    SL = "sl"
    SL_BE = "sl_breakeven"
    MAX_HOLD = "max_hold"
    CIRCUIT_BREAKER = "circuit_breaker"
    END = "end_of_data"
    EMA_REJECT = "ema_reject"


@dataclass
class SidewaysBTConfig:
    position_usd: float = 10.0
    leverage: float = 50.0
    fee_pct: float = 0.0004
    slippage_pct: float = 0.001
    candle_hours: float = 1.0

    sl_pct_from_level: float = 0.005

    use_atr_sl: bool = False
    sl_atr_mult: float = 1.5
    atr_period: int = 14

    tp1_ratio: float = 0.5
    tp2_ratio: float = 0.3
    tp3_ratio: float = 0.2
    move_sl_to_be_after_tp1: bool = True

    max_hold_candles: int = 12

    max_consec_losses: int = 5
    max_drawdown_pct: float = 0.10
    cooldown_after_breaker: int = 48

    use_ema_dynamic_exit: bool = False
    ema_exit_period: int = 20
    ema_exit_min_profit_pct: float = 0.003
    use_close_confirm_sl: bool = False


@dataclass
class SidewaysTradeRecord:
    entry_idx: int
    exit_idx: int
    side: str
    mode: str
    reason: str
    regime: str
    confidence: float
    score: int
    mtf_confidence: int
    position_usd: float
    entry_price: float
    exit_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    exit_reason: str
    pnl_net: float
    hold_candles: int
    ema_slope_pct: float = 0.0
    max_profit_pct: float = 0.0
    bias_4h: int = 0


@dataclass
class SidewaysBTStats:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    total_pnl_net: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    trades_per_day: float = 0.0
    tp1_hit_rate: float = 0.0
    tp2_hit_rate: float = 0.0
    tp3_hit_rate: float = 0.0
    exit_by_reason: dict = field(default_factory=dict)
    by_regime: dict = field(default_factory=dict)
    by_mode: dict = field(default_factory=dict)
    by_confidence_tier: dict = field(default_factory=dict)
    by_mtf_tier: dict = field(default_factory=dict)
    runtime_sec: float = 0.0
    total_candles: int = 0


@dataclass
class SidewaysBTResult:
    stats: SidewaysBTStats
    trades: list[SidewaysTradeRecord]
    error: Optional[str] = None


def _tier_label(conf: float) -> str:
    if conf >= 0.99: return "full"
    elif conf >= 0.49: return "half"
    elif conf >= 0.24: return "quarter"
    else: return "skip"


def _mtf_tier_label(mtf_conf: int) -> str:
    if mtf_conf == 3: return "3_of_3"
    elif mtf_conf == 2: return "2_of_3"
    elif mtf_conf == 1: return "1_of_3"
    elif mtf_conf == 0: return "0_of_3"
    else: return "no_mtf"


def _close_position_now(active_pos, cfg, exit_price, exit_reason, i):
    side = active_pos['side']
    entry = active_pos['entry_price']
    notional = active_pos['position_usd'] * cfg.leverage
    remaining = active_pos['remaining_ratio']
    if remaining > 0:
        gross_pct = (exit_price - entry) / entry if side == 'long' else (entry - exit_price) / entry
        remaining_notional = notional * remaining
        remaining_pnl = gross_pct * remaining_notional
        remaining_fee = cfg.fee_pct * remaining_notional
        remaining_slip = cfg.slippage_pct * remaining_notional
        final_pnl = active_pos['realized_pnl'] + (remaining_pnl - remaining_fee - remaining_slip)
    else:
        final_pnl = active_pos['realized_pnl']
    entry_fee = cfg.fee_pct * notional
    entry_slip = cfg.slippage_pct * notional
    final_pnl -= entry_fee + entry_slip

    return SidewaysTradeRecord(
        entry_idx=active_pos['entry_idx'],
        exit_idx=i,
        side=side,
        mode=active_pos['mode'],
        reason=active_pos['reason'],
        regime=active_pos['regime'],
        confidence=active_pos['confidence'],
        score=active_pos['score'],
        mtf_confidence=active_pos['mtf_confidence'],
        position_usd=active_pos['position_usd'],
        entry_price=entry,
        exit_price=exit_price,
        sl_price=active_pos['orig_sl'],
        tp1_price=active_pos['tp1'], tp2_price=active_pos['tp2'], tp3_price=active_pos['tp3'],
        tp1_hit=active_pos['tp1_hit'],
        tp2_hit=active_pos['tp2_hit'],
        tp3_hit=active_pos['tp3_hit'],
        exit_reason=exit_reason.value,
        pnl_net=final_pnl,
        hold_candles=i - active_pos['entry_idx'],
        ema_slope_pct=active_pos.get('ema_slope_pct', 0.0),
        max_profit_pct=active_pos.get('max_profit_pct', 0.0),
        bias_4h=active_pos.get('bias_4h', 0),
    )


def run_sideways_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: SidewaysBTConfig,
    regime_cfg: Optional[RegimeConfig] = None,
    strategy_cfg: Optional[SidewaysConfig] = None,
    warmup: int = 100,
    mtf_classifications: Optional[list] = None,
    opens: Optional[np.ndarray] = None,
    bias_arr_1h: Optional[np.ndarray] = None,   # v0.8
) -> SidewaysBTResult:
    t0 = time.time()

    regime_cfg = regime_cfg or RegimeConfig()
    strategy_cfg = strategy_cfg or SidewaysConfig()

    n = len(closes)
    if n < warmup + 50:
        return SidewaysBTResult(
            stats=SidewaysBTStats(), trades=[],
            error=f"insufficient candles: {n}",
        )

    print(f"[SW BT v0.8] Classifying regime for {n} candles...")
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)

    print(f"[SW BT v0.8] Generating signals (MTF: {strategy_cfg.use_mtf_filter}, 4h bias: {strategy_cfg.use_4h_bias_filter})...")
    signals = generate_sideways_signals(
        highs, lows, closes, volumes, regime_states, strategy_cfg,
        mtf_classifications=mtf_classifications,
        opens=opens,
        bias_arr_1h=bias_arr_1h,
    )
    print(f"[SW BT v0.8] {len(signals)} signals generated")

    atr_arr = None
    if cfg.use_atr_sl:
        atr_arr = compute_atr(highs, lows, closes, cfg.atr_period)

    ema_arr = None
    if cfg.use_ema_dynamic_exit:
        ema_arr = compute_ema(closes, cfg.ema_exit_period)

    trades: list[SidewaysTradeRecord] = []
    equity = cfg.position_usd * 10
    starting_equity = equity
    peak_equity = equity
    max_dd = 0.0
    consec_losses = 0
    breaker_until = -1

    active_pos = None
    sig_iter = iter(signals)
    next_sig = next(sig_iter, None)

    for i in range(n):
        if active_pos is not None:
            h, l, c = highs[i], lows[i], closes[i]
            side = active_pos['side']
            entry = active_pos['entry_price']
            sl = active_pos['sl']
            tp1, tp2, tp3 = active_pos['tp1'], active_pos['tp2'], active_pos['tp3']
            notional = active_pos['position_usd'] * cfg.leverage

            if side == 'long':
                cur_profit_wick = (h - entry) / entry
            else:
                cur_profit_wick = (entry - l) / entry
            if cur_profit_wick > active_pos.get('max_profit_pct', 0.0):
                active_pos['max_profit_pct'] = cur_profit_wick

            close_pos = False
            exit_reason = None
            exit_price = 0.0

            if cfg.use_close_confirm_sl:
                sl_hit = (side == 'long' and c <= sl) or (side == 'short' and c >= sl)
            else:
                sl_hit = (side == 'long' and l <= sl) or (side == 'short' and h >= sl)

            if sl_hit:
                if active_pos['moved_to_be']:
                    exit_reason = ExitReasonSW.SL_BE
                else:
                    exit_reason = ExitReasonSW.SL
                exit_price = sl if not cfg.use_close_confirm_sl else c
                close_pos = True

            if not close_pos:
                if not active_pos['tp1_hit']:
                    tp1_reached = (side == 'long' and h >= tp1) or (side == 'short' and l <= tp1)
                    if tp1_reached:
                        active_pos['tp1_hit'] = True
                        gross_pct = (tp1 - entry) / entry if side == 'long' else (entry - tp1) / entry
                        partial_notional = notional * cfg.tp1_ratio
                        active_pos['realized_pnl'] += gross_pct * partial_notional - cfg.fee_pct * partial_notional - cfg.slippage_pct * partial_notional
                        active_pos['remaining_ratio'] -= cfg.tp1_ratio
                        if cfg.move_sl_to_be_after_tp1:
                            active_pos['sl'] = entry
                            active_pos['moved_to_be'] = True

                if active_pos['tp1_hit'] and not active_pos['tp2_hit']:
                    tp2_reached = (side == 'long' and h >= tp2) or (side == 'short' and l <= tp2)
                    if tp2_reached:
                        active_pos['tp2_hit'] = True
                        gross_pct = (tp2 - entry) / entry if side == 'long' else (entry - tp2) / entry
                        partial_notional = notional * cfg.tp2_ratio
                        active_pos['realized_pnl'] += gross_pct * partial_notional - cfg.fee_pct * partial_notional - cfg.slippage_pct * partial_notional
                        active_pos['remaining_ratio'] -= cfg.tp2_ratio

                if active_pos['tp2_hit'] and not active_pos['tp3_hit']:
                    tp3_reached = (side == 'long' and h >= tp3) or (side == 'short' and l <= tp3)
                    if tp3_reached:
                        active_pos['tp3_hit'] = True
                        exit_reason = ExitReasonSW.TP3
                        exit_price = tp3
                        close_pos = True

            if not close_pos and cfg.use_ema_dynamic_exit and ema_arr is not None and i < len(ema_arr):
                cur_ema = float(ema_arr[i])
                if cur_ema > 0 and not active_pos.get('ema_broken_through', False):
                    if side == 'long':
                        cur_profit_at_close = (c - entry) / entry
                    else:
                        cur_profit_at_close = (entry - c) / entry
                    min_profit_ok = cur_profit_at_close >= cfg.ema_exit_min_profit_pct

                    if side == 'long':
                        if c >= cur_ema:
                            active_pos['ema_broken_through'] = True
                        elif h >= cur_ema and c < cur_ema and min_profit_ok:
                            exit_reason = ExitReasonSW.EMA_REJECT
                            exit_price = c
                            close_pos = True
                    else:
                        if c <= cur_ema:
                            active_pos['ema_broken_through'] = True
                        elif l <= cur_ema and c > cur_ema and min_profit_ok:
                            exit_reason = ExitReasonSW.EMA_REJECT
                            exit_price = c
                            close_pos = True

            if not close_pos and (i - active_pos['entry_idx']) >= cfg.max_hold_candles:
                exit_reason = ExitReasonSW.MAX_HOLD
                exit_price = c
                close_pos = True

            if close_pos:
                trade = _close_position_now(active_pos, cfg, exit_price, exit_reason, i)
                trades.append(trade)
                equity += trade.pnl_net

                if equity > peak_equity:
                    peak_equity = equity
                dd = peak_equity - equity
                if dd > max_dd:
                    max_dd = dd

                if trade.pnl_net < 0:
                    consec_losses += 1
                elif trade.pnl_net > 0:
                    consec_losses = 0

                if consec_losses >= cfg.max_consec_losses:
                    breaker_until = i + cfg.cooldown_after_breaker
                    consec_losses = 0
                if peak_equity > 0 and (peak_equity - equity) / peak_equity >= cfg.max_drawdown_pct:
                    breaker_until = i + cfg.cooldown_after_breaker

                active_pos = None

        if i < breaker_until:
            while next_sig is not None and next_sig.idx <= i:
                next_sig = next(sig_iter, None)
            continue

        while next_sig is not None and next_sig.idx < i:
            next_sig = next(sig_iter, None)

        if active_pos is None and next_sig is not None and next_sig.idx == i:
            sig = next_sig
            next_sig = next(sig_iter, None)

            if sig.confidence <= 0.0:
                continue

            entry_price = closes[i]
            if sig.side == SideEnum.LONG:
                entry_price = entry_price * (1 + cfg.slippage_pct)
            else:
                entry_price = entry_price * (1 - cfg.slippage_pct)

            side_str = 'long' if sig.side == SideEnum.LONG else 'short'

            if cfg.use_atr_sl and atr_arr is not None:
                cur_atr = float(atr_arr[i]) if i < len(atr_arr) else 0.0
                if cur_atr <= 0:
                    sl = sig.val * (1 - cfg.sl_pct_from_level) if side_str == 'long' else sig.vah * (1 + cfg.sl_pct_from_level)
                else:
                    sl = entry_price - cur_atr * cfg.sl_atr_mult if side_str == 'long' else entry_price + cur_atr * cfg.sl_atr_mult
            else:
                sl = sig.val * (1 - cfg.sl_pct_from_level) if side_str == 'long' else sig.vah * (1 + cfg.sl_pct_from_level)

            if side_str == 'long':
                tp1 = sig.poc
                tp2 = (sig.poc + sig.vah) / 2
                tp3 = sig.vah
            else:
                tp1 = sig.poc
                tp2 = (sig.poc + sig.val) / 2
                tp3 = sig.val

            if side_str == 'long' and (tp1 <= entry_price or sl >= entry_price):
                continue
            if side_str == 'short' and (tp1 >= entry_price or sl <= entry_price):
                continue

            ema_broken_through_initial = False
            if cfg.use_ema_dynamic_exit and ema_arr is not None and i < len(ema_arr):
                cur_ema = float(ema_arr[i])
                if side_str == 'long' and entry_price >= cur_ema:
                    ema_broken_through_initial = True
                elif side_str == 'short' and entry_price <= cur_ema:
                    ema_broken_through_initial = True

            scaled_position = cfg.position_usd * sig.confidence

            active_pos = {
                'side': side_str,
                'mode': sig.mode.value,
                'reason': sig.reason,
                'regime': sig.regime,
                'confidence': sig.confidence,
                'score': sig.score,
                'mtf_confidence': sig.mtf_confidence,
                'ema_slope_pct': sig.ema_slope_pct,
                'bias_4h': getattr(sig, 'bias_4h', 0),
                'position_usd': scaled_position,
                'entry_idx': i,
                'entry_price': entry_price,
                'sl': sl,
                'orig_sl': sl,
                'tp1': tp1, 'tp2': tp2, 'tp3': tp3,
                'tp1_hit': False, 'tp2_hit': False, 'tp3_hit': False,
                'realized_pnl': 0.0,
                'remaining_ratio': 1.0,
                'moved_to_be': False,
                'ema_broken_through': ema_broken_through_initial,
                'max_profit_pct': 0.0,
            }

    if active_pos is not None:
        trade = _close_position_now(active_pos, cfg, closes[-1], ExitReasonSW.END, n - 1)
        trades.append(trade)
        equity += trade.pnl_net

    stats = SidewaysBTStats()
    stats.total_trades = len(trades)
    stats.total_candles = n
    stats.runtime_sec = time.time() - t0

    wins_pnl, losses_pnl = [], []
    tp1_hits, tp2_hits, tp3_hits = 0, 0, 0
    tier_data = {"full": {"trades": 0, "wins": 0, "pnl": 0.0},
                 "half": {"trades": 0, "wins": 0, "pnl": 0.0},
                 "quarter": {"trades": 0, "wins": 0, "pnl": 0.0}}
    mtf_tier_data = {"3_of_3": {"trades": 0, "wins": 0, "pnl": 0.0},
                     "2_of_3": {"trades": 0, "wins": 0, "pnl": 0.0},
                     "1_of_3": {"trades": 0, "wins": 0, "pnl": 0.0},
                     "no_mtf": {"trades": 0, "wins": 0, "pnl": 0.0}}

    for t in trades:
        stats.total_pnl_net += t.pnl_net
        is_win = t.pnl_net > 0.01
        is_loss = t.pnl_net < -0.01
        if is_win:
            stats.wins += 1
            wins_pnl.append(t.pnl_net)
        elif is_loss:
            stats.losses += 1
            losses_pnl.append(t.pnl_net)
        else:
            stats.breakeven += 1
        stats.exit_by_reason[t.exit_reason] = stats.exit_by_reason.get(t.exit_reason, 0) + 1
        stats.by_regime[t.regime] = stats.by_regime.get(t.regime, 0) + 1
        stats.by_mode[t.mode] = stats.by_mode.get(t.mode, 0) + 1
        if t.tp1_hit: tp1_hits += 1
        if t.tp2_hit: tp2_hits += 1
        if t.tp3_hit: tp3_hits += 1

        tier = _tier_label(t.confidence)
        if tier in tier_data:
            tier_data[tier]["trades"] += 1
            tier_data[tier]["pnl"] += t.pnl_net
            if is_win: tier_data[tier]["wins"] += 1

        mtier = _mtf_tier_label(t.mtf_confidence)
        if mtier in mtf_tier_data:
            mtf_tier_data[mtier]["trades"] += 1
            mtf_tier_data[mtier]["pnl"] += t.pnl_net
            if is_win: mtf_tier_data[mtier]["wins"] += 1

    for tier, td in tier_data.items():
        wr = td["wins"] / td["trades"] if td["trades"] > 0 else 0.0
        stats.by_confidence_tier[tier] = {"trades": td["trades"], "wins": td["wins"], "win_rate": round(wr, 4), "pnl_net": round(td["pnl"], 2)}
    for mtier, td in mtf_tier_data.items():
        wr = td["wins"] / td["trades"] if td["trades"] > 0 else 0.0
        stats.by_mtf_tier[mtier] = {"trades": td["trades"], "wins": td["wins"], "win_rate": round(wr, 4), "pnl_net": round(td["pnl"], 2)}

    if stats.wins + stats.losses > 0:
        stats.win_rate = stats.wins / (stats.wins + stats.losses)
    if wins_pnl:
        stats.avg_win = float(np.mean(wins_pnl))
    if losses_pnl:
        stats.avg_loss = float(np.mean(losses_pnl))

    if stats.total_trades > 0:
        stats.tp1_hit_rate = tp1_hits / stats.total_trades
        stats.tp2_hit_rate = tp2_hits / stats.total_trades
        stats.tp3_hit_rate = tp3_hits / stats.total_trades

    stats.max_drawdown_usd = max_dd
    stats.max_drawdown_pct = max_dd / starting_equity if starting_equity > 0 else 0.0

    days = (n * cfg.candle_hours) / 24.0
    stats.trades_per_day = stats.total_trades / days if days > 0 else 0.0

    return SidewaysBTResult(stats=stats, trades=trades)


__all__ = ["SidewaysBTConfig", "SidewaysTradeRecord", "SidewaysBTStats",
           "SidewaysBTResult", "run_sideways_backtest", "ExitReasonSW"]
