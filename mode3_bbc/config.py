"""Mode3 BBC Config — Bull Bear Continuation variant.

═══════════════════════════════════════════════════════════════
CHECKPOINT v2.0 (2026-07-16)
═══════════════════════════════════════════════════════════════

Backtest: 4 pair (BTC/ETH/BNB/SOL), 1h TF, 925 days, wick exit, level fill (no phantom PnL).

PRESETS (BULL/BEAR TP×SL — choose via full sweep):

  Preset A — Max PnL at WR≥70%:
    BULL: TP 1.3% × SL 2.0% → WR 77.4%, PnL $1,325, Edge +16.8%
    BEAR: TP 1.5% × SL 2.0% → WR 72.2%, PnL $1,149, Edge +15.1%
    SW:   as-is → PnL ~$280
    Total: ~$2,754

  Preset B — Symmetric R:R 1:1 (DEFAULT):
    BULL: TP 1.3% × SL 1.3% → WR 70.8%, PnL $1,306, Edge +20.8%
    BEAR: TP 1.3% × SL 1.3% → WR 69.5%, PnL $1,121, Edge +19.5%
    SW:   as-is → PnL ~$280
    Total: ~$2,756

  Preset C — Max Edge (tightest):
    BULL: TP 1.0% × SL 0.8% → WR 70.0%, PnL $1,066, Edge +25.6%
    BEAR: TP 0.8% × SL 0.8% → WR 72.6%, PnL $721, Edge +22.6%
    SW:   as-is → PnL ~$280
    Total: ~$2,067

  Preset D — Max PnL (low WR, high R:R):
    BULL/BEAR: TP 4.0% × SL 1.3% → WR 42%, PnL $3,518
    SW:   body 0.5, TP 1.5% → PnL $283
    Total: ~$3,801

FIXED PARAMS (all presets):
  - use_wick_exit = True           (realistic limit/stop order sim)
  - bull_mtf_15m_enabled = True    (15m entry precision)
  - bear_mtf_15m_enabled = True
  - sideways_mtf_15m_enabled = True
  - bull_body_ratio_min = 0.7      (sweep candle filter)
  - bear_body_ratio_min = 0.6      (bearish sharp/impulsive)
  - sideways_body_ratio_min = 0.5  (v2.0 updated from 0.6)
  - sideways_tp_pct = 0.015        (SW TP 1.5%)
  - sideways_sl_pct = 0.0          (wick-based, keep)

KEY DISCOVERIES (v1.0→v2.0):
  - v1.2: phantom PnL bug fix (exit at LEVEL, not close price)
  - v1.3: fixed SL override (sl_pct) — enables TP×SL grid sweep
  - v1.4: move-to-BE trailing — REJECTED (kills trend winners)
  - v1.5: SW EMA filter — improves SW WR +12% but kills cascade
  - v1.6: SW dual-mode — works mechanically but baseline better
  - MTF 15m CRITICAL even with fixed SL (entry quality, not just SL)
  - BULL 100% winners had EMA rising during trade
  - SW 97% losers were counter-trend entries (essential for detection)
  - Funding rate impact ~3% ($82/925d) — manageable
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
    tp_pct: float = 0.013              # BULL TP 1.3%
    sideways_tp_pct: float = 0.015     # SW TP 1.5%
    bear_tp_pct: float = 0.0           # 0 = use tp_pct

    # ── Stop-loss (Preset B default) ──
    sl_pct: float = 0.013              # BULL SL 1.3%
    sideways_sl_pct: float = 0.0       # SW SL wick
    bear_sl_pct: float = 0.0           # 0 = use sl_pct

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
    sideways_body_ratio_min: float = 0.5     # v2.0: updated from 0.6
    sideways_ema_filter_enabled: bool = False
    sideways_min_sl_dist_pct: float = 0.0
    sideways_dual_mode_enabled: bool = False
    sideways_detector_size_ratio: float = 0.1

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct

    def get_bear_tp_pct(self) -> float:
        return self.bear_tp_pct if self.bear_tp_pct > 0 else self.tp_pct

    def get_bear_sl_pct(self) -> float:
        return self.bear_sl_pct if self.bear_sl_pct > 0 else self.sl_pct
