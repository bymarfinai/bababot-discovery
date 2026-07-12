"""
Mode3 Config v4.3 — Fix #20 Liquidity Sweep Detector.

Sweep DOWN (bullish signal): prev bar wick pierced HTF VAL then closed back above.
Sweep UP (bearish signal): prev bar wick pierced HTF VAH then closed back below.

Applied as SIZING AMPLIFIER for BULL LONG (sweep down) and SW SHORT (sweep up).
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

    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True
    bull_countertrend_max_close_pct: float = 0.0
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    bull_countertrend_tp_pct: float = 0.012
    bull_countertrend_size_mult: float = 2.0

    bear_trend_rider_enabled: bool = True
    bear_trend_rider_regime_bars: int = 3
    bear_trend_rider_regime_slope_max: float = -0.3
    bear_trend_rider_tp_pct: float = 0.030
    bear_trend_rider_trailing_activate_pct: float = 0.015
    bear_trend_rider_trailing_distance_pct: float = 0.008
    bear_trend_rider_disable_ct_bull: bool = False

    bull_trend_rider_enabled: bool = False
    bull_trend_rider_regime_bars: int = 3
    bull_trend_rider_regime_slope_min: float = 0.3
    bull_trend_rider_tp_pct: float = 0.030
    bull_trend_rider_trailing_activate_pct: float = 0.015
    bull_trend_rider_trailing_distance_pct: float = 0.008

    crs_enabled: bool = False
    crs_lookback_4h_bars: int = 10
    crs_active_hours: int = 8
    crs_size_mult: float = 1.0
    crs_use_projection_tp: bool = False
    crs_projection_divisor: float = 2.6
    crs_skip_bull_hours: int = 0
    crs_regime_gate: bool = False
    crs_regime_max_slope: float = 0.3

    amt_enabled: bool = False
    amt_boundary_pct: float = 0.005
    amt_skip_sw_above: bool = True
    amt_skip_bull_below: bool = True
    amt_bull_near_vah_mult: float = 2.0
    amt_bull_above_mult: float = 1.5

    amt_smart_levels_enabled: bool = False
    amt_sw_above_use_vah_tp: bool = True
    amt_bull_near_vah_use_projection_tp: bool = True
    amt_projection_divisor: float = 2.6
    amt_bull_below_use_val_sl: bool = True

    bull_wick_tolerance_enabled: bool = False
    bull_wick_tolerance_pct: float = 0.002
    bull_below_use_val_tp: bool = False

    # v4.3 Fix #20 Liquidity Sweep Detector
    sweep_enabled: bool = False
    sweep_bull_mult: float = 2.0        # amplify BULL entry after sweep down
    sweep_sw_short_mult: float = 2.0    # amplify SW SHORT entry after sweep up
    sweep_lookback_bars: int = 1        # check N prior 1h bars for sweep pattern

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
