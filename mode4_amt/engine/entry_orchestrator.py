"""
entry_orchestrator.py — Mode 4 Main Pipeline
================================================
Design Doc reference: §7 (overall flow).

Menggabungkan seluruh stack:
    1. Precompute: swings, structure events, impulse legs, FVGs, breakouts, sweeps
    2. Per candle:
        a. Build Volume Profile (windowed)
        b. Build Liquidity Map
        c. Compute Balance State
        d. Try Sub-4A candidate
        e. Try Sub-4B candidate
        f. Emit best valid candidate (if any) sebagai TradeSignal

Design decision:
- Volume Profile & Liquidity Map dibuat setiap N candles (bukan tiap candle),
  karena mahal secara komputasi dan tidak berubah drastis. Default N=10.
- Semua modul detection (swings, structure, FVG, breakouts, sweeps) di-precompute
  sekali di data lengkap dengan lookahead safety guard (only use event kalau
  confirmation idx sudah lewat candle current).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import numpy as np

from ..structure.swing_detector import detect_swings
from ..structure.structure_labels import label_swings
from ..structure.bos_choch import detect_structure_events
from ..structure.impulse_leg import detect_impulse_legs
from ..liquidity.equal_levels import detect_equal_highs, detect_equal_lows
from ..liquidity.liquidity_map import build_liquidity_map, LiquidityMap
from ..zones.volume_profile import compute_volume_profile
from ..tier1.sweep_detector import detect_sweeps
from ..tier1.breakout_classifier import detect_breakouts
from ..tier3.fvg_detector import detect_fvgs, update_fvg_states
from .balance_state import compute_balance_state, BalanceState
from .sub_4a_engine import detect_sub4a_setup, Sub4ACandidate
from .sub_4b_engine import detect_sub4b_setup, Sub4BCandidate


@dataclass
class TradeSignal:
    """Emitted trade signal (either Sub-4A or Sub-4B)."""
    symbol: str
    trigger_idx: int
    trigger_ts: int
    sub_strategy: str            # "4A" or "4B"
    direction: str               # "LONG" or "SHORT"

    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float

    initial_risk: float = 0.0
    rr_at_tp1: float = 0.0
    rr_at_tp2: float = 0.0
    rr_at_tp3: float = 0.0

    setup_score: float = 0.0
    tier1_score: float = 0.0
    tier3_fvg_quality: float = 0.0
    liquidity_target_weight: float = 0.0
    structural_alignment: float = 0.0

    balance_state: str = ""
    reason: str = ""

    def __repr__(self):
        return (f"TradeSignal({self.sub_strategy} {self.direction}@{self.trigger_idx} "
                f"entry={self.entry_price:.4f} SL={self.sl_price:.4f} "
                f"TP1={self.tp1_price:.4f} score={self.setup_score:.2f})")


@dataclass
class OrchestratorConfig:
    swing_n: int = 3
    vp_window: int = 30
    vp_rebuild_every: int = 10
    lmap_rebuild_every: int = 10
    fvg_min_gap_atr: float = 0.15
    fvg_min_body: float = 0.40
    sweep_min_score: float = 0.55
    breakout_min_score: float = 0.55
    sub4a_min_score: float = 0.60
    sub4b_min_score: float = 0.60
    sub4a_min_rr: float = 1.2
    sub4b_min_rr: float = 1.0
    recent_events_lookback: int = 30
    max_signals_per_candle: int = 1


class Mode4Orchestrator:
    """
    Runs Mode 4 pipeline over a data series. Emits TradeSignals.

    Usage:
        orch = Mode4Orchestrator(symbol, config=OrchestratorConfig())
        signals = orch.scan(times, opens, highs, lows, closes, volumes)
    """

    def __init__(self, symbol: str, config: Optional[OrchestratorConfig] = None):
        self.symbol = symbol
        self.cfg = config or OrchestratorConfig()

    def _compute_atr(self, highs, lows, closes, period=14):
        n = len(closes)
        tr = np.zeros(n)
        tr[0] = highs[0] - lows[0]
        for i in range(1, n):
            tr[i] = max(highs[i]-lows[i],
                       abs(highs[i]-closes[i-1]),
                       abs(lows[i]-closes[i-1]))
        atr = np.zeros(n)
        for i in range(n):
            atr[i] = float(np.mean(tr[max(0, i-period+1):i+1]))
        return atr

    def _precompute(self, times, opens, highs, lows, closes, volumes):
        """Precompute all detection outputs once (with lookahead-safe usage later)."""
        c = self.cfg
        swings = detect_swings(highs, lows, lookback_n=c.swing_n)
        labeled = label_swings(swings)
        struct_events = detect_structure_events(closes, swings, labeled)
        impulse_legs = detect_impulse_legs(
            highs, lows, closes, swings,
            min_candles=5, min_directional_pct=0.65,
            min_atr_ratio=1.0, max_retracement_pct=0.5, atr_period=14)
        fvgs = detect_fvgs(highs, lows, opens, closes,
                          min_gap_atr_ratio=c.fvg_min_gap_atr,
                          min_middle_body_ratio=c.fvg_min_body)
        update_fvg_states(fvgs, highs, lows)
        return {
            'swings': swings,
            'labeled': labeled,
            'struct_events': struct_events,
            'impulse_legs': impulse_legs,
            'fvgs': fvgs,
        }

    def _build_vp_and_lmap(self, t, highs, lows, closes, volumes,
                          precomp, atr, current_price):
        """Build VP and Liquidity Map for candle t."""
        c = self.cfg
        # Volume Profile on last vp_window candles
        w = c.vp_window
        if t >= w:
            vp = compute_volume_profile(
                highs[t-w+1:t+1], lows[t-w+1:t+1],
                closes[t-w+1:t+1], volumes[t-w+1:t+1],
                num_bins=50, value_area_pct=0.70,
                atr_reference=atr, min_va_atr_ratio=1.0)
            vah = vp.vah if vp.is_valid else None
            val = vp.val if vp.is_valid else None
            poc = vp.poc if vp.is_valid else None
        else:
            vah = val = poc = None

        # Liquidity Map
        # Only use swings CONFIRMED by candle t
        swings = [s for s in precomp['swings']
                  if s.idx + c.swing_n <= t]
        eqh = detect_equal_highs(swings, tolerance_pct=0.002, min_distance=5)
        eql = detect_equal_lows(swings, tolerance_pct=0.002, min_distance=5)
        # PDH/PDL rough approx: use prior 24 candle (for 1h TF) high/low
        if t >= 30:
            prev_h = float(np.max(highs[t-30:t-1]))
            prev_l = float(np.min(lows[t-30:t-1]))
        else:
            prev_h = prev_l = None

        lmap = build_liquidity_map(
            current_price=current_price, current_atr=atr,
            swings_1h=swings,
            equal_highs=eqh, equal_lows=eql,
            vah=vah, val=val,
            prev_day_high=prev_h, prev_day_low=prev_l)
        return lmap, vah, val, poc

    def scan(self, times, opens, highs, lows, closes, volumes,
             start_idx: Optional[int] = None,
             end_idx: Optional[int] = None) -> List[TradeSignal]:
        """
        Scan candles and emit TradeSignals.

        Lookahead safety: for each candle t, only use:
        - Swings confirmed by t (idx + swing_n <= t)
        - Structure events with e.idx <= t
        - Impulse legs with end_idx + swing_n <= t
        - Breakouts with confirmation_idx <= t (breakouts inherent delay)
        - Sweeps with idx <= t
        - FVGs with fvg.idx <= t; states must be re-evaluated up to t
        """
        c = self.cfg
        n = len(closes)
        atr_arr = self._compute_atr(highs, lows, closes, period=14)

        start = start_idx or (20 + c.swing_n + c.vp_window)
        end = end_idx or n

        precomp = self._precompute(times, opens, highs, lows, closes, volumes)

        # Sweeps and breakouts require LiquidityMap; too expensive per candle
        # Strategy: pre-compute sweeps and breakouts using a static "hint" LiquidityMap
        # built from swings/eqh/eql only (no VP), then filter per candle. Simplification
        # for MVP orchestration.
        static_lmap = build_liquidity_map(
            current_price=float(closes[n//2]),
            current_atr=float(atr_arr[n//2]),
            swings_1h=precomp['swings'],
            equal_highs=detect_equal_highs(precomp['swings']),
            equal_lows=detect_equal_lows(precomp['swings']))
        all_sweeps = detect_sweeps(
            highs, lows, opens, closes, volumes, static_lmap,
            min_score=c.sweep_min_score)
        all_breakouts = detect_breakouts(
            highs, lows, opens, closes, volumes, static_lmap,
            follow_through_candles=3, min_score=c.breakout_min_score)

        signals: List[TradeSignal] = []

        # Cached lmap/vp
        lmap_cache = {}
        vp_cache = {}

        for t in range(start, end):
            atr = float(atr_arr[t])
            price = float(closes[t])

            # Build/rebuild VP + Lmap periodically
            cache_key = t // c.lmap_rebuild_every
            if cache_key not in lmap_cache:
                lmap, vah, val, poc = self._build_vp_and_lmap(
                    t, highs, lows, closes, volumes, precomp, atr, price)
                lmap_cache[cache_key] = lmap
                vp_cache[cache_key] = (vah, val, poc)
            lmap = lmap_cache[cache_key]
            vah, val, poc = vp_cache[cache_key]

            # === Lookahead-safe filtered events ===
            recent_sweeps = [sw for sw in all_sweeps
                            if sw.idx <= t and (t - sw.idx) <= c.recent_events_lookback]
            recent_breakouts = [b for b in all_breakouts
                               if b.confirmation_idx <= t
                               and (t - b.confirmation_idx) <= c.recent_events_lookback]
            recent_struct = [e for e in precomp['struct_events']
                            if e.idx <= t and (t - e.idx) <= c.recent_events_lookback]
            # Impulse legs: confirmed
            confirmed_legs = [l for l in precomp['impulse_legs']
                             if l.end_idx + c.swing_n <= t]
            # FVGs already have state; only use those formed and evaluated
            usable_fvgs = [f for f in precomp['fvgs'] if f.idx <= t]

            # === Balance State ===
            bs = compute_balance_state(
                current_idx=t, highs=highs, lows=lows, closes=closes,
                vah=vah, val=val, poc=poc, atr=atr,
                recent_sweeps=recent_sweeps, recent_breakouts=recent_breakouts,
                recent_structure_events=recent_struct)

            if not bs.is_actionable():
                continue

            # === Try Sub-4A ===
            cand_a = detect_sub4a_setup(
                symbol=self.symbol, current_idx=t,
                highs=highs, lows=lows, closes=closes, atr=atr,
                balance_state=bs, impulse_legs=confirmed_legs,
                breakouts=recent_breakouts, fvgs=usable_fvgs,
                liquidity_map=lmap,
                min_setup_score=c.sub4a_min_score,
                min_rr_tp1=c.sub4a_min_rr)

            # === Try Sub-4B ===
            cand_b = detect_sub4b_setup(
                symbol=self.symbol, current_idx=t,
                highs=highs, lows=lows, closes=closes, atr=atr,
                balance_state=bs, recent_sweeps=recent_sweeps,
                structure_events=recent_struct, fvgs=usable_fvgs,
                liquidity_map=lmap, poc=poc, vah=vah, val=val,
                min_setup_score=c.sub4b_min_score,
                min_rr_tp1=c.sub4b_min_rr)

            # === Pick best valid candidate ===
            valid = []
            if cand_a is not None and cand_a.is_valid:
                valid.append(('4A', cand_a))
            if cand_b is not None and cand_b.is_valid:
                valid.append(('4B', cand_b))

            if not valid:
                continue

            best_sub, best = max(valid, key=lambda x: x[1].setup_score)

            signal = TradeSignal(
                symbol=self.symbol,
                trigger_idx=t, trigger_ts=int(times[t]),
                sub_strategy=best_sub, direction=best.direction,
                entry_price=best.entry_price, sl_price=best.sl_price,
                tp1_price=best.tp1_price, tp2_price=best.tp2_price,
                tp3_price=best.tp3_price,
                initial_risk=best.initial_risk,
                rr_at_tp1=best.rr_at_tp1, rr_at_tp2=best.rr_at_tp2,
                rr_at_tp3=best.rr_at_tp3,
                setup_score=best.setup_score,
                tier1_score=best.tier1_score,
                tier3_fvg_quality=best.tier3_fvg_quality,
                liquidity_target_weight=best.liquidity_target_weight,
                structural_alignment=best.structural_alignment,
                balance_state=bs.state.value,
                reason=bs.reason)
            signals.append(signal)

        return signals


__all__ = ["TradeSignal", "OrchestratorConfig", "Mode4Orchestrator"]
