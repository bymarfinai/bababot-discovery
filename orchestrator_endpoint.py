"""
orchestrator_endpoint.py — v1.4.1 with vah_break_margin param fix
"""
from fastapi import APIRouter
import os

router = APIRouter()
DB_PATH = os.environ.get("DB_PATH", "market_data.db")


def _load_candles(symbol: str, days: int):
    import sqlite3
    import numpy as np

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows_1h = conn.execute(
        "SELECT open, high, low, close, volume, open_time FROM klines WHERE symbol=? AND timeframe='1h' ORDER BY open_time ASC",
        (symbol,)
    ).fetchall()
    rows_4h = conn.execute(
        "SELECT open, high, low, close, volume, open_time FROM klines WHERE symbol=? AND timeframe='4h' ORDER BY open_time ASC",
        (symbol,)
    ).fetchall()
    conn.close()

    if not rows_1h:
        return None, None

    if days > 0:
        ms_limit = days * 86400 * 1000
        last_time = rows_1h[-1][5]
        cutoff = last_time - ms_limit
        rows_1h = [r for r in rows_1h if r[5] >= cutoff]
        rows_4h = [r for r in rows_4h if r[5] >= cutoff - (30 * 86400 * 1000)]

    d1 = {
        "opens": np.array([r[0] for r in rows_1h], dtype=np.float64),
        "highs": np.array([r[1] for r in rows_1h], dtype=np.float64),
        "lows": np.array([r[2] for r in rows_1h], dtype=np.float64),
        "closes": np.array([r[3] for r in rows_1h], dtype=np.float64),
        "volumes": np.array([r[4] for r in rows_1h], dtype=np.float64),
        "ts": np.array([r[5] for r in rows_1h], dtype=np.int64),
    }
    d4 = {
        "opens": np.array([r[0] for r in rows_4h], dtype=np.float64),
        "highs": np.array([r[1] for r in rows_4h], dtype=np.float64),
        "lows": np.array([r[2] for r in rows_4h], dtype=np.float64),
        "closes": np.array([r[3] for r in rows_4h], dtype=np.float64),
        "volumes": np.array([r[4] for r in rows_4h], dtype=np.float64),
        "ts": np.array([r[5] for r in rows_4h], dtype=np.int64),
    }
    return d1, d4


@router.get("/mtf/bull_backtest")
def bull_backtest(
    symbol: str = "BTCUSDT",
    days: int = 30,
    ema_period: int = 20,
    min_pullback_pct: float = 0.015,
    sl_buffer_pct: float = 0.001,
    tp1_target_pct: float = 0.01,
    max_hold: int = 200,
    include_trades: int = 30,
):
    try:
        from mode3_regime.bull_tool import BullConfig, run_bull_backtest
        d1, _ = _load_candles(symbol, days)
        if d1 is None:
            return {"ok": False, "error": f"no data for {symbol}"}
        cfg = BullConfig(ema_period=ema_period, min_pullback_pct=min_pullback_pct)
        result = run_bull_backtest(
            d1["highs"], d1["lows"], d1["closes"], d1["opens"],
            cfg=cfg, max_hold=max_hold,
            sl_buffer_pct=sl_buffer_pct, tp1_target_pct=tp1_target_pct,
        )
        if include_trades and result.get("trades"):
            result["trades"] = result["trades"][:include_trades]
        return result
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


@router.get("/mtf/bear_backtest")
def bear_backtest(
    symbol: str = "BTCUSDT",
    days: int = 30,
    ema_period: int = 20,
    min_rally_pct: float = 0.015,
    sl_buffer_pct: float = 0.001,
    tp1_target_pct: float = 0.01,
    max_hold: int = 200,
    include_trades: int = 30,
):
    try:
        from mode3_regime.bear_tool import BearConfig, run_bear_backtest
        d1, _ = _load_candles(symbol, days)
        if d1 is None:
            return {"ok": False, "error": f"no data for {symbol}"}
        cfg = BearConfig(ema_period=ema_period, min_rally_pct=min_rally_pct)
        result = run_bear_backtest(
            d1["highs"], d1["lows"], d1["closes"], d1["opens"],
            cfg=cfg, max_hold=max_hold,
            sl_buffer_pct=sl_buffer_pct, tp1_target_pct=tp1_target_pct,
        )
        if include_trades and result.get("trades"):
            result["trades"] = result["trades"][:include_trades]
        return result
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


