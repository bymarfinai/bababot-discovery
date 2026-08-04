"""
Dual Instance Safety Guard — BabaBot v5.1

When two Railway instances share the same Binance API key/secret,
they can see each other's positions on the exchange. This module
provides flags that live trading modules check before performing
dangerous auto-cleanup actions:

1. Orphan cleanup at startup (baret_live.py)
2. Orphan adoption after warmup (bbc_live.py)
3. Auto-close in reconciliation (live_fixes/integrate.py)
4. SL/TP auto-fix for untracked positions (bbc_account_monitor.py)

Usage:
    from dual_instance_safe import DUAL_INSTANCE, INSTANCE_ID

    if not DUAL_INSTANCE:
        # safe to close orphans
    else:
        # log-only, don't close
"""

import os

# Set by Railway env var: "MAIN" or "CLONE"
INSTANCE_ID = os.environ.get("INSTANCE_ID", "")
DUAL_INSTANCE = bool(INSTANCE_ID)

if DUAL_INSTANCE:
    print(f"[GUARD] ═══ Dual-instance mode ACTIVE ═══")
    print(f"[GUARD] INSTANCE_ID = {INSTANCE_ID}")
    print(f"[GUARD] Orphan cleanup DISABLED")
    print(f"[GUARD] Orphan adoption DISABLED")
    print(f"[GUARD] Auto-reconciliation close DISABLED")
    print(f"[GUARD] SL/TP auto-fix for untracked positions DISABLED")
else:
    print(f"[GUARD] Single-instance mode — all safety features active")
