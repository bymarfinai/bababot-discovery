"""Mode3 BBC Config — Bull Bear Continuation variant.

CHECKPOINT v1.0 (2026-07-14): Winning config discovered via sweep exploration.
Backtest 4 pair (BTC, ETH, BNB, SOL), 1h TF, 925 days:
  BULL:     582tr, WR 59.5%, PnL +$1,459
  BEAR:     564tr, WR 55.0%, PnL +$1,086
  SIDEWAYS: 1196tr, WR 48.3%, PnL +$386
  TOTAL:    +$2,931  (beats Champion mode3 +$2,604 by $327 / 12.5%)

Winning parameters (locked in as defaults):
  - tp_pct = 0.010                     (BULL/BEAR TP 1.0%, sweet spot for R:R 2:1)
  - sideways_tp_pct = 0.008            (SW TP 0.8%, cascade-optimal)
  - bull_mtf_15m_enabled = True        (15m entry precision, tighter SL)
  - bull_body_ratio_min = 0.7          (filter wicky sweep candles at EMA reclaim)
  - bear_mtf_15m_enabled = True        (15m entry precision for BEAR)
  - bear_body_ratio_min = 0.6          (BEAR sweet spot lower — bearish sharp/impulsive)
  - sideways_mtf_15m_enabled = True    (15m for VAH/VAL touch)
  - sideways_body_ratio_min = 0.6      (filter VAH/VAL sweep candles)
"""
from dataclasses import dataclass


@dataclass
class Mode3BBCConfig:
    # ---- Indicators & warmup ----
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    # ---- Take-profit (locked to winning config) ----
    tp_pct: float = 0.010              # BULL/BEAR TP (v1.0 winner: 1.0%)
    sideways_tp_pct: float = 0.008     # SW TP (v1.0 winner: 0.8%)
    bear_tp_pct: float = 0.0           # 0 = use tp_pct

    # ---- Exit style ----
    # Wick-based exit: TP/SL trigger on bar wick touch (realistic limit/stop order behavior).
    # When both TP and SL levels hit in same bar, SL wins (conservative pessimistic sim).
    # Legacy close-based exit if False.
    use_wick_exit: bool = True

    # ---- Capital & fees ----
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    # ---- BULL entry (locked to winning config) ----
    bull_mtf_15m_enabled: bool = True         # v1.0 winner
    bull_body_ratio_min: float = 0.7          # v1.0 winner (sweep candle filter)

    # BULL — optional expansions (default off, opt-in per experiment)
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

    # ---- BEAR entry (locked to winning config) ----
    bear_mtf_15m_enabled: bool = True         # v1.0 winner
    bear_body_ratio_min: float = 0.6          # v1.0 winner (BEAR lower than BULL)

    # ---- SIDEWAYS entry (locked to winning config) ----
    sideways_mtf_15m_enabled: bool = True     # v1.0 winner
    sideways_body_ratio_min: float = 0.6      # v1.0 winner (VAH/VAL sweep filter)

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct
