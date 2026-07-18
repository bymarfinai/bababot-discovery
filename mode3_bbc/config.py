"""Mode3 BBC Config — v2.5 CLEAN.

Cleaned: removed 4H directional filter (tested, didn't improve WR/PnL).
Kept: trailing EMA (v2.4), direct transition (v2.2), body ratio tuning (v2.3).

Best configs discovered:
  EMA7 TP1.3% SL1.3% → WR 65.4%, PnL $6,060 (max PnL)
  EMA7 TP1.0% SL1.3% → WR 72.0%, PnL $5,344 (high WR)
  EMA7 TP0.9% SL1.3% → WR 74.7%, PnL $5,197 (balanced)
  EMA20 TP1.3% SL1.3% → WR 66.6%, PnL $3,918 (conservative)
"""
from dataclasses import dataclass

def preset_a() -> dict:
    return dict(tp_pct=0.013, sl_pct=0.020, bear_tp_pct=0.015, bear_sl_pct=0.020,
                sideways_body_ratio_min=0.6, sideways_tp_pct=0.015)
def preset_b() -> dict:
    return dict(tp_pct=0.013, sl_pct=0.013,
                sideways_body_ratio_min=0.6, sideways_tp_pct=0.015)
def preset_c() -> dict:
    return dict(tp_pct=0.010, sl_pct=0.008, bear_tp_pct=0.008, bear_sl_pct=0.008,
                sideways_body_ratio_min=0.6, sideways_tp_pct=0.015)
def preset_d() -> dict:
    return dict(tp_pct=0.040, sl_pct=0.013,
                sideways_body_ratio_min=0.6, sideways_tp_pct=0.015)

@dataclass
class Mode3BBCConfig:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.013
    sideways_tp_pct: float = 0.015
    bear_tp_pct: float = 0.0

    sl_pct: float = 0.013
    sideways_sl_pct: float = 0.0
    bear_sl_pct: float = 0.0

    trail_to_be_trigger_pct: float = 0.0
    sideways_trail_to_be_trigger_pct: float = 0.0
    use_wick_exit: bool = True

    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    bull_mtf_15m_enabled: bool = True
    bull_body_ratio_min: float = 0.5
    bull_poc_entry_enabled: bool = False
    bull_poc_max_distance_pct: float = 0.02
    bull_wait_retest_enabled: bool = False
    bull_retest_swing_lookback: int = 20
    bull_retest_tolerance_pct: float = 0.003
    bull_retest_max_bars: int = 5
    bull_retest_max_ema_dist_pct: float = 0.003
    bull_use_swing_break: bool = False
    bull_swing_lookback: int = 20
    bull_use_26_support: bool = False
    bull_26_lookback: int = 50
    bull_26_ratio: float = 2.6
    bull_26_tolerance_pct: float = 0.003

    bear_mtf_15m_enabled: bool = True
    bear_body_ratio_min: float = 0.6

    sideways_mtf_15m_enabled: bool = True
    sideways_body_ratio_min: float = 0.6
    sideways_ema_filter_enabled: bool = False
    sideways_min_sl_dist_pct: float = 0.0
    sideways_dual_mode_enabled: bool = False
    sideways_detector_size_ratio: float = 0.1

    sideways_poc_breakout_enabled: bool = False
    sideways_poc_body_ratio_min: float = 0.5

    direct_transition_enabled: bool = True

    # v2.4: trailing EMA exit (kept — useful for sweep)
    trailing_ema_enabled: bool = False
    trailing_ema_period: int = 7
    trailing_ema_min_bars: int = 1
    trailing_ema_max_tp_pct: float = 0.0

    def notional(self) -> float:
        return self.entry_usd * self.leverage
    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct
    def get_bear_sl_pct(self) -> float:
        return self.bear_sl_pct if self.bear_sl_pct > 0 else self.sl_pct
