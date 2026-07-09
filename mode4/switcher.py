"""
Mode4 Switcher v0.2 — Trend-following with 5 improvement options.
"""
from dataclasses import dataclass
from typing import Optional, List
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
    peak_price: float = 0.0
    trough_price: float = 1e18
    trailing_active: bool = False


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
        self._close_history = deque(maxlen=max(config.confirmation_bars + 1, config.bos_window + 5))
        self._high_history = deque(maxlen=config.bos_window + 5)
        self._low_history = deque(maxlen=config.bos_window + 5)
        # ATR
        self._tr_history = deque(maxlen=config.atr_period)
        # HTF data (set externally)
        self.htf_ema_at_bar = None  # list of 4h EMA values aligned to 1h bars
        self.htf_close_at_bar = None
        # Counters
        self._blocked_volume = 0
        self._blocked_slope = 0
        self._blocked_confirmation = 0
        self._blocked_htf = 0
        self._blocked_bos = 0
        self._prev_ema20 = None
        self._prev_close = None
        self._prev_high = None
        self._prev_low = None

    def process_candle(self, bar_idx, o, h, l, c, v, ema20):
        self._volume_history.append(v)
        if ema20 > 0:
            self._ema_history.append(ema20)
        # ATR update
        if self._prev_close is not None:
            tr = max(h - l, abs(h - self._prev_close), abs(l - self._prev_close))
            self._tr_history.append(tr)

        # Exit check (trailing stop update)
        if self.position is not None:
            self._update_position(h, l)
            self._check_exit(bar_idx, c)

        # Entry check
        if self.position is None:
            self._check_entry(bar_idx, o, h, l, c, v, ema20)

        # Update history AFTER entry check
        self._close_history.append(c)
        self._high_history.append(h)
        self._low_history.append(l)
        self._prev_ema20 = ema20
        self._prev_close = c
        self._prev_high = h
        self._prev_low = l

    def _update_position(self, h, l):
        pos = self.position
        pos.peak_price = max(pos.peak_price, h)
        pos.trough_price = min(pos.trough_price, l)
        # Trailing stop
        if self.config.use_trailing_stop:
            move = 0
            if pos.side == 'LONG':
                move = (pos.peak_price - pos.entry_price) / pos.entry_price
                if move >= self.config.trail_activation_pct:
                    pos.trailing_active = True
                if pos.trailing_active:
                    new_sl = pos.peak_price * (1 - self.config.trail_distance_pct)
                    if new_sl > pos.sl_level:
                        pos.sl_level = new_sl
            else:
                move = (pos.entry_price - pos.trough_price) / pos.entry_price
                if move >= self.config.trail_activation_pct:
                    pos.trailing_active = True
                if pos.trailing_active:
                    new_sl = pos.trough_price * (1 + self.config.trail_distance_pct)
                    if new_sl < pos.sl_level:
                        pos.sl_level = new_sl

    def _check_exit(self, bar_idx, c):
        pos = self.position
        if pos.side == 'LONG':
            if c >= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); return
            if c <= pos.sl_level:
                exit_type = 'TRAIL' if pos.trailing_active else 'SL'
                self._close_position(bar_idx, c, exit_type); return
        else:
            if c <= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); return
            if c >= pos.sl_level:
                exit_type = 'TRAIL' if pos.trailing_active else 'SL'
                self._close_position(bar_idx, c, exit_type); return

    def _volume_ok(self, v):
        if self.config.min_volume_ratio <= 0: return True
        if len(self._volume_history) < self.config.volume_window: return False
        avg = sum(self._volume_history) / len(self._volume_history)
        return avg > 0 and v >= avg * self.config.min_volume_ratio

    def _slope_ok(self):
        if self.config.min_slope_pct <= 0: return True
        if len(self._ema_history) < self.config.slope_window: return False
        hist = list(self._ema_history)
        if hist[0] <= 0: return True
        return abs(hist[-1] - hist[0]) / hist[0] >= self.config.min_slope_pct

    def _confirmation_ok(self, c, ema20, side):
        """Check if last N candles closed on the same side of EMA."""
        n = self.config.confirmation_bars
        if n <= 1: return True
        if len(self._close_history) < n - 1: return False
        recent = list(self._close_history)[-(n-1):]  # previous n-1 candles + current = n
        if side == 'LONG':
            return all(cl > ema20 for cl in recent) and c > ema20
        else:
            return all(cl < ema20 for cl in recent) and c < ema20

    def _htf_ok(self, bar_idx, side):
        if not self.config.use_htf_filter: return True
        if self.htf_ema_at_bar is None or self.htf_close_at_bar is None: return True
        if bar_idx >= len(self.htf_ema_at_bar): return True
        htf_ema = self.htf_ema_at_bar[bar_idx]
        htf_close = self.htf_close_at_bar[bar_idx]
        if htf_ema is None or htf_close is None: return True
        if side == 'LONG':
            return htf_close > htf_ema
        else:
            return htf_close < htf_ema

    def _bos_ok(self, c, side):
        """Break of Structure: close breaks recent swing high/low."""
        if not self.config.use_bos_entry: return True
        if len(self._high_history) < self.config.bos_window: return False
        recent_highs = list(self._high_history)[-self.config.bos_window:]
        recent_lows = list(self._low_history)[-self.config.bos_window:]
        if side == 'LONG':
            return c > max(recent_highs)
        else:
            return c < min(recent_lows)

    def _get_atr(self):
        if len(self._tr_history) < self.config.atr_period: return None
        return sum(self._tr_history) / len(self._tr_history)

    def _check_entry(self, bar_idx, o, h, l, c, v, ema20):
        if ema20 <= 0 or self._prev_close is None or self._prev_ema20 is None:
            return

        # Basic EMA cross detection
        long_break = (self._prev_close <= self._prev_ema20) and (c > ema20) and (c > o)
        short_break = (self._prev_close >= self._prev_ema20) and (c < ema20) and (c < o)

        # If using BOS, override cross detection
        if self.config.use_bos_entry:
            long_break = self._bos_ok(c, 'LONG') and (c > ema20)
            short_break = self._bos_ok(c, 'SHORT') and (c < ema20)

        if not (long_break or short_break): return

        side = 'LONG' if long_break else 'SHORT'

        if not self._volume_ok(v):
            self._blocked_volume += 1; return
        if not self._slope_ok():
            self._blocked_slope += 1; return
        if not self._confirmation_ok(c, ema20, side):
            self._blocked_confirmation += 1; return
        if not self._htf_ok(bar_idx, side):
            self._blocked_htf += 1; return

        # Compute SL/TP
        if self.config.use_atr_sl:
            atr = self._get_atr()
            if atr is None: return
            sl_dist = atr * self.config.atr_sl_mult
        else:
            sl_dist = c * self.config.sl_pct

        if side == 'LONG':
            sl_level = c - sl_dist
            tp_level = c * (1.0 + self.config.tp_pct)
        else:
            sl_level = c + sl_dist
            tp_level = c * (1.0 - self.config.tp_pct)

        self.position = Position(
            tool='TREND', side=side,
            entry_price=c, entry_bar=bar_idx,
            sl_level=sl_level, tp_level=tp_level,
            peak_price=c, trough_price=c,
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
