"""
Mode3 Config v2.0 - final champion with SIDEWAYS breakthrough.

Proven config:
- BULL: volume 1.5x + MTF 15m entry (WR 91%)
- BEAR: pure 1h entry (no filter)
- SIDEWAYS: MTF 15m entry + TP 0.7% + tolerance 0.15% + slope 1.8%
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # Trading parameters
    tp_pct: float = 0.003                # BULL/BEAR: 0.3%
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # SIDEWAYS entry & exit
    sideways_ema_distance_cap: float = 0.003
    sideways_ema_invalidation: bool = True
    sideways_ema_invalidation_tolerance: float = 0.0015    # PROVEN: 0.15%
    sideways_mtf_15m_entry: bool = True                    # PROVEN: breakthrough
    sideways_tp_pct: float = 0.007                         # PROVEN: 0.7% (higher R:R)
    sideways_max_slope_pct: float = 0.018                  # PROVEN: 1.8% (skip trending)
    sideways_slope_window: int = 20

    # Global chop filter
    chop_window: int = 20
    chop_max_crossings: int = 4                            # PROVEN

    # BULL filters
    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5                     # PROVEN
    bull_mtf_15m_entry: bool = True                        # PROVEN

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
