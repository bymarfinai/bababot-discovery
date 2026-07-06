"""
mtf_analyze_endpoint.py — Standalone FastAPI router for MTF container analysis.
Mounted in app.py via include_router.
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
    """
    Validate MTF container concept.
    Loads 1h + 4h data, aggregates 4h to 1D and 1W on-the-fly, classifies each 1h candle.
    Returns distribution statistics.
    """
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
        sample_first = valid_cls[:5]
        sample_last = valid_cls[-5:]

        def cls_to_dict(c):
            return {
                "idx": c.idx,
                "timestamp_ms": c.timestamp_ms,
                "close": round(c.close, 2),
                "range_4h": [round(c.range_4h_low, 2), round(c.range_4h_high, 2)],
                "range_1d": [round(c.range_1d_low, 2), round(c.range_1d_high, 2)],
                "range_1w": [round(c.range_1w_low, 2), round(c.range_1w_high, 2)],
                "pos_4h": round(c.pos_in_4h, 3),
                "pos_1d": round(c.pos_in_1d, 3),
                "pos_1w": round(c.pos_in_1w, 3),
                "inside_4h": c.inside_4h,
                "inside_1d": c.inside_1d,
                "inside_1w": c.inside_1w,
                "confidence": c.inside_confidence,
            }

        return {
            "ok": True,
            "symbol": symbol,
            "days": days,
            "n_candles_per_layer": n_candles_per_layer,
            "total_1h_loaded": len(closes_1h),
            "total_4h_loaded": len(closes_4h),
            "classified": stats.total_1h_candles,
            "stats": {
                "inside_pct": {
                    "4h": stats.inside_4h_pct,
                    "1d": stats.inside_1d_pct,
                    "1w": stats.inside_1w_pct,
                },
                "break_pct": {
                    "4h_total": stats.break_4h_pct,
                    "1d_total": stats.break_1d_pct,
                    "1w_total": stats.break_1w_pct,
                    "4h_up": round(stats.break_up_4h / max(stats.total_1h_candles, 1), 4),
                    "4h_down": round(stats.break_down_4h / max(stats.total_1h_candles, 1), 4),
                    "1d_up": round(stats.break_up_1d / max(stats.total_1h_candles, 1), 4),
                    "1d_down": round(stats.break_down_1d / max(stats.total_1h_candles, 1), 4),
                    "1w_up": round(stats.break_up_1w / max(stats.total_1h_candles, 1), 4),
                    "1w_down": round(stats.break_down_1w / max(stats.total_1h_candles, 1), 4),
                },
                "hierarchy_consistency": {
                    "break_1d_also_break_4h_pct": stats.break_1d_also_break_4h_pct,
                    "break_1w_also_break_1d_pct": stats.break_1w_also_break_1d_pct,
                },
                "confidence_distribution": {
                    "3_of_3": stats.conf_3_of_3_pct,
                    "2_of_3": stats.conf_2_of_3_pct,
                    "1_of_3": stats.conf_1_of_3_pct,
                    "0_of_3": stats.conf_0_of_3_pct,
                },
            },
            "sample_first_5": [cls_to_dict(c) for c in sample_first],
            "sample_last_5": [cls_to_dict(c) for c in sample_last],
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


__all__ = ["router"]
