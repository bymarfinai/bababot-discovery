"""Mode3 Config v5.2 — BEAR deep bear filter (skip if HTF close-EMA gap < threshold)."""
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

    # v5.2 Fix #22: skip BEAR entry when HTF is deep bear (CT Bull dominates there)
    bear_skip_deep_bear: bool = False
    bear_skip_deep_bear_threshold: float = -0.03  # skip if (close-EMA)/EMA < this

    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2

    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True
    bull_countertrend_max_close_pct: float = 0.0
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    bull_countertrend_tp_pct: float = 0.012
    bull_countertrend_size_mult: float = 3.0

    bear_trend_rider_enabled: bool = True
    bear_trend_rider_regime_bars: int = 3
    bear_trend_rider_regime_slope_max: float = -0.3
    bear_trend_rider_tp_pct: float = 0.030
    bear_trend_rider_trailing_activate_pct: float = 0.015
    bear_trend_rider_trailing_distance_pct: float = 0.008
    bear_trend_rider_disable_ct_bull: bool = False

    amt_enabled: bool = True
    amt_boundary_pct: float = 0.005
    amt_skip_sw_above: bool = False
    amt_skip_bull_below: bool = False
    amt_bull_near_vah_mult: float = 2.0
    amt_bull_above_mult: float = 1.5

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
