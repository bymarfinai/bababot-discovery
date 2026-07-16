"""Mode3 BBC Config — Bull Bear Continuation variant.

v1.4: Move-to-BE trailing.
v1.5 (2026-07-16): SW with-trend mean-reversion entry.
  - sideways_ema_filter_enabled: SHORT only below EMA, LONG only above EMA
  - sideways_min_sl_dist_pct: block entries with SL distance too tight
"""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.010
    sideways_tp_pct: float = 0.008
    bear_tp_pct: float = 0.0

    sl_pct: float = 0.0
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

    # ---- BULL ----
    bull_mtf_15m_enabled: bool = True
    bull_body_ratio_min: float = 0.7
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

    # ---- BEAR ----
    bear_mtf_15m_enabled: bool = True
    bear_body_ratio_min: float = 0.6

    # ---- SIDEWAYS ----
    sideways_mtf_15m_enabled: bool = True
    sideways_body_ratio_min: float = 0.6

    # With-trend mean-reversion filter (v1.5):
    # SHORT only when close < EMA (downtrend → revert from VAH)
    # LONG only when close > EMA (uptrend → revert from VAL)
    # Blocks counter-trend entries that cause 97% of losses
    sideways_ema_filter_enabled: bool = False

    # Minimum SL distance filter (v1.5):
    # Block entry if SL distance < threshold. Tight SL (<0.15%) has 14% WR.
    sideways_min_sl_dist_pct: float = 0.0

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct

    def get_bear_sl_pct(self) -> float:
        return self.bear_sl_pct if self.bear_sl_pct > 0 else self.sl_pct
