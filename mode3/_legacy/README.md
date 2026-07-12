# Mode3 Legacy Features (Removed in v5.0)

Semua fitur di bawah ini pernah dibangun tapi terbukti tidak improve Champion Option A.
Dihapus dari codebase v5.0. Restore via `git checkout db0b5b2` (v4.4 final commit).

## Removed Features

### 1. CRS (Confirmed Rejection Short) — Fix #16
- Config: `crs_enabled`, `crs_lookback_4h_bars`, `crs_active_hours`, `crs_size_mult`, `crs_use_projection_tp`, `crs_projection_divisor`, `crs_skip_bull_hours`, `crs_regime_gate`, `crs_regime_max_slope`
- Reason: State coupling failure, PnL turun
- Test result: -$91

### 2. AMT Filter (skip mode)
- Removed toggle: `amt_skip_sw_above=true` / `amt_skip_bull_below=true`
- Reason: Amplify (bukan filter) yang works
- KEEP: `amt_enabled` + amp multipliers

### 3. AMT Smart Levels — Fix #17.1
- Config: `amt_smart_levels_enabled`, `amt_sw_above_use_vah_tp`, `amt_bull_near_vah_use_projection_tp`, `amt_projection_divisor`, `amt_bull_below_use_val_sl`
- Reason: Marginal +$3 impact
- Methods removed: `_apply_smart_tp_sw_short`, `_apply_smart_tp_bull`, `_apply_smart_sl_bull`

### 4. Wick Tolerance SL — Fix #19A
- Config: `bull_wick_tolerance_enabled`, `bull_wick_tolerance_pct`
- Reason: PnL turun -$75 (wider SL cost > wick save)

### 5. BULL BELOW VAL TP — Fix #19B
- Config: `bull_below_use_val_tp`
- Reason: Applied 1x setahun, tak berguna

### 6. Sweep Detector — Fix #20
- Config: `sweep_enabled`, `sweep_bull_mult`, `sweep_sw_short_mult`, `sweep_lookback_bars`
- Removed: OHLC buffer, `_detect_sweep_down/up` methods
- Reason: Marginal +$4, tidak fix WR

### 7. Break-Even SL — v4.4
- Config: `be_sl_enabled`, `be_activation_pct`, `be_sl_apply_bull`, `be_sl_apply_sw`
- Removed: `_apply_be_sl_long`, `_apply_be_sl_short`
- Reason: PnL -$307. Winners retrace ke entry lebih sering dari yang diperkirakan

### 8. Bull Trend Rider
- Config: `bull_trend_rider_enabled` + 5 related fields
- Removed: BULL TR branches di `_execute_bull_entry` dan `_exit_bull`
- Reason: Redundant dengan CT Bull

### 9. Trap Logic
- Config: `trap_enabled` + 5 related fields
- Removed: `_check_trap_entry`, `_exit_trap`, TRAP tool paths
- Reason: Kompleks, marginal impact

### 10. SM Fix 1 & 4
- Config: `sm_fix_1_htf_confirm`, `sm_fix_4_bull_confirm`, `sm_fix_4_bear_confirm`
- Reason: Never enabled di champion, delay entry gagal test
- KEEP: SM Fix 2 (bear streak), SM Fix 3 (extreme low)

## Kept in v5.0 Champion

- Base state machine (SIDEWAYS/BULL/BEAR/WAIT_SEE_*)
- CT Bull 3x sizing
- AMT Amplify (NEAR_VAH 2x, ABOVE 1.5x)
- Per-pair TP (via Query param)
- BEAR Trend Rider (works)
- SM Fix 2 (bear streak → sideways)
- SM Fix 3 (extreme low → sideways)
- MTF 15m entry (SW/BULL/BEAR)
- Volume filter, chop filter

## Champion Config Reference

```
bull_countertrend_size_mult=3.0
amt_enabled=true
amt_skip_sw_above=false      # allow SW ABOVE (amplify handles it)
amt_skip_bull_below=false    # allow BULL BELOW (amplify handles it)
amt_bull_near_vah_mult=2.0
amt_bull_above_mult=1.5

Per-pair TP:
  BTCUSDT: 0.008
  ETHUSDT: 0.018
  SOLUSDT: 0.010
  BNBUSDT: 0.015
  DOGEUSDT: 0.018
```

Performance: +$1,796/year (359% ROI on $500 portfolio), all pairs positive di 2024 dan 2025-2026.

## Restore Legacy

```bash
git checkout db0b5b2 -- mode3/config.py mode3/switcher.py mode3_backtest_endpoint.py
```

commit `db0b5b2` = v4.4 final with all features intact.
