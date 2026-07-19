"""
SL/TP Placement with Retry — Fix for silent algoOrder failures.

Replaces _place_sl_tp in baret_live.py.
Retry up to 3 times. If ALL retries fail -> Telegram alert.
"""

import time


def place_sl_tp_with_retry(client, symbol, position_side, sl_price, tp_price,
                            _log_fn=None, _send_telegram_fn=None,
                            _fmt_price_fn=None, max_retries=3):
    """Place SL and TP via algoOrder with retry logic.
    
    If ALL retries fail -> Telegram alert CRITICAL.
    Returns: dict with "sl" and "tp" results (each containing algoId on success)
    """
    _log = _log_fn or (lambda msg: print(f"[SL/TP] {msg}"))
    _send_telegram = _send_telegram_fn or (lambda msg: None)
    _fmt_price = _fmt_price_fn or (lambda s, p: f"{p:.6f}")

    close_side = "SELL" if position_side == "LONG" else "BUY"
    results = {}

    # SL with retry
    for attempt in range(1, max_retries + 1):
        try:
            r = client.place_algo_order(symbol, close_side, "STOP_MARKET", sl_price)
            if r.get("algoId"):
                results["sl"] = r
                break
            _log(f"    SL attempt {attempt}/{max_retries} failed: {r.get('msg', r)}")
            if attempt < max_retries:
                time.sleep(1)
        except Exception as e:
            _log(f"    SL attempt {attempt}/{max_retries} error: {e}")
            if attempt < max_retries:
                time.sleep(1)

    if "sl" not in results:
        _log(f"    CRITICAL: SL placement FAILED after {max_retries} attempts for {symbol}!")
        _send_telegram(
            f"*CRITICAL: SL FAILED*\n"
            f"{symbol} {position_side}\n"
            f"SL @ ${_fmt_price(symbol, sl_price)}\n"
            f"Position UNPROTECTED! Close manually!"
        )
        results["sl"] = {"error": f"Failed after {max_retries} attempts"}

    # TP with retry
    for attempt in range(1, max_retries + 1):
        try:
            r = client.place_algo_order(symbol, close_side, "TAKE_PROFIT_MARKET", tp_price)
            if r.get("algoId"):
                results["tp"] = r
                break
            _log(f"    TP attempt {attempt}/{max_retries} failed: {r.get('msg', r)}")
            if attempt < max_retries:
                time.sleep(1)
        except Exception as e:
            _log(f"    TP attempt {attempt}/{max_retries} error: {e}")
            if attempt < max_retries:
                time.sleep(1)

    if "tp" not in results:
        _log(f"    CRITICAL: TP placement FAILED after {max_retries} attempts for {symbol}!")
        _send_telegram(
            f"*CRITICAL: TP FAILED*\n"
            f"{symbol} {position_side}\n"
            f"TP @ ${_fmt_price(symbol, tp_price)}\n"
            f"No take-profit set! Monitor manually!"
        )
        results["tp"] = {"error": f"Failed after {max_retries} attempts"}

    return results
