"""
Mode4 Switcher — Trend-following bot.

Entry rules:
- TREND_LONG: close breaks EMA20 up + volume > 1.5x avg + slope > 1%
- TREND_SHORT: close breaks EMA20 down + volume > 1.5x avg + slope > 1%

Exit rules:
- TP: fixed 1.0%
- SL: fixed 0.5%
- No EMA_INVALIDATION (trend-follower stays in until TP/SL)

State: simpler than Mode3 — just IDLE or IN_POSITION.
"""
from dataclasses import dataclass
from typing import Optional
from collections import deque
from .config import Mode4Config


@dataclass
class Position:
    tool: str
    side: str
    entry_price: float
    entry_bar: int
    sl_level: float
    tp_level: float


@dataclass
class Trade:
    tool: str
    side: str
    entry_price: float
    exit_price: float
    entry_bar: int
    exit_bar: int
    exit_type: str
    pnl_pct: float
    pnl_usd: float


class Switcher:
    def __init__(self, config):
        self.config = config
        self.position = None
        self.trades = []
        self._volume_history = deque(maxlen=config.volume_window)
        self._ema_history = deque(maxlen=config.slope_window)
        self._blocked_volume = 0
        self._blocked_slope = 0
        self._prev_ema20 = None
        self._prev_close = None

    def process_candle(self, bar_idx, o, h, l, c, v, ema20):
        self._volume_history.append(v)
        if ema20 > 0:
            self._ema_history.append(ema20)

        # Exit check
        if self.position is not None:
            self._check_exit(bar_idx, c)

        # Entry check
        if self.position is None:
            self._check_entry(bar_idx, o, c, v, ema20)

        self._prev_ema20 = ema20
        self._prev_close = c

    def _check_exit(self, bar_idx, c):
        pos = self.position
        if pos.side == 'LONG':
            if c >= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); return
            if c <= pos.sl_level:
                self._close_position(bar_idx, c, 'SL'); return
        else:  # SHORT
            if c <= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); return
            if c >= pos.sl_level:
                self._close_position(bar_idx, c, 'SL'); return

    def _volume_ok(self, v):
        min_ratio = self.config.min_volume_ratio
        if min_ratio <= 0: return True
        if len(self._volume_history) < self.config.volume_window: return False
        avg = sum(self._volume_history) / len(self._volume_history)
        if avg <= 0: return True
        return v >= avg * min_ratio

    def _slope_ok(self):
        """Require STRONG trend (opposite of Mode3)."""
        min_slope = self.config.min_slope_pct
        if min_slope <= 0: return True
        if len(self._ema_history) < self.config.slope_window: return False
        hist = list(self._ema_history)
        if hist[0] <= 0: return True
        slope_pct = abs(hist[-1] - hist[0]) / hist[0]
        return slope_pct >= min_slope

    def _check_entry(self, bar_idx, o, c, v, ema20):
        if ema20 <= 0 or self._prev_close is None or self._prev_ema20 is None:
            return

        # BREAKOUT LONG: close crosses ABOVE EMA20
        long_break = (self._prev_close <= self._prev_ema20) and (c > ema20) and (c > o)
        # BREAKOUT SHORT: close crosses BELOW EMA20
        short_break = (self._prev_close >= self._prev_ema20) and (c < ema20) and (c < o)

        if not (long_break or short_break):
            return

        # Filters
        if not self._volume_ok(v):
            self._blocked_volume += 1
            return
        if not self._slope_ok():
            self._blocked_slope += 1
            return

        # Enter
        if long_break:
            self.position = Position(
                tool='TREND', side='LONG',
                entry_price=c, entry_bar=bar_idx,
                sl_level=c * (1.0 - self.config.sl_pct),
                tp_level=c * (1.0 + self.config.tp_pct),
            )
        elif short_break:
            self.position = Position(
                tool='TREND', side='SHORT',
                entry_price=c, entry_bar=bar_idx,
                sl_level=c * (1.0 + self.config.sl_pct),
                tp_level=c * (1.0 - self.config.tp_pct),
            )

    def _close_position(self, bar_idx, exit_price, exit_type):
        pos = self.position
        if pos.side == 'LONG':
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        pnl_pct_net = pnl_pct - self.config.total_cost_pct()
        pnl_usd = pnl_pct_net * self.config.notional()
        self.trades.append(Trade(
            tool=pos.tool, side=pos.side,
            entry_price=pos.entry_price, exit_price=exit_price,
            entry_bar=pos.entry_bar, exit_bar=bar_idx,
            exit_type=exit_type,
            pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
        ))
        self.position = None
