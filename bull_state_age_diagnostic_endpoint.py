"""Causal BULL-only limit diagnostic with explicit state freshness controls.

This route is intentionally separate from the production BBC live routes and
from the existing causal-state-mtf-limit diagnostic.  It exists to measure
whether stale/permissive BULL state is responsible for poor causal results.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher
from causal_bbc_endpoint import (
    _body_ratio,
    _ema_series,
    _load_rows,
    _sync_state_after_exit,
    _value_area,
)
from causal_state_mtf_reject_endpoint import _dummy_position


router = APIRouter(prefix="/mode3_bbc", tags=["bbc_bull_state_age_diagnostic"])
HOUR_MS = 60 * 60 * 1000


@dataclass
class BullPosition:
    tool: str
    side: str
    entry_price: float
    sl: float
    tp: float
    entry_hour: int
    entry_time: int
    peak_high: float
    trough_low: float
    state_age_hours: int
    limit_ema: float


@dataclass
class BullTrade:
    tool: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: int
    exit_time: int
    exit_type: str
    pnl_pct: float
    pnl_usd: float
    state_age_hours: int


def _close(position, price, timestamp, exit_type, cfg):
    raw_pct = (float(price) - position.entry_price) / position.entry_price
    net_pct = raw_pct - cfg.total_cost_pct()
    return BullTrade(
        tool="BULL",
        side="LONG",
        entry_price=position.entry_price,
        exit_price=float(price),
        entry_time=position.entry_time,
        exit_time=int(timestamp),
        exit_type=exit_type,
        pnl_pct=net_pct,
        pnl_usd=net_pct * cfg.notional(),
        state_age_hours=position.state_age_hours,
    )


def _summarize(trades):
    wins = [trade for trade in trades if trade.pnl_usd > 0]
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    loss_streak = 0
    max_loss_streak = 0
    exits = {}
    for trade in trades:
        equity += trade.pnl_usd
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        exits[trade.exit_type] = exits.get(trade.exit_type, 0) + 1
        if trade.pnl_usd <= 0:
            loss_streak += 1
            max_loss_streak = max(max_loss_streak, loss_streak)
        else:
            loss_streak = 0
    count = len(trades)
    return {
        "total_trades": count,
        "wins": len(wins),
        "losses": count - len(wins),
        "win_rate_pct": round(100.0 * len(wins) / count, 2) if count else 0.0,
        "total_pnl_usd": round(sum(t.pnl_usd for t in trades), 2),
        "max_drawdown_usd": round(max_drawdown, 2),
        "max_loss_streak": max_loss_streak,
        "avg_state_age_hours": round(
            sum(t.state_age_hours for t in trades) / count, 2
        ) if count else 0.0,
        "exit_type_breakdown": exits,
    }


def _qualifies_bull_refresh(row, ema_now, ema_previous, body_min,
                            require_positive_slope, max_distance_pct):
    o = float(row[1])
    h = float(row[2])
    l = float(row[3])
    c = float(row[4])
    if c <= ema_now or c <= o:
        return False
    if _body_ratio(o, h, l, c) < body_min:
        return False
    if require_positive_slope and ema_now <= ema_previous:
        return False
    if max_distance_pct > 0 and (c - ema_now) / ema_now > max_distance_pct:
        return False
    return True


@router.get("/bull-state-age-limit")
def bull_state_age_limit(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(20, ge=5, le=100),
    limit_ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.001, le=0.10),
    bull_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    regime_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    max_state_age_hours: int = Query(0, ge=0, le=1000),
    freshness_mode: str = Query("transition"),
    require_positive_slope: bool = Query(False),
    max_close_distance_pct: float = Query(0.0, ge=0.0, le=0.25),
    regime_exit_enabled: bool = Query(False),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    fee_pct: float = Query(0.001, ge=0.0, le=0.10),
    slippage_pct: float = Query(0.0005, ge=0.0, le=0.10),
    include_trades: bool = Query(False),
):
    """Run a true BULL-only, causal one-candle EMA limit simulation.

    ``transition`` freshness measures age since the BBC state entered BULL.
    ``body_refresh`` refreshes age only after a completed qualifying BULL 1H
    candle.  A value of zero for max_state_age_hours disables the age cap.
    """
    if freshness_mode not in ("transition", "body_refresh"):
        return {"error": "freshness_mode must be transition or body_refresh"}

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ms = now_ms - end_days_ago * 86400 * 1000
    start_ms = end_ms - days * 86400 * 1000
    rows = _load_rows(symbol, timeframe, start_ms, end_ms)
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if len(rows) < va_window + 5:
        return {"error": f"Not enough 1H candles: {len(rows)}", "trades": []}
    if not rows15:
        return {"error": "15m data is required", "trades": []}

    cfg = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        bull_body_ratio_min=bull_body_ratio_min,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        enable_sideways_trades=False,
    )
    ema1h = _ema_series([float(row[4]) for row in rows], ema_period)
    ema15 = _ema_series([float(row[4]) for row in rows15], limit_ema_period)
    ema15_before = {
        int(rows15[j][0]): ema15[j - 1]
        for j in range(1, len(rows15))
    }
    vah, val, poc = _value_area(rows, va_window)

    by_hour = {}
    for row in rows15:
        by_hour.setdefault(int(row[0]) // HOUR_MS, []).append(row)
    for bars in by_hour.values():
        bars.sort(key=lambda row: int(row[0]))

    switcher = Switcher(cfg)
    active: Optional[BullPosition] = None
    trades = []
    bull_entered_at = None
    last_body_refresh_at = None
    pending_regime_exit = False
    order_attempts = 0
    fills = 0
    eligible_15m_bars = 0
    blocked_by_age = 0
    blocked_without_refresh = 0
    no_reentry_after_exit = 0

    for i, row in enumerate(rows):
        hour_key = int(row[0]) // HOUR_MS
        bars = by_hour.get(hour_key, [])[:4]
        if len(bars) < 4:
            continue

        source_index = (
            bull_entered_at
            if freshness_mode == "transition"
            else last_body_refresh_at
        )
        state_age = i - source_index if source_index is not None else None
        age_is_valid = (
            max_state_age_hours == 0
            or (state_age is not None and state_age <= max_state_age_hours)
        )

        for bar_index, bar in enumerate(bars):
            bar_time = int(bar[0])
            exited_this_bar = False

            # A reversal is known only after the prior 1H candle closes, so
            # execution occurs at the next available 15m open.
            if pending_regime_exit and bar_index == 0:
                if active is not None:
                    trades.append(_close(active, float(bar[1]), bar_time, "REGIME", cfg))
                    active = None
                    bull_entered_at = None
                    last_body_refresh_at = None
                    if switcher.state == "BULL":
                        switcher.state = "WAIT_SEE_BULLISH"
                    exited_this_bar = True
                pending_regime_exit = False

            if active is not None:
                active.peak_high = max(active.peak_high, float(bar[2]))
                active.trough_low = min(active.trough_low, float(bar[3]))
                hit_sl = float(bar[3]) < active.sl
                hit_tp = float(bar[2]) >= active.tp
                if hit_sl:
                    trades.append(_close(active, active.sl, bar_time, "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                    exited_this_bar = True
                elif hit_tp:
                    trades.append(_close(active, active.tp, bar_time, "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
                    exited_this_bar = True

            if active is not None:
                continue
            if exited_this_bar:
                no_reentry_after_exit += 1
                continue
            # A TP keeps BULL warm; an SL/regime exit moves the Switcher to a
            # WAIT state immediately and must block later entries this hour.
            if switcher.state != "BULL":
                continue
            if freshness_mode == "body_refresh" and source_index is None:
                blocked_without_refresh += 1
                continue
            if not age_is_valid:
                blocked_by_age += 1
                continue

            eligible_15m_bars += 1
            level = ema15_before.get(bar_time)
            if level is None:
                continue
            order_attempts += 1
            o = float(bar[1])
            h = float(bar[2])
            l = float(bar[3])
            if l > level:
                continue

            fills += 1
            fill_price = o if o <= level else level
            active = BullPosition(
                tool="BULL",
                side="LONG",
                entry_price=fill_price,
                sl=fill_price * (1.0 - sl_pct),
                tp=fill_price * (1.0 + tp_pct),
                entry_hour=i,
                entry_time=bar_time,
                peak_high=h,
                trough_low=l,
                state_age_hours=int(state_age or 0),
                limit_ema=level,
            )

            # Conservative completed-candle ordering: SL wins ambiguity.
            if l < active.sl:
                trades.append(_close(active, active.sl, bar_time, "SL", cfg))
                _sync_state_after_exit(switcher, active, "SL")
                active = None
                no_reentry_after_exit += 1
            elif h >= active.tp:
                trades.append(_close(active, active.tp, bar_time, "TP", cfg))
                _sync_state_after_exit(switcher, active, "TP")
                active = None
                no_reentry_after_exit += 1

        state_before_close = switcher.state
        if active is not None:
            switcher.position = _dummy_position(active)
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            switcher.position = None
        else:
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            # Direct entries from the 1H Switcher are signals only here.
            switcher.position = None

        if switcher.state == "BULL" and state_before_close != "BULL":
            bull_entered_at = i
        elif switcher.state != "BULL":
            bull_entered_at = None
            last_body_refresh_at = None

        if switcher.state == "BULL" and i > 0 and _qualifies_bull_refresh(
            row,
            ema1h[i],
            ema1h[i - 1],
            bull_body_ratio_min,
            require_positive_slope,
            max_close_distance_pct,
        ):
            last_body_refresh_at = i

        if regime_exit_enabled and active is not None:
            o = float(row[1])
            h = float(row[2])
            l = float(row[3])
            c = float(row[4])
            pending_regime_exit = (
                c < ema1h[i]
                and c < o
                and _body_ratio(o, h, l, c) >= regime_body_ratio_min
            )

    if active is not None:
        last = rows15[-1]
        trades.append(_close(active, float(last[4]), int(last[0]), "END", cfg))

    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "causal": True,
        "bull_only": True,
        "entry_timing": "one_candle_limit_at_previous_completed_15m_ema",
        "regime_exit_timing": "next_15m_open_after_completed_1h_flip",
        "config": {
            "ema_period": ema_period,
            "limit_ema_period": limit_ema_period,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "bull_body_ratio_min": bull_body_ratio_min,
            "regime_body_ratio_min": regime_body_ratio_min,
            "max_state_age_hours": max_state_age_hours,
            "freshness_mode": freshness_mode,
            "require_positive_slope": require_positive_slope,
            "max_close_distance_pct": max_close_distance_pct,
            "regime_exit_enabled": regime_exit_enabled,
            "fee_pct": fee_pct,
            "slippage_pct": slippage_pct,
        },
        "orders": {
            "eligible_15m_bars": eligible_15m_bars,
            "attempts": order_attempts,
            "fills": fills,
            "fill_rate_pct": round(100.0 * fills / order_attempts, 2)
            if order_attempts else 0.0,
            "blocked_by_age": blocked_by_age,
            "blocked_without_refresh": blocked_without_refresh,
            "no_reentry_after_exit": no_reentry_after_exit,
        },
        "summary": _summarize(trades),
    }
    if include_trades:
        result["trades"] = [asdict(trade) for trade in trades]
    return result


@router.get("/health-bull-state-age-limit")
def health_bull_state_age_limit():
    return {
        "status": "ok",
        "module": "bbc_bull_state_age_diagnostic",
        "live_trading_changed": False,
    }
