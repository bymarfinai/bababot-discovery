"""
Mode3 Config v2.8 — added counter-trend BULL enhancement (Fix #5).
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

    # v2.5 fixes
    sm_fix_1_htf_confirm: bool = False
    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2
    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    # v2.6 Fix #4 confirmation bar (kept but OFF)
    sm_fix_4_bull_confirm: bool = False
    sm_fix_4_bear_confirm: bool = False

    # === v2.8: FIX #5 COUNTER-TREND BULL ENHANCEMENT ===
    # Detect BULL setups when 4h HTF is bearish (oversold bounce opportunity)
    # These have shown higher WR — enhance with bigger TP and/or bigger position
    bull_countertrend_enabled: bool = False
    bull_countertrend_slope_window: int = 20   # bars for 4h EMA slope
    bull_countertrend_slope_threshold: float = -1.0  # slope < -1% = HTF meaningfully bearish
    bull_countertrend_tp_pct: float = 0.020    # 2% TP instead of standard 1.2%
    bull_countertrend_size_mult: float = 1.0   # position multiplier (2.0 = double size)

    # v2.3 TRAP
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
