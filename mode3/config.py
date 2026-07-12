"""
Mode3 Config v5.0 — Cleaned up. Champion Option A only.

Removed features (see mode3/_legacy/README.md):
- CRS, Trap, Bull Trend Rider, SM Fix 1 & 4
- AMT Smart Levels, Wick tolerance, BULL BELOW VAL TP
- Sweep Detector, Break-Even SL

Champion config:
- CT Bull 3x sizing
- AMT Amplify (NEAR_VAH 2x, ABOVE 1.5x)
- Per-pair TP via Query
- BEAR Trend Rider (trailing)
- SM Fix 2 (bear streak → sideways)
- SM Fix 3 (extreme low → sideways)

Performance: +$1,796/year, 359% ROI
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    # Base
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # Position sizing
    tp_pct: float = 0.012
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # Sideways
    sideways_ema_distance_cap: float = 0.003
    sideways_ema_invalidation: bool = True
    sideways_ema_invalidation_tolerance: float = 0.0015
    sideways_mtf_15m_entry: bool = True
    sideways_tp_pct: float = 0.003
    sideways_max_slope_pct: float = 0.018
    sideways_slope_window: int = 20

    # Chop filter
    chop_window: int = 20
    chop_max_crossings: int = 4

    # Bull
    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5
    bull_mtf_15m_entry: bool = True
    bull_use_rr_tp: bool = False
    bull_rr_ratio: float = 1.0

    # Bear
    bear_mtf_15m_entry: bool = True
    bear_min_sl_dist: float = 0.0
    bear_use_1h_sl_fallback: bool = False

    # SM Fix 2 (bear streak → sideways)
    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2

    # SM Fix 3 (bear extreme low → sideways)
    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    # CT Bull (dip buy in bearish HTF)
    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True
    bull_countertrend_max_close_pct: float = 0.0
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    bull_countertrend_tp_pct: float = 0.012
    bull_countertrend_size_mult: float = 3.0  # champion 3x

    # BEAR Trend Rider (trailing SL, extended TP in bearish regime)
    bear_trend_rider_enabled: bool = True
    bear_trend_rider_regime_bars: int = 3
    bear_trend_rider_regime_slope_max: float = -0.3
    bear_trend_rider_tp_pct: float = 0.030
    bear_trend_rider_trailing_activate_pct: float = 0.015
    bear_trend_rider_trailing_distance_pct: float = 0.008
    bear_trend_rider_disable_ct_bull: bool = False

    # AMT (Auction Market Theory) — Amplify only
    amt_enabled: bool = True
    amt_boundary_pct: float = 0.005
    amt_skip_sw_above: bool = False    # champion: allow, amplify only
    amt_skip_bull_below: bool = False  # champion: allow, amplify only
    amt_bull_near_vah_mult: float = 2.0
    amt_bull_above_mult: float = 1.5

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
