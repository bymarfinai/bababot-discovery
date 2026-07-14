"""Mode3 BBC Config — minimal config for Bull Bear Continuation variant.
All filter-related fields intentionally removed.
"""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    # Volume Area & EMA basics
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # TP configuration
    tp_pct: float = 0.012
    sideways_tp_pct: float = 0.003

    # Capital & fees
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # POC-strengthened BULL entry (opt-in)
    bull_poc_entry_enabled: bool = False
    bull_poc_max_distance_pct: float = 0.02

    # MTF 15m entry precision for BULL (opt-in)
    bull_mtf_15m_enabled: bool = False

    # Opsi A: BULL body strength filter (sweep vs BoS discrimination)
    # Body/range ratio must be >= threshold. Wicky sweep candles get filtered.
    # 0 = disabled. Typical values: 0.5-0.7.
    bull_body_ratio_min: float = 0.0

    # Opsi B: BULL wait-for-retest pattern (2-bar setup)
    # After EMA reclaim (candidate), wait for retest bar within N bars:
    # retest = pullback near EMA + bullish close.
    bull_wait_retest_enabled: bool = False
    bull_retest_max_ema_dist_pct: float = 0.003  # pullback allowed within 0.3% of EMA
    bull_retest_max_bars: int = 3  # discard candidate after N bars

    # Opsi C: BULL uses swing high break instead of EMA reclaim
    # Trigger: c > max(highs[bar-N:bar]) AND c > o
    bull_use_swing_break: bool = False
    bull_swing_lookback: int = 20

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
