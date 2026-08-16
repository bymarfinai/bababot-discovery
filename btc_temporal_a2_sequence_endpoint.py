"""BTC Temporal A2 — dynamic causal sequence discovery.

Purpose
-------
Deepen the strongest A1 temporal cluster (Tuesday 06:00-08:00 WIB SELL)
without touching live trading.  The temporal anomaly is treated as a prior,
not as an automatic entry.

Causal architecture:
    TIME PRIOR -> PRE-WINDOW CONTEXT -> COMPLETED 15M EVENT SEQUENCE -> SELL/WAIT

Frozen rules for this first A2 pass:
- BTCUSDT only, existing 15m Railway DB.
- WIB / UTC+7.
- Research window: Tuesday 06:00 <= local time < 08:00.
- Context at 06:00 uses completed candles strictly before 06:00 only.
- Structural levels frozen at 06:00: HOD/LOD-so-far, local daily open,
  previous-1h high/low.
- Event triggers use completed 15m bars sequentially inside the window.
- Entry is the NEXT 15m bar open after the first qualifying trigger.
- At most one event/trade per Tuesday per rule.
- No same-trigger-bar outcome measurement.
- Outcomes: 30m/60m/120m/240m directional SELL, MFE/MAE and symmetric
  first-touch geometry.
- Candidate rules are a small, predeclared market-structure vocabulary;
  there is no indicator sweep or ML classifier.

This endpoint is discovery/forensic only. It does not place orders or modify
BBC live state.
"""

import math
import os
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

