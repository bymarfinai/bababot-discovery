"""
config.py — Mode 4 Parameter Constants
========================================
Semua parameter di sini di-default sesuai Design Doc v1.0.
Parameter yang di-sweep di backtest akan di-override via kwargs saat runtime.

Grouping:
- Group A: Volume Profile
- Group B: Structure Detection
- Group C: Tier 1 Classifier
- Group D: Entry & Exit
- Group E: Risk Sizing
"""

from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Mode4Config:
    # ============================================================
    # Group A — Volume Profile (see Design Doc §14.1 Group A)
    # ============================================================
    vp_window_4h: int = 20          # 4h candles for VP window
    vp_window_1d: int = 20          # 1d candles for VP window
    vp_window_1w: int = 12          # 1w candles for VP window
    vp_num_bins: int = 50           # Price bins resolution
    value_area_pct: float = 0.70    # Standard Steidlmayer
    vp_recompute_freq_4h: int = 1   # Every N new 4h candle
    vp_min_va_atr_ratio: float = 1.0  # Sanity: VAH-VAL >= 1×ATR

    # ============================================================
    # Group B — Structure Detection (§14.1 Group B)
    # ============================================================
    swing_lookback_1h: int = 3      # N-bar swing on 1h
    swing_lookback_4h: int = 5      # N-bar swing on 4h
    equal_level_tolerance: float = 0.001    # 0.1% price tolerance
    equal_level_min_distance: int = 5       # Min candles between equal levels
    swing_confirmed_after_bars: int = 3     # Delay before swing confirmed

    # ============================================================
    # Group C — Tier 1 Classifier (§7.2 & §14.1 Group C)
    # ============================================================
    sweep_score_threshold: float = 0.65
    breakout_score_threshold: float = 0.70

    # Sweep score component weights (must sum to 1.0)
    sweep_w_wick_body: float = 0.30
    sweep_w_close_back: float = 0.30
    sweep_w_volume: float = 0.25
    sweep_w_speed: float = 0.15

    # Breakout score component weights
    breakout_w_sustained: float = 0.30
    breakout_w_volume_prog: float = 0.25
    breakout_w_body_dom: float = 0.25
    breakout_w_bos_confirm: float = 0.20

    # Sweep indicator thresholds
    sweep_wick_body_ratio: float = 1.5
    sweep_volume_multiplier: float = 2.0
    sweep_body_min_pct_of_price: float = 0.0001  # Avoid div-by-zero

    # Classification window
    classification_window_candles: int = 5

    # Volume signature
    volume_avg_lookback: int = 20
    volume_spike_multiplier: float = 3.0
    volume_drop_multiplier: float = 0.8

    # Breakout sustained close
    breakout_min_sustained_candles: int = 2
    breakout_body_dominance_min: float = 0.6

    # ============================================================
    # Group D — Entry & Exit (§9-12, §14.1 Group D)
    # ============================================================
    # Retracement target (Zona 2.6 = 0.382)
    retracement_target: float = 0.382
    retracement_fallback_1: float = 0.5
    retracement_fallback_2: float = 0.618  # OTE upper
    retracement_fallback_3: float = 0.79   # OTE lower / invalidation

    # SL buffers (× ATR)
    sl_buffer_4a_atr: float = 0.3
    sl_buffer_4b_atr: float = 0.15

    # TP split ratios (must sum to 1.0)
    tp1_split_pct: float = 0.50
    tp2_split_pct: float = 0.30
    tp3_split_pct: float = 0.20

    # TP multipliers (measured move via Fib extension)
    tp2_multiplier: float = 1.618
    tp3_multiplier: float = 2.618

    # Time stops (1h candles)
    time_stop_4a_candles: int = 48   # 2 days
    time_stop_4b_candles: int = 12   # 12 hours

    # Setup lifetimes (candles from Tier 1 trigger)
    setup_lifetime_4a: int = 24      # 1 day
    setup_lifetime_4b: int = 8       # 8 hours

    # BOS/CHoCH confirmation windows
    bos_confirm_window_4a: int = 10
    choch_confirm_window_4b: int = 5

    # Minimum RR requirements
    min_rr_4a: float = 1.5
    min_rr_4b: float = 2.0

    # Rejection candle detection
    rejection_wick_body_ratio: float = 1.5
    rejection_volume_multiplier: float = 1.2

    # ============================================================
    # Group E — Risk Sizing (§13, §14.1 Group E)
    # ============================================================
    risk_pct_4a: float = 0.010       # 1.0% per trade
    risk_pct_4b: float = 0.0075      # 0.75% per trade
    max_concurrent_mode4_positions: int = 3
    max_positions_per_symbol: int = 1
    portfolio_risk_cap_pct: float = 0.05  # 5% total across Mode 3+4

    # Regime-aware size multipliers
    size_mult_4a_bos_strong: float = 1.0     # BOS score > 0.85
    size_mult_4a_bos_moderate: float = 0.7   # BOS score 0.70-0.85
    size_mult_4b_equal_highs: float = 1.0
    size_mult_4b_swing_4h: float = 0.8
    size_mult_recent_losses: float = 0.5     # 3+ losses in last 5 trades
    size_mult_recent_wins: float = 0.8       # 4+ wins in last 5 trades

    # Liquidity level weight scores (§7.2.1)
    weight_equal_hl: float = 1.0
    weight_swing_4h: float = 0.9
    weight_vah_val: float = 0.85
    weight_pdh_pdl: float = 0.8
    weight_session_hl: float = 0.7
    weight_swing_1h: float = 0.6
    weight_round_number: float = 0.5

    # Sub-4B minimum swept level quality (§10.2 Kondisi 4B-2)
    min_swept_level_weight_for_4b: float = 0.7

    # ============================================================
    # Session UTC times (§7.2.1)
    # ============================================================
    session_asia_start_utc: int = 0       # 00:00 UTC
    session_asia_end_utc: int = 8         # 08:00 UTC
    session_london_start_utc: int = 7     # 07:00 UTC
    session_london_end_utc: int = 16      # 16:00 UTC
    session_ny_start_utc: int = 13        # 13:00 UTC
    session_ny_end_utc: int = 22          # 22:00 UTC

    # ============================================================
    # Meta
    # ============================================================
    atr_period: int = 14
    slippage_pct: float = 0.001           # 0.1% for backtest
    fee_taker_pct: float = 0.00075        # Binance default

    # v2 flag: Tier 2 SMT disabled in v1
    enable_tier2_smt: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging and backtest reproducibility."""
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def validate(self) -> None:
        """Sanity check config on load. Raises AssertionError."""
        # Sweep weights sum to 1.0
        sweep_sum = (self.sweep_w_wick_body + self.sweep_w_close_back +
                     self.sweep_w_volume + self.sweep_w_speed)
        assert abs(sweep_sum - 1.0) < 1e-6, f"Sweep weights sum={sweep_sum}, must be 1.0"

        # Breakout weights sum to 1.0
        bo_sum = (self.breakout_w_sustained + self.breakout_w_volume_prog +
                  self.breakout_w_body_dom + self.breakout_w_bos_confirm)
        assert abs(bo_sum - 1.0) < 1e-6, f"Breakout weights sum={bo_sum}, must be 1.0"

        # TP splits sum to 1.0
        tp_sum = self.tp1_split_pct + self.tp2_split_pct + self.tp3_split_pct
        assert abs(tp_sum - 1.0) < 1e-6, f"TP splits sum={tp_sum}, must be 1.0"

        # Value area pct sane
        assert 0.5 <= self.value_area_pct <= 0.9, f"value_area_pct={self.value_area_pct}"

        # Thresholds in [0, 1]
        assert 0.0 <= self.sweep_score_threshold <= 1.0
        assert 0.0 <= self.breakout_score_threshold <= 1.0

        # Portfolio risk cap sane
        assert 0.0 < self.portfolio_risk_cap_pct <= 0.20


# Default instance for import convenience
DEFAULT_CONFIG = Mode4Config()
DEFAULT_CONFIG.validate()


__all__ = ["Mode4Config", "DEFAULT_CONFIG"]
