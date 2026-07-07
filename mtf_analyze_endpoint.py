"""
mtf_analyze_endpoint.py — v0.7: 3 fixes from user review
"""
from fastapi import APIRouter
import os

router = APIRouter()

DB_PATH = os.environ.get("DB_PATH", "market_data.db")


@router.get("/mtf/analyze")
def mtf_analyze(
    symbol: str = "BTCUSDT",
    days: int = 30,
    n_candles_per_layer: int = 1,
):
    try:
        import sqlite3
        import numpy as np
        from mode3_regime.mtf_container import classify_mtf

        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows_1h = conn.execute("""
            SELECT open, high, low, close, volume, open_time
            FROM klines WHERE symbol = ? AND timeframe = '1h'
            ORDER BY open_time ASC
        """, (symbol,)).fetchall()
        rows_4h = conn.execute("""
            SELECT open, high, low, close, volume, open_time
            FROM klines WHERE symbol = ? AND timeframe = '4h'
            ORDER BY open_time ASC
        """, (symbol,)).fetchall()
        conn.close()

        if not rows_1h or not rows_4h:
            return {"ok": False, "error": f"no data for {symbol}"}

        if days > 0:
            ms_limit = days * 86400 * 1000
            last_time = rows_1h[-1][5]
            cutoff = last_time - ms_limit
            rows_1h = [r for r in rows_1h if r[5] >= cutoff]
            cutoff_4h = cutoff - (10 * 86400 * 1000)
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

        classifications, stats = classify_mtf(
            opens_1h, highs_1h, lows_1h, closes_1h, volumes_1h, ts_1h,
            opens_4h, highs_4h, lows_4h, closes_4h, volumes_4h, ts_4h,
            n_candles_per_layer=n_candles_per_layer,
        )

        valid_cls = [c for c in classifications if c.range_4h_high is not None]

        def cls_to_dict(c):
            return {
                "idx": c.idx, "timestamp_ms": c.timestamp_ms, "close": round(c.close, 2),
                "range_4h": [round(c.range_4h_low, 2), round(c.range_4h_high, 2)],
                "range_1d": [round(c.range_1d_low, 2), round(c.range_1d_high, 2)],
                "range_1w": [round(c.range_1w_low, 2), round(c.range_1w_high, 2)],
                "pos_4h": round(c.pos_in_4h, 3), "pos_1d": round(c.pos_in_1d, 3), "pos_1w": round(c.pos_in_1w, 3),
                "inside_4h": c.inside_4h, "inside_1d": c.inside_1d, "inside_1w": c.inside_1w,
                "confidence": c.inside_confidence,
            }

        return {
            "ok": True, "symbol": symbol, "days": days,
            "n_candles_per_layer": n_candles_per_layer,
            "total_1h_loaded": len(closes_1h), "total_4h_loaded": len(closes_4h),
            "classified": stats.total_1h_candles,
            "stats": {
                "confidence_distribution": {
                    "3_of_3": stats.conf_3_of_3_pct, "2_of_3": stats.conf_2_of_3_pct,
                    "1_of_3": stats.conf_1_of_3_pct, "0_of_3": stats.conf_0_of_3_pct,
                },
            },
            "sample_first_5": [cls_to_dict(c) for c in valid_cls[:5]],
            "sample_last_5": [cls_to_dict(c) for c in valid_cls[-5:]],
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


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
    # v0.7 NEW params
    ema_exit_min_profit_pct: float = 0.003,
    use_close_confirm_sl: bool = False,
    # display
    include_trades: int = 20,
    use_pine_candle: bool = True,
):
    """v0.7 — EMA min-profit gate + SL close-confirm."""
    try:
        import sqlite3
        import numpy as np
        from mode3_regime.mtf_container import classify_mtf
        from mode3_regime.strategy_sideways import SidewaysConfig
        from mode3_regime.backtest_sideways import SidewaysBTConfig, run_sideways_backtest
        from mode3_regime.regime import RegimeConfig

        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        rows_1h = conn.execute("""
            SELECT open, high, low, close, volume, open_time
            FROM klines WHERE symbol = ? AND timeframe = '1h'
            ORDER BY open_time ASC
        """, (symbol,)).fetchall()
        rows_4h = conn.execute("""
            SELECT open, high, low, close, volume, open_time
            FROM klines WHERE symbol = ? AND timeframe = '4h'
            ORDER BY open_time ASC
        """, (symbol,)).fetchall()
        conn.close()

        if not rows_1h or not rows_4h:
            return {"ok": False, "error": f"no data for {symbol}"}

        if days > 0:
            ms_limit = days * 86400 * 1000
            last_time = rows_1h[-1][5]
            cutoff = last_time - ms_limit
            rows_1h = [r for r in rows_1h if r[5] >= cutoff]
            cutoff_4h = cutoff - (10 * 86400 * 1000)
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
        )

        opens_arg = opens_1h if use_pine_candle else None

        result = run_sideways_backtest(
            highs_1h, lows_1h, closes_1h, volumes_1h,
            cfg=bt_cfg, regime_cfg=RegimeConfig(),
            strategy_cfg=strategy_cfg, warmup=100,
            mtf_classifications=mtf_classifications if use_mtf_filter else None,
            opens=opens_arg,
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
                "mtf_conf": t.mtf_confidence, "ema_slope_pct": round(t.ema_slope_pct, 3),
                "confidence": round(t.confidence, 2),
                "position_usd": round(t.position_usd, 2),
                "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
                "sl_price": round(t.sl_price, 2),
                "sl_dist_pct": round(sl_dist_pct, 3),
                "tp1_dist_pct": round(tp1_dist_pct, 3),
                "max_profit_pct": round(t.max_profit_pct * 100, 3),  # v0.7 NEW
                "tp1_hit": t.tp1_hit, "tp2_hit": t.tp2_hit, "tp3_hit": t.tp3_hit,
                "exit_reason": t.exit_reason, "pnl_net": round(t.pnl_net, 2),
                "hold": t.hold_candles,
            })

        return {
            "ok": True,
            "strategy": "sideways_tektok_v0.7",
            "symbol": symbol, "days": days,
            "config": {
                "n_candles_per_layer": n_candles_per_layer,
                "min_mtf_confidence": min_mtf_confidence,
                "use_mtf_filter": use_mtf_filter,
                "use_pine_candle": use_pine_candle,
                "use_atr_sl": use_atr_sl, "sl_atr_mult": sl_atr_mult,
                "use_ema_dynamic_exit": use_ema_dynamic_exit,
                "ema_exit_period": ema_exit_period,
                "ema_exit_min_profit_pct": ema_exit_min_profit_pct,
                "use_close_confirm_sl": use_close_confirm_sl,
                "use_ema_slope_filter": use_ema_slope_filter,
                "short_max_slope_pct": short_max_slope_pct,
                "long_min_slope_pct": long_min_slope_pct,
                "max_hold_candles": max_hold_candles,
            },
            "stats": {
                "total_trades": s.total_trades, "wins": s.wins, "losses": s.losses,
                "win_rate": round(s.win_rate, 4),
                "total_pnl_net": round(s.total_pnl_net, 2),
                "avg_win": round(s.avg_win, 2), "avg_loss": round(s.avg_loss, 2),
                "max_drawdown_pct": round(s.max_drawdown_pct, 4),
                "max_drawdown_usd": round(s.max_drawdown_usd, 2),
                "trades_per_day": round(s.trades_per_day, 4),
                "tp1_hit_rate": round(s.tp1_hit_rate, 4),
                "tp2_hit_rate": round(s.tp2_hit_rate, 4),
                "tp3_hit_rate": round(s.tp3_hit_rate, 4),
                "exit_by_reason": s.exit_by_reason,
                "by_regime": s.by_regime, "by_mode": s.by_mode,
                "by_confidence_tier": s.by_confidence_tier,
                "by_mtf_tier": s.by_mtf_tier,
            },
            "sample_trades": sample_trades,
            "runtime_sec": round(s.runtime_sec, 2),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


__all__ = ["router"]
