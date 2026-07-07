"""
mtf_sideways_backtest_endpoint.py — MTF-integrated sideways backtest endpoint.
Bypasses the mysterious mode3_regime_api.py — self-contained router.
"""
from fastapi import APIRouter
from typing import Optional
import os

router = APIRouter()

DB_PATH = os.environ.get("DB_PATH", "market_data.db")


@router.get("/mtf/sideways_backtest")
def mtf_sideways_backtest(
    symbol: str = "BTCUSDT",
    days: int = 1825,
    n_candles_per_layer: int = 3,        # MTF container N (default 3, optimal from validation)
    min_mtf_confidence: int = 2,          # skip signals with mtf conf < this
    enable_low_conf_quarter: bool = False,
    use_mtf_filter: bool = True,          # master switch, false = baseline no-MTF
    # Strategy params
    range_max_width_pct: float = 1.0,     # loose default (match v0.3 test)
    touch_tolerance: float = 0.003,
    volume_multiplier: float = 1.3,
    cooldown_bars: int = 10,
    # Backtest params
    sl_pct_from_level: float = 0.005,
    tp1_ratio: float = 0.5,
    tp2_ratio: float = 0.3,
    tp3_ratio: float = 0.2,
    max_hold_candles: int = 12,
    include_trades: int = 20,  # how many sample trades to return
):
    """
    Run sideways tektok backtest with MTF Container filter.
    Compares v0.4 (with MTF) vs baseline (no MTF filter).
    """
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

        # Classify MTF containers
        mtf_classifications, mtf_stats = classify_mtf(
            opens_1h, highs_1h, lows_1h, closes_1h, volumes_1h, ts_1h,
            opens_4h, highs_4h, lows_4h, closes_4h, volumes_4h, ts_4h,
            n_candles_per_layer=n_candles_per_layer,
        )

        # Build configs
        strategy_cfg = SidewaysConfig(
            range_max_width_pct=range_max_width_pct,
            touch_tolerance=touch_tolerance,
            volume_multiplier=volume_multiplier,
            cooldown_bars=cooldown_bars,
            use_mtf_filter=use_mtf_filter,
            min_mtf_confidence=min_mtf_confidence,
            enable_low_conf_quarter=enable_low_conf_quarter,
            skip_regime_filter=True,          # match v0.3 test config
            skip_range_width_filter=False,
        )

        bt_cfg = SidewaysBTConfig(
            sl_pct_from_level=sl_pct_from_level,
            tp1_ratio=tp1_ratio,
            tp2_ratio=tp2_ratio,
            tp3_ratio=tp3_ratio,
            max_hold_candles=max_hold_candles,
        )

        result = run_sideways_backtest(
            highs_1h, lows_1h, closes_1h, volumes_1h,
            cfg=bt_cfg,
            regime_cfg=RegimeConfig(),
            strategy_cfg=strategy_cfg,
            warmup=100,
            mtf_classifications=mtf_classifications if use_mtf_filter else None,
        )

        if result.error:
            return {"ok": False, "error": result.error}

        s = result.stats
        sample_trades = []
        for t in result.trades[:include_trades]:
            sample_trades.append({
                "entry_idx": t.entry_idx,
                "side": t.side,
                "mode": t.mode,
                "mtf_conf": t.mtf_confidence,
                "confidence": round(t.confidence, 2),
                "position_usd": round(t.position_usd, 2),
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "sl_price": round(t.sl_price, 2),
                "tp1_hit": t.tp1_hit,
                "tp2_hit": t.tp2_hit,
                "tp3_hit": t.tp3_hit,
                "exit_reason": t.exit_reason,
                "pnl_net": round(t.pnl_net, 2),
                "hold": t.hold_candles,
            })

        return {
            "ok": True,
            "strategy": "sideways_tektok_v0.4_mtf",
            "symbol": symbol,
            "days": days,
            "config": {
                "n_candles_per_layer": n_candles_per_layer,
                "min_mtf_confidence": min_mtf_confidence,
                "use_mtf_filter": use_mtf_filter,
                "range_max_width_pct": range_max_width_pct,
            },
            "mtf_context": {
                "conf_3_of_3_pct": mtf_stats.conf_3_of_3_pct,
                "conf_2_of_3_pct": mtf_stats.conf_2_of_3_pct,
                "conf_1_of_3_pct": mtf_stats.conf_1_of_3_pct,
                "conf_0_of_3_pct": mtf_stats.conf_0_of_3_pct,
            },
            "stats": {
                "total_trades": s.total_trades,
                "wins": s.wins,
                "losses": s.losses,
                "win_rate": round(s.win_rate, 4),
                "total_pnl_net": round(s.total_pnl_net, 2),
                "avg_win": round(s.avg_win, 2),
                "avg_loss": round(s.avg_loss, 2),
                "max_drawdown_pct": round(s.max_drawdown_pct, 4),
                "max_drawdown_usd": round(s.max_drawdown_usd, 2),
                "trades_per_day": round(s.trades_per_day, 4),
                "tp1_hit_rate": round(s.tp1_hit_rate, 4),
                "tp2_hit_rate": round(s.tp2_hit_rate, 4),
                "tp3_hit_rate": round(s.tp3_hit_rate, 4),
                "exit_by_reason": s.exit_by_reason,
                "by_regime": s.by_regime,
                "by_mode": s.by_mode,
                "by_confidence_tier": s.by_confidence_tier,
                "by_mtf_tier": s.by_mtf_tier,  # v0.4 KEY METRIC
            },
            "sample_trades": sample_trades,
            "runtime_sec": round(s.runtime_sec, 2),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


__all__ = ["router"]
