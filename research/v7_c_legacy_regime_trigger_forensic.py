#!/usr/bin/env python3
"""V7-C — exact legacy BBC skip-SIDEWAYS trigger forensic.

Research-only forensic. No live/order integration.

Purpose:
- Reproduce the historical 971-day, 4-pair skip-SIDEWAYS BBC fingerprint:
  4,945 trades, 3,237 wins, 1,708 losses, WR 65.46%, PnL +$6,229.75.
- Use the exact economic configuration implied by that fingerprint:
  EMA7, TP=1.3%, SL=1.3%, $10 entry, 50x, 0.10% fee + 0.05% slippage.
- Preserve the legacy 15m MTF entry mechanics and body-ratio gates.
- Instrument the unmodified Switcher externally to label the pre-entry state / trigger path.
- Break results down by trigger, pair, side, and four chronological blocks.

This script does NOT optimize parameters. Historical end-time is fixed near the
August 4, 2026 skip-SIDEWAYS experiment. If the known fingerprint is not matched,
results are marked parity-failed and must not be promoted as the canonical breakdown.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np

import v7_regime_failed_breakout as data
from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar

PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
DAYS = 971
# The true skip-SIDEWAYS implementation/fix landed Aug 4 around 13:31 UTC.
# Use 14:00 UTC as the first frozen reconstruction boundary (full-hour aligned).
END = datetime(2026, 8, 4, 14, 0, 0, tzinfo=timezone.utc)
START = END - timedelta(days=DAYS)

TARGET = {
    "trades": 4945,
    "wins": 3237,
    "losses": 1708,
    "wr_pct": 65.46,
    "pnl_usd": 6229.75,
    "per_pair_pnl": {
        "BTCUSDT": 826.00,
        "ETHUSDT": 1847.50,
        "SOLUSDT": 2258.25,
        "BNBUSDT": 1298.00,
    },
}


def compute_mtf_bull_entry(rows_1h, rows_15m):
    if not rows_15m:
        return [None] * len(rows_1h), [None] * len(rows_1h)
    o15 = np.array([r["open"] for r in rows_15m], dtype=float)
    l15 = np.array([r["low"] for r in rows_15m], dtype=float)
    c15 = np.array([r["close"] for r in rows_15m], dtype=float)
    ema15 = compute_ema_series(c15, 20)
    idx = {r["t"]: i for i, r in enumerate(rows_15m)}
    step = timedelta(minutes=15)
    ec, el = [], []
    for r in rows_1h:
        t = r["t"]; fc = fl = None
        for k in range(4):
            j = idx.get(t + k * step)
            if j is not None and l15[j] <= ema15[j] and c15[j] > ema15[j] and c15[j] > o15[j]:
                fc = float(c15[j]); fl = float(l15[j]); break
        ec.append(fc); el.append(fl)
    return ec, el


def compute_mtf_bear_entry(rows_1h, rows_15m):
    if not rows_15m:
        return [None] * len(rows_1h), [None] * len(rows_1h)
    o15 = np.array([r["open"] for r in rows_15m], dtype=float)
    h15 = np.array([r["high"] for r in rows_15m], dtype=float)
    c15 = np.array([r["close"] for r in rows_15m], dtype=float)
    ema15 = compute_ema_series(c15, 20)
    idx = {r["t"]: i for i, r in enumerate(rows_15m)}
    step = timedelta(minutes=15)
    ec, eh = [], []
    for r in rows_1h:
        t = r["t"]; fc = fh = None
        for k in range(4):
            j = idx.get(t + k * step)
            if j is not None and h15[j] >= ema15[j] and c15[j] < ema15[j] and c15[j] < o15[j]:
                fc = float(c15[j]); fh = float(h15[j]); break
        ec.append(fc); eh.append(fh)
    return ec, eh


def trigger_label(pre_state, post_state, tool, pos_trigger):
    if tool == "BULL":
        if pre_state == "BULL": return "BULL_STAY_EMA_RECLAIM"
        if pre_state == "SIDEWAYS": return "DIRECT_SIDEWAYS_TO_BULL"
        if pre_state == "WAIT_SEE_BEARISH": return "DIRECT_WAIT_BEARISH_TO_BULL"
        if pre_state == "BEAR": return "DIRECT_BEAR_TO_BULL"
        if pre_state == "STARTUP": return "STARTUP_TO_BULL"
        return f"BULL_FROM_{pre_state}_{pos_trigger or 'EMA_RECLAIM'}"
    if tool == "BEAR":
        if pre_state == "BEAR": return "BEAR_STAY_EMA_REJECTION"
        if pre_state == "SIDEWAYS": return "DIRECT_SIDEWAYS_TO_BEAR"
        if pre_state == "WAIT_SEE_BULLISH": return "DIRECT_WAIT_BULLISH_TO_BEAR"
        if pre_state == "BULL": return "DIRECT_BULL_TO_BEAR"
        if pre_state == "STARTUP": return "STARTUP_TO_BEAR"
        return f"BEAR_FROM_{pre_state}"
    return f"{tool}_FROM_{pre_state}"


def stat(rows):
    n = len(rows)
    wins = sum(r["win"] for r in rows)
    losses = n - wins
    pnl = sum(r["pnl_usd"] for r in rows)
    return {
        "trades": n,
        "wins": wins,
        "losses": losses,
        "wr_pct": round(100.0 * wins / n, 2) if n else None,
        "pnl_usd": round(pnl, 2),
        "expectancy_usd": round(pnl / n, 4) if n else None,
    }


def build_config():
    return Mode3BBCConfig(
        ema_period=7,
        tp_pct=0.013,
        sl_pct=0.013,
        bear_tp_pct=0.0,
        bear_sl_pct=0.0,
        enable_sideways_trades=False,
        direct_transition_enabled=True,
        use_wick_exit=True,
        entry_usd=10.0,
        leverage=50.0,
        fee_pct_roundtrip=0.001,
        slippage_pct=0.0005,
        bull_mtf_15m_enabled=True,
        bull_body_ratio_min=0.5,
        bear_mtf_15m_enabled=True,
        bear_body_ratio_min=0.6,
        sideways_mtf_15m_enabled=True,
        sideways_body_ratio_min=0.6,
        trailing_ema_enabled=False,
        bull_poc_entry_enabled=False,
        bull_wait_retest_enabled=False,
        bull_use_swing_break=False,
        bull_use_26_support=False,
        sideways_poc_breakout_enabled=False,
    )


def run_pair(symbol):
    rows1 = data.load_klines(symbol, "1h", START, END)
    rows15 = data.load_klines(symbol, "15m", START, END)
    cfg = build_config()
    if len(rows1) < cfg.startup_warmup_candles:
        raise RuntimeError(f"{symbol}: insufficient 1h rows {len(rows1)}")

    O = np.array([r["open"] for r in rows1], dtype=float)
    H = np.array([r["high"] for r in rows1], dtype=float)
    L = np.array([r["low"] for r in rows1], dtype=float)
    C = np.array([r["close"] for r in rows1], dtype=float)
    V = np.array([r["volume"] for r in rows1], dtype=float)
    ema = compute_ema_series(C, cfg.ema_period)

    vahs, vals, pocs = [], [], []
    for i in range(len(rows1)):
        vah, val, poc = compute_va_at_bar(H, L, C, V, i, cfg.va_window, cfg.va_percentile_high, cfg.va_percentile_low)
        vahs.append(vah); vals.append(val); pocs.append(poc)

    sw = Switcher(cfg)
    bec, bel = compute_mtf_bull_entry(rows1, rows15)
    sec, seh = compute_mtf_bear_entry(rows1, rows15)
    sw.mtf_bull_entry_close = bec; sw.mtf_bull_entry_low = bel
    sw.mtf_bear_entry_close = sec; sw.mtf_bear_entry_high = seh

    entry_meta = {}
    entry_counts = Counter()
    for i in range(len(rows1)):
        pre_state = sw.state
        pre_had_pos = sw.position is not None
        sw.process_candle(i, O[i], H[i], L[i], C[i], ema[i], vahs[i], vals[i], pocs[i])
        if not pre_had_pos and sw.position is not None:
            pos = sw.position
            label = trigger_label(pre_state, sw.state, pos.tool, getattr(pos, "entry_trigger", ""))
            entry_counts[label] += 1
            entry_meta[i] = {
                "trigger": label,
                "pre_state": pre_state,
                "post_state": sw.state,
                "entry_time": rows1[i]["t"],
                "tool": pos.tool,
                "side": pos.side,
            }

    rows = []
    missing_meta = 0
    for t in sw.trades:
        meta = entry_meta.get(t.entry_bar)
        if meta is None:
            missing_meta += 1
            meta = {"trigger": "UNLABELED", "pre_state": None, "post_state": None,
                    "entry_time": rows1[t.entry_bar]["t"], "tool": t.tool, "side": t.side}
        rows.append({
            "symbol": symbol,
            "trigger": meta["trigger"],
            "pre_state": meta["pre_state"],
            "tool": t.tool,
            "side": t.side,
            "entry_time": meta["entry_time"],
            "exit_time": rows1[t.exit_bar]["t"] if 0 <= t.exit_bar < len(rows1) else None,
            "exit_type": t.exit_type,
            "pnl_usd": float(t.pnl_usd),
            "win": bool(t.pnl_usd > 0),
        })

    return rows, {
        "bars_1h": len(rows1), "bars_15m": len(rows15),
        "first_1h": rows1[0]["t"].isoformat() if rows1 else None,
        "last_1h": rows1[-1]["t"].isoformat() if rows1 else None,
        "entries_opened": int(sum(entry_counts.values())),
        "trades_closed": len(rows), "open_position_at_end": sw.position is not None,
        "missing_entry_metadata": missing_meta,
        "entry_counts": dict(entry_counts),
    }


def main():
    all_rows = []
    coverage = {}; errors = {}
    for p in PAIRS:
        try:
            rows, cov = run_pair(p)
            all_rows.extend(rows); coverage[p] = cov
        except Exception as ex:
            errors[p] = str(ex)

    overall = stat(all_rows)
    by_pair = {p: stat([r for r in all_rows if r["symbol"] == p]) for p in PAIRS}
    triggers = sorted(set(r["trigger"] for r in all_rows))
    by_trigger = {g: stat([r for r in all_rows if r["trigger"] == g]) for g in triggers}
    by_tool = {x: stat([r for r in all_rows if r["tool"] == x]) for x in ("BULL", "BEAR")}
    by_side = {x: stat([r for r in all_rows if r["side"] == x]) for x in ("LONG", "SHORT")}

    by_trigger_pair = {}
    for g in triggers:
        by_trigger_pair[g] = {p: stat([r for r in all_rows if r["trigger"] == g and r["symbol"] == p]) for p in PAIRS}

    span = END - START
    cuts = [START + span * k / 4 for k in range(5)]
    block_names = ["Q1_early", "Q2", "Q3", "Q4_recent"]
    by_block = {}
    by_trigger_block = {g: {} for g in triggers}
    for k, name in enumerate(block_names):
        lo, hi = cuts[k], cuts[k + 1]
        xs = [r for r in all_rows if lo <= r["entry_time"] < hi]
        by_block[name] = {**stat(xs), "start": lo.isoformat(), "end": hi.isoformat()}
        for g in triggers:
            by_trigger_block[g][name] = stat([r for r in xs if r["trigger"] == g])

    target_delta = {
        "trades": overall["trades"] - TARGET["trades"],
        "wins": overall["wins"] - TARGET["wins"],
        "losses": overall["losses"] - TARGET["losses"],
        "pnl_usd": round(overall["pnl_usd"] - TARGET["pnl_usd"], 2),
        "per_pair_pnl": {p: round(by_pair[p]["pnl_usd"] - TARGET["per_pair_pnl"][p], 2) for p in PAIRS},
    }
    parity_pass = (
        target_delta["trades"] == 0 and target_delta["wins"] == 0 and
        target_delta["losses"] == 0 and abs(target_delta["pnl_usd"]) < 0.01 and
        all(abs(v) < 0.01 for v in target_delta["per_pair_pnl"].values())
    )

    # Stability diagnostics: not a filter-selection gate. Identify triggers with
    # adequate sample and positive edge across pair/time dimensions.
    robustness = {}
    for g in triggers:
        s = by_trigger[g]
        pair_pos = sum(1 for p in PAIRS if by_trigger_pair[g][p]["trades"] >= 20 and by_trigger_pair[g][p]["expectancy_usd"] is not None and by_trigger_pair[g][p]["expectancy_usd"] > 0)
        block_pos = sum(1 for b in block_names if by_trigger_block[g][b]["trades"] >= 20 and by_trigger_block[g][b]["expectancy_usd"] is not None and by_trigger_block[g][b]["expectancy_usd"] > 0)
        robustness[g] = {
            "trades": s["trades"], "wr_pct": s["wr_pct"], "pnl_usd": s["pnl_usd"],
            "positive_expectancy_pairs_n": pair_pos,
            "positive_expectancy_blocks_n": block_pos,
            "all_4_pairs_positive": pair_pos == 4,
            "all_4_blocks_positive": block_pos == 4,
        }

    result = {
        "phase": "V7-C",
        "status": "LEGACY_SKIP_SIDEWAYS_971D_TRIGGER_FORENSIC",
        "window": {"start": START.isoformat(), "end_exclusive": END.isoformat(), "days": DAYS},
        "frozen_config": {
            "ema_period": 7, "tp_pct": 0.013, "sl_pct": 0.013,
            "entry_usd": 10, "leverage": 50,
            "fee_pct_roundtrip": 0.001, "slippage_pct": 0.0005,
            "total_cost_pct": 0.0015,
            "enable_sideways_trades": False,
            "direct_transition_enabled": True,
            "bull_mtf_15m_enabled": True, "bear_mtf_15m_enabled": True,
            "bull_body_ratio_min": 0.5, "bear_body_ratio_min": 0.6,
            "use_wick_exit": True,
            "parameter_optimization": False,
        },
        "known_historical_fingerprint": TARGET,
        "parity": {"pass": parity_pass, "delta": target_delta},
        "coverage": coverage, "errors": errors,
        "overall": overall, "by_pair": by_pair, "by_tool": by_tool, "by_side": by_side,
        "by_trigger": by_trigger,
        "by_trigger_pair": by_trigger_pair,
        "by_block": by_block,
        "by_trigger_block": by_trigger_block,
        "trigger_robustness_diagnostic": robustness,
        "interpretation_lock": (
            "If parity.pass is false, use this run only to diagnose reconstruction mismatch; "
            "do not promote trigger rankings as the canonical historical breakdown."
        ),
    }
    print("V7_C_RESULT", json.dumps(result, separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
