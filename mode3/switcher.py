"""
Mode3 Switcher v2.0 — final champion, cleaned.

Kept (all proven):
- Global: chop filter
- BULL: volume filter + MTF 15m entry
- BEAR: pure 1h entry (no filter)
- SIDEWAYS: MTF 15m entry + tolerance filter + slope filter
"""
from dataclasses import dataclass
from typing import Optional, List
from collections import deque
from .config import Mode3Config


@dataclass
class MarkerState:
    marker_high_short: Optional[float] = None
    marker_close_short: Optional[float] = None
    marker_low_long: Optional[float] = None
    marker_close_long: Optional[float] = None
    peak_high_bull: Optional[float] = None
    trough_low_bear: Optional[float] = None
    hh_breach_case: str = 'none'
    ll_breach_case: str = 'none'
    def hh_breach_level(self):
        if self.hh_breach_case == 'A': return self.marker_high_short
        if self.hh_breach_case == 'B': return self.peak_high_bull
        return None
    def ll_breach_level(self):
        if self.ll_breach_case == 'A': return self.marker_low_long
        if self.ll_breach_case == 'B': return self.trough_low_bear
        return None


@dataclass
class Position:
    tool: str
    side: str
    entry_price: float
    entry_bar: int
    entry_high: float
    entry_low: float
    sl_level: float
    tp_level: float
    peak_high: float = 0.0
    trough_low: float = 1e18
    ema_at_entry: float = 0.0


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
    peak_high: float
    trough_low: float
    sl_level: float = 0.0
    tp_level: float = 0.0
    ema_at_entry: float = 0.0
    ema_at_exit: float = 0.0


