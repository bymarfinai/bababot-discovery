"""
Mode3 Switcher v5.0 — Cleaned up. Champion Option A only.

Kept:
- State machine (STARTUP/SIDEWAYS/BULL/BEAR/WAIT_SEE_*)
- CT Bull 3x + AMT amplify
- BEAR Trend Rider (trailing)
- SM Fix 2 (bear streak) + Fix 3 (extreme low)
- MTF 15m entry
- Chop + volume filter

Removed (see mode3/_legacy/README.md):
- Trap, CRS, Bull Trend Rider
- AMT Smart Levels, Wick tolerance, BULL BELOW VAL TP
- Sweep, BE SL, SM Fix 1 & 4
"""
from dataclasses import dataclass
from typing import Optional
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
    size_mult: float = 1.0
    is_trend_rider: bool = False       # BEAR trend rider
    trailing_active: bool = False
    is_countertrend: bool = False      # CT Bull
    amt_position: str = ''             # INSIDE/NEAR_VAH/ABOVE/BELOW/NEAR_VAL


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
    size_mult: float = 1.0
    is_trend_rider: bool = False
    is_countertrend: bool = False
    amt_position: str = ''


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
        # Filters
        self._chop_history = deque(maxlen=config.chop_window)
        self._ema_history = deque(maxlen=config.sideways_slope_window)
        self._volume_history = deque(maxlen=config.bull_volume_window)
        self._high_history = deque(maxlen=max(config.sm_fix_3_high_lookback, 10))
        # Blocked counters
        self._sideways_blocked_count = 0
        self._sideways_blocked_slope = 0
        self._sideways_blocked_mtf = 0
        self._chop_blocked_count = 0
        self._bull_blocked_volume = 0
        self._bull_blocked_mtf = 0
        self._bear_blocked_mtf = 0
        self._bear_blocked_min_sl = 0
        # BEAR streak
        self._bear_loss_streak = 0
        self._last_exit_bar = 0
        # SM Fix counters
        self._sm_fix2_count = 0
        self._sm_fix3_count = 0
        # CT Bull counter
        self._bull_countertrend_count = 0
        # BEAR Trend Rider counters
        self._bear_trend_rider_count = 0
        self._bear_trend_rider_trailing_hits = 0
        self._bear_trend_rider_hard_exits = 0
        # AMT counter
        self._amt_bull_amplified = 0
        # MTF 15m entry data (populated externally)
        self.mtf_bull_entry_close = None
        self.mtf_bull_entry_low = None
        self.mtf_bear_entry_close = None
        self.mtf_bear_entry_high = None
        self.mtf_sideways_short_entry_close = None
        self.mtf_sideways_short_entry_high = None
        self.mtf_sideways_long_entry_close = None
        self.mtf_sideways_long_entry_low = None
        # HTF context (populated externally)
        self.htf_4h_vah = None
        self.htf_4h_val = None
        self.htf_4h_close = None
        self.htf_4h_ema20 = None
        self.htf_4h_slope = None
        self.htf_4h_downtrend = None

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
        self._high_history.append(h)

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

    def _get_balance_position(self, bar_idx, price):
        if self.htf_4h_vah is None or self.htf_4h_val is None: return 'UNKNOWN'
        if bar_idx >= len(self.htf_4h_vah) or bar_idx >= len(self.htf_4h_val): return 'UNKNOWN'
        vah = self.htf_4h_vah[bar_idx]; val = self.htf_4h_val[bar_idx]
        if vah is None or val is None or price is None: return 'UNKNOWN'
        if price > vah: return 'ABOVE'
        if price < val: return 'BELOW'
        boundary = self.config.amt_boundary_pct
        if (vah - price) / vah < boundary: return 'NEAR_VAH'
        if (price - val) / val < boundary: return 'NEAR_VAL'
        return 'INSIDE'

    def _is_choppy(self):
        if self.config.chop_max_crossings <= 0: return False
        if len(self._chop_history) < self.config.chop_window: return False
        crossings = 0; hist = list(self._chop_history); prev = hist[0]
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
        return abs(hist[-1] - hist[0]) / hist[0] <= max_slope

    def _sideways_ema_inv_ok_short(self, c, ema20):
        if not self.config.sideways_ema_invalidation: return False
        tol = self.config.sideways_ema_invalidation_tolerance
        if tol > 0 and (c - ema20) / ema20 < tol: return False
        return True

    def _sideways_ema_inv_ok_long(self, c, ema20):
        if not self.config.sideways_ema_invalidation: return False
        tol = self.config.sideways_ema_invalidation_tolerance
        if tol > 0 and (ema20 - c) / ema20 < tol: return False
        return True

    def _sideways_tp_pct(self):
        return self.config.sideways_tp_pct if self.config.sideways_tp_pct > 0 else self.config.tp_pct

    def _bull_tp_level(self, entry_price, sl_level):
        if self.config.bull_use_rr_tp:
            sl_distance = entry_price - sl_level
            if sl_distance > 0:
                return entry_price + sl_distance * self.config.bull_rr_ratio
        return entry_price * (1.0 + self.config.tp_pct)

    def _is_bear_trend_rider_regime(self, bar_idx):
        if not self.config.bear_trend_rider_enabled: return False
        if self.htf_4h_downtrend is None or bar_idx >= len(self.htf_4h_downtrend): return False
        return bool(self.htf_4h_downtrend[bar_idx])

    def _is_countertrend_bull(self, bar_idx):
        if not self.config.bull_countertrend_enabled: return False
        if (self.config.bear_trend_rider_enabled
                and self.config.bear_trend_rider_disable_ct_bull
                and self._is_bear_trend_rider_regime(bar_idx)): return False
        if self.config.bull_countertrend_use_position:
            if self.htf_4h_close is None or self.htf_4h_ema20 is None: return False
            if bar_idx >= len(self.htf_4h_close) or bar_idx >= len(self.htf_4h_ema20): return False
            c = self.htf_4h_close[bar_idx]; e = self.htf_4h_ema20[bar_idx]
            if c is None or e is None or e <= 0: return False
            dist_pct = (c - e) / e * 100
            return dist_pct < self.config.bull_countertrend_max_close_pct
        else:
            if self.htf_4h_slope is None or bar_idx >= len(self.htf_4h_slope): return False
            slope = self.htf_4h_slope[bar_idx]
            if slope is None: return False
            return slope < self.config.bull_countertrend_slope_threshold

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
        elif et == 'TP':
            self.state = 'SIDEWAYS'
        else:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'A'

    def _post_exit_sideways_long(self, et):
        if et == 'SL':
            self.state = 'BEAR'; self.bear_stay_warmup = False; self.markers.ll_breach_case = 'none'
        elif et == 'TP':
            self.state = 'SIDEWAYS'
        else:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'A'

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
        if pos.is_trend_rider:
            # BEAR trend rider: HTF reclaim exit
            if (self.htf_4h_close is not None and self.htf_4h_ema20 is not None
                    and bar_idx < len(self.htf_4h_close)):
                htf_c = self.htf_4h_close[bar_idx]; htf_e = self.htf_4h_ema20[bar_idx]
                if htf_c is not None and htf_e is not None and htf_c > htf_e:
                    self._close_position(bar_idx, c, 'HTF_RECLAIM'); self._bear_trend_rider_hard_exits += 1
                    self._post_exit_bear('HTF_RECLAIM'); return
            # Trailing SL
            profit_pct = (pos.entry_price - c) / pos.entry_price
            activate_th = self.config.bear_trend_rider_trailing_activate_pct
            trail_dist = self.config.bear_trend_rider_trailing_distance_pct
            if not pos.trailing_active and profit_pct >= activate_th:
                pos.trailing_active = True; pos.sl_level = pos.trough_low * (1.0 + trail_dist)
            if pos.trailing_active:
                new_sl = pos.trough_low * (1.0 + trail_dist)
                if new_sl < pos.sl_level: pos.sl_level = new_sl
                if c > pos.sl_level:
                    self._close_position(bar_idx, c, 'TRAILING_SL'); self._bear_trend_rider_trailing_hits += 1
                    self._post_exit_bear('TRAILING_SL'); return
        # Standard SL/TP
        if c > pos.sl_level: self._close_position(bar_idx, c, 'SL'); self._post_exit_bear('SL'); return
        if c <= pos.tp_level: self._close_position(bar_idx, c, 'TP'); self._post_exit_bear('TP'); return

    def _post_exit_bear(self, et):
        last_trough = self.position.trough_low if self.position else self.trades[-1].trough_low
        last_entry = self.trades[-1].entry_price
        self.markers.trough_low_bear = last_trough
        if et in ('TP', 'TRAILING_SL'):
            self._bear_loss_streak = 0
            # SM Fix 3: bear win at extreme low → sideways
            if self.config.sm_fix_3_extreme_low and len(self._high_history) >= 20:
                recent_high = max(self._high_history)
                if recent_high > 0:
                    distance = (recent_high - last_entry) / recent_high
                    if distance >= self.config.sm_fix_3_extreme_pct:
                        self.state = 'SIDEWAYS'; self.bear_stay_warmup = False; self._sm_fix3_count += 1; return
            self.state = 'BEAR'; self.bear_stay_warmup = True
        else:
            if et == 'SL':
                self._bear_loss_streak += 1
                # SM Fix 2: bear loss streak → sideways
                if (self.config.sm_fix_2_bear_streak
                        and self._bear_loss_streak >= self.config.sm_fix_2_streak_threshold):
                    self.state = 'SIDEWAYS'; self.bear_stay_warmup = False
                    self._bear_loss_streak = 0; self._sm_fix2_count += 1; return
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False

    def _check_entry(self, bar_idx, o, h, l, c, ema20, vah, val, poc):
        if vah is None or val is None: return
        if self.state == 'SIDEWAYS': self._entry_sideways(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BULLISH': self._entry_wait_see_bullish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'WAIT_SEE_BEARISH': self._entry_wait_see_bearish(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BULL': self._entry_bull(bar_idx, o, h, l, c, ema20, vah, val)
        elif self.state == 'BEAR': self._entry_bear(bar_idx, o, h, l, c, ema20, vah, val)

    def _entry_sideways(self, bar_idx, o, h, l, c, ema20, vah, val):
        short_ok = (h >= vah) and (c <= vah); long_ok = (l <= val) and (c >= val)
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
        if not self._sideways_distance_ok(c): self._sideways_blocked_count += 1; return
        if not self._sideways_slope_ok(): self._sideways_blocked_slope += 1; return
        tp_pct = self._sideways_tp_pct()
        if self.config.sideways_mtf_15m_entry and self.mtf_sideways_short_entry_close is not None:
            if bar_idx < len(self.mtf_sideways_short_entry_close):
                mtf_close = self.mtf_sideways_short_entry_close[bar_idx]
                mtf_high = self.mtf_sideways_short_entry_high[bar_idx]
                if mtf_close is None or mtf_high is None:
                    self._sideways_blocked_mtf += 1; return
                self.markers.marker_high_short = mtf_high; self.markers.marker_close_short = mtf_close
                self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=mtf_close, entry_bar=bar_idx,
                    entry_high=mtf_high, entry_low=l, sl_level=mtf_high, tp_level=mtf_close*(1.0-tp_pct),
                    peak_high=mtf_high, trough_low=l, ema_at_entry=self._current_ema20)
                self._bear_loss_streak = 0; return
        self.markers.marker_high_short = h; self.markers.marker_close_short = c
        self.position = Position(tool='SIDEWAYS', side='SHORT', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=h, tp_level=c*(1.0-tp_pct),
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)
        self._bear_loss_streak = 0

    def _open_long_sideways(self, bar_idx, h, l, c):
        if not self._sideways_distance_ok(c): self._sideways_blocked_count += 1; return
        if not self._sideways_slope_ok(): self._sideways_blocked_slope += 1; return
        tp_pct = self._sideways_tp_pct()
        if self.config.sideways_mtf_15m_entry and self.mtf_sideways_long_entry_close is not None:
            if bar_idx < len(self.mtf_sideways_long_entry_close):
                mtf_close = self.mtf_sideways_long_entry_close[bar_idx]
                mtf_low = self.mtf_sideways_long_entry_low[bar_idx]
                if mtf_close is None or mtf_low is None:
                    self._sideways_blocked_mtf += 1; return
                self.markers.marker_low_long = mtf_low; self.markers.marker_close_long = mtf_close
                self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=mtf_close, entry_bar=bar_idx,
                    entry_high=h, entry_low=mtf_low, sl_level=mtf_low, tp_level=mtf_close*(1.0+tp_pct),
                    peak_high=h, trough_low=mtf_low, ema_at_entry=self._current_ema20)
                self._bear_loss_streak = 0; return
        self.markers.marker_low_long = l; self.markers.marker_close_long = c
        self.position = Position(tool='SIDEWAYS', side='LONG', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=l, tp_level=c*(1.0+tp_pct),
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20)
        self._bear_loss_streak = 0

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

    def _execute_bull_entry(self, bar_idx, o, h, l, c, ema20, vah, val):
        # Determine entry price for AMT position check
        entry_price_for_pos = c
        if self.config.bull_mtf_15m_entry and self.mtf_bull_entry_close is not None:
            if bar_idx < len(self.mtf_bull_entry_close):
                mtf_c = self.mtf_bull_entry_close[bar_idx]
                if mtf_c is not None: entry_price_for_pos = mtf_c
        # AMT position (for amplify)
        amt_pos = ''
        if self.config.amt_enabled:
            amt_pos = self._get_balance_position(bar_idx, entry_price_for_pos)
            # amt_skip_bull_below/above filter (default false = allow all, amplify only)
            if self.config.amt_skip_bull_below and amt_pos == 'BELOW':
                return
        # Volume filter
        if not self._bull_volume_ok(self._volume_history[-1] if self._volume_history else 0):
            self._bull_blocked_volume += 1; return
        # Sizing: CT Bull > AMT amplify
        is_ct = self._is_countertrend_bull(bar_idx)
        size_mult = self.config.bull_countertrend_size_mult if is_ct else 1.0
        if self.config.amt_enabled and amt_pos in ('NEAR_VAH', 'ABOVE'):
            amt_mult = (self.config.amt_bull_near_vah_mult if amt_pos == 'NEAR_VAH' 
                        else self.config.amt_bull_above_mult)
            if amt_mult > size_mult:
                size_mult = amt_mult
                self._amt_bull_amplified += 1
        # Execute
        if self.config.bull_mtf_15m_entry and self.mtf_bull_entry_close is not None:
            if bar_idx < len(self.mtf_bull_entry_close):
                mtf_close = self.mtf_bull_entry_close[bar_idx]
                mtf_low = self.mtf_bull_entry_low[bar_idx]
                if mtf_close is None or mtf_low is None:
                    self._bull_blocked_mtf += 1; return
                entry_price = mtf_close; sl_level = mtf_low
                if is_ct:
                    tp_level = entry_price * (1.0 + self.config.bull_countertrend_tp_pct)
                    self._bull_countertrend_count += 1
                else:
                    tp_level = self._bull_tp_level(entry_price, sl_level)
                self.position = Position(tool='BULL', side='LONG', entry_price=entry_price, entry_bar=bar_idx,
                    entry_high=h, entry_low=mtf_low, sl_level=sl_level, tp_level=tp_level,
                    peak_high=h, trough_low=mtf_low, ema_at_entry=self._current_ema20,
                    size_mult=size_mult, is_countertrend=is_ct, amt_position=amt_pos)
                self._bear_loss_streak = 0; return
        if is_ct:
            tp_level = c * (1.0 + self.config.bull_countertrend_tp_pct)
            self._bull_countertrend_count += 1
        else:
            tp_level = self._bull_tp_level(c, l)
        self.position = Position(tool='BULL', side='LONG', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=l, tp_level=tp_level,
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20,
            size_mult=size_mult, is_countertrend=is_ct, amt_position=amt_pos)
        self._bear_loss_streak = 0

    def _entry_bull(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bull_stay_warmup and c < ema20:
            self.state = 'WAIT_SEE_BULLISH'; self.markers.hh_breach_case = 'B'; self.bull_stay_warmup = False
            return
        # 1h EMA20 reclaim setup + bullish body
        if (l <= ema20) and (c > ema20) and (c > o):
            self._execute_bull_entry(bar_idx, o, h, l, c, ema20, vah, val)

    def _execute_bear_entry(self, bar_idx, o, h, l, c, ema20, vah, val):
        is_trend_rider = self._is_bear_trend_rider_regime(bar_idx)
        size_mult = 1.0
        if self.config.bear_mtf_15m_entry and self.mtf_bear_entry_close is not None:
            if bar_idx < len(self.mtf_bear_entry_close):
                mtf_close = self.mtf_bear_entry_close[bar_idx]
                mtf_high = self.mtf_bear_entry_high[bar_idx]
                if mtf_close is None or mtf_high is None:
                    self._bear_blocked_mtf += 1; return
                entry_price = mtf_close; sl_level = mtf_high
                if self.config.bear_min_sl_dist > 0:
                    sl_dist = (sl_level - entry_price) / entry_price
                    if sl_dist < self.config.bear_min_sl_dist:
                        if self.config.bear_use_1h_sl_fallback:
                            sl_level_1h = h
                            sl_dist_1h = (sl_level_1h - entry_price) / entry_price
                            if sl_dist_1h >= self.config.bear_min_sl_dist:
                                sl_level = sl_level_1h
                            else:
                                self._bear_blocked_min_sl += 1; return
                        else:
                            self._bear_blocked_min_sl += 1; return
                if is_trend_rider:
                    tp_level = entry_price * (1.0 - self.config.bear_trend_rider_tp_pct)
                    self._bear_trend_rider_count += 1
                else:
                    tp_level = entry_price * (1.0 - self.config.tp_pct)
                self.position = Position(tool='BEAR', side='SHORT', entry_price=entry_price, entry_bar=bar_idx,
                    entry_high=mtf_high, entry_low=l, sl_level=sl_level, tp_level=tp_level,
                    peak_high=mtf_high, trough_low=l, ema_at_entry=self._current_ema20,
                    is_trend_rider=is_trend_rider, size_mult=size_mult)
                return
        if self.config.bear_min_sl_dist > 0:
            sl_dist = (h - c) / c
            if sl_dist < self.config.bear_min_sl_dist:
                self._bear_blocked_min_sl += 1; return
        if is_trend_rider:
            tp_level = c * (1.0 - self.config.bear_trend_rider_tp_pct)
            self._bear_trend_rider_count += 1
        else:
            tp_level = c * (1.0 - self.config.tp_pct)
        self.position = Position(tool='BEAR', side='SHORT', entry_price=c, entry_bar=bar_idx,
            entry_high=h, entry_low=l, sl_level=h, tp_level=tp_level,
            peak_high=h, trough_low=l, ema_at_entry=self._current_ema20,
            is_trend_rider=is_trend_rider, size_mult=size_mult)

    def _entry_bear(self, bar_idx, o, h, l, c, ema20, vah, val):
        if self.bear_stay_warmup and c > ema20:
            self.state = 'WAIT_SEE_BEARISH'; self.markers.ll_breach_case = 'B'; self.bear_stay_warmup = False
            return
        if (h >= ema20) and (c < ema20) and (c < o):
            self._execute_bear_entry(bar_idx, o, h, l, c, ema20, vah, val)

    def _close_position(self, bar_idx, exit_price, exit_type):
        pos = self.position
        if pos.side == 'LONG':
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
        pnl_pct_net = pnl_pct - self.config.total_cost_pct()
        pnl_usd = pnl_pct_net * self.config.notional() * pos.size_mult
        self.trades.append(Trade(tool=pos.tool, side=pos.side, entry_price=pos.entry_price, exit_price=exit_price,
            entry_bar=pos.entry_bar, exit_bar=bar_idx, exit_type=exit_type, pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
            peak_high=pos.peak_high, trough_low=pos.trough_low, sl_level=pos.sl_level, tp_level=pos.tp_level,
            ema_at_entry=pos.ema_at_entry, ema_at_exit=self._current_ema20, size_mult=pos.size_mult,
            is_trend_rider=pos.is_trend_rider, is_countertrend=pos.is_countertrend,
            amt_position=pos.amt_position))
        self.position = None
        self._action_taken_this_bar = True
        self._last_exit_bar = bar_idx
