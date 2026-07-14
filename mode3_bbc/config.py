"""Mode3 BBC Config — minimal config for Bull Bear Continuation variant.
All filter-related fields intentionally removed.
"""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.012
    sideways_tp_pct: float = 0.003

    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # POC bounce entry
    bull_poc_entry_enabled: bool = False
    bull_poc_max_distance_pct: float = 0.02

    # MTF 15m entry precision
    bull_mtf_15m_enabled: bool = False

    # Opsi A: body ratio filter
    bull_body_ratio_min: float = 0.0

    # Opsi B v2: STRUCTURAL retest to broken swing high (not EMA)
    # At trigger, save broken_level = swing high of past N bars
    # Wait bar N+1..N+K: bar low touches broken_level, close reclaims, bullish
    # Invalidated if close < broken_level (support failed)
    bull_wait_retest_enabled: bool = False
    bull_retest_swing_lookback: int = 20
    bull_retest_tolerance_pct: float = 0.003  # bar low within X% of broken_level
    bull_retest_max_bars: int = 5
    bull_retest_max_ema_dist_pct: float = 0.003  # legacy (unused in v2)

    # Opsi C: swing high break as trigger
    bull_use_swing_break: bool = False
    bull_swing_lookback: int = 20

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
