"""Mode3 BBC Switcher — v2.2: Direct BULL↔BEAR transitions.

When in BULL state (no position), check for BEAR entry signal → go directly to BEAR.
When in BEAR state (no position), check for BULL entry signal → go directly to BULL.
Skips SIDEWAYS detection phase for faster reversal catching.
"""
from dataclasses import dataclass, field
from typing import Optional
from collections import deque
from .config import Mode3BBCConfig

@dataclass
class MarkerState:
    marker_high_short: Optional[float] = None; marker_close_short: Optional[float] = None
    marker_low_long: Optional[float] = None; marker_close_long: Optional[float] = None
    peak_high_bull: Optional[float] = None; trough_low_bear: Optional[float] = None
    hh_breach_case: str = 'none'; ll_breach_case: str = 'none'
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
    tool: str; side: str; entry_price: float; entry_bar: int
    entry_high: float; entry_low: float; sl_level: float; tp_level: float
    peak_high: float = 0.0; trough_low: float = 1e18
    ema_at_entry: float = 0.0; entry_trigger: str = ''
    be_triggered: bool = False; original_sl: float = 0.0
    size_ratio: float = 1.0
    is_poc_entry: bool = False

@dataclass
class Trade:
    tool: str; side: str; entry_price: float; exit_price: float
    entry_bar: int; exit_bar: int; exit_type: str
    pnl_pct: float; pnl_usd: float; peak_high: float; trough_low: float
    sl_level: float = 0.0; tp_level: float = 0.0
    ema_at_entry: float = 0.0; ema_at_exit: float = 0.0; entry_trigger: str = ''

