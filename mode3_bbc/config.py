"""Mode3 BBC Config — minimal config for Bull Bear Continuation variant."""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.012
    sideways_tp_pct: float = 0.003
    bear_tp_pct: float = 0.0

    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # ---- BULL ----
    bull_poc_entry_enabled: bool = False
    bull_poc_max_distance_pct: float = 0.02

    bull_mtf_15m_enabled: bool = False
    bull_body_ratio_min: float = 0.0

    bull_wait_retest_enabled: bool = False
    bull_retest_swing_lookback: int = 20
    bull_retest_tolerance_pct: float = 0.003
    bull_retest_max_bars: int = 5
    bull_retest_max_ema_dist_pct: float = 0.003

    bull_use_swing_break: bool = False
    bull_swing_lookback: int = 20

    bull_use_26_support: bool = False
    bull_26_lookback: int = 50
    bull_26_ratio: float = 2.6
    bull_26_tolerance_pct: float = 0.003

    # ---- BEAR ----
    bear_mtf_15m_enabled: bool = False
    bear_body_ratio_min: float = 0.0

    # ---- SIDEWAYS ----
    # MTF 15m precision for SIDEWAYS entries.
    # SHORT: scan 4 sub-15m for h>=vah AND c<=vah pattern.
    # LONG:  scan 4 sub-15m for l<=val AND c>=val pattern.
    # If found: use 15m close as entry, 15m high/low as SL.
    # If not: BLOCK entry.
    sideways_mtf_15m_enabled: bool = False

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct
