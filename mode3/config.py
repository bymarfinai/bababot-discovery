"""
Mode3 Config - all parameters centralized.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    # VA (v0.19)
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0

    # EMA
    ema_period: int = 20

    # TP (v0.11)
    tp_pct: float = 0.006

    # Position sizing (v0.21)
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0

    # Trading costs (v0.21)
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # Startup (v0.19)
    startup_warmup_candles: int = 51

    # v0.24: SIDEWAYS distance filter
    # Block SIDEWAYS entry if |close - EMA20| / EMA20 > sideways_ema_distance_cap
    # Rationale: deep counter-trend = market trending, mean reversion melawan momentum
    sideways_ema_distance_cap: float = 0.005  # 0.5%

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
