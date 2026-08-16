"""BTC Temporal A2.1 — refine the strongest executable Tuesday sequence.

Frozen parent state from A2:
    Tuesday 06:00-08:00 WIB SELL prior
    + price in upper half of day range at 06:00
    + after trading above the 06:00 window open, a completed 15m bar closes
      back below that open (OPEN_LOSS)
    + entry on the next 15m open

A2 parent produced strong excursion geometry but not yet >=70% executable WR.
This endpoint deepens only that coherent path. It tests predeclared causal
substates: trigger timing, prior 24h/7d direction, and event sequence around
HOD/previous-1h liquidity. No EMA, ML, or arbitrary numeric threshold sweep.
"""

from collections import defaultdict
from datetime import timezone, timedelta
from fastapi import APIRouter, Query

from btc_temporal_a2_sequence_endpoint import (
    _load, _local_dt, _context, _bar_features, _metrics,
    TF_MS, DAY_MS, HORIZONS, H_BARS,
)

router = APIRouter(prefix="/research/btc-temporal-a2-refine", tags=["btc_temporal_a2_refine"])


def _extended_context(rows, idx, base):
    entry = float(rows[idx][1])
    out = dict(base)
    if idx >= 96:
        o24 = float(rows[idx - 96][1])
        out["pre24_ret"] = 100.0 * (entry - o24) / o24
        out["pre24_up"] = entry > o24
        out["pre24_down"] = entry < o24
    else:
        out["pre24_ret"] = None; out["pre24_up"] = False; out["pre24_down"] = False
    if idx >= 672:
        o7 = float(rows[idx - 672][1])
        out["pre7d_ret"] = 100.0 * (entry - o7) / o7
        out["pre7d_up"] = entry > o7
        out["pre7d_down"] = entry < o7
    else:
        out["pre7d_ret"] = None; out["pre7d_up"] = False; out["pre7d_down"] = False
    return out


def _event(entry_row, path, block, trigger_local):
    entry = float(entry_row[1])
    return {
        "ts": int(entry_row[0]),
        "block": block,
        "entry": entry,
        "trigger_local": trigger_local,
        "ret_pct": 100.0 * (float(path[-1][4]) - entry) / entry,
        "max_high": max(float(x[2]) for x in path),
        "min_low": min(float(x[3]) for x in path),
        "path": path,
    }


