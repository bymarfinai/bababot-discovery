"""
Mode3 Config v1.4 - final cleanup.

All params below are proven defaults. Removed:
- sideways_ema_invalidation_mtf_15m (proven useless — 15m close = 1h close at boundary)
- sideways_ema_invalidation_mtf_early_exit (proven bad — 15m break mostly noise)
- sideways_ema_invalidation_delay (proven bad — early SL hits when delayed)
- sideways_early_exit_tolerance (dead code)
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
    sideways_ema_invalidation_tolerance: float = 0.0015  # PROVEN: 0.15% sweet spot

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
