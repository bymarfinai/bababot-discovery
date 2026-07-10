"""
Mode3 Config v3.3 CHAMPION FINAL — Fix #7 CT BULL + Fix #8/#9 BEAR Trend Rider.

Champion: Fix #7 + #8 + #9 all ON, coexist without conflict.

DEPRECATED (kept for backward compat, but proved net-negative):
- Fix #10 HTF Flat Filter (marginal +$1)
- Fix #11 Local Resistance (-$41)
- Fix #12 HH/LH Structural (-$55)
- Fix #13 Recent High Distance (-$29)
All default OFF. Do not enable.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.012
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    sideways_ema_distance_cap: float = 0.003
    sideways_ema_invalidation: bool = True
    sideways_ema_invalidation_tolerance: float = 0.0015
    sideways_mtf_15m_entry: bool = True
    sideways_tp_pct: float = 0.003
    sideways_max_slope_pct: float = 0.018
    sideways_slope_window: int = 20

    chop_window: int = 20
    chop_max_crossings: int = 4

    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5
    bull_mtf_15m_entry: bool = True
    bull_use_rr_tp: bool = False
    bull_rr_ratio: float = 1.0

    bear_mtf_15m_entry: bool = True
    bear_min_sl_dist: float = 0.0
    bear_use_1h_sl_fallback: bool = False

    sm_fix_1_htf_confirm: bool = False
    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2
    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    sm_fix_4_bull_confirm: bool = False
    sm_fix_4_bear_confirm: bool = False

    # === ACTIVE CHAMPION FIXES ===
    # Fix #7: CT BULL position-based (2x size when 4h close < 4h EMA20)
    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True
    bull_countertrend_max_close_pct: float = 0.0
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    bull_countertrend_tp_pct: float = 0.012
    bull_countertrend_size_mult: float = 2.0

    # Fix #8/#9: BEAR Trend Rider
    bear_trend_rider_enabled: bool = True
    bear_trend_rider_regime_bars: int = 3
    bear_trend_rider_regime_slope_max: float = -0.3
    bear_trend_rider_tp_pct: float = 0.030
    bear_trend_rider_trailing_activate_pct: float = 0.015
    bear_trend_rider_trailing_distance_pct: float = 0.008
    bear_trend_rider_disable_ct_bull: bool = False

    # === DEPRECATED FIXES (all default OFF, proved net-negative) ===
    bull_htf_flat_filter_enabled: bool = False
    bull_htf_flat_min_dist_pct: float = 0.0
    bull_htf_flat_max_slope_pct: float = 0.15
    bull_local_resistance_filter_enabled: bool = False
    bull_local_resistance_zone_pct: float = 0.02
    bull_hh_lh_filter_enabled: bool = False
    bull_hh_lh_lookback_bars: int = 168
    bull_hh_lh_min_hh_dist_pct: float = 0.005
    bull_recent_high_filter_enabled: bool = False
    bull_recent_high_lookback_bars: int = 720
    bull_recent_high_max_ratio: float = 0.98

    trap_enabled: bool = False
    trap_lookback_4h: int = 3
    trap_zone_tolerance: float = 0.002
    trap_tp_pct: float = 0.012
    trap_use_1h_va_tp: bool = False
    trap_priority_over_state: bool = True

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