router = APIRouter(prefix="/research/btc-temporal-a2", tags=["btc_temporal_a2"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

TF_MS = 15 * 60 * 1000
DAY_MS = 24 * 60 * 60 * 1000
HORIZONS = (30, 60, 120, 240)
H_BARS = {m: m // 15 for m in HORIZONS}
THRESHOLDS = (0.3, 0.5, 0.8, 1.0)


def _median(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.median(vals)) if vals else None


def _mean(xs):
    vals = [float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return float(statistics.mean(vals)) if vals else None


def _r(x, n=4):
    return round(float(x), n) if x is not None and math.isfinite(float(x)) else None


def _load(days):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        max_ts = cur.execute(
            "SELECT MAX(open_time) FROM klines WHERE symbol='BTCUSDT' AND timeframe='15m'"
        ).fetchone()[0]
        if max_ts is None:
            return [], None, None
        end_ms = int(max_ts) + TF_MS
        start_ms = end_ms - days * DAY_MS
        rows = cur.execute(
            """
            SELECT open_time, open, high, low, close, volume
            FROM klines
            WHERE symbol='BTCUSDT' AND timeframe='15m'
              AND open_time>=? AND open_time<?
            ORDER BY open_time ASC
            """,
            (start_ms, end_ms),
        ).fetchall()
        return rows, start_ms, end_ms
    finally:
        conn.close()


def _local_dt(ts, tz):
    return datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).astimezone(tz)


def _bar_features(row):
    o, h, l, c = map(float, row[1:5])
    rng = max(0.0, h - l)
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return {
        "o": o, "h": h, "l": l, "c": c, "range": rng,
        "body": body,
        "body_ratio": body / rng if rng > 0 else 0.0,
        "upper_wick_ratio": upper / rng if rng > 0 else 0.0,
        "lower_wick_ratio": lower / rng if rng > 0 else 0.0,
        "close_loc": (c - l) / rng if rng > 0 else 0.5,
        "bear": c < o,
        "bull": c > o,
    }


def _first_touch(path, entry, threshold_pct):
    # SELL direction only.
    fav = entry * (1.0 - threshold_pct / 100.0)
    adv = entry * (1.0 + threshold_pct / 100.0)
    for row in path:
        hi, lo = float(row[2]), float(row[3])
        hit_f = lo <= fav
        hit_a = hi >= adv
        if hit_f and hit_a:
            return "AMBIGUOUS"
        if hit_f:
            return "FAVORABLE"
        if hit_a:
            return "ADVERSE"
    return "NONE"


def _metrics(events, blocks):
    if not events:
        return None
    signed = [-float(e["ret_pct"]) for e in events]  # SELL-positive
    wins = sum(x > 0 for x in signed)
    losses = sum(x < 0 for x in signed)
    resolved = wins + losses

    mfe, mae = [], []
    for e in events:
        entry = float(e["entry"])
        mfe.append(100.0 * (entry - float(e["min_low"])) / entry)
        mae.append(100.0 * (float(e["max_high"]) - entry) / entry)

    block_rows = []
    for b in range(blocks):
        xs = [-float(e["ret_pct"]) for e in events if e["block"] == b]
        bw = sum(x > 0 for x in xs)
        bl = sum(x < 0 for x in xs)
        br = bw + bl
        block_rows.append({
            "block": b + 1,
            "n": len(xs),
            "wr_pct": _r(100.0 * bw / br, 2) if br else None,
            "avg_signed_return_pct": _r(_mean(xs), 4),
        })
    wrs = [x["wr_pct"] for x in block_rows if x["wr_pct"] is not None]

    ft = {}
    for th in THRESHOLDS:
        counts = defaultdict(int)
        for e in events:
            counts[_first_touch(e["path"], e["entry"], th)] += 1
        decisive = counts["FAVORABLE"] + counts["ADVERSE"]
        ft[str(th)] = {
            "favorable": counts["FAVORABLE"],
            "adverse": counts["ADVERSE"],
            "ambiguous": counts["AMBIGUOUS"],
            "none": counts["NONE"],
            "decisive_wr_pct": _r(100.0 * counts["FAVORABLE"] / decisive, 2) if decisive else None,
        }

    med_mfe = _median(mfe)
    med_mae = _median(mae)
    return {
        "n": len(events),
        "wins": wins,
        "losses": losses,
        "wr_pct": _r(100.0 * wins / resolved, 2) if resolved else None,
        "avg_signed_return_pct": _r(_mean(signed), 4),
        "median_signed_return_pct": _r(_median(signed), 4),
        "median_mfe_pct": _r(med_mfe, 4),
        "median_mae_pct": _r(med_mae, 4),
        "mfe_mae_ratio": _r(med_mfe / med_mae, 4) if med_mae and med_mae > 0 else None,
        "positive_blocks_gt50": sum(x > 50 for x in wrs),
        "strong_blocks_ge60": sum(x >= 60 for x in wrs),
        "very_strong_blocks_ge65": sum(x >= 65 for x in wrs),
        "median_block_wr_pct": _r(_median(wrs), 2),
        "min_block_wr_pct": _r(min(wrs), 2) if wrs else None,
        "blocks": block_rows,
        "first_touch_symmetric_pct": ft,
    }


def _context(rows, idx, tz):
    """Context known at the OPEN of rows[idx], using prior bars only."""
    if idx < 16:
        return None
    anchor = rows[idx]
    ts = int(anchor[0])
    dt = _local_dt(ts, tz)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_ms = int(day_start.astimezone(timezone.utc).timestamp() * 1000)

    prior = rows[:idx]
    day_rows = [r for r in prior if int(r[0]) >= day_start_ms]
    if not day_rows:
        return None
    pre1 = rows[idx - 4:idx]
    pre4 = rows[idx - 16:idx]
    pre8 = rows[idx - 8:idx]

    entry = float(anchor[1])
    daily_open = float(day_rows[0][1])
    hod = max(float(r[2]) for r in day_rows)
    lod = min(float(r[3]) for r in day_rows)
    day_range = max(1e-12, hod - lod)
    pre1_open = float(pre1[0][1])
    pre4_open = float(pre4[0][1])
    prev1h_high = max(float(r[2]) for r in pre1)
    prev1h_low = min(float(r[3]) for r in pre1)
    ranges = [float(r[2]) - float(r[3]) for r in pre8]

    return {
        "entry": entry,
        "daily_open": daily_open,
        "hod": hod,
        "lod": lod,
        "day_pos": (entry - lod) / day_range,
        "pre1_ret": 100.0 * (entry - pre1_open) / pre1_open,
        "pre4_ret": 100.0 * (entry - pre4_open) / pre4_open,
        "prev1h_high": prev1h_high,
        "prev1h_low": prev1h_low,
        "pre_range_median": _median(ranges) or 0.0,
        "above_daily_open": entry >= daily_open,
        "upper_half": (entry - lod) / day_range >= 0.5,
        "upper_third": (entry - lod) / day_range >= (2.0 / 3.0),
        "pre1_up": entry > pre1_open,
        "pre4_up": entry > pre4_open,
    }


def _event_flags(bar, prev_bar, ctx, window_open, had_close_above_hod, had_trade_above_open):
    f = _bar_features(bar)
    pf = _bar_features(prev_bar) if prev_bar is not None else None
    rng_med = max(1e-12, float(ctx["pre_range_median"]))

    high_sweep_reject = f["h"] > ctx["hod"] and f["c"] < ctx["hod"]
    prev1h_high_reject = f["h"] > ctx["prev1h_high"] and f["c"] < ctx["prev1h_high"]
    breakdown_accept = f["c"] < ctx["prev1h_low"] and f["bear"]
    bearish_rejection = (
        f["bear"] and f["close_loc"] <= 0.40 and f["upper_wick_ratio"] >= 0.25
    )
    range_expansion_bear = f["bear"] and f["range"] >= 1.5 * rng_med
    two_bear = bool(pf and pf["bear"] and f["bear"] and f["c"] < pf["c"])
    open_loss = had_trade_above_open and f["c"] < window_open and f["bear"]
    failed_acceptance = had_close_above_hod and f["c"] < ctx["hod"] and f["bear"]

    return {
        "BEAR_CANDLE": f["bear"],
        "BEAR_REJECTION": bearish_rejection,
        "HOD_SWEEP_REJECT": high_sweep_reject,
        "PREV1H_HIGH_REJECT": prev1h_high_reject,
        "BREAKDOWN_ACCEPT": breakdown_accept,
        "RANGE_EXPANSION_BEAR": range_expansion_bear,
        "TWO_BEAR": two_bear,
        "OPEN_LOSS": open_loss,
        "FAILED_HOD_ACCEPTANCE": failed_acceptance,
    }


# Predeclared rule vocabulary.  Each is interpretable and causal.
RULES = {
    "HOD_SWEEP_REJECT": ("HOD_SWEEP_REJECT", None),
    "PREV1H_HIGH_REJECT": ("PREV1H_HIGH_REJECT", None),
    "BEAR_REJECTION": ("BEAR_REJECTION", None),
    "BREAKDOWN_ACCEPT": ("BREAKDOWN_ACCEPT", None),
    "RANGE_EXPANSION_BEAR": ("RANGE_EXPANSION_BEAR", None),
    "TWO_BEAR": ("TWO_BEAR", None),
    "OPEN_LOSS": ("OPEN_LOSS", None),
    "FAILED_HOD_ACCEPTANCE": ("FAILED_HOD_ACCEPTANCE", None),

    "PRE4_UP__HOD_SWEEP_REJECT": ("HOD_SWEEP_REJECT", "pre4_up"),
    "PRE4_UP__PREV1H_HIGH_REJECT": ("PREV1H_HIGH_REJECT", "pre4_up"),
    "PRE4_UP__BEAR_REJECTION": ("BEAR_REJECTION", "pre4_up"),
    "PRE4_UP__OPEN_LOSS": ("OPEN_LOSS", "pre4_up"),
    "PRE4_UP__FAILED_HOD_ACCEPTANCE": ("FAILED_HOD_ACCEPTANCE", "pre4_up"),

    "UPPER_HALF__BEAR_REJECTION": ("BEAR_REJECTION", "upper_half"),
    "UPPER_HALF__HOD_SWEEP_REJECT": ("HOD_SWEEP_REJECT", "upper_half"),
    "UPPER_HALF__OPEN_LOSS": ("OPEN_LOSS", "upper_half"),
    "UPPER_THIRD__BEAR_REJECTION": ("BEAR_REJECTION", "upper_third"),
    "UPPER_THIRD__HOD_SWEEP_REJECT": ("HOD_SWEEP_REJECT", "upper_third"),

    "ABOVE_DOPEN__BEAR_REJECTION": ("BEAR_REJECTION", "above_daily_open"),
    "ABOVE_DOPEN__OPEN_LOSS": ("OPEN_LOSS", "above_daily_open"),
    "PRE1_UP__BEAR_REJECTION": ("BEAR_REJECTION", "pre1_up"),
    "PRE1_UP__HOD_SWEEP_REJECT": ("HOD_SWEEP_REJECT", "pre1_up"),
}


@router.get("")
def temporal_a2(
    days: int = Query(971, ge=240, le=1500),
    blocks: int = Query(8, ge=4, le=12),
    min_n: int = Query(20, ge=10, le=100),
):
    rows, start_ms, end_ms = _load(days)
    if not rows:
        return {"error": "No BTCUSDT 15m data"}
    by_ts = {int(r[0]): i for i, r in enumerate(rows)}
    tz = timezone(timedelta(hours=7))
    span = max(1, end_ms - start_ms)

    # Each rule -> horizon -> events.  Rule fires only once per Tuesday window.
    events = defaultdict(lambda: defaultdict(list))
    baseline = defaultdict(list)
    occurrence_contexts = []

    for idx, row in enumerate(rows):
        ts = int(row[0])
        dt = _local_dt(ts, tz)
        if dt.weekday() != 1 or dt.hour != 6 or dt.minute != 0:  # Tuesday 06:00 WIB
            continue
        ctx = _context(rows, idx, tz)
        if ctx is None:
            continue
        block = min(blocks - 1, max(0, int((ts - start_ms) * blocks / span)))
        occurrence_contexts.append({
            "ts": ts, "block": block,
            "pre1_ret": _r(ctx["pre1_ret"]), "pre4_ret": _r(ctx["pre4_ret"]),
            "day_pos": _r(ctx["day_pos"]),
        })

        # Baseline exact 06:00 entry, for direct comparison with A1.
        for horizon in HORIZONS:
            hb = H_BARS[horizon]
            path = rows[idx:idx + hb]
            if len(path) != hb:
                continue
            entry = float(row[1])
            baseline[horizon].append({
                "ts": ts, "block": block, "entry": entry,
                "ret_pct": 100.0 * (float(path[-1][4]) - entry) / entry,
                "max_high": max(float(x[2]) for x in path),
                "min_low": min(float(x[3]) for x in path),
                "path": path,
            })

        window_open = float(row[1])
        fired = set()
        had_close_above_hod = False
        had_trade_above_open = False
        prev_bar = rows[idx - 1]

        # Observe 8 completed bars: 06:00..07:45. Entry is next bar open.
        for j in range(8):
            bi = idx + j
            if bi >= len(rows):
                break
            bar = rows[bi]
            if int(bar[0]) != ts + j * TF_MS:
                break
            flags = _event_flags(
                bar, prev_bar, ctx, window_open,
                had_close_above_hod, had_trade_above_open,
            )

            # State used for current bar was established only by earlier bars.
            for rule_name, (flag_name, context_name) in RULES.items():
                if rule_name in fired:
                    continue
                if not flags.get(flag_name, False):
                    continue
                if context_name and not bool(ctx.get(context_name)):
                    continue

                entry_i = bi + 1
                if entry_i >= len(rows) or int(rows[entry_i][0]) != int(bar[0]) + TF_MS:
                    continue
                entry_row = rows[entry_i]
                entry = float(entry_row[1])
                fired.add(rule_name)

                for horizon in HORIZONS:
                    hb = H_BARS[horizon]
                    path = rows[entry_i:entry_i + hb]
                    if len(path) != hb:
                        continue
                    # Require contiguous candles for the entire forward path.
                    if any(int(path[k][0]) != int(entry_row[0]) + k * TF_MS for k in range(hb)):
                        continue
                    events[rule_name][horizon].append({
                        "ts": int(entry_row[0]), "block": block, "entry": entry,
                        "trigger_local": _local_dt(int(bar[0]), tz).strftime("%H:%M"),
                        "entry_local": _local_dt(int(entry_row[0]), tz).strftime("%H:%M"),
                        "ret_pct": 100.0 * (float(path[-1][4]) - entry) / entry,
                        "max_high": max(float(x[2]) for x in path),
                        "min_low": min(float(x[3]) for x in path),
                        "path": path,
                    })

            bf = _bar_features(bar)
            had_close_above_hod = had_close_above_hod or (bf["c"] > ctx["hod"])
            had_trade_above_open = had_trade_above_open or (bf["h"] > window_open)
            prev_bar = bar

    baseline_out = {}
    for horizon in HORIZONS:
        m = _metrics(baseline[horizon], blocks)
        if m:
            baseline_out[str(horizon)] = m

    candidates = []
    for rule_name, by_h in events.items():
        for horizon in HORIZONS:
            xs = by_h.get(horizon, [])
            if len(xs) < min_n:
                continue
            m = _metrics(xs, blocks)
            if not m:
                continue
            trigger_counts = defaultdict(int)
            for e in xs:
                trigger_counts[e["trigger_local"]] += 1
            candidates.append({
                "rule": rule_name,
                "horizon_min": horizon,
                **m,
                "trigger_time_counts": dict(sorted(trigger_counts.items())),
            })

    # Discovery ranking prioritizes target WR, then sample/stability/geometry.
    by_wr = sorted(
        candidates,
        key=lambda x: (
            x["wr_pct"] if x["wr_pct"] is not None else -1,
            x["n"],
            x["positive_blocks_gt50"],
            x["median_block_wr_pct"] if x["median_block_wr_pct"] is not None else -1,
            x["mfe_mae_ratio"] if x["mfe_mae_ratio"] is not None else -1,
        ),
        reverse=True,
    )
    stability_first = sorted(
        candidates,
        key=lambda x: (
            x["very_strong_blocks_ge65"],
            x["strong_blocks_ge60"],
            x["positive_blocks_gt50"],
            x["wr_pct"] if x["wr_pct"] is not None else -1,
            x["n"],
        ),
        reverse=True,
    )

    target70 = [x for x in by_wr if x["wr_pct"] is not None and x["wr_pct"] >= 70.0]
    target65 = [x for x in by_wr if x["wr_pct"] is not None and x["wr_pct"] >= 65.0]

    expected = max(1, int((end_ms - start_ms) / TF_MS))
    return {
        "status": "BTC_TEMPORAL_A2_DYNAMIC_SEQUENCE",
        "symbol": "BTCUSDT",
        "timezone": "WIB (UTC+7)",
        "cluster": "Tuesday 06:00-08:00 SELL",
        "causal": True,
        "one_trigger_per_rule_per_tuesday": True,
        "entry": "next_15m_open_after_completed_trigger",
        "data": {
            "days": days,
            "rows_15m": len(rows),
            "expected_rows_15m": expected,
            "coverage_pct": _r(100.0 * len(rows) / expected, 2),
            "tuesday_occurrences": len(occurrence_contexts),
            "start_utc": datetime.fromtimestamp(start_ms / 1000.0, tz=timezone.utc).isoformat(),
            "end_utc_exclusive": datetime.fromtimestamp(end_ms / 1000.0, tz=timezone.utc).isoformat(),
        },
        "baseline_exact_0600": baseline_out,
        "rules_declared": list(RULES.keys()),
        "candidate_count": len(candidates),
        "target70_count": len(target70),
        "target65_count": len(target65),
        "leaderboard_wr": by_wr[:30],
        "leaderboard_stability": stability_first[:30],
        "target70": target70[:30],
        "target65": target65[:30],
        "notes": [
            "Temporal prior is permission, not automatic SELL.",
            "All sequence triggers are known before entry; trigger bar itself is never an entry bar.",
            "Directional WR and symmetric first-touch execution geometry are reported separately.",
            "A2 discovery rules are intentionally small/interpretable; no EMA/ML/random feature mining.",
        ],
    }
