"""
Mode3 Config - final v1.0 (session cleanup).

Only proven-working parameters kept.
Removed: trailing_sl, bull_confirmation_candle, bull_min_ema_distance,
         bull_disable_downtrend, bull_max_candle_range, bull_mtf_confirm,
         bull_mtf_strict, bear_min_volume, bear_max_volume, bear_mtf_entry.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    # Core mechanics
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # Trading parameters
    tp_pct: float = 0.003                     # PROVEN: 0.3% optimal
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # SIDEWAYS filter
    sideways_ema_distance_cap: float = 0.003  # PROVEN: 0.3% cap optimal

    # Chop filter (global, all tools)
    chop_window: int = 20
    chop_max_crossings: int = 4               # PROVEN: chop=4 optimal for 90d

    # BULL filters (only what works)
    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5        # PROVEN: block low-conviction fake breakouts
    bull_mtf_15m_entry: bool = True           # PROVEN: tight SL via 15m rejection candle

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
