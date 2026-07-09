"""
Mode3 Config v1.2 - added MTF 15m confirmation for SIDEWAYS EMA_INVALIDATION.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51
    tp_pct: float = 0.003
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005
    sideways_ema_distance_cap: float = 0.003
    chop_window: int = 20
    chop_max_crossings: int = 4
    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5
    bull_mtf_15m_entry: bool = True
    sideways_ema_invalidation: bool = True
    sideways_ema_invalidation_tolerance: float = 0.0
    sideways_ema_invalidation_delay: int = 0
    # v1.2: MTF 15m confirmation for SIDEWAYS invalidation
    sideways_ema_invalidation_mtf_15m: bool = False

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
