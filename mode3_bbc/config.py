"""Mode3 BBC Config — Bull Bear Continuation variant.

═══════════════════════════════════════════════════════════════
CHECKPOINT v2.0 (2026-07-16) + v2.1 POC Breakout
═══════════════════════════════════════════════════════════════
v2.1: SIDEWAYS POC breakout — trend-following entry at fair value break.
  Price breaks through POC = shift of control → enter with trend.
  POC SL → stays SIDEWAYS (intra-range, not boundary break).
  Only 1 position at a time (skip if already open).
"""
from dataclasses import dataclass


# ── Preset factories ──
def preset_a() -> dict:
    """Max PnL at WR≥70%. BULL TP1.3/SL2.0, BEAR TP1.5/SL2.0."""
    return dict(tp_pct=0.013, sl_pct=0.020, bear_tp_pct=0.015, bear_sl_pct=0.020,
                sideways_body_ratio_min=0.5, sideways_tp_pct=0.015)

def preset_b() -> dict:
    """Symmetric R:R 1:1. BULL/BEAR TP1.3/SL1.3."""
    return dict(tp_pct=0.013, sl_pct=0.013,
                sideways_body_ratio_min=0.5, sideways_tp_pct=0.015)

def preset_c() -> dict:
    """Max Edge (tightest). BULL TP1.0/SL0.8, BEAR TP0.8/SL0.8."""
    return dict(tp_pct=0.010, sl_pct=0.008, bear_tp_pct=0.008, bear_sl_pct=0.008,
                sideways_body_ratio_min=0.5, sideways_tp_pct=0.015)

def preset_d() -> dict:
    """Max PnL (low WR). BULL/BEAR TP4.0/SL1.3."""
    return dict(tp_pct=0.040, sl_pct=0.013,
                sideways_body_ratio_min=0.5, sideways_tp_pct=0.015)


@dataclass
class Mode3BBCConfig:
    # ── Indicators ──
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # ── Take-profit (Preset B default) ──
    tp_pct: float = 0.013
    sideways_tp_pct: float = 0.015
    bear_tp_pct: float = 0.0

    # ── Stop-loss (Preset B default) ──
    sl_pct: float = 0.013
    sideways_sl_pct: float = 0.0
    bear_sl_pct: float = 0.0

    # ── Trailing ──
    trail_to_be_trigger_pct: float = 0.0
    sideways_trail_to_be_trigger_pct: float = 0.0

    # ── Exit style ──
    use_wick_exit: bool = True

    # ── Capital ──
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # ── BULL entry ──
    bull_mtf_15m_enabled: bool = True
    bull_body_ratio_min: float = 0.7
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

    # ── BEAR entry ──
    bear_mtf_15m_enabled: bool = True
    bear_body_ratio_min: float = 0.6

    # ── SIDEWAYS entry ──
    sideways_mtf_15m_enabled: bool = True
    sideways_body_ratio_min: float = 0.5
    sideways_ema_filter_enabled: bool = False
    sideways_min_sl_dist_pct: float = 0.0
    sideways_dual_mode_enabled: bool = False
    sideways_detector_size_ratio: float = 0.1

    # ── SIDEWAYS POC breakout (v2.1) ──
    # Trend-following entry when price breaks through POC (fair value).
    # POC break UP + bullish candle → LONG. POC break DOWN + bearish → SHORT.
    # SL = candle wick (or fixed sideways_sl_pct). TP = sideways_tp_pct.
    # POC SL → stays SIDEWAYS (no state transition, intra-range trade).
    # Only fires if no position open (1 trade at a time).
    sideways_poc_breakout_enabled: bool = False
    sideways_poc_body_ratio_min: float = 0.5   # body ratio for POC breakout candle

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct

    def get_bear_sl_pct(self) -> float:
        return self.bear_sl_pct if self.bear_sl_pct > 0 else self.sl_pct
