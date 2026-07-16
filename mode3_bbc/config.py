"""Mode3 BBC Config — Bull Bear Continuation variant.

CHECKPOINT v1.0 (2026-07-14): Winning config discovered via sweep exploration.
v1.2 (2026-07-14): No-phantom exits (level fill for both wick and closed modes).
v1.3 (2026-07-15): Add fixed SL % override — sl_pct / sideways_sl_pct.
"""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # ---- Take-profit ----
    tp_pct: float = 0.010
    sideways_tp_pct: float = 0.008
    bear_tp_pct: float = 0.0

    # ---- Stop-loss ----
    # If > 0, override wick-based SL with fixed % below (LONG) / above (SHORT) entry.
    # If 0, use wick-based SL (default: MTF 15m low/high, else bar wick).
    sl_pct: float = 0.0                 # BULL/BEAR fixed SL
    sideways_sl_pct: float = 0.0        # SIDEWAYS fixed SL
    bear_sl_pct: float = 0.0            # BEAR-specific override (0 = use sl_pct)

    # ---- Exit style ----
    use_wick_exit: bool = True

    # ---- Capital & fees ----
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # ---- BULL entry ----
    bull_mtf_15m_enabled: bool = True
    bull_body_ratio_min: float = 0.7

    # BULL optional experiments (default off)
    bull_poc_entry_enabled: bool = False
    bull_poc_max_distance_pct: float = 0.02
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

    # ---- BEAR entry ----
    bear_mtf_15m_enabled: bool = True
    bear_body_ratio_min: float = 0.6

    # ---- SIDEWAYS entry ----
    sideways_mtf_15m_enabled: bool = True
    sideways_body_ratio_min: float = 0.6

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct

    def get_bear_sl_pct(self) -> float:
        return self.bear_sl_pct if self.bear_sl_pct > 0 else self.sl_pct
