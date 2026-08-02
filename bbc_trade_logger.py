"""BBC trade logger — logs with 'BBC_V3_' prefix.

Usage in bbc_live.py:
    from bbc_trade_logger import _log_trade_to_d1  # shadows baret_live version
"""
import os
import time
import requests

_WORKER_URL = os.environ.get("WORKER_URL", "https://bababot-pro.bymarfinai.workers.dev")


def _log_trade_to_d1(symbol, timeframe, side, entry_price, exit_price, entry_time, exit_time,
                     sl_pct, tp_pct, pnl_dollar, pnl_pct, exit_reason, acct_name=""):
    """Log trade to D1 with 'BBC_V3_' prefix. Retries up to 3 times on failure."""
    notes = f"BBC_V3_{acct_name}" if acct_name else "BBC_V3"
    payload = {
        "strategy_id": 0, "symbol": symbol, "timeframe": timeframe, "side": side,
        "entry_price": entry_price, "exit_price": exit_price,
        "entry_time": entry_time, "exit_time": exit_time,
        "sl_pct": sl_pct, "tp_pct": tp_pct,
        "pnl_dollar": pnl_dollar, "pnl_pct": pnl_pct, "exit_reason": exit_reason,
        "regime_at_entry": None, "minimax_entry_verdict": None,
        "minimax_exit_verdict": None, "minimax_adjustments": None,
        "bars_held": None, "max_favorable": None, "max_adverse": None,
        "backtest_wr": None,
        "notes": notes,
    }
    for attempt in range(3):
        try:
            r = requests.post(f"{_WORKER_URL}/bot/trade-log", json=payload, timeout=10)
            if r.status_code < 300:
                return True
        except Exception:
            pass
        if attempt < 2:
            time.sleep(2 ** attempt)
    try:
        from baret_live import _log
        _log(f"  ❌ TRADE LOG FAILED after 3 retries: {symbol} {side} {exit_reason} PnL=${pnl_dollar:.4f} [{notes}]")
    except Exception:
        pass
    return False
