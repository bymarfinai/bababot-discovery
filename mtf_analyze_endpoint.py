"""
mtf_analyze_endpoint.py — v0.9 + auto-mount orchestrator v1.0
"""
from fastapi import APIRouter
import os

router = APIRouter()

DB_PATH = os.environ.get("DB_PATH", "market_data.db")


@router.get("/mtf/analyze")
def mtf_analyze(symbol: str = "BTCUSDT", days: int = 30, n_candles_per_layer: int = 1):
    try:
        import sqlite3
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows_1h = conn.execute("SELECT COUNT(*) FROM klines WHERE symbol=? AND timeframe='1h'", (symbol,)).fetchone()
        conn.close()
        return {"ok": True, "symbol": symbol, "count_1h": rows_1h[0]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _compute_4h_bias_arr(ts_1h, ts_4h, closes_4h, ema_period=50, margin_pct=0.005):
    import numpy as np
    from mode3_regime.indicators import ema as compute_ema

    ema50_4h = compute_ema(closes_4h, ema_period)
    bias_arr = np.zeros(len(ts_1h), dtype=np.int8)
    ms_4h = 4 * 3600 * 1000
    j = 0
    for i in range(len(ts_1h)):
        t1 = ts_1h[i]
        while j + 1 < len(ts_4h) and ts_4h[j + 1] <= t1:
            j += 1
        if ts_4h[j] + ms_4h > t1:
            if j == 0: continue
            j_use = j - 1
        else:
            j_use = j
        if j_use < ema_period: continue
        close_4h = float(closes_4h[j_use])
        ema_val = float(ema50_4h[j_use])
        if ema_val <= 0: continue
        pct_diff = (close_4h - ema_val) / ema_val
        if pct_diff > margin_pct: bias_arr[i] = 1
        elif pct_diff < -margin_pct: bias_arr[i] = -1
    return bias_arr


@router.get("/mtf/sideways_backtest")
def mtf_sideways_backtest(
    symbol: str = "BTCUSDT",
    days: int = 1825,
    n_candles_per_layer: int = 3,
    min_mtf_confidence: int = 2,
    enable_low_conf_quarter: bool = False,
    use_mtf_filter: bool = True,
    range_max_width_pct: float = 1.0,
    touch_tolerance: float = 0.003,
    volume_multiplier: float = 1.3,
    cooldown_bars: int = 10,
    use_atr_sl: bool = False,
    sl_atr_mult: float = 1.5,
    atr_period: int = 14,
    sl_pct_from_level: float = 0.005,
    tp1_ratio: float = 0.5,
    tp2_ratio: float = 0.3,
    tp3_ratio: float = 0.2,
    max_hold_candles: int = 12,
    use_ema_dynamic_exit: bool = False,
    ema_exit_period: int = 20,
    use_ema_slope_filter: bool = False,
    ema_slope_period: int = 20,
    ema_slope_lookback: int = 10,
    long_min_slope_pct: float = -1.0,
    short_max_slope_pct: float = 1.0,
    ema_exit_min_profit_pct: float = 0.003,
    use_close_confirm_sl: bool = False,
    use_4h_bias_filter: bool = False,
    bias_4h_ema_period: int = 50,
    bias_margin_pct: float = 0.005,
    bias_filter_mode: str = "mean_revert",
    ema_reject_same_dir_cooldown: int = 0,
    include_trades: int = 20,
    use_pine_candle: bool = True,
):
    """v0.9 — post-EMA-reject same-direction cooldown (flip logic)."""
    try:
        import sqlite3
        import numpy as np
        from mode3_regime.mtf_container import classify_mtf
        from mode3_regime.strategy_sideways import SidewaysConfig
        from mode3_regime.backtest_sideways import SidewaysBTConfig, run_sideways_backtest
        from mode3_regime.regime import RegimeConfig

        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows_1h = conn.execute("SELECT open, high, low, close, volume, open_time FROM klines WHERE symbol = ? AND timeframe = '1h' ORDER BY open_time ASC", (symbol,)).fetchall()
        rows_4h = conn.execute("SELECT open, high, low, close, volume, open_time FROM klines WHERE symbol = ? AND timeframe = '4h' ORDER BY open_time ASC", (symbol,)).fetchall()
        conn.close()

        if not rows_1h or not rows_4h:
            return {"ok": False, "error": f"no data for {symbol}"}

        if days > 0:
            ms_limit = days * 86400 * 1000
            last_time = rows_1h[-1][5]
            cutoff = last_time - ms_limit
            rows_1h = [r for r in rows_1h if r[5] >= cutoff]
            cutoff_4h = cutoff - (30 * 86400 * 1000)
            rows_4h = [r for r in rows_4h if r[5] >= cutoff_4h]

        opens_1h = np.array([r[0] for r in rows_1h], dtype=np.float64)
        highs_1h = np.array([r[1] for r in rows_1h], dtype=np.float64)
        lows_1h = np.array([r[2] for r in rows_1h], dtype=np.float64)
        closes_1h = np.array([r[3] for r in rows_1h], dtype=np.float64)
        volumes_1h = np.array([r[4] for r in rows_1h], dtype=np.float64)
        ts_1h = np.array([r[5] for r in rows_1h], dtype=np.int64)
        opens_4h = np.array([r[0] for r in rows_4h], dtype=np.float64)
        highs_4h = np.array([r[1] for r in rows_4h], dtype=np.float64)
        lows_4h = np.array([r[2] for r in rows_4h], dtype=np.float64)
        closes_4h = np.array([r[3] for r in rows_4h], dtype=np.float64)
        volumes_4h = np.array([r[4] for r in rows_4h], dtype=np.float64)
        ts_4h = np.array([r[5] for r in rows_4h], dtype=np.int64)

        mtf_classifications, mtf_stats = classify_mtf(
            opens_1h, highs_1h, lows_1h, closes_1h, volumes_1h, ts_1h,
            opens_4h, highs_4h, lows_4h, closes_4h, volumes_4h, ts_4h,
            n_candles_per_layer=n_candles_per_layer,
        )

        bias_arr_1h = None
        if use_4h_bias_filter:
            bias_arr_1h = _compute_4h_bias_arr(ts_1h, ts_4h, closes_4h,
                                                ema_period=bias_4h_ema_period,
                                                margin_pct=bias_margin_pct)

        strategy_cfg = SidewaysConfig(
            range_max_width_pct=range_max_width_pct,
            touch_tolerance=touch_tolerance,
            volume_multiplier=volume_multiplier,
            cooldown_bars=cooldown_bars,
            use_mtf_filter=use_mtf_filter,
            min_mtf_confidence=min_mtf_confidence,
            enable_low_conf_quarter=enable_low_conf_quarter,
            skip_regime_filter=True,
            skip_range_width_filter=False,
            use_ema_slope_filter=use_ema_slope_filter,
            ema_slope_period=ema_slope_period,
            ema_slope_lookback=ema_slope_lookback,
            long_min_slope_pct=long_min_slope_pct,
            short_max_slope_pct=short_max_slope_pct,
            use_4h_bias_filter=use_4h_bias_filter,
            bias_margin_pct=bias_margin_pct,
            bias_filter_mode=bias_filter_mode,
        )
        bt_cfg = SidewaysBTConfig(
            sl_pct_from_level=sl_pct_from_level,
            use_atr_sl=use_atr_sl,
            sl_atr_mult=sl_atr_mult,
            atr_period=atr_period,
            tp1_ratio=tp1_ratio, tp2_ratio=tp2_ratio, tp3_ratio=tp3_ratio,
            max_hold_candles=max_hold_candles,
            use_ema_dynamic_exit=use_ema_dynamic_exit,
            ema_exit_period=ema_exit_period,
            ema_exit_min_profit_pct=ema_exit_min_profit_pct,
            use_close_confirm_sl=use_close_confirm_sl,
            ema_reject_same_dir_cooldown=ema_reject_same_dir_cooldown,
        )

        opens_arg = opens_1h if use_pine_candle else None

        result = run_sideways_backtest(
            highs_1h, lows_1h, closes_1h, volumes_1h,
            cfg=bt_cfg, regime_cfg=RegimeConfig(),
            strategy_cfg=strategy_cfg, warmup=100,
            mtf_classifications=mtf_classifications if use_mtf_filter else None,
            opens=opens_arg,
            bias_arr_1h=bias_arr_1h,
        )
        if result.error:
            return {"ok": False, "error": result.error}

        s = result.stats
        sample_trades = []
        for t in result.trades[:include_trades]:
            if t.side == 'long':
                sl_dist_pct = (t.entry_price - t.sl_price) / t.entry_price * 100
                tp1_dist_pct = (t.tp1_price - t.entry_price) / t.entry_price * 100
            else:
                sl_dist_pct = (t.sl_price - t.entry_price) / t.entry_price * 100
                tp1_dist_pct = (t.entry_price - t.tp1_price) / t.entry_price * 100
            sample_trades.append({
                "entry_idx": t.entry_idx, "side": t.side, "mode": t.mode,
                "bias_4h": t.bias_4h,
                "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
                "sl_price": round(t.sl_price, 2),
                "sl_dist_pct": round(sl_dist_pct, 3),
                "tp1_dist_pct": round(tp1_dist_pct, 3),
                "max_profit_pct": round(t.max_profit_pct * 100, 3),
                "tp1_hit": t.tp1_hit, "tp2_hit": t.tp2_hit, "tp3_hit": t.tp3_hit,
                "exit_reason": t.exit_reason, "pnl_net": round(t.pnl_net, 2),
                "hold": t.hold_candles,
            })

        return {
            "ok": True, "strategy": "sideways_tektok_v0.9",
            "symbol": symbol, "days": days,
            "config": {
                "use_mtf_filter": use_mtf_filter,
                "use_atr_sl": use_atr_sl,
                "use_ema_dynamic_exit": use_ema_dynamic_exit,
                "ema_exit_min_profit_pct": ema_exit_min_profit_pct,
                "use_close_confirm_sl": use_close_confirm_sl,
                "use_4h_bias_filter": use_4h_bias_filter,
                "bias_filter_mode": bias_filter_mode,
                "ema_reject_same_dir_cooldown": ema_reject_same_dir_cooldown,
                "max_hold_candles": max_hold_candles,
            },
            "stats": {
                "total_trades": s.total_trades, "wins": s.wins, "losses": s.losses,
                "win_rate": round(s.win_rate, 4),
                "total_pnl_net": round(s.total_pnl_net, 2),
                "avg_win": round(s.avg_win, 2), "avg_loss": round(s.avg_loss, 2),
                "max_drawdown_pct": round(s.max_drawdown_pct, 4),
                "trades_per_day": round(s.trades_per_day, 4),
                "tp1_hit_rate": round(s.tp1_hit_rate, 4),
                "tp2_hit_rate": round(s.tp2_hit_rate, 4),
                "tp3_hit_rate": round(s.tp3_hit_rate, 4),
                "exit_by_reason": s.exit_by_reason,
                "ema_reject_flips_avoided": s.ema_reject_flips_avoided,
            },
            "sample_trades": sample_trades,
            "runtime_sec": round(s.runtime_sec, 2),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# ══════════════════════════════════════════════════════════════
# v1.0 Auto-mount orchestrator sub-endpoints
# Copies orchestrator routes into this router so app.py needs no edit
# ══════════════════════════════════════════════════════════════
try:
    from orchestrator_endpoint import router as _orch_router
    for _route in _orch_router.routes:
        router.routes.append(_route)
    print(f"[INIT] Orchestrator v1.0 sub-mounted via mtf_router ({len(_orch_router.routes)} routes)")
except Exception as _e:
    print(f"[WARN] orchestrator sub-mount failed: {_e}")


__all__ = ["router"]
