"""Mode3 BBC Config — minimal config for Bull Bear Continuation variant."""
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

    # Opsi B v2: structural retest to broken swing high
    bull_wait_retest_enabled: bool = False
    bull_retest_swing_lookback: int = 20
    bull_retest_tolerance_pct: float = 0.003
    bull_retest_max_bars: int = 5
    bull_retest_max_ema_dist_pct: float = 0.003  # legacy

    # Opsi C: swing high break as trigger
    bull_use_swing_break: bool = False
    bull_swing_lookback: int = 20

    # Opsi D: 2.6 support bounce (video-inspired)
    # Level = swing_low + range/2.6 (shallow retracement zone ~38.5% from bottom)
    # BULL entry when bar wick touches level AND close reclaims AND bullish.
    bull_use_26_support: bool = False
    bull_26_lookback: int = 50
    bull_26_ratio: float = 2.6
    bull_26_tolerance_pct: float = 0.003  # touch tolerance around level

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
