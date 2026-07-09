"""
Mode3 Config v2.9 CHAMPION — Fix #7 position-based counter-trend BULL.

Champion config (BTC 1h):
- Fixed TP 1.2% (BULL/BEAR), 0.3% (SIDEWAYS)
- Fix #2: BEAR streak → SIDEWAYS
- Fix #3: Extreme low 5% → SIDEWAYS
- Fix #7: Counter-trend BULL 2x size when 4h close < 4h EMA20
   (replaces Fix #5 slope-based; position more robust with larger sample)

Performance (BTC full year): estimated +$380 (vs +$285 v2.8)
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

    # v2.5 state machine fixes (CHAMPION)
    sm_fix_1_htf_confirm: bool = False
    sm_fix_2_bear_streak: bool = True
    sm_fix_2_streak_threshold: int = 2
    sm_fix_3_extreme_low: bool = True
    sm_fix_3_high_lookback: int = 100
    sm_fix_3_extreme_pct: float = 0.05

    # v2.6 Fix #4 (kept off)
    sm_fix_4_bull_confirm: bool = False
    sm_fix_4_bear_confirm: bool = False

    # === v2.9: FIX #7 POSITION-BASED COUNTER-TREND BULL (CHAMPION) ===
    # BULL 2x size when 4h close position <= threshold vs 4h EMA20
    bull_countertrend_enabled: bool = True
    bull_countertrend_use_position: bool = True   # NEW v2.9: True=Fix#7 (position), False=Fix#5 (slope)
    bull_countertrend_max_close_pct: float = 0.0  # NEW v2.9: max % close above EMA (0 = must be below)
    # Legacy Fix #5 slope params (retained if use_position=False)
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5
    # Common
    bull_countertrend_tp_pct: float = 0.012        # keep standard TP
    bull_countertrend_size_mult: float = 2.0       # 2x amplify

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