class Switcher:
    def __init__(self, config: Mode3BBCConfig):
        self.config = config; self.markers = MarkerState(); self.state = 'STARTUP'
        self.position = None; self.trades = []
        self.bull_stay_warmup = False; self.bear_stay_warmup = False; self.startup_bias = None
        self._action_taken_this_bar = False; self._current_ema20 = 0.0
        self._current_vah = None; self._current_val = None; self._current_poc = None
        self.mtf_bull_entry_close = None; self.mtf_bull_entry_low = None
        self.mtf_bear_entry_close = None; self.mtf_bear_entry_high = None
        self.mtf_sideways_short_entry_close = None; self.mtf_sideways_short_entry_high = None
        self.mtf_sideways_long_entry_close = None; self.mtf_sideways_long_entry_low = None
        self._high_deque = deque(maxlen=200); self._low_deque = deque(maxlen=200)
        self._bull_retest_pending = False; self._bull_retest_bar_count = 0; self._bull_broken_level = None
        self._sideways_entries = 0; self._sideways_blocked_mtf = 0; self._sideways_blocked_body = 0
        self._sideways_blocked_ema = 0; self._sideways_blocked_min_sl = 0
        self._sideways_detector_entries = 0; self._sideways_trader_entries = 0
        self._sideways_poc_breakout_entries = 0
        self._bull_entries = 0; self._bear_entries = 0
        self._bull_ema_reclaim_entries = 0; self._bull_poc_bounce_entries = 0
        self._bull_swing_break_entries = 0; self._bull_retest_entries = 0; self._bull_26_bounce_entries = 0
        self._bull_blocked_mtf = 0; self._bull_blocked_body = 0
        self._bull_blocked_retest_timeout = 0; self._bull_blocked_retest_invalidated = 0; self._bull_blocked_no_swing_history = 0
        self._bear_blocked_mtf = 0; self._bear_blocked_body = 0
        self._be_triggered_count = 0; self._be_exit_count = 0
        self._direct_bull_to_bear = 0; self._direct_bear_to_bull = 0

    def process_candle(self, bar_idx, o, h, l, c, ema20, vah, val, poc=None):
        self._action_taken_this_bar = False; self._current_ema20 = ema20
        self._current_vah = vah; self._current_val = val; self._current_poc = poc
        if self.state == 'STARTUP':
            if vah is None or val is None: self._high_deque.append(h); self._low_deque.append(l); return
            self._startup_transition(c, ema20)
        if self.position is not None:
            self._update_position_tracking(h, l); self._check_move_to_be(h, l)
            self._check_exit(bar_idx, o, h, l, c, ema20, vah, val)
        if self.position is None and not self._action_taken_this_bar:
            self._check_entry(bar_idx, o, h, l, c, ema20, vah, val)
        self._high_deque.append(h); self._low_deque.append(l)

    def _startup_transition(self, close, ema20):
        if close > ema20: self.startup_bias = 'bullish'
        elif close < ema20: self.startup_bias = 'bearish'
        self.state = 'SIDEWAYS'

    def _update_position_tracking(self, h, l):
        self.position.peak_high = max(self.position.peak_high, h)
        self.position.trough_low = min(self.position.trough_low, l)

    def _check_move_to_be(self, h, l):
        pos = self.position
        if pos.be_triggered: return
        trigger = self.config.sideways_trail_to_be_trigger_pct if pos.tool == 'SIDEWAYS' else self.config.trail_to_be_trigger_pct
        if trigger <= 0: return
        entry = pos.entry_price
        if pos.side == 'LONG':
            if (h - entry) / entry >= trigger: pos.original_sl = pos.sl_level; pos.sl_level = entry; pos.be_triggered = True; self._be_triggered_count += 1
        else:
            if (entry - l) / entry >= trigger: pos.original_sl = pos.sl_level; pos.sl_level = entry; pos.be_triggered = True; self._be_triggered_count += 1

    def _check_exit(self, bar_idx, o, h, l, c, ema20, vah, val):
        pos = self.position
        if pos.tool == 'SIDEWAYS': self._exit_sideways(bar_idx, h, l, c)
        elif pos.tool == 'BULL': self._exit_bull(bar_idx, h, l, c)
        elif pos.tool == 'BEAR': self._exit_bear(bar_idx, h, l, c)

    def _get_exit_type_label(self, base_type):
        if base_type == 'SL' and self.position and self.position.be_triggered: self._be_exit_count += 1; return 'BE'
        return base_type

    def _exit_sideways(self, bar_idx, h, l, c):
        pos = self.position
        if self.config.use_wick_exit:
            if pos.side == 'SHORT':
                if h > pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_sideways_short(et, pos.is_poc_entry); return
                if l <= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_short('TP', pos.is_poc_entry); return
            else:
                if l < pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_sideways_long(et, pos.is_poc_entry); return
                if h >= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_long('TP', pos.is_poc_entry); return
        else:
            if pos.side == 'SHORT':
                if c > pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_sideways_short(et, pos.is_poc_entry); return
                if c <= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_short('TP', pos.is_poc_entry); return
            else:
                if c < pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_sideways_long(et, pos.is_poc_entry); return
                if c >= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_sideways_long('TP', pos.is_poc_entry); return

    def _post_exit_sideways_short(self, et, is_poc=False):
        if is_poc: self.state = 'SIDEWAYS'
        elif et in ('SL', 'BE'): self.state = 'BULL'; self.bull_stay_warmup = False; self.markers.hh_breach_case = 'none'; self._reset_retest()
        else: self.state = 'SIDEWAYS'
    def _post_exit_sideways_long(self, et, is_poc=False):
        if is_poc: self.state = 'SIDEWAYS'
        elif et in ('SL', 'BE'): self.state = 'BEAR'; self.bear_stay_warmup = False; self.markers.ll_breach_case = 'none'
        else: self.state = 'SIDEWAYS'

    def _exit_bull(self, bar_idx, h, l, c):
        pos = self.position
        if self.config.use_wick_exit:
            if l < pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_bull(et); return
            if h >= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bull('TP'); return
        else:
            if c < pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_bull(et); return
            if c >= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bull('TP'); return
    def _post_exit_bull(self, et):
        last_peak = self.position.peak_high if self.position else self.trades[-1].peak_high
        self.markers.peak_high_bull = last_peak; self._reset_retest()
        if et == 'TP': self.state = 'BULL'; self.bull_stay_warmup = True
        else: self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False

    def _exit_bear(self, bar_idx, h, l, c):
        pos = self.position
        if self.config.use_wick_exit:
            if h > pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_bear(et); return
            if l <= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bear('TP'); return
        else:
            if c > pos.sl_level: et = self._get_exit_type_label('SL'); self._close_position(bar_idx, pos.sl_level, et); self._post_exit_bear(et); return
            if c <= pos.tp_level: self._close_position(bar_idx, pos.tp_level, 'TP'); self._post_exit_bear('TP'); return
    def _post_exit_bear(self, et):
        last_trough = self.position.trough_low if self.position else self.trades[-1].trough_low
        self.markers.trough_low_bear = last_trough
        if et == 'TP': self.state = 'BEAR'; self.bear_stay_warmup = True
        else: self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False

    def _check_entry(self, bar_idx, o, h, l, c, ema20, vah, val):
        if vah is None or val is None: return
        if self.state == 'SIDEWAYS': self._entry_sideways(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BULLISH': self._entry_wait_see_bullish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BEARISH': self._entry_wait_see_bearish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BULL': self._entry_bull(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BEAR': self._entry_bear(bar_idx, o, h, l, c, ema20, vah, val)

    def _check_sideways_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0: return False
        return abs(c - o) / bar_range >= self.config.sideways_body_ratio_min

    def _is_bear_signal(self, o, h, l, c, ema20):
        """Check if current bar has a BEAR entry signal (EMA reject + bearish)."""
        return (h >= ema20) and (c < ema20) and (c < o)

    def _is_bull_signal(self, o, h, l, c, ema20):
        """Check if current bar has a BULL entry signal (EMA reclaim + bullish)."""
        return (l <= ema20) and (c > ema20) and (c > o)

    def _entry_sideways(self, bar_idx, o, h, l, c, ema20, vah, val):
        short_ok = (h >= vah) and (c <= vah)
        long_ok = (l <= val) and (c >= val)
        if self.config.sideways_ema_filter_enabled:
            if short_ok and c >= ema20: short_ok = False; self._sideways_blocked_ema += 1
            if long_ok and c <= ema20: long_ok = False; self._sideways_blocked_ema += 1
        else:
            if short_ok and long_ok:
                if c > ema20: short_ok = False
                else: long_ok = False
        if (short_ok or long_ok) and self.config.sideways_body_ratio_min > 0:
            if not self._check_sideways_body_ratio(o, h, l, c): self._sideways_blocked_body += 1; short_ok = False; long_ok = False
        if short_ok: self._open_short_sideways(bar_idx, h, l, c, ema20); return
        if long_ok: self._open_long_sideways(bar_idx, h, l, c, ema20); return
        if self.config.sideways_poc_breakout_enabled:
            self._try_poc_breakout(bar_idx, o, h, l, c)

    def _try_poc_breakout(self, bar_idx, o, h, l, c):
        poc = self._current_poc
        if poc is None or poc <= 0: return
        bar_range = h - l
        if bar_range <= 0 or abs(c - o) / bar_range < self.config.sideways_poc_body_ratio_min: return
        tp_pct = self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct
        if l <= poc and c > poc and c > o:
            sl_price = l if self.config.sideways_sl_pct <= 0 else c * (1.0 - self.config.sideways_sl_pct)
            self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=c, entry_bar=bar_idx,
                entry_high=c, entry_low=sl_price, sl_level=sl_price, original_sl=sl_price,
                tp_level=c * (1.0 + tp_pct), peak_high=c, trough_low=sl_price,
                ema_at_entry=self._current_ema20, entry_trigger='poc_breakout', is_poc_entry=True)
            self._sideways_entries += 1; self._sideways_poc_breakout_entries += 1; return
        if h >= poc and c < poc and c < o:
            sl_price = h if self.config.sideways_sl_pct <= 0 else c * (1.0 + self.config.sideways_sl_pct)
            self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=c, entry_bar=bar_idx,
                entry_high=sl_price, entry_low=c, sl_level=sl_price, original_sl=sl_price,
                tp_level=c * (1.0 - tp_pct), peak_high=sl_price, trough_low=c,
                ema_at_entry=self._current_ema20, entry_trigger='poc_breakout', is_poc_entry=True)
            self._sideways_entries += 1; self._sideways_poc_breakout_entries += 1

    def _get_mtf_sideways_short(self, bar_idx):
        if self.mtf_sideways_short_entry_close is None: return None, None
        if bar_idx >= len(self.mtf_sideways_short_entry_close): return None, None
        return self.mtf_sideways_short_entry_close[bar_idx], self.mtf_sideways_short_entry_high[bar_idx]
    def _get_mtf_sideways_long(self, bar_idx):
        if self.mtf_sideways_long_entry_close is None: return None, None
        if bar_idx >= len(self.mtf_sideways_long_entry_close): return None, None
        return self.mtf_sideways_long_entry_close[bar_idx], self.mtf_sideways_long_entry_low[bar_idx]

    def _open_short_sideways(self, bar_idx, h, l, c, ema20=None):
        if ema20 is None: ema20 = self._current_ema20
        tp_pct = self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct
        entry_price = c; sl_price = h
        if self.config.sideways_mtf_15m_enabled:
            mtf_c, mtf_h = self._get_mtf_sideways_short(bar_idx)
            if mtf_c is None or mtf_h is None: self._sideways_blocked_mtf += 1; return
            entry_price = mtf_c; sl_price = mtf_h
        if self.config.sideways_sl_pct > 0: sl_price = entry_price * (1.0 + self.config.sideways_sl_pct)
        sl_dist = abs(sl_price - entry_price) / entry_price
        if self.config.sideways_min_sl_dist_pct > 0 and sl_dist < self.config.sideways_min_sl_dist_pct:
            self._sideways_blocked_min_sl += 1; return
        size_ratio = 1.0
        if self.config.sideways_dual_mode_enabled:
            if c < ema20: self._sideways_trader_entries += 1
            else: size_ratio = self.config.sideways_detector_size_ratio; self._sideways_detector_entries += 1
        self.markers.marker_high_short = sl_price; self.markers.marker_close_short = entry_price
        self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=sl_price, entry_low=l, sl_level=sl_price, original_sl=sl_price,
            tp_level=entry_price * (1.0 - tp_pct), peak_high=sl_price, trough_low=l,
            ema_at_entry=self._current_ema20, size_ratio=size_ratio)
        self._sideways_entries += 1

    def _open_long_sideways(self, bar_idx, h, l, c, ema20=None):
        if ema20 is None: ema20 = self._current_ema20
        tp_pct = self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct
        entry_price = c; sl_price = l
        if self.config.sideways_mtf_15m_enabled:
            mtf_c, mtf_l = self._get_mtf_sideways_long(bar_idx)
            if mtf_c is None or mtf_l is None: self._sideways_blocked_mtf += 1; return
            entry_price = mtf_c; sl_price = mtf_l
        if self.config.sideways_sl_pct > 0: sl_price = entry_price * (1.0 - self.config.sideways_sl_pct)
        sl_dist = abs(entry_price - sl_price) / entry_price
        if self.config.sideways_min_sl_dist_pct > 0 and sl_dist < self.config.sideways_min_sl_dist_pct:
            self._sideways_blocked_min_sl += 1; return
        size_ratio = 1.0
        if self.config.sideways_dual_mode_enabled:
            if c > ema20: self._sideways_trader_entries += 1
            else: size_ratio = self.config.sideways_detector_size_ratio; self._sideways_detector_entries += 1
        self.markers.marker_low_long = sl_price; self.markers.marker_close_long = entry_price
        self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=h, entry_low=sl_price, sl_level=sl_price, original_sl=sl_price,
            tp_level=entry_price * (1.0 + tp_pct), peak_high=h, trough_low=sl_price,
            ema_at_entry=self._current_ema20, size_ratio=size_ratio)
        self._sideways_entries += 1

    def _entry_wait_see_bullish(self, bar_idx, o, h, l, c, ema20, vah, val):
        hh_lvl = self.markers.hh_breach_level()
        if hh_lvl is not None and c > hh_lvl: self.state = 'BULL'; self.bull_stay_warmup = False; return
        # v2.2: direct transition — if BEAR signal while waiting for bullish confirmation
        if self.config.direct_transition_enabled and self._is_bear_signal(o, h, l, c, ema20):
            if self.config.bear_body_ratio_min <= 0 or self._check_bear_body_ratio(o, h, l, c):
                self.state = 'BEAR'; self._direct_bull_to_bear += 1
                self._execute_bear_entry(bar_idx, o, h, l, c, ema20); return
        if self.markers.marker_close_short is not None:
            if (h >= vah) and (c <= self.markers.marker_close_short): self._open_short_sideways(bar_idx, h, l, c, ema20); return
        if (l <= val) and (c >= val): self._open_long_sideways(bar_idx, h, l, c, ema20); return

    def _entry_wait_see_bearish(self, bar_idx, o, h, l, c, ema20, vah, val):
        ll_lvl = self.markers.ll_breach_level()
        if ll_lvl is not None and c < ll_lvl: self.state = 'BEAR'; self.bear_stay_warmup = False; return
        # v2.2: direct transition — if BULL signal while waiting for bearish confirmation
        if self.config.direct_transition_enabled and self._is_bull_signal(o, h, l, c, ema20):
            if self.config.bull_body_ratio_min <= 0 or self._check_body_ratio(o, h, l, c):
                self.state = 'BULL'; self._direct_bear_to_bull += 1
                self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger='ema_reclaim'); return
        if self.markers.marker_close_long is not None:
            if (l <= val) and (c >= self.markers.marker_close_long): self._open_long_sideways(bar_idx, h, l, c, ema20); return
        if (h >= vah) and (c <= vah): self._open_short_sideways(bar_idx, h, l, c, ema20); return

    def _check_poc_bounce(self, o, h, l, c):
        if not self.config.bull_poc_entry_enabled: return False
        poc = self._current_poc
        if poc is None or poc <= 0 or c <= 0: return False
        if not ((l <= poc) and (c >= poc) and (c > o)): return False
        return abs(poc - c) / c <= self.config.bull_poc_max_distance_pct
    def _get_mtf_bull_entry(self, bar_idx):
        if self.mtf_bull_entry_close is None: return None, None
        if bar_idx >= len(self.mtf_bull_entry_close): return None, None
        return self.mtf_bull_entry_close[bar_idx], self.mtf_bull_entry_low[bar_idx]
    def _check_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0: return False
        return abs(c - o) / bar_range >= self.config.bull_body_ratio_min
    def _check_bear_body_ratio(self, o, h, l, c):
        bar_range = h - l
        if bar_range <= 0: return False
        return abs(c - o) / bar_range >= self.config.bear_body_ratio_min
    def _get_swing_high(self, lookback):
        if len(self._high_deque) < lookback: return None
        return max(list(self._high_deque)[-lookback:])
    def _check_structural_retest(self, l, c, o):
        if self._bull_broken_level is None: return False
        lvl = self._bull_broken_level; tol = self.config.bull_retest_tolerance_pct
        return l <= lvl * (1 + tol) and c > lvl and c > o
    def _reset_retest(self): self._bull_retest_pending = False; self._bull_retest_bar_count = 0; self._bull_broken_level = None
    def _check_swing_break(self, h, c, o):
        lookback = self.config.bull_swing_lookback
        if len(self._high_deque) < lookback: return False
        return max(list(self._high_deque)[-lookback:]) > 0 and c > max(list(self._high_deque)[-lookback:]) and c > o
    def _get_26_support_level(self):
        lookback = self.config.bull_26_lookback
        if len(self._high_deque) < lookback or len(self._low_deque) < lookback: return None
        sh = max(list(self._high_deque)[-lookback:]); sl = min(list(self._low_deque)[-lookback:])
        if sh <= sl: return None
        return sl + (sh - sl) / self.config.bull_26_ratio if self.config.bull_26_ratio > 0 else None
    def _check_26_bounce(self, o, h, l, c):
        if not self.config.bull_use_26_support: return False
        level = self._get_26_support_level()
        if level is None or level <= 0: return False
        tol = self.config.bull_26_tolerance_pct
        return l <= level and l >= level * (1 - tol * 2) and c > level and c > o

    def _entry_bull(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bull_stay_warmup and c < ema20:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False; self._reset_retest(); return
        # v2.2: check for BEAR signal while in BULL state (no position open)
        if self.config.direct_transition_enabled and self._is_bear_signal(o, h, l, c, ema20):
            if self.config.bear_body_ratio_min <= 0 or self._check_bear_body_ratio(o, h, l, c):
                self.state = 'BEAR'; self._direct_bull_to_bear += 1
                self._execute_bear_entry(bar_idx, o, h, l, c, ema20); return
        if self.config.bull_use_swing_break: primary_trigger = self._check_swing_break(h, c, o); trigger_name = 'swing_break'
        else: primary_trigger = self._is_bull_signal(o, h, l, c, ema20); trigger_name = 'ema_reclaim'
        if self.config.bull_wait_retest_enabled and self._bull_retest_pending:
            self._bull_retest_bar_count += 1
            if c < self._bull_broken_level: self._bull_blocked_retest_invalidated += 1; self._reset_retest(); return
            if self._bull_retest_bar_count > self.config.bull_retest_max_bars: self._bull_blocked_retest_timeout += 1; self._reset_retest(); return
            if self._check_structural_retest(l, c, o): self._reset_retest(); self._open_bull(bar_idx, h, l, c, 'retest_entry'); self._bull_retest_entries += 1
            return
        if primary_trigger:
            if self.config.bull_body_ratio_min > 0 and not self._check_body_ratio(o, h, l, c):
                self._bull_blocked_body += 1
                if self._check_poc_bounce(o, h, l, c): self._open_bull(bar_idx, h, l, c, 'poc_bounce'); return
                if self._check_26_bounce(o, h, l, c): self._open_bull(bar_idx, h, l, c, '26_bounce')
                return
            if self.config.bull_wait_retest_enabled:
                broken = self._get_swing_high(self.config.bull_retest_swing_lookback)
                if broken is None: self._bull_blocked_no_swing_history += 1; self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger=trigger_name); return
                self._bull_broken_level = broken; self._bull_retest_pending = True; self._bull_retest_bar_count = 0; return
            self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger=trigger_name); return
        if self._check_poc_bounce(o, h, l, c): self._open_bull(bar_idx, h, l, c, 'poc_bounce'); return
        if self._check_26_bounce(o, h, l, c): self._open_bull(bar_idx, h, l, c, '26_bounce')

    def _execute_bull_entry(self, bar_idx, o, h, l, c, ema20, trigger):
        entry_price = c; sl_price = l
        if trigger == 'ema_reclaim' and self.config.bull_mtf_15m_enabled:
            mtf_c, mtf_l = self._get_mtf_bull_entry(bar_idx)
            if mtf_c is None or mtf_l is None: self._bull_blocked_mtf += 1; return
            entry_price = mtf_c; sl_price = mtf_l
        self._open_bull(bar_idx, h, sl_price, entry_price, trigger)

    def _open_bull(self, bar_idx, entry_high, sl_level, entry_price, trigger='ema_reclaim'):
        if self.config.sl_pct > 0: sl_level = entry_price * (1.0 - self.config.sl_pct)
        tp_level = entry_price * (1.0 + self.config.tp_pct)
        self.position = Position(tool='BULL', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=entry_high, entry_low=sl_level, sl_level=sl_level, original_sl=sl_level, tp_level=tp_level,
            peak_high=entry_high, trough_low=sl_level, ema_at_entry=self._current_ema20, entry_trigger=trigger)
        self._bull_entries += 1
        if trigger == 'ema_reclaim': self._bull_ema_reclaim_entries += 1
        elif trigger == 'poc_bounce': self._bull_poc_bounce_entries += 1
        elif trigger == 'swing_break': self._bull_swing_break_entries += 1
        elif trigger == '26_bounce': self._bull_26_bounce_entries += 1

    def _get_mtf_bear_entry(self, bar_idx):
        if self.mtf_bear_entry_close is None: return None, None
        if bar_idx >= len(self.mtf_bear_entry_close): return None, None
        return self.mtf_bear_entry_close[bar_idx], self.mtf_bear_entry_high[bar_idx]

    def _execute_bear_entry(self, bar_idx, o, h, l, c, ema20):
        """Execute BEAR entry (used by both normal _entry_bear and direct transition)."""
        entry_price = c; sl_price = h
        if self.config.bear_mtf_15m_enabled:
            mtf_c, mtf_h = self._get_mtf_bear_entry(bar_idx)
            if mtf_c is None or mtf_h is None: self._bear_blocked_mtf += 1; return
            entry_price = mtf_c; sl_price = mtf_h
        self._open_bear(bar_idx, h, l, sl_price, entry_price)

    def _entry_bear(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bear_stay_warmup and c > ema20:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False; return
        # v2.2: check for BULL signal while in BEAR state (no position open)
        if self.config.direct_transition_enabled and self._is_bull_signal(o, h, l, c, ema20):
            if self.config.bull_body_ratio_min <= 0 or self._check_body_ratio(o, h, l, c):
                self.state = 'BULL'; self._direct_bear_to_bull += 1
                self._execute_bull_entry(bar_idx, o, h, l, c, ema20, trigger='ema_reclaim'); return
        if not self._is_bear_signal(o, h, l, c, ema20): return
        if self.config.bear_body_ratio_min > 0 and not self._check_bear_body_ratio(o, h, l, c): self._bear_blocked_body += 1; return
        self._execute_bear_entry(bar_idx, o, h, l, c, ema20)

    def _open_bear(self, bar_idx, entry_high, entry_low, sl_level, entry_price):
        bear_sl_pct = self.config.get_bear_sl_pct()
        if bear_sl_pct > 0: sl_level = entry_price * (1.0 + bear_sl_pct)
        tp_level = entry_price * (1.0 - self.config.get_bear_tp_pct())
        self.position = Position(tool='BEAR', side='SHORT', entry_price=entry_price, entry_bar=bar_idx,
            entry_high=entry_high, entry_low=entry_low, sl_level=sl_level, original_sl=sl_level, tp_level=tp_level,
            peak_high=entry_high, trough_low=entry_low, ema_at_entry=self._current_ema20)
        self._bear_entries += 1

    def _close_position(self, bar_idx, exit_price, exit_type):
        pos = self.position
        if pos.side == 'LONG': pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else: pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        pnl_pct_net = pnl_pct - self.config.total_cost_pct()
        pnl_usd = pnl_pct_net * self.config.notional() * pos.size_ratio
        self.trades.append(Trade(tool=pos.tool, side=pos.side, entry_price=pos.entry_price, exit_price=exit_price,
            entry_bar=pos.entry_bar, exit_bar=bar_idx, exit_type=exit_type, pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
            peak_high=pos.peak_high, trough_low=pos.trough_low, sl_level=pos.sl_level, tp_level=pos.tp_level,
            ema_at_entry=pos.ema_at_entry, ema_at_exit=self._current_ema20, entry_trigger=pos.entry_trigger))
        self.position = None; self._action_taken_this_bar = True
