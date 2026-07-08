"""
Mode3 Config - all parameters centralized.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    tp_pct: float = 0.006
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005
    startup_warmup_candles: int = 51
    sideways_ema_distance_cap: float = 0.005
    chop_window: int = 20
    chop_max_crossings: int = 6
    # v0.28: trailing SL (0 = disabled). Only tightens SL as position moves favorable.
    # LONG: SL = peak_high * (1 - trailing_sl_pct)
    # SHORT: SL = trough_low * (1 + trailing_sl_pct)
    trailing_sl_pct: float = 0.0

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
