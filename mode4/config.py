"""
Mode4 Config — Trend-Following bot with configurable improvements.
"""
from dataclasses import dataclass


@dataclass
class Mode4Config:
    ema_period: int = 20
    startup_warmup_candles: int = 30
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # Fixed TP/SL (baseline)
    tp_pct: float = 0.010
    sl_pct: float = 0.005

    # Volume filter
    volume_window: int = 20
    min_volume_ratio: float = 1.5

    # Slope filter
    min_slope_pct: float = 0.010
    slope_window: int = 20

    # === IMPROVEMENTS (all off by default) ===

    # 1. Multi-candle confirmation
    confirmation_bars: int = 1  # 1 = single candle (default), 2-3 = require N bars above/below EMA

    # 2. Higher-timeframe (4h) filter
    use_htf_filter: bool = False
    htf_ema_period: int = 20  # 4h EMA20 for trend confirmation

    # 3. ATR-based SL
    use_atr_sl: bool = False
    atr_period: int = 14
    atr_sl_mult: float = 1.5  # SL distance = ATR × this

    # 4. Trailing stop
    use_trailing_stop: bool = False
    trail_activation_pct: float = 0.005  # activate trailing after price moves this much
    trail_distance_pct: float = 0.003  # trail distance behind peak

    # 5. Break of Structure (BOS) entry
    use_bos_entry: bool = False
    bos_window: int = 20  # look back N bars for swing highs/lows

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
