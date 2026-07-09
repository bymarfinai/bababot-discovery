"""
Mode3 Config v2.3 - added TRAP tool (HTF context contrarian entries).
"""
from dataclasses import dataclass


@dataclass
class Mode3Config:
    va_window: int = 50
    va_percentile_high: float = 85.0
    va_percentile_low: float = 15.0
    ema_period: int = 20
    startup_warmup_candles: int = 51

    tp_pct: float = 0.003
    capital_usd: float = 100.0
    entry_usd: float = 10.0
    leverage: float = 50.0
    fee_pct_roundtrip: float = 0.001
    slippage_pct: float = 0.0005

    sideways_ema_distance_cap: float = 0.003
    sideways_ema_invalidation: bool = True
    sideways_ema_invalidation_tolerance: float = 0.0015
    sideways_mtf_15m_entry: bool = True
    sideways_tp_pct: float = 0.007
    sideways_max_slope_pct: float = 0.018
    sideways_slope_window: int = 20

    chop_window: int = 20
    chop_max_crossings: int = 4

    bull_volume_window: int = 20
    bull_min_volume_ratio: float = 1.5
    bull_mtf_15m_entry: bool = True
    bull_use_rr_tp: bool = False
    bull_rr_ratio: float = 1.0

    bear_mtf_15m_entry: bool = True

    # === v2.3: TRAP TOOL ===
    # Contrarian entry based on HTF (4h) rejection at VAH/VAL
    trap_enabled: bool = False           # Toggle TRAP tool
    trap_lookback_4h: int = 3            # How many recent 4h bars to check for rejection
    trap_zone_tolerance: float = 0.002   # 4h VAH/VAL zone tolerance (0.2%)
    trap_tp_pct: float = 0.012           # TRAP TP (fixed for simplicity)
    trap_use_1h_va_tp: bool = False      # If True, TP at 1h VAL/VAH instead of fixed
    trap_priority_over_state: bool = True  # If True, TRAP overrides mode3 state entries

    def notional(self) -> float:
        return self.entry_usd * self.leverage

    def total_cost_pct(self) -> float:
        return self.fee_pct_roundtrip + self.slippage_pct