@router.get("")
def refine(days: int = Query(971, ge=240, le=1500), blocks: int = Query(8, ge=4, le=12), min_n: int = Query(12, ge=8, le=80)):
    rows, start_ms, end_ms = _load(days)
    if not rows:
        return {"error": "No BTCUSDT 15m data"}
    tz = timezone(timedelta(hours=7))
    span = max(1, end_ms - start_ms)
    events = defaultdict(lambda: defaultdict(list))
    tuesdays = 0

    for idx, row in enumerate(rows):
        ts = int(row[0])
        dt = _local_dt(ts, tz)
        if dt.weekday() != 1 or dt.hour != 6 or dt.minute != 0:
            continue
        base = _context(rows, idx, tz)
        if base is None:
            continue
        ctx = _extended_context(rows, idx, base)
        tuesdays += 1
        block = min(blocks - 1, max(0, int((ts - start_ms) * blocks / span)))
        window_open = float(row[1])

        had_trade_above_open = False
        had_hod_attack = False
        had_hod_close_above = False
        had_prev1h_high_attack = False
        had_bear_rejection = False
        fired = set()
        prev = rows[idx - 1]

        for j in range(8):
            bi = idx + j
            if bi >= len(rows) or int(rows[bi][0]) != ts + j * TF_MS:
                break
            bar = rows[bi]
            f = _bar_features(bar)
            pf = _bar_features(prev)
            range_med = max(1e-12, float(ctx["pre_range_median"]))

            open_loss = had_trade_above_open and f["bear"] and f["c"] < window_open
            breakdown = f["bear"] and f["c"] < ctx["prev1h_low"]
            range_exp = f["bear"] and f["range"] >= 1.5 * range_med
            bear_rej = f["bear"] and f["close_loc"] <= 0.40 and f["upper_wick_ratio"] >= 0.25
            hod_sweep_now = f["h"] > ctx["hod"] and f["c"] < ctx["hod"]
            prev1h_reject_now = f["h"] > ctx["prev1h_high"] and f["c"] < ctx["prev1h_high"]
            two_bear = pf["bear"] and f["bear"] and f["c"] < pf["c"]

            if ctx["upper_half"] and open_loss:
                rules = {
                    "PARENT_UPPER_HALF_OPEN_LOSS": True,
                    "EARLY_LE0630": j <= 2,
                    "TRIGGER_0615": j == 1,
                    "TRIGGER_0630": j == 2,
                    "PRE1_UP": ctx["pre1_up"],
                    "PRE4_UP": ctx["pre4_up"],
                    "PRE24_UP": ctx["pre24_up"],
                    "PRE24_DOWN": ctx["pre24_down"],
                    "PRE7D_UP": ctx["pre7d_up"],
                    "PRE7D_DOWN": ctx["pre7d_down"],
                    "ABOVE_DAILY_OPEN": ctx["above_daily_open"],
                    "AFTER_HOD_ATTACK": had_hod_attack,
                    "AFTER_HOD_CLOSE_ABOVE": had_hod_close_above,
                    "AFTER_PREV1H_HIGH_ATTACK": had_prev1h_high_attack,
                    "AFTER_BEAR_REJECTION": had_bear_rejection,
                    "SAMEBAR_BREAKDOWN": breakdown,
                    "SAMEBAR_RANGE_EXP": range_exp,
                    "SAMEBAR_BEAR_REJECTION": bear_rej,
                    "SAMEBAR_HOD_SWEEP": hod_sweep_now,
                    "SAMEBAR_PREV1H_REJECT": prev1h_reject_now,
                    "SAMEBAR_TWO_BEAR": two_bear,
                    "PRE24_UP__EARLY": ctx["pre24_up"] and j <= 2,
                    "PRE7D_UP__EARLY": ctx["pre7d_up"] and j <= 2,
                    "PRE24_UP__AFTER_HOD_ATTACK": ctx["pre24_up"] and had_hod_attack,
                    "PRE24_DOWN__AFTER_HOD_ATTACK": ctx["pre24_down"] and had_hod_attack,
                    "PRE24_UP__SAMEBAR_BREAKDOWN": ctx["pre24_up"] and breakdown,
                    "PRE24_DOWN__SAMEBAR_BREAKDOWN": ctx["pre24_down"] and breakdown,
                    "EARLY__SAMEBAR_BREAKDOWN": j <= 2 and breakdown,
                    "EARLY__SAMEBAR_RANGE_EXP": j <= 2 and range_exp,
                    "HOD_ATTACK__SAMEBAR_BREAKDOWN": had_hod_attack and breakdown,
                }
                entry_i = bi + 1
                if entry_i < len(rows) and int(rows[entry_i][0]) == int(bar[0]) + TF_MS:
                    entry_row = rows[entry_i]
                    trig = _local_dt(int(bar[0]), tz).strftime("%H:%M")
                    for name, ok in rules.items():
                        if not ok or name in fired:
                            continue
                        fired.add(name)
                        for horizon in HORIZONS:
                            hb = H_BARS[horizon]
                            path = rows[entry_i:entry_i + hb]
                            if len(path) != hb:
                                continue
                            if any(int(path[k][0]) != int(entry_row[0]) + k * TF_MS for k in range(hb)):
                                continue
                            events[name][horizon].append(_event(entry_row, path, block, trig))

            had_trade_above_open = had_trade_above_open or f["h"] > window_open
            had_hod_attack = had_hod_attack or f["h"] > ctx["hod"]
            had_hod_close_above = had_hod_close_above or f["c"] > ctx["hod"]
            had_prev1h_high_attack = had_prev1h_high_attack or f["h"] > ctx["prev1h_high"]
            had_bear_rejection = had_bear_rejection or bear_rej
            prev = bar

    candidates = []
    for rule, by_h in events.items():
        for horizon in HORIZONS:
            xs = by_h.get(horizon, [])
            if len(xs) < min_n:
                continue
            m = _metrics(xs, blocks)
            if not m:
                continue
            ft05 = m["first_touch_symmetric_pct"].get("0.5", {})
            ft08 = m["first_touch_symmetric_pct"].get("0.8", {})
            candidates.append({
                "rule": rule,
                "horizon_min": horizon,
                **m,
                "ft05_wr_pct": ft05.get("decisive_wr_pct"),
                "ft05_decisive_n": (ft05.get("favorable", 0) + ft05.get("adverse", 0)),
                "ft08_wr_pct": ft08.get("decisive_wr_pct"),
                "ft08_decisive_n": (ft08.get("favorable", 0) + ft08.get("adverse", 0)),
            })

    directional = sorted(candidates, key=lambda x: (x["wr_pct"] or -1, x["n"], x["positive_blocks_gt50"], x["mfe_mae_ratio"] or -1), reverse=True)
    executable05 = sorted(candidates, key=lambda x: (x["ft05_wr_pct"] or -1, x["ft05_decisive_n"], x["positive_blocks_gt50"], x["n"]), reverse=True)
    executable08 = sorted(candidates, key=lambda x: (x["ft08_wr_pct"] or -1, x["ft08_decisive_n"], x["positive_blocks_gt50"], x["n"]), reverse=True)

    viable70_dir = [x for x in directional if (x["wr_pct"] or 0) >= 70 and x["n"] >= min_n]
    viable70_05 = [x for x in executable05 if (x["ft05_wr_pct"] or 0) >= 70 and x["ft05_decisive_n"] >= min_n]
    viable70_08 = [x for x in executable08 if (x["ft08_wr_pct"] or 0) >= 70 and x["ft08_decisive_n"] >= min_n]

    expected = max(1, int((end_ms - start_ms) / TF_MS))
    return {
        "status": "BTC_TEMPORAL_A2_REFINED_SEQUENCE",
        "data": {"days": days, "rows_15m": len(rows), "expected_rows_15m": expected, "coverage_pct": round(100*len(rows)/expected,2), "tuesday_occurrences": tuesdays},
        "parent": "Tuesday 06-08 SELL + upper-half daily location + OPEN_LOSS + next-15m entry",
        "candidate_count": len(candidates),
        "viable70_directional_count": len(viable70_dir),
        "viable70_ft05_count": len(viable70_05),
        "viable70_ft08_count": len(viable70_08),
        "viable70_directional": viable70_dir[:20],
        "viable70_ft05": viable70_05[:20],
        "viable70_ft08": viable70_08[:20],
        "top_directional": directional[:25],
        "top_ft05": executable05[:25],
        "top_ft08": executable08[:25],
        "notes": [
            "All substates are causal and known before next-15m entry.",
            "Trigger-time refinement was predeclared because A1/A2 explicitly called for entry timing discovery.",
            "0.5% and 0.8% first-touch tables are gross symmetric execution geometry; fees are not yet deducted.",
        ],
    }
