"""Mode3 BBC Switcher — state machine with opt-in signal quality options.
BULL/BEAR/SIDEWAYS all support MTF 15m precision, body ratio filter.

Exit modes (both fill at LEVEL, not at close price — no phantom PnL):
  use_wick_exit=True:  WICK trigger (bar wick touches level) + level fill
  use_wick_exit=False: CLOSED confirmation (candle closes past level) + level fill
"""
from dataclasses import dataclass
from typing import Optional
from collections import deque
from .config import Mode3BBCConfig


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
    entry_trigger: str = ''


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
    entry_trigger: str = ''


class Switcher:
    def __init__(self, config: Mode3BBCConfig):
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
        self._current_poc = None
        self.mtf_bull_entry_close = None
        self.mtf_bull_entry_low = None
        self.mtf_bear_entry_close = None
        self.mtf_bear_entry_high = None
        self.mtf_sideways_short_entry_close = None
        self.mtf_sideways_short_entry_high = None
        self.mtf_sideways_long_entry_close = None
        self.mtf_sideways_long_entry_low = None
        self._high_deque = deque(maxlen=200)
        self._low_deque = deque(maxlen=200)
        self._bull_retest_pending = False
        self._bull_retest_bar_count = 0
        self._bull_broken_level = None
        self._sideways_entries = 0
        self._sideways_blocked_mtf = 0
        self._sideways_blocked_body = 0
        self._bull_entries = 0
        self._bear_entries = 0
        self._bull_ema_reclaim_entries = 0
        self._bull_poc_bounce_entries = 0
        self._bull_swing_break_entries = 0
        self._bull_retest_entries = 0
        self._bull_26_bounce_entries = 0
        self._bull_blocked_mtf = 0
        self._bull_blocked_body = 0
        self._bull_blocked_retest_timeout = 0
        self._bull_blocked_retest_invalidated = 0
        self._bull_blocked_no_swing_history = 0
        self._bear_blocked_mtf = 0
        self._bear_blocked_body = 0

    def process_candle(self, bar_idx, o, h, l, c, ema20, vah, val, poc=None):
        self._action_taken_this_bar = False
        self._current_ema20 = ema20
        self._current_vah = vah
        self._current_val = val
        self._current_poc = poc

        if self.state == 'STARTUP':
            if vah is None or val is None:
                self._high_deque.append(h)
                self._low_deque.append(l)
                return
            self._startup_transition(c, ema20)

        if self.position is not None:
            self._update_position_tracking(h, l)
            self._check_exit(bar_idx, o, h, l, c, ema20, vah, val)

        if self.position is None and not self._action_taken_this_bar:
            self._check_entry(bar_idx, o, h, l, c, ema20, vah, val)

        self._high_deque.append(h)
        self._low_deque.append(l)

    def _startup_transition(self, close, ema20):
        if close > ema20: self.startup_bias = 'bullish'
        elif close < ema20: self.startup_bias = 'bearish'
        self.state = 'SIDEWAYS'

    def _update_position_tracking(self, h, l):
        self.position.peak_high = max(self.position.peak_high, h)
        self.position.trough_low = min(self.position.trough_low, l)

    def _check_exit(self, bar_idx, o, h, l, c, ema20, vah, val):
        pos = self.position
        if pos.tool == 'SIDEWAYS':
            self._exit_sideways(bar_idx, h, l, c)
        elif pos.tool == 'BULL':
            self._exit_bull(bar_idx, h, l, c)
        elif pos.tool == 'BEAR':
            self._exit_bear(bar_idx, h, l, c)

    def _exit_sideways(self, bar_idx, h, l, c):
        """SIDEWAYS exit: wick or closed-confirm mode, both fill at LEVEL."""
        pos = self.position
        if self.config.use_wick_exit:
            # WICK trigger: SL first (worst case)
            if pos.side == 'SHORT':
                if h > pos.sl_level:
                    self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_sideways_short('SL'); return
                if l <= pos.tp_level:
                    self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_short('TP'); return
            else:  # LONG
                if l < pos.sl_level:
                    self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_sideways_long('SL'); return
                if h >= pos.tp_level:
                    self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_long('TP'); return
        else:
            # CLOSED confirmation: candle must close past level, fill at LEVEL (no phantom bonus)
            if pos.side == 'SHORT':
                if c > pos.sl_level:
                    self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_sideways_short('SL'); return
                if c <= pos.tp_level:
                    self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_short('TP'); return
            else:
                if c < pos.sl_level:
                    self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_sideways_long('SL'); return
                if c >= pos.tp_level:
                    self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_long('TP'); return

    def _post_exit_sideways_short(self, et):
        if et == 'SL':
            self.state = 'BULL'; self.bull_stay_warmup = False
            self.markers.hh_breach_case = 'none'
            self._reset_retest()
        else:
            self.state = 'SIDEWAYS'

    def _post_exit_sideways_long(self, et):
        if et == 'SL':
            self.state = 'BEAR'; self.bear_stay_warmup = False
            self.markers.ll_breach_case = 'none'
        else:
            self.state = 'SIDEWAYS'

    def _exit_bull(self, bar_idx, h, l, c):
        pos = self.position
        if self.config.use_wick_exit:
            # WICK trigger: SL first
            if l < pos.sl_level:
                self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_bull('SL'); return
            if h >= pos.tp_level:
                self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bull('TP'); return
        else:
            # CLOSED confirmation, fill at LEVEL
            if c < pos.sl_level:
                self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_bull('SL'); return
            if c >= pos.tp_level:
                self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bull('TP'); return

    def _post_exit_bull(self, et):
        last_peak = self.position.peak_high if self.position else self.trades[-1].peak_high
        self.markers.peak_high_bull = last_peak
        self._reset_retest()
        if et == 'TP':
            self.state = 'BULL'; self.bull_stay_warmup = True
        else:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False

    def _exit_bear(self, bar_idx, h, l, c):
        pos = self.position
        if self.config.use_wick_exit:
            if h > pos.sl_level:
                self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_bear('SL'); return
            if l <= pos.tp_level:
                self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bear('TP'); return
        else:
            # CLOSED confirmation, fill at LEVEL
            if c > pos.sl_level:
                self._close_position(bar_idx, pos.sl_level, 'SL'); self._post_exit_bear('SL'); return
            if c <= pos.tp_level:
                self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bear('TP'); return

    def _post_exit_bear(self, et):
        last_trough = self.position.trough_low if self.position else self.trades[-1].trough_low
        self.markers.trough_low_bear = last_trough
        if et == 'TP':
            self.state = 'BEAR'; self.bear_stay_warmup = True
        else:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False

    def _check_entry(self, bar_idx, o, h, l, c, ema20, vah, val):
        if vah is None or val is None:
            return
        if self.state == 'SIDEWAYS':
            self._entry_sideways(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BULLISH':
            self._entry_wait_see_bullish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BEARISH':
            self._entry_wait_see_bearish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BULL':
            self._entry_bull(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BEAR':
            self._entry_bear(bar_idx, o, h, l, c, ema20, vah, val)

    def _check_sideways_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0:
            return False
        body = abs(c - o)
        return (body / bar_range) >= self.config.sideways_body_ratio_min

    def _entry_sideways(self, bar_idx, o, h, l, c, ema20, vah, val):
        short_ok = (h >= vah) and (c <= vah)
        long_ok = (l <= val) and (c >= val)
        if short_ok and long_ok:
            if c > ema20: short_ok = False
            else: long_ok = False
        if (short_ok or long_ok) and self.config.sideways_body_ratio_min > 0:
            if not self._check_sideways_body_ratio(o, h, l, c):
                self._sideways_blocked_body += 1
                return
        if short_ok:
            self._open_short_sideways(bar_idx, h, l, c)
        elif long_ok:
            self._open_long_sideways(bar_idx, h, l, c)

    def _get_mtf_sideways_short(self, bar_idx):
        if self.mtf_sideways_short_entry_close is None:
            return None, None
        if bar_idx >= len(self.mtf_sideways_short_entry_close):
            return None, None
        return self.mtf_sideways_short_entry_close[bar_idx], self.mtf_sideways_short_entry_high[bar_idx]

    def _get_mtf_sideways_long(self, bar_idx):
        if self.mtf_sideways_long_entry_close is None:
            return None, None
        if bar_idx >= len(self.mtf_sideways_long_entry_close):
            return None, None
        return self.mtf_sideways_long_entry_close[bar_idx], self.mtf_sideways_long_entry_low[bar_idx]

    def _open_short_sideways(self, bar_idx, h, l, c):
        tp_pct = self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct
        entry_price = c
        sl_price = h
        if self.config.sideways_mtf_15m_enabled:
            mtf_c, mtf_h = self._get_mtf_sideways_short(bar_idx)
            if mtf_c is None or mtf_h is None:
                self._sideways_blocked_mtf += 1
                return
            entry_price = mtf_c
            sl_price = mtf_h
        self.markers.marker_high_short = sl_price
        self.markers.marker_close_short = entry_price
        self.position = Position(
            tool='SIDEWAYS', side='SHORT', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=sl_price, entry_low=l, sl_level=sl_price,
            tp_level=entry_price * (1.0 - tp_pct),
            peak_high=sl_price, trough_low=l, ema_at_entry=self._current_ema20,
        )
        self._sideways_entries += 1

    def _open_long_sideways(self, bar_idx, h, l, c):
        tp_pct = self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct
        entry_price = c
        sl_price = l
        if self.config.sideways_mtf_15m_enabled:
            mtf_c, mtf_l = self._get_mtf_sideways_long(bar_idx)
            if mtf_c is None or mtf_l is None:
                self._sideways_blocked_mtf += 1
                return
            entry_price = mtf_c
            sl_price = mtf_l
        self.markers.marker_low_long = sl_price
        self.markers.marker_close_long = entry_price
        self.position = Position(
            tool='SIDEWAYS', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=h, entry_low=sl_price, sl_level=sl_price,
            tp_level=entry_price * (1.0 + tp_pct),
            peak_high=h, trough_low=sl_price, ema_at_entry=self._current_ema20,
        )
        self._sideways_entries += 1

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

    def _check_poc_bounce(self, o, h, l, c):
        if not self.config.bull_poc_entry_enabled:
            return False
        poc = self._current_poc
        if poc is None or poc <= 0 or c <= 0:
            return False
        if not ((l <= poc) and (c >= poc) and (c > o)):
            return False
        dist_pct = abs(poc - c) / c
        if dist_pct > self.config.bull_poc_max_distance_pct:
            return False
        return True

    def _get_mtf_bull_entry(self, bar_idx):
        if self.mtf_bull_entry_close is None:
            return None, None
        if bar_idx >= len(self.mtf_bull_entry_close):
            return None, None
        return self.mtf_bull_entry_close[bar_idx], self.mtf_bull_entry_low[bar_idx]

    def _check_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0:
            return False
        body = abs(c - o)
        return (body / bar_range) >= self.config.bull_body_ratio_min

    def _get_swing_high(self, lookback):
        if len(self._high_deque) < lookback:
            return None
        recent = list(self._high_deque)[-lookback:]
        return max(recent) if recent else None

    def _check_structural_retest(self, l, c, o):
        if self._bull_broken_level is None:
            return False
        lvl = self._bull_broken_level
        tolerance = self.config.bull_retest_tolerance_pct
        if l > lvl * (1 + tolerance):
            return False
        if c <= lvl:
            return False
        if c <= o:
            return False
        return True

    def _reset_retest(self):
        self._bull_retest_pending = False
        self._bull_retest_bar_count = 0
        self._bull_broken_level = None

    def _check_swing_break(self, h, c, o):
        lookback = self.config.bull_swing_lookback
        if len(self._high_deque) < lookback:
            return False
        recent_highs = list(self._high_deque)[-lookback:]
        swing_high = max(recent_highs)
        if swing_high <= 0:
            return False
        return c > swing_high and c > o

    def _get_26_support_level(self):
        lookback = self.config.bull_26_lookback
        if len(self._high_deque) < lookback or len(self._low_deque) < lookback:
            return None
        recent_highs = list(self._high_deque)[-lookback:]
        recent_lows = list(self._low_deque)[-lookback:]
        swing_high = max(recent_highs)
        swing_low = min(recent_lows)
        if swing_high <= swing_low:
            return None
        range_ = swing_high - swing_low
        ratio = self.config.bull_26_ratio
        if ratio <= 0:
            return None
        return swing_low + range_ / ratio

    def _check_26_bounce(self, o, h, l, c):
        if not self.config.bull_use_26_support:
            return False
        level = self._get_26_support_level()
        if level is None or level <= 0:
            return False
        tolerance = self.config.bull_26_tolerance_pct
        if l > level:
            return False
        if l < level * (1 - tolerance * 2):
            return False
        if c <= level:
            return False
        if c <= o:
            return False
        return True

    def _entry_bull(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bull_stay_warmup and c < ema20:
            self.state = 'WAIT_SEE_BULLISH'
            self.markers.hh_breach_case = 'B'
            self.bull_stay_warmup = False
            self._reset_retest()
            return

        if self.config.bull_use_swing_break:
            primary_trigger = self._check_swing_break(h, c, o)
            trigger_name = 'swing_break'
        else:
            primary_trigger = (l <= ema20) and (c > ema20) and (c > o)
            trigger_name = 'ema_reclaim'

        if self.config.bull_wait_retest_enabled and self._bull_retest_pending:
            self._bull_retest_bar_count += 1
            if c < self._bull_broken_level:
                self._bull_blocked_retest_invalidated += 1
                self._reset_retest()
                return
            if self._bull_retest_bar_count > self.config.bull_retest_max_bars:
                self._bull_blocked_retest_timeout += 1
                self._reset_retest()
                return
            if self._check_structural_retest(l, c, o):
                self._reset_retest()
                self._open_bull(bar_idx, h, l, c, 'retest_entry')
                self._bull_retest_entries += 1
                return
            return

        if primary_trigger:
            if self.config.bull_body_ratio_min > 0:
                if not self._check_body_ratio(o, h, l, c):
                    self._bull_blocked_body += 1
                    if self._check_poc_bounce(o, h, l, c):
                        self._open_bull(bar_idx, h, l, c, 'poc_bounce')
                        return
                    if self._check_26_bounce(o, h, l, c):
                        self._open_bull(bar_idx, h, l, c, '26_bounce')
                    return

            if self.config.bull_wait_retest_enabled:
                broken = self._get_swing_high(self.config.bull_retest_swing_lookback)
                if broken is None:
                    self._bull_blocked_no_swing_history += 1
                    self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger=trigger_name)
                    return
                self._bull_broken_level = broken
                self._bull_retest_pending = True
                self._bull_retest_bar_count = 0
                return

            self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger=trigger_name)
            return

        if self._check_poc_bounce(o, h, l, c):
            self._open_bull(bar_idx, h, l, c, 'poc_bounce')
            return
        if self._check_26_bounce(o, h, l, c):
            self._open_bull(bar_idx, h, l, c, '26_bounce')

    def _execute_bull_entry(self, bar_idx, o, h, l, c, ema20, trigger):
        entry_price = c
        sl_price = l
        if trigger == 'ema_reclaim' and self.config.bull_mtf_15m_enabled:
            mtf_c, mtf_l = self._get_mtf_bull_entry(bar_idx)
            if mtf_c is None or mtf_l is None:
                self._bull_blocked_mtf += 1
                return
            entry_price = mtf_c
            sl_price = mtf_l
        self._open_bull(bar_idx, h, sl_price, entry_price, trigger)

    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        tp_level = entry_price * (1.0 + self.config.tp_pct)
        self.position = Position(
            tool='BULL', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=entry_high, entry_low=sl_level, sl_level=sl_level, tp_level=tp_level,
            peak_high=entry_high, trough_low=sl_level, ema_at_entry=self._current_ema20,
            entry_trigger=trigger,
        )
        self._bull_entries += 1
        if trigger == 'ema_reclaim':
            self._bull_ema_reclaim_entries += 1
        elif trigger == 'poc_bounce':
            self._bull_poc_bounce_entries += 1
        elif trigger == 'swing_break':
            self._bull_swing_break_entries += 1
        elif trigger == '26_bounce':
            self._bull_26_bounce_entries += 1

    def _check_bear_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0:
            return False
        body = abs(c - o)
        return (body / bar_range) >= self.config.bear_body_ratio_min

    def _get_mtf_bear_entry(self, bar_idx):
        if self.mtf_bear_entry_close is None:
            return None, None
        if bar_idx >= len(self.mtf_bear_entry_close):
            return None, None
        return self.mtf_bear_entry_close[bar_idx], self.mtf_bear_entry_high[bar_idx]

    def _entry_bear(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bear_stay_warmup and c > ema20:
            self.state = 'WAIT_SEE_BEARISH'
            self.markers.ll_breach_case = 'B'
            self.bear_stay_warmup = False
            return

        ema_reject = (h >= ema20) and (c < ema20) and (c < o)
        if not ema_reject:
            return

        if self.config.bear_body_ratio_min > 0:
            if not self._check_bear_body_ratio(o, h, l, c):
                self._bear_blocked_body += 1
                return

        entry_price = c
        sl_price = h
        if self.config.bear_mtf_15m_enabled:
            mtf_c, mtf_h = self._get_mtf_bear_entry(bar_idx)
            if mtf_c is None or mtf_h is None:
                self._bear_blocked_mtf += 1
                return
            entry_price = mtf_c
            sl_price = mtf_h

        self._open_bear(bar_idx, h, l, sl_price, entry_price)

    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        tp_level = entry_price * (1.0 - self.config.get_bear_tp_pct())
        self.position = Position(
            tool='BEAR', side='SHORT', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=entry_high, entry_low=entry_low,
            sl_level=sl_level, tp_level=tp_level,
            peak_high=entry_high, trough_low=entry_low,
            ema_at_entry=self._current_ema20,
        )
        self._bear_entries += 1

    def _close_position(self, bar_idx, exit_price, exit_type):
        pos = self.position
        if pos.side == 'LONG':
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        pnl_pct_net = pnl_pct - self.config.total_cost_pct()
        pnl_usd = pnl_pct_net * self.config.notional()
        self.trades.append(Trade(
            tool=pos.tool, side=pos.side, entry_price=pos.entry_price, exit_price=exit_price,
            entry_bar=pos.entry_bar, exit_bar=bar_idx, exit_type=exit_type,
            pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
            peak_high=pos.peak_high, trough_low=pos.trough_low,
            sl_level=pos.sl_level, tp_level=pos.tp_level,
            ema_at_entry=pos.ema_at_entry, ema_at_exit=self._current_ema20,
            entry_trigger=pos.entry_trigger,
        ))
        self.position = None
        self._action_taken_this_bar = True
