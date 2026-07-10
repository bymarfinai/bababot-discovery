"""
Mode3 Config v3.0 — Fix #8/#9 BEAR Trend Rider (crash regime capture).

Champion + new crash-mode BEAR:
- v2.9 CHAMPION baseline (all previous fixes)
- Fix #8: 4h downtrend regime detector
- Fix #9: BEAR Trend Rider with wider TP + trailing stop
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

    # v2.5 state machine fixes
    sm_fix_1_htf_confirm: bool = False
    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2
    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    sm_fix_4_bull_confirm: bool = False
    sm_fix_4_bear_confirm: bool = False

    # v2.9 Fix #7 Counter-trend BULL (CHAMPION)
    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True
    bull_countertrend_max_close_pct: float = 0.0
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    bull_countertrend_tp_pct: float = 0.012
    bull_countertrend_size_mult: float = 2.0

    # === v3.0 Fix #8/#9: BEAR TREND RIDER (crash regime capture) ===
    bear_trend_rider_enabled: bool = False
    # Regime detection: N consecutive 4h bars close < 4h EMA20
    bear_trend_rider_regime_bars: int = 3
    # 4h slope must be at least this negative to confirm downtrend
    bear_trend_rider_regime_slope_max: float = -0.3
    # Wider TP for trend rider entries
    bear_trend_rider_tp_pct: float = 0.030
    # Trailing stop: activate when profit exceeds this
    bear_trend_rider_trailing_activate_pct: float = 0.015
    # Trail SL by this distance from peak profit
    bear_trend_rider_trailing_distance_pct: float = 0.008
    # Optional: block Fix #7 CT BULL when in trend rider regime
    bear_trend_rider_disable_ct_bull: bool = True

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
