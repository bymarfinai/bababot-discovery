"""
BBC Live Trading — v3.1: Detection + Reconciliation.

v3.0 FIX: MTF 15m enabled in switcher config (not manually checked outside).
     Entry price = 15m close (same as backtest), not 1H close.
     Warmup pre-computes MTF arrays. Live cycle extends per bar.

v2.2: Per-pair configs + state-safe SKIP handling.

v3.1: Detection layers — phantom position check after warmup + dead bot alert.
      Post-restart trade reconciliation via exchange history.
"""

import time
import threading
import traceback
import numpy as np
from datetime import datetime, timezone, timedelta
from collections import deque

from baret_live import (
    ExchangeClient, _log, _send_telegram, _get_price,
    _fetch_candles, _calc_quantity, _place_sl_tp, _cancel_sl_tp,
    _fmt_price, _fmt_qty, _log_trade_to_d1,
    _get_default_client, _account_bots,
    PRECISION,
)
from mode3_bbc.config import Mode3BBCConfig
from mode3_bbc.switcher import Switcher
from bbc_reconcile import reconcile_missed_trades
