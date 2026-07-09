"""
Mode3 Config v2.8 CHAMPION — Fix #5 counter-trend BULL enhancement as default.

Champion config (BTC 1h):
- Fixed TP 1.2% (BULL/BEAR), 0.3% (SIDEWAYS)
- MTF 15m entry all tools
- Fix #2: BEAR streak switch to SIDEWAYS
- Fix #3: Extreme low (5%) switch to SIDEWAYS
- Fix #5: Counter-trend BULL 2x size when HTF slope < -0.5%

Performance (BTC full year): +$285.34 (vs +$233.31 v2.5)
2026 YTD: +$251.32 (vs +$193.14 v2.5)
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

    # === v2.8: FIX #5 COUNTER-TREND BULL (CHAMPION) ===
    bull_countertrend_enabled: bool = True         # CHAMPION ON
    bull_countertrend_slope_window: int = 20
    bull_countertrend_slope_threshold: float = -0.5  # CHAMPION -0.5%
    bull_countertrend_tp_pct: float = 0.012        # keep standard TP
    bull_countertrend_size_mult: float = 2.0       # CHAMPION 2x size

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
