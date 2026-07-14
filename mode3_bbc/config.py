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
    tp_pct: float = 0.012       # BULL/BEAR TP
    sideways_tp_pct: float = 0.003

    # Capital & fees
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