class Switcher:
    def __init__(self, config):
        self.config = config
        self.markers = MarkerState()
        self.state = 'STARTUP'
        self.position = None
        self.trades = []
        self.bull_stay_warmup = False
        self.bear_stay_warmup = False
        self.startup_bias = None
        self._action_taken_this_bar = False
        self._current_ema20 = 0.0
        self._current_vah = None
        self._current_val = None
        self._sideways_blocked_count = 0
        self._chop_history = deque(maxlen=config.chop_window)
        self._chop_blocked_count = 0
        self._volume_history = deque(maxlen=config.bull_volume_window)
        self._bull_blocked_volume = 0
        self._bull_blocked_mtf = 0
        self._sideways_blocked_mtf = 0
        self._sideways_blocked_slope = 0
        self._ema_history = deque(maxlen=config.sideways_slope_window)
        # MTF 15m entry data
        self.mtf_bull_entry_close = None
        self.mtf_bull_entry_low = None
        self.mtf_sideways_short_entry_close = None
        self.mtf_sideways_short_entry_high = None
        self.mtf_sideways_long_entry_close = None
        self.mtf_sideways_long_entry_low = None

    def process_candle(self, bar_idx, o, h, l, c, v, ema20, vah, val, poc):
        self._action_taken_this_bar = False
        self._current_ema20 = ema20
        self._current_vah = vah
        self._current_val = val
        if ema20 > 0:
            sign = 1 if c > ema20 else (-1 if c < ema20 else 0)
            self._chop_history.append(sign)
            self._ema_history.append(ema20)
        self._volume_history.append(v)

        if self.state == 'STARTUP':
            if vah is None or val is None: return
            self._startup_transition(c, ema20)

        if self.position is not None:
            self._update_position_tracking(h, l)
            self._check_exit(bar_idx, o, h, l, c, ema20, vah, val)

        if self.position is None and not self._action_taken_this_bar:
            if self._is_choppy():
                self._chop_blocked_count += 1
                return
            self._check_entry(bar_idx, o, h, l, c, ema20, vah, val, poc)

    def _is_choppy(self):
        if self.config.chop_max_crossings <= 0: return False
        if len(self._chop_history) < self.config.chop_window: return False
        crossings = 0
        hist = list(self._chop_history)
        prev = hist[0]
        for s in hist[1:]:
            if s != 0 and prev != 0 and s != prev: crossings += 1
            if s != 0: prev = s
        return crossings > self.config.chop_max_crossings

    def _bull_volume_ok(self, v):
        min_ratio = self.config.bull_min_volume_ratio
        if min_ratio <= 0: return True
        if len(self._volume_history) < self.config.bull_volume_window: return True
        avg = sum(self._volume_history) / len(self._volume_history)
        if avg <= 0: return True
        return v >= avg * min_ratio

    def _sideways_slope_ok(self):
        max_slope = self.config.sideways_max_slope_pct
        if max_slope <= 0: return True
        if len(self._ema_history) < self.config.sideways_slope_window: return True
        hist = list(self._ema_history)
        if hist[0] <= 0: return True
        slope_pct = abs(hist[-1] - hist[0]) / hist[0]
        return slope_pct <= max_slope

    def _sideways_ema_inv_ok_short(self, c, ema20):
        if not self.config.sideways_ema_invalidation:
            return False
        tol = self.config.sideways_ema_invalidation_tolerance
        if tol > 0 and (c - ema20) / ema20 < tol:
            return False
        return True

    def _sideways_ema_inv_ok_long(self, c, ema20):
        if not self.config.sideways_ema_invalidation:
            return False
        tol = self.config.sideways_ema_invalidation_tolerance
        if tol > 0 and (ema20 - c) / ema20 < tol:
            return False
        return True

    def _sideways_tp_pct(self):
        return self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct

    def _startup_transition(self, close, ema20):
        if close > ema20: self.startup_bias = 'bullish'
        elif close < ema20: self.startup_bias = 'bearish'
        self.state = 'SIDEWAYS'

    def _update_position_tracking(self, h, l):
        self.position.peak_high = max(self.position.peak_high, h)
        self.position.trough_low = min(self.position.trough_low, l)

    def _check_exit(self, bar_idx, o, h, l, c, ema20, vah, val):
        pos = self.position
        if pos.tool == 'SIDEWAYS': self._exit_sideways(bar_idx, c, ema20, l=l, h=h)
        elif pos.tool == 'BULL': self._exit_bull(bar_idx, c)
        elif pos.tool == 'BEAR': self._exit_bear(bar_idx, c)

    def _exit_sideways(self, bar_idx, c, ema20, l=None, h=None):
        pos = self.position
        if pos.side == 'SHORT':
            if c > pos.sl_level:
                self._close_position(bar_idx, c, 'SL'); self._post_exit_sideways_short('SL'); return
            if c <= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); self._post_exit_sideways_short('TP'); return
            if l is not None and l <= ema20 and c > ema20:
                if self._sideways_ema_inv_ok_short(c, ema20):
                    self._close_position(bar_idx, c, 'EMA_INVALIDATION'); self._post_exit_sideways_short('EMA_INVALIDATION'); return
        else:
            if c < pos.sl_level:
                self._close_position(bar_idx, c, 'SL'); self._post_exit_sideways_long('SL'); return
            if c >= pos.tp_level:
                self._close_position(bar_idx, c, 'TP'); self._post_exit_sideways_long('TP'); return
            if h is not None and h >= ema20 and c < ema20:
                if self._sideways_ema_inv_ok_long(c, ema20):
                    self._close_position(bar_idx, c, 'EMA_INVALIDATION'); self._post_exit_sideways_long('EMA_INVALIDATION'); return

    def _post_exit_sideways_short(self, et):
        if et == 'SL':
            self.state = 'BULL'; self.bull_stay_warmup = False; self.markers.hh_breach_case = 'none'
        elif et == 'TP': self.state = 'SIDEWAYS'
        else: self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'A'

    def _post_exit_sideways_long(self, et):
        if et == 'SL':
            self.state = 'BEAR'; self.bear_stay_warmup = False; self.markers.ll_breach_case = 'none'
        elif et == 'TP': self.state = 'SIDEWAYS'
        else: self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'A'

    def _exit_bull(self, bar_idx, c):
        pos = self.position
        if c < pos.sl_level:
            self._close_position(bar_idx, c, 'SL'); self._post_exit_bull('SL'); return
        if c >= pos.tp_level:
            self._close_position(bar_idx, c, 'TP'); self._post_exit_bull('TP'); return

    def _post_exit_bull(self, et):
        last_peak = self.position.peak_high if self.position else self.trades[-1].peak_high
        self.markers.peak_high_bull = last_peak
        if et == 'TP':
            self.state = 'BULL'; self.bull_stay_warmup = True
        else:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False

    def _exit_bear(self, bar_idx, c):
        pos = self.position
        if c > pos.sl_level:
            self._close_position(bar_idx, c, 'SL'); self._post_exit_bear('SL'); return
        if c <= pos.tp_level:
            self._close_position(bar_idx, c, 'TP'); self._post_exit_bear('TP'); return

    def _post_exit_bear(self, et):
        last_trough = self.position.trough_low if self.position else self.trades[-1].trough_low
        self.markers.trough_low_bear = last_trough
        if et == 'TP':
            self.state = 'BEAR'; self.bear_stay_warmup = True
        else:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False

    def _check_entry(self, bar_idx, o, h, l, c, ema20, vah, val, poc):
        if vah is None or val is None: return
        if self.state == 'SIDEWAYS': self._entry_sideways(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BULLISH': self._entry_wait_see_bullish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BEARISH': self._entry_wait_see_bearish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BULL': self._entry_bull(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BEAR': self._entry_bear(bar_idx, o, h, l, c, ema20, vah, val)

    def _entry_sideways(self, bar_idx, o, h, l, c, ema20, vah, val):
        short_ok = (h >= vah) and (c <= vah)
        long_ok = (l <= val) and (c >= val)
        if short_ok and long_ok:
            if c > ema20: short_ok = False
            else: long_ok = False
        if short_ok: self._open_short_sideways(bar_idx, h, l, c)
        elif long_ok: self._open_long_sideways(bar_idx, h, l, c)

    def _sideways_distance_ok(self, c):
        ema = self._current_ema20
        if ema <= 0: return True
        return abs(c - ema) / ema <= self.config.sideways_ema_distance_cap

    def _open_short_sideways(self, bar_idx, h, l, c):
        if not self._sideways_distance_ok(c):
            self._sideways_blocked_count += 1; return
        if not self._sideways_slope_ok():
            self._sideways_blocked_slope += 1; return
        tp_pct = self._sideways_tp_pct()
        if self.config.sideways_mtf_15m_entry and self.mtf_sideways_short_entry_close is not None:
            if bar_idx < len(self.mtf_sideways_short_entry_close):
                mtf_close = self.mtf_sideways_short_entry_close[bar_idx]
                mtf_high = self.mtf_sideways_short_entry_high[bar_idx]
                if mtf_close is None or mtf_high is None:
                    self._sideways_blocked_mtf += 1
                    return
                self.markers.marker_high_short = mtf_high; self.markers.marker_close_short = mtf_close
                self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=mtf_close, entry_bar=bar_idx,
                    entry_high=mtf_high, entry_low=l, sl_level=mtf_high, tp_level=mtf_close*(1.0-tp_pct),
                    peak_high=mtf_high, trough_low=l, ema_at_entry=self._current_ema20)
                return
        self.markers.marker_high_short = h; self.markers.marker_close_short = c
        self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=h, tp_level=c*(1.0-tp_pct),
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)

    def _open_long_sideways(self, bar_idx, h, l, c):
        if not self._sideways_distance_ok(c):
            self._sideways_blocked_count += 1; return
        if not self._sideways_slope_ok():
            self._sideways_blocked_slope += 1; return
        tp_pct = self._sideways_tp_pct()
        if self.config.sideways_mtf_15m_entry and self.mtf_sideways_long_entry_close is not None:
            if bar_idx < len(self.mtf_sideways_long_entry_close):
                mtf_close = self.mtf_sideways_long_entry_close[bar_idx]
                mtf_low = self.mtf_sideways_long_entry_low[bar_idx]
                if mtf_close is None or mtf_low is None:
                    self._sideways_blocked_mtf += 1
                    return
                self.markers.marker_low_long = mtf_low; self.markers.marker_close_long = mtf_close
                self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=mtf_close, entry_bar=bar_idx,
                    entry_high=h, entry_low=mtf_low, sl_level=mtf_low, tp_level=mtf_close*(1.0+tp_pct),
                    peak_high=h, trough_low=mtf_low, ema_at_entry=self._current_ema20)
                return
        self.markers.marker_low_long = l; self.markers.marker_close_long = c
        self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=l, tp_level=c*(1.0+tp_pct),
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)

    def _entry_wait_see_bullish(self, bar_idx, o, h, l, c, ema20, vah, val):
        hh_lvl = self.markers.hh_breach_level()
        if hh_lvl is not None and c > hh_lvl:
            self.state = 'BULL'; self.bull_stay_warmup = False; return
        if self.markers.marker_close_short is not None:
            if (h >= vah) and (c <= self.markers.marker_close_short):
                self._open_short_sideways(bar_idx, h, l, c); return
        if (l <= val) and (c >= val):
            self._open_long_sideways(bar_idx, h, l, c); return

    def _entry_wait_see_bearish(self, bar_idx, o, h, l, c, ema20, vah, val):
        ll_lvl = self.markers.ll_breach_level()
        if ll_lvl is not None and c < ll_lvl:
            self.state = 'BEAR'; self.bear_stay_warmup = False; return
        if self.markers.marker_close_long is not None:
            if (l <= val) and (c >= self.markers.marker_close_long):
                self._open_long_sideways(bar_idx, h, l, c); return
        if (h >= vah) and (c <= vah):
            self._open_short_sideways(bar_idx, h, l, c); return

    def _entry_bull(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bull_stay_warmup and c < ema20:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False; return
        if (l <= ema20) and (c > ema20) and (c > o):
            if not self._bull_volume_ok(self._volume_history[-1] if self._volume_history else 0):
                self._bull_blocked_volume += 1
                return
            if self.config.bull_mtf_15m_entry and self.mtf_bull_entry_close is not None:
                if bar_idx < len(self.mtf_bull_entry_close):
                    mtf_close = self.mtf_bull_entry_close[bar_idx]
                    mtf_low = self.mtf_bull_entry_low[bar_idx]
                    if mtf_close is None or mtf_low is None:
                        self._bull_blocked_mtf += 1
                        return
                    entry_price = mtf_close
                    sl_level = mtf_low
                    tp_level = entry_price * (1.0 + self.config.tp_pct)
                    self.position = Position(tool='BULL', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
                        entry_high=h, entry_low=mtf_low, sl_level=sl_level, tp_level=tp_level,
                        peak_high=h, trough_low=mtf_low, ema_at_entry=self._current_ema20)
                    return
            self.position = Position(tool='BULL', side='LONG', entry_price=c, entry_bar=bar_idx,
                entry_high=h, entry_low=l, sl_level=l, tp_level=c*(1.0+self.config.tp_pct),
                peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)

    def _entry_bear(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bear_stay_warmup and c > ema20:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False; return
        if (h >= ema20) and (c < ema20) and (c < o):
            self.position = Position(tool='BEAR', side='SHORT', entry_price=c, entry_bar=bar_idx,
                entry_high=h, entry_low=l, sl_level=h, tp_level=c*(1.0-self.config.tp_pct),
                peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)

    def _close_position(self, bar_idx, exit_price, exit_type):
        pos = self.position
        if pos.side == 'LONG':
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        pnl_pct_net = pnl_pct - self.config.total_cost_pct()
        pnl_usd = pnl_pct_net * self.config.notional()
        self.trades.append(Trade(tool=pos.tool, side=pos.side, entry_price=pos.entry_price, exit_price=exit_price,
            entry_bar=pos.entry_bar, exit_bar=bar_idx, exit_type=exit_type, pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
            peak_high=pos.peak_high, trough_low=pos.trough_low, sl_level=pos.sl_level, tp_level=pos.tp_level,
            ema_at_entry=pos.ema_at_entry, ema_at_exit=self._current_ema20))
        self.position = None
        self._action_taken_this_bar = True
