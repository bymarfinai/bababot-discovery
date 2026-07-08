"""
Mode3 Config — all parameters centralized.
Every rule number from BabaBot_Switcher_Spec_v0_21 lives here.
Zero magic numbers in any other file.
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    # =========================================================================
    # VA computation (spec §3.0, v0.19 locked — percentile-based)
    # =========================================================================
    va_window: int = 50                    # candle lookback
    va_percentile_high: float = 85.0       # VAH percentile
    va_percentile_low: float = 15.0        # VAL percentile

    # =========================================================================
    # EMA (spec §2.5, 6.2, 7.2)
    # =========================================================================
    ema_period: int = 20

    # =========================================================================
    # TP fixed 0.6% (spec §3.3 sideways, §6.3 BULL, §7.3 BEAR — v0.11)
    # =========================================================================
    tp_pct: float = 0.006                  # 0.6% profit target, all tools

    # =========================================================================
    # Position sizing (spec §11 v0.21)
    # =========================================================================
    capital_usd: float = 100.0
    entry_usd: float = 10.0                # 10% of capital
    leverage: float = 50.0

    # =========================================================================
    # Trading costs (spec §11 v0.21)
    # =========================================================================
    fee_pct_roundtrip: float = 0.001       # 0.10% (0.05% × 2 sides, market taker)
    slippage_pct: float = 0.0005           # 0.05%

    # =========================================================================
    # Startup (spec §12 v0.19)
    # =========================================================================
    startup_warmup_candles: int = 51       # va_window + 1

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
