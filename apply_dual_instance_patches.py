#!/usr/bin/env python3
"""
BabaBot Dual-Instance Isolation — Auto-Patch Script (Step 2)

Run this script ONCE in your repo root to patch all 4 conflict files:
  1. baret_live.py — disable orphan cleanup at startup
  2. bbc_live.py — disable orphan adoption after warmup
  3. live_fixes/integrate.py — disable auto-close in reconciliation
  4. bbc_account_monitor.py — skip SL/TP fix for untracked positions

Usage:
  cd /path/to/bababot-discovery
  python apply_dual_instance_patches.py

After running, commit and push:
  git add -A && git commit -m "feat: dual-instance isolation patches" && git push
"""

import re
import os
import sys


def patch_file(filepath, patches, description):
    """Apply text replacements to a file."""
    if not os.path.exists(filepath):
        print(f"  ⚠️  SKIP: {filepath} not found")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in patches:
        if old not in content:
            print(f"  ⚠️  Pattern not found in {filepath}:")
            print(f"       {old[:80]}...")
            continue
        content = content.replace(old, new, 1)

    if content == original:
        print(f"  ⏩ {filepath}: no changes needed (already patched?)")
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  ✅ {filepath}: {description}")
    return True


def main():
    print("═══ BabaBot Dual-Instance Isolation Patches ═══")
    print()

    changes = 0

    # ══════════════════════════════════════════════
    # PATCH 1: baret_live.py — disable orphan cleanup at startup
    # ══════════════════════════════════════════════
    print("1️⃣  baret_live.py — orphan cleanup → log-only")

    # Add import at top (after existing imports)
    p1_patches = []

    # Add dual_instance_safe import after urlencode import
    p1_patches.append((
        "from urllib.parse import urlencode",
        "from urllib.parse import urlencode\nfrom dual_instance_safe import DUAL_INSTANCE, INSTANCE_ID"
    ))

    # Replace orphan cleanup section with guarded version
    p1_patches.append((
        '''    # ── Auto-cleanup orphan positions ──
    _log(f"{prefix}  🔍 Checking for orphan positions...")
    orphan_count = 0
    for cfg in configs:
        symbol = cfg["symbol"]
        try:
            pos = client.get_position(symbol)
            if pos:
                amt = float(pos.get("positionAmt", 0))
                if amt != 0:
                    side_close = "SELL" if amt > 0 else "BUY"
                    client.cancel_all_orders(symbol)
                    _cancel_sl_tp(client, symbol)
                    client.place_market_close(symbol, side_close, abs(amt))
                    _log(f"{prefix}  🧹 {symbol}: closed orphan {\\'LONG\\' if amt > 0 else \\'SHORT\\'} {abs(amt)}")
                    orphan_count += 1
        except Exception as e:
            _log(f"{prefix}  ⚠️ Orphan cleanup {symbol}: {e}")
    _log(f"{prefix}  ✅ {orphan_count} orphan positions cleaned" if orphan_count else f"{prefix}  ✅ No orphan positions")''',

        '''    # ── Auto-cleanup orphan positions (DUAL-INSTANCE SAFE) ──
    _log(f"{prefix}  🔍 Checking for orphan positions...")
    orphan_count = 0
    for cfg in configs:
        symbol = cfg["symbol"]
        try:
            pos = client.get_position(symbol)
            if pos:
                amt = float(pos.get("positionAmt", 0))
                if amt != 0:
                    if DUAL_INSTANCE:
                        _log(f"{prefix}  ⚠️ {symbol}: found existing {\\'LONG\\' if amt > 0 else \\'SHORT\\'} {abs(amt)} — NOT closing (INSTANCE={INSTANCE_ID}, may belong to other instance)")
                    else:
                        side_close = "SELL" if amt > 0 else "BUY"
                        client.cancel_all_orders(symbol)
                        _cancel_sl_tp(client, symbol)
                        client.place_market_close(symbol, side_close, abs(amt))
                        _log(f"{prefix}  🧹 {symbol}: closed orphan {\\'LONG\\' if amt > 0 else \\'SHORT\\'} {abs(amt)}")
                    orphan_count += 1
        except Exception as e:
            _log(f"{prefix}  ⚠️ Orphan cleanup {symbol}: {e}")
    if DUAL_INSTANCE:
        _log(f"{prefix}  ⚠️ {orphan_count} existing positions detected (not closed, dual-instance)" if orphan_count else f"{prefix}  ✅ No existing positions")
    else:
        _log(f"{prefix}  ✅ {orphan_count} orphan positions cleaned" if orphan_count else f"{prefix}  ✅ No orphan positions")'''
    ))

    if patch_file("baret_live.py", p1_patches, "orphan cleanup guarded"):
        changes += 1


    # ══════════════════════════════════════════════
    # PATCH 2: bbc_live.py — disable orphan adoption after warmup
    # ══════════════════════════════════════════════
    print("2️⃣  bbc_live.py — orphan adoption → log-only")

    p2_patches = []

    # Add import after existing imports
    p2_patches.append((
        "from bbc_account_monitor import check_account_health",
        "from bbc_account_monitor import check_account_health\nfrom dual_instance_safe import DUAL_INSTANCE, INSTANCE_ID"
    ))

    # Guard the orphan adoption section
    p2_patches.append((
        '''        # ═══ ORPHAN ADOPTION (v3.2 — was log-only, now adopts) ═══
        for symbol in symbols:
            ps = pair_states[symbol]
            if not ps.warmup_ok:
                continue
            try:
                pos = client.get_position(symbol)
                if pos and float(pos.get("positionAmt", 0)) != 0:
                    amt = float(pos["positionAmt"])
                    side = "LONG" if amt > 0 else "SHORT"
                    entry = float(pos.get("entryPrice", 0))
                    if ps.exchange_position:
                        continue
                    if side == "LONG":
                        tp = entry * (1 + ps.config.tp_pct)
                        sl = entry * (1 - ps.config.sl_pct)
                    else:
                        tp = entry * (1 - ps.config.get_bear_tp_pct())
                        sl = entry * (1 + ps.config.get_bear_sl_pct())
                    _log(f"{prefix}  📌 ADOPTING {symbol}: {side} @ ${entry:.4f} | setting TP=${tp:.4f} SL=${sl:.4f}")
                    try:
                        _cancel_sl_tp(client, symbol)
                    except:
                        pass
                    sl_tp = _place_sl_tp(client, symbol, side, sl, tp)
                    ps.exchange_position = {
                        "side": side, "entry": entry, "qty": abs(amt),
                        "tp": tp, "sl": sl, "tool": "ADOPTED",
                        "sl_algo_id": sl_tp.get("sl", {}).get("algoId"),
                        "tp_algo_id": sl_tp.get("tp", {}).get("algoId"),
                        "filled_at": datetime.now(timezone.utc).isoformat(),
                    }
                    state["positions"][symbol] = {
                        "side": side, "entry": entry, "qty": abs(amt),
                        "tp": tp, "sl": sl, "tool": "ADOPTED",
                    }
                    _send_telegram(f"📌 *ADOPTED ORPHAN*\\n{symbol} {side} @ ${entry:.4f}\\nTP: ${tp:.4f} SL: ${sl:.4f}")
            except Exception as e:
                _log(f"{prefix}  ⚠️ Orphan check {symbol}: {e}")''',

        '''        # ═══ ORPHAN ADOPTION (v3.2 — DUAL-INSTANCE SAFE) ═══
        for symbol in symbols:
            ps = pair_states[symbol]
            if not ps.warmup_ok:
                continue
            try:
                pos = client.get_position(symbol)
                if pos and float(pos.get("positionAmt", 0)) != 0:
                    amt = float(pos["positionAmt"])
                    side = "LONG" if amt > 0 else "SHORT"
                    entry = float(pos.get("entryPrice", 0))
                    if ps.exchange_position:
                        continue
                    if DUAL_INSTANCE:
                        _log(f"{prefix}  ⚠️ {symbol}: found {side} @ ${entry:.4f} — NOT adopting (INSTANCE={INSTANCE_ID}, may belong to other instance)")
                        continue
                    if side == "LONG":
                        tp = entry * (1 + ps.config.tp_pct)
                        sl = entry * (1 - ps.config.sl_pct)
                    else:
                        tp = entry * (1 - ps.config.get_bear_tp_pct())
                        sl = entry * (1 + ps.config.get_bear_sl_pct())
                    _log(f"{prefix}  📌 ADOPTING {symbol}: {side} @ ${entry:.4f} | setting TP=${tp:.4f} SL=${sl:.4f}")
                    try:
                        _cancel_sl_tp(client, symbol)
                    except:
                        pass
                    sl_tp = _place_sl_tp(client, symbol, side, sl, tp)
                    ps.exchange_position = {
                        "side": side, "entry": entry, "qty": abs(amt),
                        "tp": tp, "sl": sl, "tool": "ADOPTED",
                        "sl_algo_id": sl_tp.get("sl", {}).get("algoId"),
                        "tp_algo_id": sl_tp.get("tp", {}).get("algoId"),
                        "filled_at": datetime.now(timezone.utc).isoformat(),
                    }
                    state["positions"][symbol] = {
                        "side": side, "entry": entry, "qty": abs(amt),
                        "tp": tp, "sl": sl, "tool": "ADOPTED",
                    }
                    _send_telegram(f"📌 *ADOPTED ORPHAN*\\n{symbol} {side} @ ${entry:.4f}\\nTP: ${tp:.4f} SL: ${sl:.4f}")
            except Exception as e:
                _log(f"{prefix}  ⚠️ Orphan check {symbol}: {e}")'''
    ))

    if patch_file("bbc_live.py", p2_patches, "orphan adoption guarded"):
        changes += 1


    # ══════════════════════════════════════════════
    # PATCH 3: live_fixes/integrate.py — disable auto-close in reconciliation
    # ══════════════════════════════════════════════
    print("3️⃣  live_fixes/integrate.py — reconciliation auto-close → log-only")

    p3_patches = []

    # Add import at top of file
    p3_patches.append((
        "import traceback",
        "import traceback\nfrom dual_instance_safe import DUAL_INSTANCE, INSTANCE_ID"
    ))

    # Guard the "close orphan" action in reconciliation
    # The reconciliation code closes positions not tracked by the bot.
    # In dual-instance mode, these may belong to the other instance.
    # Look for the pattern where it closes untracked positions
    p3_patches.append((
        '                    _log(f"[RECON] ⚠️ {symbol}: exchange has position but bot doesn\'t track it — closing orphan")',
        '                    if DUAL_INSTANCE:\n'
        '                        _log(f"[RECON] ⚠️ {symbol}: exchange has position but bot doesn\'t track it — NOT closing (INSTANCE={INSTANCE_ID}, may belong to other instance)")\n'
        '                        continue\n'
        '                    _log(f"[RECON] ⚠️ {symbol}: exchange has position but bot doesn\'t track it — closing orphan")'
    ))

    if patch_file("live_fixes/integrate.py", p3_patches, "reconciliation auto-close guarded"):
        changes += 1


    # ══════════════════════════════════════════════
    # PATCH 4: bbc_account_monitor.py — skip SL/TP fix for untracked positions
    # ══════════════════════════════════════════════
    print("4️⃣  bbc_account_monitor.py — SL/TP auto-fix → log-only for untracked")

    p4_patches = []

    # Add import
    p4_patches.append((
        "import requests as req",
        "import requests as req\nfrom dual_instance_safe import DUAL_INSTANCE, INSTANCE_ID"
    ))

    # Guard the SL/TP auto-fix for positions not tracked by this instance
    p4_patches.append((
        '            # Position exists but no SL/TP — fix it',
        '            # Position exists but no SL/TP — fix it\n'
        '            if DUAL_INSTANCE:\n'
        '                _log(f"[MONITOR] ⚠️ {symbol}: has position without SL/TP — NOT fixing (INSTANCE={INSTANCE_ID}, may belong to other instance)")\n'
        '                continue'
    ))

    if patch_file("bbc_account_monitor.py", p4_patches, "SL/TP auto-fix guarded"):
        changes += 1


    # ══════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════
    print()
    print(f"═══ DONE: {changes}/4 files patched ═══")
    if changes > 0:
        print()
        print("Next steps:")
        print("  1. Review changes: git diff")
        print("  2. Commit:  git add -A && git commit -m 'feat: dual-instance isolation patches'")
        print("  3. Push:    git push")
        print("  4. Railway will auto-redeploy Main instance")
        print()
        print("NOTE: Clone instance (bababot-discovery-v23jul) does NOT need these patches")
        print("      because it's a separate repo with its own code.")
    else:
        print("  No changes were made. Files may already be patched.")


if __name__ == "__main__":
    main()
