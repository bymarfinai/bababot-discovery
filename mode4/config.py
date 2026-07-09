"""
Mode4 Config — Trend-Following bot (hedge for Mode3).

Filosofi: Kebalikan Mode3.
- Mode3 (mean-reversion): reject VAH/VAL/EMA → bet balik
- Mode4 (trend-following): break EMA with momentum → bet lanjut
"""
from dataclasses import dataclass


@dataclass
class Mode4Config:
    # Common
    ema_period: int = 20
    startup_warmup_candles: int = 21
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # Trend-following TP/SL
    tp_pct: float = 0.010   # 1.0% — bigger reward for trending
    sl_pct: float = 0.005   # 0.5% — tighter risk

    # Volume filter (institutional participation confirms trend)
    volume_window: int = 20
    min_volume_ratio: float = 1.5

    # Slope filter — REQUIRE trending (opposite of Mode3)
    min_slope_pct: float = 0.010  # 1.0% — market must be trending
    slope_window: int = 20

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