@router.get("/mtf/orchestrator_backtest")
def orchestrator_backtest(
    symbol: str = "BTCUSDT",
    days: int = 30,
    use_mtf_filter: bool = True,
    min_mtf_confidence: int = 3,
    sw_max_hold: int = 48,
    sw_ema_reject_cooldown: int = 48,
    trending_max_hold: int = 200,
    bull_min_pullback: float = 0.015,
    bear_min_rally: float = 0.015,
    post_transition_wait: int = 24,
    # v1.4 core toggles
    use_rolling_va: bool = True,
    va_window: int = 50,
    va_recompute_every: int = 20,
    use_va_tp: bool = True,
    tp1_partial_ratio: float = 0.5,
    use_sl_buffer: bool = True,
    sl_buffer_pct: float = 0.001,
    # State transition
    vah_break_candles: int = 1,
    val_break_candles: int = 1,
    vah_break_margin: float = 0.0,  # ← v1.4.1 FIX: now properly exposed
    enable_state_timeout: bool = True,
    state_timeout_candles: int = 100,
    include_trades: int = 50,
):
    """v1.4.1 orchestrator — vah_break_margin properly wired."""
    try:
        from mode3_regime.mtf_container import classify_mtf
        from mode3_regime.strategy_sideways import SidewaysConfig
        from mode3_regime.bull_tool import BullConfig
        from mode3_regime.bear_tool import BearConfig
        from mode3_regime.state_orchestrator import OrchestratorConfig, run_state_machine_backtest

        d1, d4 = _load_candles(symbol, days)
        if d1 is None:
            return {"ok": False, "error": f"no data for {symbol}"}

        mtf_cls = None
        if use_mtf_filter:
            mtf_cls, _ = classify_mtf(
                d1["opens"], d1["highs"], d1["lows"], d1["closes"], d1["volumes"], d1["ts"],
                d4["opens"], d4["highs"], d4["lows"], d4["closes"], d4["volumes"], d4["ts"],
                n_candles_per_layer=3,
            )

        sw_cfg = SidewaysConfig(
            range_max_width_pct=999,
            touch_tolerance=0.003,
            volume_multiplier=1.3,
            cooldown_bars=10,
            use_mtf_filter=use_mtf_filter,
            min_mtf_confidence=min_mtf_confidence,
            skip_regime_filter=True,
            skip_range_width_filter=False,
        )
        bull_cfg = BullConfig(ema_period=20, min_pullback_pct=bull_min_pullback)
        bear_cfg = BearConfig(ema_period=20, min_rally_pct=bear_min_rally)

        orch_cfg = OrchestratorConfig(
            sideways_cfg=sw_cfg, bull_cfg=bull_cfg, bear_cfg=bear_cfg,
            sw_max_hold=sw_max_hold,
            sw_ema_reject_cooldown=sw_ema_reject_cooldown,
            trending_max_hold=trending_max_hold,
            post_transition_wait=post_transition_wait,
            use_rolling_va=use_rolling_va,
            va_window=va_window,
            va_recompute_every=va_recompute_every,
            use_va_tp=use_va_tp,
            tp1_partial_ratio=tp1_partial_ratio,
            use_sl_buffer=use_sl_buffer,
            sl_buffer_pct=sl_buffer_pct,
            vah_break_candles=vah_break_candles,
            val_break_candles=val_break_candles,
            vah_break_margin=vah_break_margin,  # ← v1.4.1 FIX
            enable_state_timeout=enable_state_timeout,
            state_timeout_candles=state_timeout_candles,
        )

        result = run_state_machine_backtest(
            d1["highs"], d1["lows"], d1["closes"], d1["opens"], d1["volumes"],
            cfg=orch_cfg, mtf_classifications=mtf_cls,
        )
        if include_trades and result.get("sample_trades"):
            result["sample_trades"] = result["sample_trades"][:include_trades]
        return result
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


__all__ = ["router"]
